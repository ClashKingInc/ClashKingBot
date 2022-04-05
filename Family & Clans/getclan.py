import disnake
from disnake.ext import commands
from utils.clash import client, getClan, link_client, coc_client
from Dictionaries.emojiDictionary import emojiDictionary
SUPER_TROOPS = ["Super Barbarian", "Super Archer", "Super Giant", "Sneaky Goblin", "Super Wall Breaker", "Rocket Balloon", "Super Wizard", "Inferno Dragon",
                "Super Minion", "Super Valkyrie", "Super Witch", "Ice Hound", "Super Bowler", "Super Dragon"]
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]
usafam = client.usafam
clans = usafam.clans
server = usafam.server

from coc import utils
import coc

import re

class getClans(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.slash_command(name="clan", description="lookup clan by tag or alias")
    async def getclan(self, ctx: disnake.ApplicationCommandInteraction, clan:str):
        """
            Parameters
            ----------
            clan: Search by clan tag, alias, or select an option from the autocomplete
        """
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
                tag = search[1]
                clan = await getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag.")
        
        await ctx.response.defer()
        embed = disnake.Embed(
            description=f"<a:loading:884400064313819146> Fetching clan...",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

        leader = utils.get(clan.members, role=coc.Role.leader)

        if clan.public_war_log:
            warwin = clan.war_wins
            warloss = clan.war_losses
            if warloss == 0:
                warloss = 1
            winstreak = clan.war_win_streak
            winrate = round((warwin/warloss),2)
        else:
            warwin = clan.war_wins
            warloss = "Hidden Log"
            winstreak = clan.war_win_streak
            winrate = "Hidden Log"

        flag = ""
        if str(clan.location) == "International":
            flag = "<a:earth:861321402909327370>"
        else:
            try:
                flag = f":flag_{clan.location.country_code.lower()}:"
            except:
                flag = "🏳️"

        from Boards.leaderboards import clan_glob_dict, clan_country_dict
        ranking = ""
        glob_rank_clan = country_rank_clan = None
        try:
            glob_rank_clan = clan_glob_dict[clan.tag]
        except:
            pass
        try:
            country_rank_clan = clan_country_dict[clan.tag]
        except:
            pass

        if glob_rank_clan is not None:
            ranking += f"<a:earth:861321402909327370> `{glob_rank_clan[0]}` | "
        else:
            ranking += f"<a:earth:861321402909327370> <:status_offline:910938138984206347> | "

        if country_rank_clan is not None:
            if clan.location.name == "International":
                ranking += f"🌍 `{country_rank_clan[0]}`"
            else:
                ranking += f":flag_{country_rank_clan[3].lower()}: `{country_rank_clan[0]}`"
        else:
            if clan.location.name == "International":
                ranking += f"🌍 <:status_offline:910938138984206347>"
            else:
                ranking += f":flag_{clan.location.country_code.lower()}: <:status_offline:910938138984206347>"
        
        embed = disnake.Embed(title=f"**{clan.name}**",description=f"Tag: [{clan.tag}]({clan.share_link})\n"
                              f"Trophies: <:trophy:825563829705637889> {clan.points} | <:vstrophy:944839518824058880> {clan.versus_points}\n"
                              f"Required Trophies: <:trophy:825563829705637889> {clan.required_trophies}\n"
                              f"Location: {flag} {clan.location.name}\n"
                              f"Rankings: {ranking}\n\n"                              
                              f"Leader: {leader.name}\n"
                              f"Level: {clan.level} \n"
                              f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
                              f"CWL: {self.leagueAndTrophies(str(clan.war_league))}{str(clan.war_league)}\n"
                              f"Wars Won: <:warwon:932212939899949176>{warwin}\nWars Lost: <:warlost:932212154164183081>{warloss}\n"
                              f"War Streak: <:warstreak:932212939983847464>{winstreak}\nWinratio: <:winrate:932212939908337705>{winrate}\n\n"
                              f"Description: {clan.description}",
                              color=disnake.Color.green())

        compo = await self.war_th_comps(clan)
        embed.add_field(name="**Townhall Composition:**", value=compo[0], inline=False)
        embed.add_field(name="**Boosted Super Troops:**", value=compo[1], inline=False)

        embed.set_thumbnail(url=clan.badge.large)

        disc = "<:disnake:840749695466864650>"
        emoji = ''.join(filter(str.isdigit, disc))
        emoji = self.bot.get_emoji(int(emoji))
        emoji = disnake.PartialEmoji(name=emoji.name, id=emoji.id)

        rx = "<:redtick:601900691312607242>"
        rx = ''.join(filter(str.isdigit, rx))
        rx = self.bot.get_emoji(int(rx))
        rx = disnake.PartialEmoji(name=rx.name, id=rx.id)

        trophy = "<:trophy:825563829705637889>"
        trophy = ''.join(filter(str.isdigit, trophy))
        trophy = self.bot.get_emoji(int(trophy))
        trophy = disnake.PartialEmoji(name=trophy.name, id=trophy.id)

        clan_e = "<:clan_castle:855688168816377857>"
        clan_e = ''.join(filter(str.isdigit, clan_e))
        clan_e = self.bot.get_emoji(int(clan_e))
        clan_e = disnake.PartialEmoji(name=clan_e.name, id=clan_e.id)

        opt = "<:opt_in:944905885367537685>"
        opt = ''.join(filter(str.isdigit, opt))
        opt = self.bot.get_emoji(int(opt))
        opt = disnake.PartialEmoji(name=opt.name, id=opt.id)

        main = embed
        options = [  # the options in your dropdown
                disnake.SelectOption(label="Clan Overview", emoji=clan_e, value="clan"),
                disnake.SelectOption(label="Linked Players", emoji=emoji, value="link"),
                disnake.SelectOption(label="Unlinked Players", emoji=rx, value="unlink"),
                disnake.SelectOption(label="Players, Sorted: Trophies", emoji=trophy, value="trophies"),
                disnake.SelectOption(label="War Opt Statuses", emoji=opt, value="opt")
            ]

        if clan.public_war_log:
            options.append(disnake.SelectOption(label="Warlog", emoji="ℹ️", value="warlog"))
        select = disnake.ui.Select(
            options=options,
            placeholder="Choose a page",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(embed=embed, components=dropdown)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.values[0] == "link":
                embed = await self.linked_players(ctx, clan)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "unlink":
                embed = await self.unlinked_players(ctx, clan)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "trophies":
                embed = await self.player_trophy_sort(clan)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "clan":
                await res.response.edit_message(embed=main)
            elif res.values[0] == "opt":
                embed = await self.opt_status(clan)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "warlog":
                embed = await self.war_log(clan)
                await res.response.edit_message(embed=embed)

    @getclan.autocomplete("clan")
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

    async def war_th_comps(self, clan: coc.Clan):
        thcount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        stroops = {"Super Barbarian" : 0, "Super Archer": 0, "Super Giant": 0, "Sneaky Goblin": 0, "Super Wall Breaker": 0, "Rocket Balloon": 0, "Super Wizard": 0, "Inferno Dragon": 0,
                "Super Minion": 0, "Super Valkyrie": 0, "Super Witch": 0, "Ice Hound": 0, "Super Bowler": 0, "Super Dragon": 0}

        async for player in clan.get_detailed_members():
            th = player.town_hall
            count = thcount[th - 1]
            thcount[th - 1] = count + 1

            troops = player.troop_cls
            troops = player.troops

            for x in range(len(troops)):
                troop = troops[x]
                if (troop.is_active):
                    try:
                        stroops[troop.name] = stroops[troop.name] + 1
                    except:
                        pass

        stats = ""
        for x in reversed(range(len(thcount))):
            count = thcount[x]
            if count != 0:
                if (x + 1) <= 9:
                    th_emoji = emojiDictionary(x + 1)
                    stats += f"{th_emoji}`{count} `"
                else:
                    th_emoji = emojiDictionary(x + 1)
                    stats += f"{th_emoji}`{count} `"

        stext = ""

        for troop in SUPER_TROOPS:
            nu = stroops[troop]
            if nu != 0:
                stext += f"{emojiDictionary(troop)}`x{nu} `"

        if stext == "":
            stext = "None"

        return [stats, stext]

    async def linked_players(self, ctx, clan):
        gch = "<:greentick:601900670823694357>"
        disc = "<:disnake:840749695466864650>"
        stats = disc + "`Name           ` **disnake**\n"
        y = 0
        tags = []
        links = []
        for player in clan.members:
            tags.append(player.tag)

        links = await link_client.get_links(*tags)
        links = dict(links)
        for player in clan.members:
            link = links[f"{player.tag}"]
            notLinked = (link == None)
            name = player.name
            linkE = gch
            if (notLinked):
                continue

            ol_name = name
            name = re.split("[^A-Za-z0-9!@#$%^&*()+=~:;<>åæ.]", name)
            name = "".join(name)
            name = name[0:15]
            if len(name) <= 2:
                name = ol_name
            for x in range(15 - len(name)):
                name += " "

            member = ""
            if not notLinked:
                y += 1
                member = disnake.utils.get(ctx.guild.members, id=link)
                member = str(member)
                if member == "None":
                    member = ""
            else:
                member = player.tag

            stats += f'\u200e{linkE}`\u200e{name}` \u200e{member}' + "\n"

        if stats == disc + "`Name           ` **disnake**\n":
            stats = "No players linked."
        embed = disnake.Embed(title=f"{clan.name} : {str(y)}/{str(clan.member_count)} linked", description=stats,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return embed


    async def unlinked_players(self, ctx, clan):
        rx = "<:redtick:601900691312607242>"
        disc = "<:disnake:840749695466864650>"
        stats = disc + "`Name           ` **Player Tag**\n"
        y = 0
        tags = []
        links = []
        for player in clan.members:
            tags.append(player.tag)

        links = await link_client.get_links(*tags)
        links = dict(links)
        for player in clan.members:
            link = links[f"{player.tag}"]
            notLinked = (link == None)
            name = player.name
            linkE = rx
            if not notLinked:
                continue

            ol_name = name
            name = re.split("[^A-Za-z0-9!@#$%^&*()+=~:;<>åæ.]", name)
            name = "".join(name)
            name = name[0:15]
            if len(name) <= 2:
                name = ol_name
            for x in range(15 - len(name)):
                name += " "

            member = ""
            if notLinked:
                y+=1
                member = player.tag

            stats += f'\u200e{linkE}`\u200e{name}` \u200e{member}' + "\n"

        if stats == disc + "`Name           ` **disnake**\n":
            stats = "No players unlinked."

        embed = disnake.Embed(title=f"{clan.name} : {str(y)} unlinked", description=stats,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return embed


    async def player_trophy_sort(self, clan):
        text = ""
        x = 0
        for player in clan.members:
            place = str(x + 1) + "."
            place = place.ljust(3)
            text += f"\u200e`{place}` \u200e<:a_cups:667119203744088094> \u200e{player.trophies} - \u200e{player.name}\n"
            x +=1

        embed = disnake.Embed(title=f"{clan.name} Players - Sorted: Trophies", description=text,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return embed


    async def opt_status(self, clan : coc.Clan):
        opted_in = ""
        opted_out = ""
        num_in = 0
        num_out = 0
        async for player in clan.get_detailed_members():
            if player.war_opted_in :
                opted_in += f"<:opt_in:944905885367537685>\u200e{player.name}\n"
                num_in += 1
            else:
                opted_out += f"<:opt_out:944905931265810432>\u200e{player.name}\n"
                num_out += 1

        if opted_in == "":
            opted_in = "None"
        if opted_out == "":
            opted_out = "None"

        embed = disnake.Embed(title=f"**{clan.name} War Opt Statuses**", description=f"**Players Opted In - {num_in}:**\n{opted_in}\n**Players Opted Out - {num_out}:**\n{opted_out}\n",
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return embed

    def leagueAndTrophies(self, league):

        if (league == "Bronze League III"):
            emoji = "<:BronzeLeagueIII:601611929311510528>"
        elif (league == "Bronze League II"):
            emoji = "<:BronzeLeagueII:601611942850986014>"
        elif (league == "Bronze League I"):
            emoji = "<:BronzeLeagueI:601611950228635648>"
        elif (league == "Silver League III"):
            emoji = "<:SilverLeagueIII:601611958067920906>"
        elif (league == "Silver League II"):
            emoji = "<:SilverLeagueII:601611965550428160>"
        elif (league == "Silver League I"):
            emoji = "<:SilverLeagueI:601611974849331222>"
        elif (league == "Gold League III"):
            emoji = "<:GoldLeagueIII:601611988992262144>"
        elif (league == "Gold League II"):
            emoji = "<:GoldLeagueII:601611996290613249>"
        elif (league == "Gold League I"):
            emoji = "<:GoldLeagueI:601612010492526592>"
        elif (league == "Crystal League III"):
            emoji = "<:CrystalLeagueIII:601612021472952330>"
        elif (league == "Crystal League II"):
            emoji = "<:CrystalLeagueII:601612033976434698>"
        elif (league == "Crystal League I"):
            emoji = "<:CrystalLeagueI:601612045359775746>"
        elif (league == "Master League III"):
            emoji = "<:MasterLeagueIII:601612064913621002>"
        elif (league == "Master League II"):
            emoji = "<:MasterLeagueII:601612075474616399>"
        elif (league == "Master League I"):
            emoji = "<:MasterLeagueI:601612085327036436>"
        elif (league == "Champion League III"):
            emoji = "<:ChampionLeagueIII:601612099226959892>"
        elif (league == "Champion League II"):
            emoji = "<:ChampionLeagueII:601612113345249290>"
        elif (league == "Champion League I"):
            emoji = "<:ChampionLeagueI:601612124447440912>"
        elif (league == "Titan League III"):
            emoji = "<:TitanLeagueIII:601612137491726374>"
        elif (league == "Titan League II"):
            emoji = "<:TitanLeagueII:601612148325744640>"
        elif (league == "Titan League I"):
            emoji = "<:TitanLeagueI:601612159327141888>"
        elif (league == "Legend League"):
            emoji = "<:LegendLeague:601612163169255436>"
        else:
            emoji = "<:Unranked:601618883853680653>"

        return emoji

    async def war_log(self, clan: coc.Clan):
        warlog = await coc_client.get_warlog(clan.tag)
        text = ""
        for war in warlog[0:25]:
            if war.is_league_entry:
                continue
            if war.result == "win":
                status = "✅"
            else:
                status = "❌"

            num_hit = SUPER_SCRIPTS[war.attacks_per_member]
            text+= f"{status} {war.clan.name} vs {war.opponent.name} | {war.team_size}{num_hit} ʰᶦᵗ\n"

        if text == "":
            text = "Empty War Log"
        embed = disnake.Embed(title=f"**{clan.name} WarLog (last 25)**",
                              description=text,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return embed



def setup(bot: commands.Bot):
    bot.add_cog(getClans(bot))