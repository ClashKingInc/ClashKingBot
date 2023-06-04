import disnake
import coc

from utils.general import get_clan_member_tags
from utils.constants import TOWNHALL_LEVELS
from typing import List
from .Utils import Clan as clan_embeds
from .Utils import Family as family_embeds
from .Utils import Graphs as graph_creator
from .Utils import Player as player_embeds
from .Utils import Shared as shared_embeds
from CustomClasses.CustomBot import CustomClient
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from ImageGen import ClanCapitalResult as capital_gen

clan_triggers = {
    "clanoverview",
    "clanwarcwlhist",
    "clanwaropt",
    "clanlinked",
    "clansort",
    "clanwarlog",
    "clanstroops",
    "clancompo",
    "capitaloverview",
    "capitalraids",
    "capitaldonos",
    "clanactgraph",
    "clanhrcompo",
    "clanact",
    "clanmoreprogress"
}

ephemeral = {
    "clanmoreprogress",
    "fmp"
}

family_triggers = {
    "donationfam",
    "fmp"
}

async def button_click_to_embed(bot: CustomClient, ctx: disnake.MessageInteraction):
    custom_id = str(ctx.data.custom_id)
    embed = None
    first = custom_id.split("_")[0]
    if first in clan_triggers:
        await ctx.response.defer(ephemeral=first in ephemeral)
        embed = await clan_parser(bot, ctx, custom_id)
    elif first in family_triggers:
        await ctx.response.defer(ephemeral=first in ephemeral)
        embed = await family_parser(bot, ctx, custom_id)
    return embed, first in ephemeral

async def clan_parser(bot: CustomClient, ctx: disnake.MessageInteraction, custom_id: str):
    split = custom_id.split("_")
    clan_tag = split[1]
    clan = await bot.getClan(clan_tag=clan_tag)
    embed = None
    if "clanoverview_" in custom_id:
        image = split[-1]
        if split[-2] == "True":
            embed = await clan_embeds.simple_clan_embed(bot, clan)
        else:
            embed = await clan_embeds.clan_overview(bot=bot, clan=clan, guild=ctx.guild)
        if image != "None":
            embed.set_image(file=disnake.File(f"TemplateStorage/{image}.png"))

    elif "clanwarcwlhist_" in custom_id:
        war_log_embed = await clan_embeds.war_log(bot=bot, clan=clan)
        cwl_history = await clan_embeds.cwl_performance(bot=bot, clan=clan)
        embed = [war_log_embed, cwl_history]

    elif "clanwaropt_" in custom_id:
        embed = await clan_embeds.opt_status(bot=bot, clan=clan)

    elif "clanlinked_" in custom_id:
        player_links = await bot.link_client.get_links(*[member.tag for member in clan.members])
        linked_players_embed = await clan_embeds.linked_players(bot=bot, clan=clan, player_links=player_links, guild=ctx.guild)
        unlinked_players_embed = await clan_embeds.unlinked_players(bot=bot, clan=clan, player_links=player_links)
        embed = [linked_players_embed, unlinked_players_embed]

    elif "clansort_" in custom_id:
        sort_by = split[-1]
        limit = int(split[-2])
        embed = await shared_embeds.player_sort(bot=bot, player_tags=[member.tag for member in clan.members],
                                                sort_by=sort_by,
                                                footer_icon=clan.badge.url,
                                                title_name=f"{clan.name} sorted by {sort_by}", limit=limit)
    elif "clanstroops_" in custom_id:
        embed = await clan_embeds.super_troop_list(bot=bot, clan=clan)

    elif "clancompo_" in custom_id:
        embed = await shared_embeds.th_composition(bot=bot, player_tags=[member.tag for member in clan.members],
                                                   title=f"{clan.name} Townhall Composition", thumbnail=clan.badge.url)

    elif "capitaloverview_" in custom_id:
        week = split[-1]
        if week == "None":
            week = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=week, bot=bot, limit=1)
        embed = await clan_embeds.clan_capital_overview(bot=bot, clan=clan, raid_log_entry=weekend_raid_entry)
        if weekend_raid_entry:
            file = await capital_gen.generate_raid_result_image(raid_entry=weekend_raid_entry, clan=clan)
            embed.set_image(file=file)

    elif "capitalraids_" in custom_id:
        week = split[-1]
        if week == "None":
            week = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=week, bot=bot, limit=1)
        embed = await clan_embeds.clan_raid_weekend_raid_stats(bot=bot, clan=clan, raid_log_entry=weekend_raid_entry)
        if weekend_raid_entry:
            file = await capital_gen.generate_raid_result_image(raid_entry=weekend_raid_entry, clan=clan)
            embed.set_image(file=file)

    elif "capitaldonos_" in custom_id:
        week = split[-1]
        if week == "None":
            week = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=week, bot=bot, limit=1)
        embed = await clan_embeds.clan_raid_weekend_donation_stats(bot=bot, clan=clan, weekend=week)
        if weekend_raid_entry:
            file = await capital_gen.generate_raid_result_image(raid_entry=weekend_raid_entry, clan=clan)
            embed.set_image(file=file)

    elif "clanactgraph_" in custom_id:
        granularity = split[2]
        season = split[3]
        if season == "None":
            season = None
        s = season if season is not None else bot.gen_season_date()
        timezone = split[-1]
        players = await bot.get_players(tags=[member.tag for member in clan.members])
        file, buttons = await shared_embeds.activity_graph(bot=bot, players=players, season=season,
                                                           title=f"{clan.name} Activity ({s}) | {timezone}",
                                                           granularity=granularity, time_zone=timezone, tier=f"clanactgraph_{clan.tag}")
        await ctx.edit_original_message(attachments=[],file=file, components=[buttons])

    elif "clanhrcompo_" in custom_id:
        embed = await shared_embeds.th_hitrate(bot=bot,
                                               player_tags=[member.tag for member in clan.members],
                                               title=f"{clan.name} TH Hitrate Compo",
                                               thumbnail=clan.badge.url)

    elif "clanact_" in custom_id:
        season = split[-1] if split[-1] != "None" else bot.gen_season_date()
        players = await bot.get_players(tags=[member.tag for member in clan.members])
        embed: disnake.Embed = await shared_embeds.activity_board(bot=bot, players=players, season=season,
                                                                  footer_icon=clan.badge.url, title_name=f"{clan.name}")
        file, buttons = await shared_embeds.activity_graph(bot=bot, players=players, season=season,
                                                           title=f"{clan.name} Activity ({season}) | UTC",
                                                           granularity="day", time_zone="UTC",
                                                           tier=f"clanactgraph_{clan.tag}", no_html=True)
        embed.set_image(file=file)

    elif "clanmoreprogress_" in custom_id:
        season = split[-2]
        type = split[-1]
        embed = await shared_embeds.total_character_progress(bot=bot, player_tags=[member.tag for member in clan.members], season=season,
                                                             footer_icon=clan.badge.url, type=type, title_name=f"{clan.name} Total Progress")
    return embed


