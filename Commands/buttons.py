import disnake

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from Commands.board_generation import donation_board, activity_board, games_board


async def basic_parser(bot: CustomClient, result: dict):
    server_result = await bot.server_db.find_one({"server": result.get("server_lookup")})
    result = result | {"tied_only": server_result.get("tied", True)}
    type = result.get("type")
    if result.get("user_id") is not None:
        tags = await bot.get_tags(result.get("user_id"))
        result = result | {"players": tags}
    title, icon = await bot.parse_to_name_icon(as_dict={"user": result.get("user"), "family": result.get("server"), "clan": result.get("clans")})
    del result["button_id"]
    del result["type"]
    del result["user"]
    del result["_id"]
    del result["server_lookup"]
    if type == "donations":
        result = await bot.ck_client.get_donations(as_dict=result)
        embed = donation_board(bot=bot, result=result, title_name=title, footer_icon=icon, embed_color=disnake.Color(server_result.get("embed_color", 0x2ECC71)))
    elif type == "activity":
        result = await bot.ck_client.get_activity(as_dict=result)
        embed = activity_board(bot=bot, result=result, title_name=title, footer_icon=icon, embed_color=disnake.Color(server_result.get("embed_color", 0x2ECC71)))
    elif type == "clan_games":
        result = await bot.ck_client.get_clan_games(as_dict=result)
        embed = games_board(bot=bot, result=result, title_name=title, footer_icon=icon, embed_color=disnake.Color(server_result.get("embed_color", 0x2ECC71)))

    return embed

class Buttons(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        result = await self.bot.button_store.find_one({"button_id" : ctx.data.custom_id})
        if result is None:
            return
        await ctx.response.defer()
        embed = await basic_parser(bot=self.bot, result=result)

        await ctx.edit_original_message(embed=embed)


def setup(bot):
    bot.add_cog(Buttons(bot))
