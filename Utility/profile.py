import coc
import disnake

from disnake.ext import commands
from Utility.profile_embeds import *
from Assets.emojiDictionary import emojiDictionary
from Utility.pagination import button_pagination
from utils.search import search_results
from utils.troop_methods import heros, heroPets
from Assets.thPicDictionary import thDictionary
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
        elif tag is not None:
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
        if discord_user is None:
            search_query = str(ctx.author.id)
        else:
            search_query = str(discord_user.id)
        await ctx.response.defer()

        results = await search_results(self.bot, search_query)

        if results == []:
            return await ctx.edit_original_message(content="No results were found.")

        text = ""
        total = 0
        sumth = 0

        for player in results:
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
        if hero is None:
            hero = ""
        else:
            hero = f"**Heroes:**\n{hero}\n"

        if pets is None:
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

    @commands.slash_command(name="upgrades", description="Show upgrades needed for an account")
    async def upgrades(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str=None, discord_user:disnake.Member=None):
        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        await ctx.response.defer()
        results = await search_results(self.bot, search_query)
        embed = upgrade_embed(self.bot, results[0])
        components = []
        if len(results) > 1:
            player_results = []
            for count, player in enumerate(results):
                player_results.append(
                    disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,
                                         value=f"{count}"))
            profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)
            st2 = disnake.ui.ActionRow()
            st2.append_item(profile_select)
            components = [st2]
        await ctx.send(embeds=embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                     timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break

            await res.response.defer()
            current_page = int(res.values[0])
            embed = upgrade_embed(self.bot, results[current_page])
            await res.edit_original_message(embeds=embed)




    @invite.autocomplete("player_tag")
    @lookup.autocomplete("tag")
    @upgrades.autocomplete("player_tag")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names


def setup(bot: CustomClient):
    bot.add_cog(profiles(bot))