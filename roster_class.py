import disnake
from utils.clashClient import client, getClan, getPlayer, coc_client
from disnake.ext import commands

usafam = client.usafam
rosters = usafam.rosters

class Roster(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.alias = None
        self.members = None
        self.msg = None
        self.clans = None


    async def get_members(self, ctx):
        executor = ctx.message.author

        embed = disnake.Embed(title="Hello " + executor.display_name + "!",
                              description="First: What is the tag of the clan to link to this roster?",
                              color=disnake.Color.green())
        embed.set_footer(text="Type `cancel` at any point to stop.")
        msg = await ctx.send(embed=embed)
        self.msg = msg

        clan = None
        while clan ==None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor and message.channel == ctx.message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                await msg.edit(embed=embed)
                return None

            clan = await getClan(response)
            if clan is None:
                embed = disnake.Embed(title=f"Sorry {response} is an invalid clan tag. Please try again.",
                                      description=" What is the tag of the clan to link to this roster?", color=disnake.Color.red())
                await msg.edit(embed=embed)
                embed.set_footer(text="Type `cancel` at any point to stop.")
                continue


        members = []
        for player in clan.members:
            members.append(player.tag)
        return [members, clan.tag]

    async def get_alias(self, ctx):
        executor = ctx.message.author
        embed = disnake.Embed(title="**Roster Alias**",
                              description=f"What is the alias/name for this roster?\n"
                              , color=disnake.Color.green())
        await self.msg.edit(embed=embed)
        alias = None
        while alias == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            # print(response)
            response = response.lower()

            results = await rosters.find_one({"$and": [
                {"alias": response},
                {"server": ctx.guild.id}
            ]})

            if results != None:
                embed = disnake.Embed(
                    title=f"Sorry {response} is already an alias for a roster on this server. Please try again.",
                    description="What is the alias for this roster?", color=disnake.Color.red())
                embed.set_footer(text="Type `cancel` at any point to stop.")
                await self.msg.edit(embed=embed)
                continue

            if response == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await self.msg.edit(embed=embed)

            alias = response

        return alias

    async def remove_member(self, alias, guild_id, member):
        change = await rosters.update_one({"$and": [
            {"alias": alias},
            {"server": guild_id}]},
            {'$pull': {'members': member}})


    async def add_member(self, alias, guild_id, member):
        mem_ = await rosters.find_one({"$and": [
            {"alias": alias},
            {"server": guild_id}
        ]})

        member_list = mem_.get("members")
        if member not in member_list:
            mem_ = await rosters.update_one({"$and": [
                {"alias": alias},
                {"server": guild_id}]},
                {'$push': {'members': member}})
            member_list.append(member)

        self.members = member_list
        return self.members

    async def fetch_members(self, alias, guild_id):
        results = await rosters.find_one({"$and": [
            {"alias": alias},
            {"server": guild_id}
        ]})
        return results.get("members")

    async def create_roster_embeds(self, alias, guild_id):
        results = await rosters.find_one({"$and": [
            {"alias": alias},
            {"server": guild_id}
        ]})

        text = ""
        num = 1
        members = results.get("members")
        clan = results.get("clan")
        clan = await getClan(clan)
        player_list = []
        async for player in coc_client.get_players(members):
            p = []
            p.append(player.town_hall)
            p.append(player.name)
            p.append(player.share_link)
            player_list.append(p)

        results = sorted(player_list, key=lambda l: l[0], reverse=True)

        embeds= []
        thcount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for player in results:
            rank = str(num) + "."
            rank = rank.rjust(3)
            th = player[0]
            count = thcount[th - 1]
            thcount[th - 1] = count + 1
            text += f"`\u200e{rank}` `TH{player[0]}`| \u200e{player[1]} \n"
            num+=1
            if num % 50 == 0:
                if embeds == []:
                    embed = discord.Embed(title=f"**{clan.name} Roster**",
                                          description=text,
                                          color=discord.Color.green())
                else:
                    embed = discord.Embed(description=text,
                                          color=discord.Color.green())
                embeds.append(embed)
                text = ""
        if text != "":
            embed = discord.Embed(description=text,
                                  color=discord.Color.green())
            embeds.append(embed)

        stats = ""
        for x in reversed(range(len(thcount))):
            count = thcount[x]
            if count != 0:
                if (x + 1) <= 9:
                    stats += f"TH{x + 1} : {count}\n"
                else:
                    stats += f"TH{x + 1} : {count}\n"

        embeds[-1].set_footer(text=stats)
        return embeds

    async def create_member_list(self, alias, guild_id):
        results = await rosters.find_one({"$and": [
            {"alias": alias},
            {"server": guild_id}
        ]})

        player_list = []
        members = results.get("members")
        async for player in coc_client.get_players(members):
            p = []
            p.append(player.town_hall)
            p.append(player.name)
            p.append(player.share_link)
            player_list.append(p)

        results = sorted(player_list, key=lambda l: l[0], reverse=True)

        text = ""
        num=1
        thcount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for player in results:
            rank = str(num) + "."
            rank = rank.rjust(3)
            th = player[0]
            count = thcount[th - 1]
            thcount[th - 1] = count + 1
            text += f"`\u200e{rank}` `TH{player[0]}`| \u200e{player[1]} \n"
            num += 1

        return text

    async def create_alias_list(self, guild_id):
        tracked = rosters.find({"server": guild_id})
        limit = await rosters.count_documents(filter={"server": guild_id})
        text = ""
        num = 1
        for document in await tracked.to_list(length=limit):
            alias = document.get("alias")
            members = document.get("members")
            clan = document.get("clan")
            clan = await getClan(clan)
            text += f"{num}. `{alias}` | {clan.name} | {len(members)} players\n"
            num+=1

        return text

    async def is_valid_alias(self, alias, guild_id):
        results = await rosters.find_one({"$and": [
            {"alias": alias},
            {"server": guild_id}
        ]})
        return (results != None)

    async def linked_clan(self, alias, guild_id):
        results = await rosters.find_one({"$and": [
            {"alias": alias},
            {"server": guild_id}
        ]})
        clan = results.get("clan")
        clan = await getClan(clan)
        return clan



def setup(bot: commands.Bot):
    bot.add_cog(Roster(bot))