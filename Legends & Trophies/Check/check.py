
import disnake
from disnake.ext import commands

from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient


class Legends(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="check")
    async def check(self, ctx):
        pass

    @check.sub_command(name="search", description="Search by player tag or name to find a player")
    async def check_search(self, ctx: disnake.ApplicationCommandInteraction, smart_search):
        """
            Parameters
            ----------
            smart_search: Type a search, pick an option, or don't to get multiple results back
        """
        await ctx.response.defer()

        tag = self.bot.parse_legend_search(smart_search)
        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Fetching Stats. | Searches of 10+ players may take a few seconds.",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)
        msg = await ctx.original_message()
        await self.legends(ctx=ctx, msg=msg, search_query=tag, ez_look=True)

    @check_search.autocomplete("smart_search")
    async def autocomp_names(self, ctx: disnake.ApplicationCommandInteraction, user_input: str):
        results = await self.bot.search_name_with_tag(user_input)
        return results

    @check.sub_command(name="user",
                       description="Check a discord user's linked accounts (empty for your own)")
    async def check_user(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member = None):
        """
            Parameters
            ----------
            discord_user: Search by @discordUser
        """

        if discord_user is None:
            discord_user = str(ctx.author.id)
        else:
            discord_user = str(discord_user.id)

        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Fetching Stats. | Searches of 10+ players may take a few seconds.",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)
        msg = await ctx.original_message()
        await self.legends(ctx=ctx, msg=msg, search_query=discord_user, ez_look=True)



    async def legends(self, ctx, msg, search_query, ez_look):
        results = await self.bot.search_results(search_query)

        #track for them if not found
        if results == []:
            player: MyCustomPlayer = await self.bot.getPlayer(search_query, custom=True)
            if player is None:
                embed = disnake.Embed(
                    description="**No results found.** \nCommands:\nUse `/track add #playerTag` to track an account.",
                    color=disnake.Color.red())
                return await msg.edit(content=None, embed=embed)
            await player.track()
            embed = disnake.Embed(
                description=f"{player.name} now tracked. View stats with `/check search {player.tag}`.\n**Note:** Legends stats aren't given, so they have to be collected as they happen. Stats will appear from now & forward :)",
                color=disnake.Color.green())
            return await msg.edit(content=None, embed=embed)


        pagination = self.bot.get_cog("Pagination")
        await pagination.button_pagination(msg, results, ez_look, ctx)




def setup(bot: CustomClient):
    bot.add_cog(Legends(bot))