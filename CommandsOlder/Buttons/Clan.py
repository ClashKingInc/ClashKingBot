import calendar
import coc
import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from BoardCommands.Utils import Clan as clan_embeds
from Utils.components import clan_board_components
from Utils.discord_utils import interaction_handler

class ClanButtons(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if ctx.data.custom_id.startswith("00"):
            split = ctx.data.custom_id.split("_")
            type = split[1]
            if type == "FREEZE":
                await ctx.response.defer()
                components = ctx.message.components[1].to_dict()
                custom_id = components.get("components")[0].get("custom_id")
                buttons = disnake.ui.ActionRow()
                buttons.append_item(disnake.ui.Button(
                    label="", emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey, custom_id=custom_id))
                await ctx.edit_original_message(components=[buttons])
            elif type == "PIN":
                await ctx.response.defer()
                await ctx.edit_original_message(components=[])
            elif type == "SEASON":
                await ctx.response.defer(ephemeral=True)
                seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
                season_select = []
                for season in seasons:
                    season_select.append(disnake.SelectOption(label=f"{season}", emoji=self.bot.emoji.calendar.partial_emoji, value=f"{season}"))
                season_select = disnake.ui.Select(options=season_select, placeholder="Select a Season", max_values=1)
                msg = await ctx.followup.send(components=[disnake.ui.ActionRow(season_select)], ephemeral=True)
                res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, msg=msg)
                await res.delete_original_response()
                season = res.values[0]
                month = list(calendar.month_name).index(season.split(" ")[0])
                year = season.split(" ")[1]
                end_date = coc.utils.get_season_end(month=int(month - 1), year=int(year))
                month = end_date.month
                if month <= 9:
                    month = f"0{month}"
                season = f"{end_date.year}-{month}"
                components = ctx.message.components[1].to_dict()
                custom_id = components.get("components")[-1].get("custom_id")
                split = custom_id.split("_")
                type = split[2]
                clan_tag = split[4]

                db_clan = await self.bot.get_stat_clan(clan_tag=clan_tag)
                embeds = await clan_embeds.type_to_board(bot=self.bot, db_clan=db_clan, type=type, season=season,
                                                         guild=ctx.guild)
                components = clan_board_components(bot=self.bot, season=season, clan_tag=clan_tag, type=type)
                await ctx.edit_original_message(embeds=embeds, components=components)
            else:
                await ctx.response.defer()
                season = None if split[2] == "None" else split[2]
                clan_tag = split[3]
                db_clan = await self.bot.get_stat_clan(clan_tag=clan_tag)
                embeds = await clan_embeds.type_to_board(bot=self.bot, db_clan=db_clan, type=type, season=season,
                                                        guild=ctx.guild)
                await ctx.edit_original_message(embeds=embeds)

    @commands.Cog.listener()
    async def on_dropdown(self, ctx: disnake.MessageInteraction):
        if ctx.values[0].startswith("00"):
            await ctx.response.defer()
            split = ctx.values[0].split("_")
            type = split[1]
            season = None if split[2] == "None" else split[2]
            clan_tag = split[3]
            db_clan = await self.bot.get_stat_clan(clan_tag=clan_tag)
            embeds = await clan_embeds.type_to_board(bot=self.bot, db_clan=db_clan, type=type, season=season, guild=ctx.guild)
            components = clan_board_components(bot=self.bot, season=season, clan_tag=clan_tag, type=type)
            await ctx.edit_original_message(embeds=embeds, components=components)



def setup(bot):
    bot.add_cog(ClanButtons(bot))

