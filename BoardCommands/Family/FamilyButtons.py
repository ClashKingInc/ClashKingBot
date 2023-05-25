import disnake
import coc
import pytz

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from datetime import datetime
from CustomClasses.Enums import TrophySort
from utils.General import get_clan_member_tags
from typing import TYPE_CHECKING, List

tiz = pytz.utc
if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    from FamilyCog import FamilyCog
    board_cog = BoardCog
    family_cog = FamilyCog
else:
    board_cog = commands.Cog
    family_cog = commands.Cog

class FamilyButtons(family_cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.graph_cog = None

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        time = datetime.now().timestamp()
        if "donationfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            self.graph_cog = self.bot.get_cog("Graphing")
            split = str(ctx.data.custom_id).split("_")
            season = split[1]
            limit = int(split[2])
            guild_id = split[3]
            townhall = split[4]
            if townhall != "None":
                townhall = [int(townhall)]
            else:
                townhall = list(range(2, 17))
            guild = await self.bot.getch_guild(guild_id)
            if season == "None":
                season = self.bot.gen_raid_date()

            clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
            clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            member_tags = get_clan_member_tags(clans=clans)
            distinct = await self.bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
            players = await self.bot.get_players(tags=distinct)
            footer_icon = ctx.guild.icon.url if ctx.guild.icon is not None else self.bot.user.avatar.url
            embed = await self.board_cog.donation_board(
                players=[player for player in players if player.town_hall in townhall], season=season,
                footer_icon=footer_icon, title_name=f"{guild.name}", type="donations", limit=limit)

            graph = await self.graph_cog.create_clan_donation_graph(all_players=players, clans=clans, season=season,
                                                                    type="donations", server_id=guild.id)
            embed.set_image(url=f"{graph}?{int(datetime.now().timestamp())}")
            await ctx.edit_original_message(embed=embed)

        elif "receivedfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            self.graph_cog = self.bot.get_cog("Graphing")
            split = str(ctx.data.custom_id).split("_")
            season = split[1]
            limit = int(split[2])
            guild_id = split[3]
            townhall = split[4]
            if townhall != "None":
                townhall = [int(townhall)]
            else:
                townhall = list(range(2, 17))
            guild = await self.bot.getch_guild(guild_id)
            if season == "None":
                season = self.bot.gen_raid_date()

            clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
            clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            member_tags = get_clan_member_tags(clans=clans)
            distinct = await self.bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
            players = await self.bot.get_players(tags=distinct)
            footer_icon = ctx.guild.icon.url if ctx.guild.icon is not None else self.bot.user.avatar.url
            embed = await self.board_cog.donation_board(
                players=[player for player in players if player.town_hall in townhall], season=season,
                footer_icon=footer_icon, title_name=f"{guild.name}", type="received", limit=limit)

            graph = await self.graph_cog.create_clan_donation_graph(all_players=players, clans=clans, season=season,
                                                                    type="received", server_id=guild.id)
            embed.set_image(url=f"{graph}?{int(datetime.now().timestamp())}")
            await ctx.edit_original_message(embed=embed)

        elif "ratiofam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            self.graph_cog = self.bot.get_cog("Graphing")
            split = str(ctx.data.custom_id).split("_")
            season = split[1]
            limit = int(split[2])
            guild_id = split[3]
            townhall = split[4]
            if townhall != "None":
                townhall = [int(townhall)]
            else:
                townhall = list(range(2, 17))
            guild = await self.bot.getch_guild(guild_id)
            if season == "None":
                season = self.bot.gen_raid_date()

            clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
            clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            member_tags = get_clan_member_tags(clans=clans)
            distinct = await self.bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
            players = await self.bot.get_players(tags=distinct)
            footer_icon = ctx.guild.icon.url if ctx.guild.icon is not None else self.bot.user.avatar.url
            embed = await self.board_cog.donation_board(
                players=[player for player in players if player.town_hall in townhall], season=season,
                footer_icon=footer_icon, title_name=f"{guild.name}", type="ratio", limit=limit)
            await ctx.edit_original_message(embed=embed)

        elif "lastonlinefam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_last_online(ctx.guild)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "activitiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_activities(ctx.guild)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "summaryfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            time = datetime.now()
            embeds = await self.create_summary(guild=ctx.guild, season=self.bot.gen_season_date())
            embeds[-1].timestamp = time
            embeds[-1].set_footer(text="Last Refreshed:")
            await ctx.edit_original_message(embeds=embeds)

        elif "cwlleaguesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_leagues(guild=ctx.guild, type="CWL")
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji,
                                  style=disnake.ButtonStyle.green,
                                  custom_id=f"cwlleaguesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.grey, custom_id=f"capitalleaguesfam_"))

            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "capitalleaguesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_leagues(guild=ctx.guild, type="Capital")
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"cwlleaguesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green, custom_id=f"capitalleaguesfam_"))

            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "raidsfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_raids(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "clangamesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_clan_games(guild=ctx.guild)
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "joinhistoryfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_joinhistory(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "warsfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_wars(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "hometrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.home
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "versustrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.versus
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "capitaltrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.capital
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "famcapd_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            self.graph_cog = self.bot.get_cog("Graphing")
            split = str(ctx.data.custom_id).split("_")
            week = split[1]
            limit = int(split[2])
            guild_id = split[3]
            townhall = split[4]
            if townhall != "None":
                townhall = [int(townhall)]
            else:
                townhall = list(range(2, 17))
            guild = await self.bot.getch_guild(guild_id)
            if week == "None":
                week = self.bot.gen_raid_date()

            clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
            clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            member_tags = get_clan_member_tags(clans=clans)
            distinct = await self.bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
            players = await self.bot.get_players(tags=distinct)
            embed: disnake.Embed = await self.board_cog.capital_donation_board(players=[player for player in players if player.town_hall in townhall], week=week,
                                                                               title_name=f"{guild.name} Top",
                                                                               footer_icon=guild.icon.url if guild.icon is not None else None,
                                                                               limit=limit)

            graph = await self.graph_cog.create_capital_graph(all_players=players, clans=clans, week=week,
                                                              type="donations", server_id=guild.id)
            embed.set_image(url=f"{graph}?{int(datetime.now().timestamp())}")
            await ctx.edit_original_message(embed=embed)

        elif "famcapr_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            self.graph_cog = self.bot.get_cog("Graphing")
            split = str(ctx.data.custom_id).split("_")
            week = split[1]
            limit = int(split[2])
            guild_id = split[3]
            townhall = split[4]
            if townhall != "None":
                townhall = [int(townhall)]
            else:
                townhall = list(range(2, 17))
            guild = await self.bot.getch_guild(guild_id)
            if week == "None":
                week = self.bot.gen_raid_date()

            clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
            clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            member_tags = get_clan_member_tags(clans=clans)
            distinct = await self.bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
            players = await self.bot.get_players(tags=distinct)
            embed: disnake.Embed = await self.board_cog.capital_raided_board(
                players=[player for player in players if player.town_hall in townhall], week=week,
                title_name=f"{guild.name} Top",
                footer_icon=guild.icon.url if guild.icon is not None else None,
                limit=limit)

            graph = await self.graph_cog.create_capital_graph(all_players=players, clans=clans, week=week,
                                                              type="raided", server_id=guild.id)
            embed.set_image(url=f"{graph}?{int(datetime.now().timestamp())}")
            await ctx.edit_original_message(embed=embed)
