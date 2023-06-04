import coc
import disnake
import pytz
import calendar

from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from typing import TYPE_CHECKING, List
from ImageGen import ClanCapitalResult as capital_gen

tiz = pytz.utc

from utils.constants import item_to_name
from disnake.ext.commands import Converter
from BoardCommands.Utils import Clan as clan_embeds
from BoardCommands.Utils import Shared as shared_embeds

class ClanCommands(commands.Cog, name="Clan Commands"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan: str):
        clan = await self.bot.getClan(clan_tag=clan, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan


    async def season_convertor(self, season: str):
        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(month=int(month - 1), year=int(year))
            month = end_date.month
            if month <= 9:
                month = f"0{month}"
            season_date = f"{end_date.year}-{month}"
        else:
            season_date = self.bot.gen_season_date()
        return season_date


    @commands.slash_command(name="clan")
    async def clan(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user" : ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        await ctx.response.defer(ephemeral=ephemeral)

    @clan.sub_command(name="search", description="look up a clan by tag")
    async def search(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                     simple: str = commands.Param(default=False, choices=["True"]),
                     button_text: str = None, button_link: str = None, image: disnake.Attachment = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            simple: A smaller, more concise embed
            button_text: can add an extra button to this board, this is the text for it
            button_link:can add an extra button to this board, this is the link for it
            image: image to add to embed
        """
        if not simple:
            embed = await clan_embeds.clan_overview(clan=clan, bot=self.bot, guild=ctx.guild)
        else:
            embed = await clan_embeds.simple_clan_embed(bot=self.bot, clan=clan)

        file = None
        if image is not None:
            file = image.id
            await image.save(f"TemplateStorage/{image.id}.png")
            embed.set_image(file=disnake.File(f"TemplateStorage/{image.id}.png"))

        page_buttons = [
            disnake.ui.Button(label="", emoji=self.bot.partial_emoji_gen((await self.bot.create_new_badge_emoji(url=clan.badge.url))),
                              style=disnake.ButtonStyle.grey,
                              custom_id=f"clanoverview_{clan.tag}_{simple}_{file}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.thick_sword.partial_emoji,
                              style=disnake.ButtonStyle.grey,
                              custom_id=f"clanwarcwlhist_{clan.tag}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.discord.partial_emoji,
                          style=disnake.ButtonStyle.grey,
                          custom_id=f"clanlinked_{clan.tag}"),
        ]

        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        buttons.append_item(disnake.ui.Button(label="", emoji="🔗", url=clan.share_link))
        if button_text is not None and button_link is not None:
            buttons.append_item(disnake.ui.Button(label=button_text, url=button_link))

        try:
            await ctx.edit_original_message(embed=embed, components=buttons)
        except disnake.errors.HTTPException:
            embed = disnake.Embed(description="Not a valid button link.",color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

    @clan.sub_command(name="links", description="List of un/linked players in clan")
    async def links(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        player_links = await self.bot.link_client.get_links(*[member.tag for member in clan.members])

        linked_players_embed = await clan_embeds.linked_players(bot=self.bot, clan=clan, player_links=player_links, guild=ctx.guild)
        unlinked_players_embed = await clan_embeds.unlinked_players(bot=self.bot, clan=clan, player_links=player_links)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"clanlinked_{clan.tag}"))

        await ctx.edit_original_message(embeds=[linked_players_embed, unlinked_players_embed], components=buttons)


    @clan.sub_command(name="progress", description="Progress by clan ")
    async def progress(self, ctx: disnake.ApplicationCommandInteraction,
                       clan: coc.Clan = commands.Param(converter=clan_converter),
                       type=commands.Param(choices=["Heroes & Pets", "Troops, Spells, & Sieges", "Loot"]),
                       season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor),
                       limit: int = commands.Param(default=50, min_value=1, max_value=50)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            type: progress type
            season: clash season to view data for
            limit: change amount of results shown
        """
        buttons = []
        if type == "Heroes & Pets":
            embed = await shared_embeds.hero_progress(bot=self.bot, player_tags=[member.tag for member in clan.members], season=season,
                                                      footer_icon=clan.badge.url, title_name=f"{clan.name} {type} Progress", limit=limit)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.magnify_glass.partial_emoji,
                style=disnake.ButtonStyle.grey, custom_id=f"clanmoreprogress_{clan.tag}_{season}_heroes"))
        elif type == "Troops, Spells, & Sieges":
            embed = await shared_embeds.troops_spell_siege_progress(bot=self.bot, player_tags=[member.tag for member in clan.members],
                                                      season=season,
                                                      footer_icon=clan.badge.url,
                                                      title_name=f"{clan.name} {type} Progress", limit=limit)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.magnify_glass.partial_emoji,
                style=disnake.ButtonStyle.grey, custom_id=f"clanmoreprogress_{clan.tag}_{season}_troopsspells"))
        elif type == "Home Trophies":
            embed = await shared_embeds.trophies_progress(bot=self.bot,
                                                                    player_tags=[member.tag for member in clan.members],
                                                                    season=season,
                                                                    footer_icon=clan.badge.url,
                                                                    title_name=f"{clan.name} {type} Progress",
                                                                    limit=limit, type="home")
        elif type == "Builder Trophies":
            embed = await shared_embeds.trophies_progress(bot=self.bot,
                                                                    player_tags=[member.tag for member in clan.members],
                                                                    season=season,
                                                                    footer_icon=clan.badge.url,
                                                                    title_name=f"{clan.name} {type} Progress",
                                                                    limit=limit, type="builder")
        elif type == "Loot":
            embed = await shared_embeds.loot_progress(bot=self.bot,
                                                          player_tags=[member.tag for member in clan.members],
                                                          season=season,
                                                          footer_icon=clan.badge.url,
                                                          title_name=f"{clan.name} {type} Progress",
                                                          limit=limit)

        await ctx.edit_original_message(embed=embed, components=[buttons] if buttons else [])


    @clan.sub_command(name="sorted", description="List of clan members, sorted by any attribute")
    async def sorted(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                     sort_by: str = commands.Param(choices=sorted(item_to_name.keys())),
                     limit: int = commands.Param(default=50, min_value=1, max_value=50)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            sort_by: Sort by any attribute
            limit: change amount of results shown
        """

        embed = await shared_embeds.player_sort(bot=self.bot, player_tags=[member.tag for member in clan.members], sort_by=sort_by,
                                                footer_icon=clan.badge.url, title_name=f"{clan.name} sorted by {sort_by}", limit=limit)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"clansort_{clan.tag}_{limit}_{sort_by}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])



    @clan.sub_command(name="war-preferences", description="List of player's war preferences")
    async def war_preferences(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        embeds = await clan_embeds.opt_status(bot=self.bot, clan=clan)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"waropt_{clan.tag}"))

        await ctx.edit_original_message(embeds=embeds, components=buttons)


    @clan.sub_command(name="donations", description="Donations given & received by clan members")
    async def donations(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                             season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor),
                            limit: int = commands.Param(default=50, min_value=1, max_value=50)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            season: clash season to view data for
            limit: change amount of results shown
        """
        players = await self.bot.get_players(tags=[member.tag for member in clan.members])

        embed: disnake.Embed = await shared_embeds.donation_board(bot=self.bot, players=players, season=season, footer_icon=clan.badge.url,
                                                                  title_name=f"{clan.name}", type="donations", limit=limit)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"donated_{season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"received_{season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"ratio_{season}_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)


    @clan.sub_command(name="war-log", description="List of clan's last 25 war win & losses")
    async def war_log(self, ctx: disnake.ApplicationCommandInteraction,
                           clan: coc.Clan = commands.Param(converter=clan_converter),
                           limit: int = commands.Param(default=25, min_value=1, max_value=25)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            limit: change amount of results shown
        """

        if not clan.public_war_log:
            raise coc.errors.PrivateWarLog

        embed = await clan_embeds.war_log(bot=self.bot, clan=clan, limit=limit)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="",
            emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"clanwarlog_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="supers", description="List of clan member's boosted & unboosted troops")
    async def super_troops(self, ctx: disnake.ApplicationCommandInteraction,
                                clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        embed: disnake.Embed = await clan_embeds.super_troop_list(bot=self.bot, clan=clan)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"clanstroops_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)


    @clan.sub_command(name="compo", description="Composition of a clan. (with a twist?)")
    async def compo(self, ctx: disnake.ApplicationCommandInteraction,
                         clan: coc.Clan = commands.Param(converter=clan_converter),
                        type: str = commands.Param(default="Totals", choices=["Totals", "Hitrate"])):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            type: type of compo calculation
        """
        if type == "Totals":
            embed = await shared_embeds.th_composition(bot=self.bot, player_tags=[member.tag for member in clan.members],
                                                       title=f"{clan.name} Townhall Composition", thumbnail=clan.badge.url)
            custom_id = f"clancompo_{clan.tag}"
        elif type == "Hitrate":
            embed = await shared_embeds.th_hitrate(bot=self.bot,
                                                       player_tags=[member.tag for member in clan.members],
                                                       title=f"{clan.name} TH Hitrate Compo",
                                                       thumbnail=clan.badge.url)
            custom_id = f"clanhrcompo_{clan.tag}"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=custom_id))

        await ctx.edit_original_message(embed=embed, components=buttons)



    @clan.sub_command(name="activity", description="Activity stats for all of a player's accounts")
    async def activity(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                       season: str = commands.Param(default=None, converter=season_convertor)):

        s = season
        season = season if season is not None else self.bot.gen_season_date()

        players = await self.bot.get_players(tags=[member.tag for member in clan.members])
        embed: disnake.Embed = await shared_embeds.activity_board(bot=self.bot, players=players, season=season, footer_icon=clan.badge.url, title_name=f"{clan.name}")
        file, buttons = await shared_embeds.activity_graph(bot=self.bot, players=players, season=season,
                                                           title=f"{clan.name} Activity ({season}) | UTC",
                                                           granularity="day", time_zone="UTC", tier=f"clanactgraph_{clan.tag}", no_html=True)
        embed.set_image(file=file)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"clanact_{clan.tag}_{s}"))
        buttons.append_item(disnake.ui.Button(
            label="Last Online", emoji=self.bot.emoji.clock.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"lo_{clan.tag}_{s}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])


    @clan.sub_command(name="graphs")
    async def activity_graph(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                       type: str = commands.Param(choices=["Activity"]),
                       season: str = commands.Param(default=None, converter=season_convertor),
                       timezone: str = "UTC"):
        s = season if season is not None else self.bot.gen_season_date()
        if type == "Activity":
            players = await self.bot.get_players(tags=[member.tag for member in clan.members])
            file, buttons = await shared_embeds.activity_graph(bot=self.bot, players=players, season=season, title=f"{clan.name} Activity ({s}) | {timezone}",
                                                               granularity="day", time_zone=timezone, tier=f"clanactgraph_{clan.tag}")
            await ctx.send(file=file, components=[buttons])


    @clan.sub_command(name="capital", description="Clan capital info for a clan for a week")
    async def clan_capital(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), weekend: str = None):
        #3 types - overview, donations, & raids
        week = weekend
        if weekend is None:
            week = gen_raid_weekend_datestrings(number_of_weeks=1)[0]

        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=week, bot=self.bot, limit=1)
        if weekend_raid_entry is None:
            embed = await clan_embeds.clan_raid_weekend_donation_stats(bot=self.bot, clan=clan, weekend=week)
        else:
            embed = await clan_embeds.clan_capital_overview(bot=self.bot, clan=clan, raid_log_entry=weekend_raid_entry)
            file = await capital_gen.generate_raid_result_image(raid_entry=weekend_raid_entry, clan=clan)
            embed.set_image(file=file)

        page_buttons = [
            disnake.ui.Button(label="", emoji=self.bot.emoji.menu.partial_emoji,
                              style=disnake.ButtonStyle.grey,
                              custom_id=f"capitaloverview_{clan.tag}_{weekend}"),
            disnake.ui.Button(label="Raids", emoji=self.bot.emoji.sword_clash.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"capitalraids_{clan.tag}_{weekend}"),
            disnake.ui.Button(label="Donos", emoji=self.bot.emoji.capital_gold.partial_emoji,
                              style=disnake.ButtonStyle.grey,
                              custom_id=f"capitaldonos_{clan.tag}_{weekend}")
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        return await ctx.send(embed=embed, components=[buttons])


    #AUTOCOMPLETES
    @donations.autocomplete("season")
    @activity.autocomplete("season")
    @activity_graph.autocomplete("season")
    @progress.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

    @donations.autocomplete("clan")
    @activity.autocomplete("clan")
    @activity_graph.autocomplete("clan")
    @clan_capital.autocomplete("clan")
    @war_preferences.autocomplete("clan")
    @search.autocomplete("clan")
    @links.autocomplete("clan")
    @progress.autocomplete("clan")
    @sorted.autocomplete("clan")
    @war_log.autocomplete("clan")
    @super_troops.autocomplete("clan")
    @compo.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id}).sort("name", 1)
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
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

    @activity_graph.autocomplete("timezone")
    async def timezone_autocomplete(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        all_tz = pytz.common_timezones
        return_list = []
        for tz in all_tz:
            if query.lower() in tz.lower():
                return_list.append(tz)
        return return_list[:25]

    @clan_capital.autocomplete("weekend")
    async def weekend(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        weekends = gen_raid_weekend_datestrings(number_of_weeks=25)
        matches = []
        for weekend in weekends:
            if query.lower() in weekend.lower():
                matches.append(weekend)
        return matches

def setup(bot):
    bot.add_cog(ClanCommands(bot))

