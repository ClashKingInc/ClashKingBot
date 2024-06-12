import disnake

from disnake.ext import commands
from discord import options
from .utils import *


class FamilyCommands(commands.Cog, name="Family Commands"):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="family")
    async def family(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()


    @family.sub_command(name="compo", description="Composition of values in a family")
    async def compo(self, ctx: disnake.ApplicationCommandInteraction,
                         type_: str = commands.Param(name="type", default="Townhall", choices=["Townhall", "Trophies", "Location", "Role", "League"]),
                         server: disnake.Guild = options.optional_family):
        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)
        embed = await family_composition(bot=self.bot, server=server, type=type_, embed_color=embed_color)
        buttons = disnake.ui.ActionRow(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"familycompo:{server.id}:{type_}"))
        await ctx.edit_original_response(embed=embed, components=[buttons])



    @family.sub_command(name="clans", description="Boards showing overview of the family clans in different ways")
    async def clans(self, ctx: disnake.ApplicationCommandInteraction,
                       server: disnake.Guild = options.optional_family,
                       types: str = commands.Param(default="Categories", choices=["Overview", "Categories", "CWL Leagues", "Capital Leagues", "Location", "TH Requirement"])):
        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)
        if types == "Overview":
            embed = await family_overview(bot=self.bot, server=server, embed_color=embed_color)
            button_id = f"familyoverview:{server.id}"
        elif types == "Categories":
            embed = await family_clans(bot=self.bot, server=server, type="db", embed_color=embed_color)
            button_id = f"familyclans:{server.id}:db"
        elif types == "CWL Leagues":
            embed = await family_clans(bot=self.bot, server=server, type="cwl", embed_color=embed_color)
            button_id = f"familyclans:{server.id}:cwl"
        elif types == "Capital Leagues":
            embed = await family_clans(bot=self.bot, server=server, type="capital", embed_color=embed_color)
            button_id = f"familyclans:{server.id}:capital"
        elif types == "Location":
            embed = await family_clans(bot=self.bot, server=server, type="location", embed_color=embed_color)
            button_id = f"familyclans:{server.id}:location"
        elif types == "TH Requirement":
            embed = await family_clans(bot=self.bot, server=server, type="th", embed_color=embed_color)
            button_id = f"familyclans:{server.id}:th"

        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=button_id))
        await ctx.edit_original_response(embed=embed, components=[buttons])


    @family.sub_command(name="stats", description="Boards showing stats by family clan")
    async def stats(self, ctx: disnake.ApplicationCommandInteraction,
                    types: str = commands.Param(choices=["Donations", "Activity", "Trophies", "Versus Trophies", "Capital Trophies"]),
                    server: disnake.Guild = options.optional_family):
        raise MessageException("Command Under Construction")
        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)
        if types == "Donations":
            embed = await family_overview(bot=self.bot, server=server, embed_color=embed_color)
        elif types == "Activity":
            pass
        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"familyoverview:{server.id}"))
        await ctx.edit_original_response(embed=embed, components=[buttons])


    @family.sub_command(name="wars", description="On-going wars in the family")
    async def wars(self, ctx: disnake.ApplicationCommandInteraction,
                    server: disnake.Guild = options.optional_family):
        server = server or ctx.guild

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)
        embed = await family_wars(bot=self.bot, server=server, embed_color=embed_color)

        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"familywars:{server.id}"))
        await ctx.edit_original_response(embed=embed, components=[buttons])


    @family.sub_command(name="raids", description="On-going raids in the family")
    async def raids(self, ctx: disnake.ApplicationCommandInteraction,
                    server: disnake.Guild = options.optional_family):
        server = server or ctx.guild

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)
        embed = await family_raids(bot=self.bot, server=server, weekend=None, embed_color=embed_color)

        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"familyraids:{server.id}:{None}"))
        await ctx.edit_original_response(embed=embed, components=[buttons])


    @family.sub_command(name="progress", description="Progress in various areas for the family")
    async def progress(self, ctx: disnake.ApplicationCommandInteraction,
                       type=commands.Param(choices=["Heroes & Pets", "Troops, Spells, & Sieges"]),
                       season: str = options.optional_season,
                       limit: int = commands.Param(default=50, min_value=1, max_value=50),
                       server: disnake.Guild = options.optional_family):

        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)
        if type == "Heroes & Pets":
            custom_id = f"familyheroprogress:{server.id}:{season}:{limit}"
            embeds = await family_hero_progress(bot=self.bot, server=server, season=season, limit=limit, embed_color=embed_color)
        elif type == "Troops, Spells, & Sieges":
            custom_id = f"familytroopprogress:{server.id}:{season}:{limit}"
            embeds = await family_troop_progress(bot=self.bot, server=server, season=season, limit=limit, embed_color=embed_color)

        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=custom_id),
        )
        await ctx.edit_original_message(embeds=embeds, components=[buttons])


    @family.sub_command(name="summary", description="Summary of stats for a family")
    async def summary(self, ctx: disnake.ApplicationCommandInteraction,
                      season: str = options.optional_season,
                      limit: int = commands.Param(default=5, min_value=1, max_value=15),
                      server: disnake.Guild = options.optional_family
                      ):

        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)
        embeds = await family_summary(bot=self.bot, server=server, limit=limit, season=season, embed_color=embed_color)
        buttons = disnake.ui.ActionRow()
        buttons.add_button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"familysummary:{server.id}:{season}:{limit}")
        await ctx.edit_original_message(embeds=embeds, components=[buttons])


    @family.sub_command(name="sorted", description="List of family members, sorted by any attribute")
    async def sorted(self, ctx: disnake.ApplicationCommandInteraction,
                     sort_by: str = commands.Param(choices=sorted(item_to_name.keys())),
                     townhall: int = None,
                     limit: int = commands.Param(default=50, min_value=1, max_value=50),
                     server: disnake.Guild = options.optional_family
                     ):
        """
            Parameters
            ----------
            sort_by: Sort by any attribute
            limit: change amount of results shown
        """
        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await family_sorted(bot=self.bot, server=server, sort_by=sort_by, limit=limit, townhall=townhall, embed_color=embed_color)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"familysorted:{server.id}:{sort_by}:{limit}:{townhall}"))
        await ctx.edit_original_message(embed=embed, components=[buttons])


    @family.sub_command(name="donations", description="Donation stats for a family")
    async def donations(self, ctx: disnake.ApplicationCommandInteraction,
                        season: str = options.optional_season,
                        townhall: int = None,
                        limit: int = commands.Param(default=50, min_value=1, max_value=50),
                        sort_by: str = commands.Param(default="Donations", choices=["Donations", "Received"]),
                        sort_order: str = commands.Param(default="Descending", choices=["Ascending", "Descending"]),
                        server: disnake.Guild = options.optional_family
                        ):
        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await family_donations(bot=self.bot, server=server, season=season, townhall=townhall, limit=limit, sort_by=sort_by, sort_order=sort_order, embed_color=embed_color)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"familydonos:{server.id}:{season}:{townhall}:{limit}:{sort_by}:{sort_order}"))
        await ctx.edit_original_message(embed=embed, components=[buttons])

    @family.sub_command(name="games", description="Clan Games stats for a family")
    async def games(self, ctx: disnake.ApplicationCommandInteraction,
                    season: str = options.optional_season,
                    limit: int = commands.Param(default=50, min_value=1, max_value=50),
                    sort_by: str = commands.Param(default="Points", choices=["Points", "Time"]),
                    sort_order: str = commands.Param(default="Descending", choices=["Ascending", "Descending"]),
                    server: disnake.Guild = options.optional_family
                    ):
        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        buttons = disnake.ui.ActionRow()
        embed = await family_clan_games(bot=self.bot, server=server, season=season, sort_by=sort_by.lower(), sort_order=sort_order.lower(), limit=limit, embed_color=embed_color)
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"familygames:{server.id}:{season}:{sort_by.lower()}:{sort_order.lower()}:{limit}"))
        await ctx.edit_original_message(embed=embed, components=[buttons])


    @family.sub_command(name="activity", description="Activity related stats for a family - last online, activity")
    async def activity(self, ctx: disnake.ApplicationCommandInteraction,
                       season: str = options.optional_season,
                       limit: int = commands.Param(default=50, min_value=1, max_value=50),
                       sort_by: str = commands.Param(default="Activity", choices=["Activity", "Last Online"]),
                       sort_order: str = commands.Param(default="Descending", choices=["Ascending", "Descending"]),
                       server: disnake.Guild = options.optional_family):
        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await family_activity(bot=self.bot, server=server, limit=limit, season=season,
                                    sort_by=sort_by.lower().replace(" ", ""), sort_order=sort_order, embed_color=embed_color)
        buttons = disnake.ui.ActionRow()
        buttons.add_button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"familyactivity:{server.id}:{season}:{limit}:{sort_by.lower().replace(' ', '')}:{sort_order}")
        await ctx.edit_original_message(embed=embed, components=[buttons])



    @family.sub_command(name="leaderboard", description="Family Image LeaderBoard for Activity, Legends, Trophies, & War Stars!")
    async def image(self, ctx: disnake.ApplicationCommandInteraction,
                    clan: coc.Clan = options.optional_clan,
                    board: str = commands.Param(choices=["Activity", "Legends", "Trophies", "War Stars"]),
                    limit: int = commands.Param(default=30, min_value=5, max_value=50),
                    server: disnake.Guild = options.optional_family
                    ):
        await ctx.response.defer(ephemeral=True)
        if clan is None:
            server = server or ctx.guild
        if board == "Legends":
            file = await image_board(bot=self.bot, clan=clan, server=server, type="legend", limit=limit)
            board_type = "clanboardlegend"

        await ctx.edit_original_message(content="Image Board Created!")

        await ctx.channel.send(content=file, components=[])

def setup(bot):
    bot.add_cog(FamilyCommands(bot))

