import disnake
import coc
import excel2img

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from Exceptions.CustomExceptions import ExportTemplateAlreadyExists
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ExportsCog import ExportCog
    cog_class = ExportCog
else:
    cog_class = commands.Cog


class ExportCommands(cog_class):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.DEFAULT_EXPORT_TYPES = ["Legend Stats"]
        self.EXPORT_LABELS = ["legend_stats"]

    async def clan_converter(self, clan: str):
        clan = await self.bot.getClan(clan_tag=clan, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan


    @commands.slash_command(name="export")
    async def export(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

    @export.sub_command(name="template", description="Upload a template")
    async def export_template(self, ctx: disnake.ApplicationCommandInteraction, name:str, excel_template: disnake.Attachment):
        template = await self.bot.excel_templates.find_one({"$and": [{"server_id": ctx.guild.id}, {"export_name": name}]})
        if template is not None:
            raise ExportTemplateAlreadyExists
        await self.bot.excel_templates.insert_one({"server_id" : ctx.guild_id,
                                                   "export_name" : name,
                                                   "path" : f"TemplateStorage/{excel_template.id}.xlsx"})
        await excel_template.save(f"TemplateStorage/{excel_template.id}.xlsx")
        embed = disnake.Embed(description=f"{name} Export Template Successfully Saved!", color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

    @export.sub_command(name="clan", description="Export info for members in a clan")
    async def export_clan(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), type: str = commands.Param(name="type")):
        if type in self.DEFAULT_EXPORT_TYPES:
            template = type
        else:
            file_path = await self.bot.excel_templates.find_one({"$and": [{"server_id": ctx.guild.id}, {"export_name": type}]})
            template = file_path.get("path")
        xlsx_data = await self.export_manager(player_tags=[member.tag for member in clan.members], season=None, template=template)
        file = disnake.File(fp=xlsx_data, filename=f"{clan.name}-{type}.xlsx")
        await ctx.send(file=file)

    @export.sub_command(name="player", description="Export info for a player")
    async def export_player(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str, type=commands.Param(choices=["Legend Stats"])):
        xlsx_data = await self.create_legend_export(player_tags=[player_tag], season=None, template=None)
        file = disnake.File(fp=xlsx_data, filename="test.xlsx")
        await ctx.send(file=file)

    @export_clan.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id}).sort("name", 1)
        clan_list = []
        for tClan in await tracked.to_list(length=100):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=5)
                for clan in results:
                    league = str(clan.war_league).replace("League ", "")
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]

    @export_clan.autocomplete("type")
    async def autocomp_exports(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        aliases = await self.bot.excel_templates.distinct("export_name", filter={"server_id": ctx.guild.id})
        aliases += self.DEFAULT_EXPORT_TYPES
        return [f"{alias}" for alias in aliases if query.lower() in alias.lower()][:25]