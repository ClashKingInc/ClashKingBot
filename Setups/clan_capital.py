
from disnake.ext import commands
from utils.clash import getPlayer, client, pingToChannel, player_handle, coc_client, getClan
import disnake
import coc


usafam = client.usafam
banlist = usafam.banlist
server = usafam.server
clans = usafam.clans
clancapital = usafam.clancapital


class clan_capital_log(commands.Cog, name="Clan Capital Log"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        coc_client.add_events(self.foo3)

    @coc.PlayerEvents.achievement_change()
    async def foo3(self, old_player: coc.Player, new_player:coc.Player, achievement:coc.Achievement):
        if achievement.name == "Most Valuable Clanmate" or achievement.name == "Aggressive Capitalism":
            #print(achievement.name)
            bot = self.bot

            old_ach = old_player.achievement_cls
            new_ach = new_player.achievement_cls

            old_capital_dono = old_player.get_achievement("Most Valuable Clanmate")
            new_capital_dono = new_player.get_achievement("Most Valuable Clanmate")

            old_raid = old_player.get_achievement("Aggressive Capitalism")
            new_raid = new_player.get_achievement("Aggressive Capitalism")

            clan = new_player.clan
            if clan is None:
                return

            if old_capital_dono.value != new_capital_dono.value and achievement.name == "Most Valuable Clanmate":
                #print(f"{new_player.name} donated {new_capital_dono.value - old_capital_dono.value}")
                tracked = clans.find({"tag": f"{clan.tag}"})
                limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
                for cc in await tracked.to_list(length=limit):
                    server = cc.get("server")
                    try:
                        server = await bot.fetch_guild(server)
                    except:
                        continue
                    clancapital_channel = cc.get("clan_capital")
                    if clancapital_channel is None:
                        continue

                    try:
                        clancapital_channel = await server.fetch_channel(clancapital_channel)
                        if clancapital_channel is None:
                            continue
                    except:
                        continue

                    embed = disnake.Embed(
                        description=f"[**{new_player.name}**]({new_player.share_link}) donated <:capitalgold:987861320286216223>{new_capital_dono.value - old_capital_dono.value}"
                        , color=disnake.Color.green())

                    embed.set_footer(icon_url=clan.badge.url, text=clan.name)

                    try:
                        await clancapital_channel.send(embed=embed)
                    except:
                        continue

            if old_raid.value != new_raid.value and achievement.name == "Aggressive Capitalism":
                #print(f"{new_player.name} | {new_raid.value - old_raid.value}")
                results = await clancapital.find_one({"tag": new_player.tag})
                if results is None:
                    await clancapital.insert_one({
                        "tag": new_player.tag,
                        "raids": [new_raid.value - old_raid.value],
                        "clan" : new_player.clan.tag
                    })
                else:
                    await clancapital.update_one({"tag": new_player.tag}, {'$push': {
                        "raids": new_raid.value - old_raid.value,
                    }})
                    await clancapital.update_one({"tag": new_player.tag}, {'$set': {
                        "clan" : new_player.clan.tag,
                    }})

                tracked = clans.find({"tag": f"{clan.tag}"})
                limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
                for cc in await tracked.to_list(length=limit):
                    server = cc.get("server")
                    try:
                        server = await bot.fetch_guild(server)
                    except:
                        continue
                    clancapital_channel = cc.get("clan_capital")
                    if clancapital_channel is None:
                        continue

                    try:
                        clancapital_channel = await server.fetch_channel(clancapital_channel)
                        if clancapital_channel is None:
                            continue
                    except:
                        continue

                    embed = disnake.Embed(
                        description=f"[**{new_player.name}**]({new_player.share_link}) raided for <:capitalgold:987861320286216223>{new_raid.value - old_raid.value}"
                        , color=disnake.Color.green())

                    embed.set_footer(icon_url=clan.badge.url, text=clan.name)
                    try:
                        await clancapital_channel.send(embed=embed)
                    except:
                        continue

    @commands.slash_command(name="raids", description="See number of clan capital raids completed by people in your clan.")
    async def raid_lb(self, ctx, clan):
        clan_search = clan.lower()
        first_clan = clan
        results = await clans.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                try:
                    tag = search[4]
                except:
                    tag = search[1]
                clan = await getClan(tag)

        if clan is None or clan.member_count == 0:
            return await ctx.send("Not a valid clan tag.")

        mem_tags = []
        tag_to_name = {}
        for mem in clan.members:
            mem_tags.append(mem.tag)
            tag_to_name[mem.tag] = mem.name

        results = clancapital.find({"clan": clan.tag})
        limit = await clancapital.count_documents(filter={"clan": clan.tag})
        if limit == 0:
            return await ctx.send("No raids tracked or found.")
        clan_tot_sum = 0
        clan_tot_len = 0
        rankings = []
        for document in await results.to_list(length=limit):
            don = document.get("raids")
            tag = document.get("tag")
            sum_raids = sum(don)
            num_raids = len(don)
            clan_tot_sum += sum_raids
            clan_tot_len += num_raids
            sum_raids_text = str(sum_raids)
            sum_raids_text = sum_raids_text.ljust(5, " ")
            try:
                text = f"<:capitalgold:987861320286216223>`{sum_raids_text}` `{num_raids}/6` {tag_to_name[tag]} \n"
                mem_tags.remove(tag)
            except:
                player = await getPlayer(tag)
                text = f"<:capitalgold:987861320286216223>`{sum_raids_text}` `{num_raids}/6` {player.name} \n"
            rankings.append([sum_raids, text])


        ranking = sorted(rankings, key=lambda l: l[0], reverse=True)

        text = "**Cap Gold | # | Name**\n"
        for r in ranking:
            text += r[1]

        embed = disnake.Embed(title=f"**{clan.name} Raid Leaderboard**",
            description=text
            , color=disnake.Color.green())
        #embed.set_thumbnail(url=clan.badge.url)
        embed.set_footer(icon_url=clan.badge.url, text=f"{limit}/50 Raiders | {clan_tot_len}/300 atk | {clan_tot_sum} gold")
        await ctx.send(embed=embed)


    @raid_lb.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]




def setup(bot: commands.Bot):
    bot.add_cog(clan_capital_log(bot))