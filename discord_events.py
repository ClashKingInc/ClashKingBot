
from disnake.ext import commands
import disnake
from Dictionaries.thPicDictionary import thDictionary
from utils.troop_methods import heros, heroPets
from utils.clash import getPlayer, client, coc_client

usafam = client.usafam
server = usafam.server
clans = usafam.clans

class DiscordEvents(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        len_g = len(self.bot.guilds)
        await self.bot.change_presence(
            activity=disnake.Activity(name=f'{len_g} servers', type=3))  # type 3 watching type#1 - playing

        tags = []
        tracked = clans.find()
        limit = await clans.count_documents(filter={})

        for tClan in await tracked.to_list(length=limit):
            tag = tClan.get("tag")
            tags.append(tag)

        coc_client.add_clan_updates(*tags)

        for g in self.bot.guilds:
            results = await server.find_one({"server": g.id})
            if results is None:
                await server.insert_one({
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
            player = await getPlayer(tag)

            clan = ""
            try:
                clan = player.clan.name
                clan = f"{clan}"
            except:
                clan = "None"
            hero = heros(player)
            pets = heroPets(player)
            if hero == None:
                hero = ""
            else:
                hero = f"**Heroes:**\n{hero}\n"

            if pets == None:
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
        results = await server.find_one({"server": guild.id})
        if results is None:
            await server.insert_one({
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
        await guild.leave()

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
        server = ctx.guild.name
        user = ctx.author
        command = ctx.data.name
        embed = disnake.Embed(
            description=f"**{command} {ctx.filled_options}** \nused by {user.mention} [{user.name}] in {server} server",
            color=disnake.Color.blue())
        embed.set_thumbnail(url=user.display_avatar.url)
        await channel.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(DiscordEvents(bot))