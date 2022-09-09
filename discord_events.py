
from disnake.ext import commands
import disnake
from Dictionaries.thPicDictionary import thDictionary
from utils.troop_methods import heros, heroPets

import requests

link_open=[]
import urllib.parse
from CustomClasses.CustomBot import CustomClient

class DiscordEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        len_g = len(self.bot.guilds)
        await self.bot.change_presence(
            activity=disnake.Activity(name=f'{len_g} servers', type=3))  # type 3 watching type#1 - playing

        '''
        print("back")
        tags = []
        tracked = self.bot.clan_db.find()
        limit = await self.bot.clan_db.count_documents(filter={})

        for tClan in await tracked.to_list(length=limit):
            tag = tClan.get("tag")
            tags.append(tag)

        self.bot.coc_client.add_clan_updates(*tags)

        print("here")
        tags = []
        tracked = self.bot.clan_db.find({"clan_capital" : {"$ne": None}})
        limit = await self.bot.clan_db.count_documents(filter={"clan_capital" : {"$ne": None}})
        for tClan in await tracked.to_list(length=limit):
            tag = tClan.get("tag")
            tags.append(tag)

        print(len(tags))
        player_tags = []
        async for clan in self.bot.coc_client.get_clans(tags=tags):
            for member in clan.members:
                player_tags.append(member.tag)
        self.bot.coc_client.add_player_updates(*player_tags)
        '''

        for g in self.bot.guilds:
            results = await self.bot.server_db.find_one({"server": g.id})
            if results is None:
                await self.bot.server_db.insert_one({
                    "server": g.id,
                    "prefix": ".",
                    "banlist": None,
                    "greeting": None,
                    "cwlcount": None,
                    "topboardchannel": None,
                    "tophour": None,
                    "lbboardChannel": None,
                    "lbhour": None
                })


        print(f'We have logged in')

    @commands.Cog.listener()
    async def on_message(self, message : disnake.Message):
        if "https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=" in message.content:
            m = message.content.replace("\n", " ")
            spots = m.split(" ")
            s = ""
            for spot in spots:
                if "https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=" in spot:
                    s = spot
                    break
            tag = s.replace("https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=", "")
            if "%23" in tag:
                tag = tag.replace("%23", "")
            player = await self.bot.getPlayer(tag)

            clan = ""
            try:
                clan = player.clan.name
                clan = f"{clan}"
            except:
                clan = "None"
            hero = heros(player)
            pets = heroPets(player)
            if hero is None:
                hero = ""
            else:
                hero = f"**Heroes:**\n{hero}\n"

            if pets is None:
                pets = ""
            else:
                pets = f"**Pets:**\n{pets}\n"

            embed = disnake.Embed(title=f"Invite {player.name} to your clan:",
                                  description=f"{player.name} - TH{player.town_hall}\n" +
                                              f"Tag: {player.tag}\n" +
                                              f"Clan: {clan}\n" +
                                              f"Trophies: {player.trophies}\n"
                                              f"War Stars: {player.war_stars}\n"
                                              f"{hero}{pets}"
                                              f'[View Stats](https://www.clashofstats.com/players/{player.tag}) | [Open in Game]({player.share_link})',
                                  color=disnake.Color.green())
            embed.set_thumbnail(url=thDictionary(player.town_hall))

            channel = message.channel
            await channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_join(self, guild:disnake.Guild):
        results = await self.bot.server_db.find_one({"server": guild.id})
        if results is None:
            await self.bot.server_db.insert_one({
                "server": guild.id,
                "prefix": ".",
                "banlist": None,
                "greeting": None,
                "cwlcount": None,
                "topboardchannel": None,
                "tophour": None,
                "lbboardChannel": None,
                "lbhour": None
            })
        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just joined {guild.name}")
        owner = guild.owner
        len_g = len(self.bot.guilds)
        await self.bot.change_presence(
            activity=disnake.Activity(name=f'{len_g} servers', type=3))  # type 3 watching type#1 - playing
        channel = self.bot.get_channel(937528942661877851)
        await channel.edit(name=f"ClashKing: {len_g} Servers")


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just left {guild.name}, {guild.member_count} members")
        len_g = len(self.bot.guilds)
        await self.bot.change_presence(
            activity=disnake.Activity(name=f'{len_g} servers', type=3))  # type 3 watching type#1 - playing
        channel = self.bot.get_channel(937528942661877851)
        await channel.edit(name=f"ClashKing: {len_g} Servers")


    @commands.Cog.listener()
    async def on_application_command(self, ctx:disnake.ApplicationCommandInteraction):
        channel = self.bot.get_channel(960972432993304616)
        try:
            server = ctx.guild.name
        except:
            server = "None"

        user = ctx.author
        command = ctx.application_command
        embed = disnake.Embed(
            description=f"</{command.qualified_name}:{ctx.data.id}> **{ctx.filled_options}** \nused by {user.mention} [{user.name}] in {server} server",
            color=disnake.Color.blue())
        embed.set_thumbnail(url=user.display_avatar.url)
        await channel.send(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(DiscordEvents(bot))