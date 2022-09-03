from disnake.ext import commands
import disnake
from Dictionaries.emojiDictionary import emojiDictionary
from Utility.pagination import button_pagination
from utils.search import search_results
from utils.troop_methods import heros, heroPets
from Dictionaries.thPicDictionary import thDictionary
from CustomClasses.CustomBot import CustomClient

class profiles(commands.Cog, name="Profile"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="lookup", description="Lookup players or discord users")
    async def lookup(self, ctx: disnake.ApplicationCommandInteraction, tag: str=None, discord_user:disnake.Member=None):
        """
            Parameters
            ----------
            tag: (optional) tag to lookup
            discord_user: (optional) discord user to lookup
        """
        search_query = None
        if tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif tag != None:
            search_query = tag
        else:
            search_query = str(discord_user.id)

        await ctx.response.defer()
        results = await search_results(self.bot, search_query)

        if results == []:
            return await ctx.edit_original_message(content="No results were found.", embed=None)
        msg = await ctx.original_message()

        await button_pagination(self.bot, ctx, msg, results)


    @commands.slash_command(name="list", description="List of accounts a user has & average th compo")
    async def list(self, ctx: disnake.ApplicationCommandInteraction, discord_user:disnake.Member=None):
        if discord_user == None:
            search_query = str(ctx.author.id)
        else:
            search_query = str(discord_user.id)
        await ctx.response.defer()

        results = await self.bot.search_results(search_query)

        if results == []:
            return await ctx.edit_original_message(content="No results were found.")

        text = ""
        total = 0
        sumth = 0

        async for player in self.bot.coc_client.get_players(results):
            emoji = emojiDictionary(player.town_hall)
            th = player.town_hall
            sumth += th
            total += 1
            text += f"{emoji} {player.name}\n"

        average = round((sumth / total), 2)
        embed = disnake.Embed(
            description=text,
            color=disnake.Color.green())

        embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
        await ctx.edit_original_message(embed=embed)


    @commands.slash_command(name="invite", description="Embed with basic info & link for a player to be invited")
    async def invite(self, ctx, player_tag):
        player = await self.bot.getPlayer(player_tag)
        if player is None:
            return await ctx.send("Not a valid playerTag.")

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

        tag = player.tag.strip("#")
        embed = disnake.Embed(title=f"Invite {player.name} to your clan:",
                              description=f"{player.name} - TH{player.town_hall}\n" +
                                          f"Tag: {player.tag}\n" +
                                          f"Clan: {clan}\n" +
                                          f"Trophies: {player.trophies}\n"
                                          f"War Stars: {player.war_stars}\n"
                                          f"{hero}{pets}"
                                          f'[View Stats](https://www.clashofstats.com/players/{tag}) | [Open in Game]({player.share_link})',
                              color=disnake.Color.green())
        if player.town_hall > 4:
            embed.set_thumbnail(url=thDictionary(player.town_hall))

        await ctx.send(embed=embed)

def setup(bot: CustomClient):
    bot.add_cog(profiles(bot))