async def family_parser(bot: CustomClient, ctx: disnake.MessageInteraction, custom_id: str):
    split = custom_id.split("_")
    season = split[1]
    limit = int(split[2])
    guild = await bot.getch_guild(int(split[3]))
    embed = None
    if "donationfam_" in custom_id:
        townhall = TOWNHALL_LEVELS if split[-1] == "None" else [int(split[-1])]
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans: List[coc.Clan] = await bot.get_clans(tags=clan_tags)
        member_tags = get_clan_member_tags(clans=clans)

        top_50 = await bot.player_stats.find(
            {"$and": [{"tag": {"$in": member_tags}}, {"townhall": {"$in": townhall}}]}, {"tag": 1}).sort(
            f"donations.{season}.donated", -1).limit(limit).to_list(length=50)
        players = await bot.get_players(tags=[p["tag"] for p in top_50])
        graph, total_donos, total_received = await graph_creator.create_clan_donation_graph(bot=bot, clans=clans,
                                                                                            season=season,
                                                                                            type="donated",
                                                                                            townhalls=townhall)
        embed = await shared_embeds.donation_board(bot=bot, players=players, season=season,
                                                   title_name=f"{guild.name}", type="donations",
                                                   footer_icon=ctx.guild.icon.url if ctx.guild.icon is not None else bot.user.avatar.url,
                                                   total_donos=total_donos, total_received=total_received)
        embed.set_image(file=graph)

    elif "fmp_" in custom_id:
        type = split[-1]
        footer_icon = guild.icon.url if guild.icon is not None else bot.user.avatar.url
        member_tags = await bot.get_family_member_tags(guild_id=guild.id)
        embed = await shared_embeds.total_character_progress(bot=bot,
                                                             player_tags=member_tags,
                                                             season=season,
                                                             footer_icon=footer_icon, type=type,
                                                             title_name=f"{guild.name} Total Progress")
    return embed




def top_parser():
    pass

def player_parser():
    pass