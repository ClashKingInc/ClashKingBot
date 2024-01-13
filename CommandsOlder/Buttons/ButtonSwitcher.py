import disnake
import coc

from utility.general import get_clan_member_tags
from utility.constants import TOWNHALL_LEVELS
from typing import List
from BoardCommands.Utils import Clan as clan_embeds
from BoardCommands.Utils import Family as family_embeds
from BoardCommands.Utils import Graphs as graph_creator
from BoardCommands.Utils import Player as player_embeds
from BoardCommands.Utils import Shared as shared_embeds
from CustomClasses.CustomBot import CustomClient
from utility.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from ImageGen import ClanCapitalResult as capital_gen
from CustomClasses.Enums import TrophySort
from utility.search import search_results

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
    "clanmoreprogress",
    "clanboardact",
    "clanboardlegend",
    "clanboardtrophies"
}

ephemeral = {
    "clanmoreprogress",
    "fmp",
    "clanwarcwlhist"
}

family_triggers = {
    "donationfam",
    "fmp",
    "famboardact",
    "famboardlegend",
    "famboardtrophies",
    "famclans",
    "famcompo",
    "famhrcompo",
    "famwars",
    "cwlleaguesfam",
    "capitalleaguesfam",
    "receivedfam",
    "famcapd",
    "famcapr",
    "clangamesfam",
    "hometrophiesfam",
    "versustrophiesfam",
    "capitaltrophiesfam"
}

top_triggers = {
    "topcapitaldonatedplayer",
    "topcapitalraidplayer",
    "topsort",
    "topactivityplayer",
    "topdonatedplayer",
    "topreceivedplayer"
}

player_triggers = {
    "donatedplayer",
    "receivedplayer",
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
    elif first in top_triggers:
        await ctx.response.defer(ephemeral=first in ephemeral)
        embed = await top_parser(bot, ctx, custom_id)
    elif first in player_triggers:
        await ctx.response.defer(ephemeral=first in ephemeral)
        embed = await player_parser(bot, ctx, custom_id)
    return embed, first in ephemeral


async def clan_parser(bot: CustomClient, ctx: disnake.MessageInteraction, custom_id: str):
    split = custom_id.split("_")
    clan_tag = split[1]
    limit = int(split[-1]) if split[-1].isnumeric() else 50
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

    elif "clanboardact_" in custom_id:
        players = await bot.get_players(tags=[member.tag for member in clan.members], custom=True)
        players.sort(key=lambda x: x.donos().donated, reverse=True)

        embed = await shared_embeds.image_board(bot=bot, players=players[:limit], logo_url=clan.badge.url, title=f'{clan.name} Activity/Donation Board', type="activities", season=bot.gen_season_date())

    elif "clanboardlegend_" in custom_id:
        players = await bot.get_players(tags=[member.tag for member in clan.members], custom=True)
        players = [player for player in players if player.is_legends()]
        players.sort(key=lambda x: x.trophies, reverse=True)
        embed= await shared_embeds.image_board(bot=bot, players=players[:limit], logo_url=clan.badge.url, title=f'{clan.name} Legend Board', type="legend")


    elif "clanboardtrophies_" in custom_id:
        players = await bot.get_players(tags=[member.tag for member in clan.members], custom=True)
        players.sort(key=lambda x: x.trophies, reverse=True)
        embed = await shared_embeds.image_board(bot=bot, players=players[:limit], logo_url=clan.badge.url, title=f'{clan.name} Trophy Board', type="trophies")

    return embed


async def family_parser(bot: CustomClient, ctx: disnake.MessageInteraction, custom_id: str):
    split = custom_id.split("_")
    if len(split) == 4:
        season = split[1]
        limit = int(split[2])
        guild = await bot.getch_guild(int(split[3]))
    elif len(split) == 2:
        guild = await bot.getch_guild(int(split[1]))
        guild_icon = guild.icon.url if guild.icon else bot.user.avatar.url
    elif len(split) == 5 and "fmp" not in custom_id:
        season = split[1]
        limit = int(split[2])
        guild = await bot.getch_guild(int(split[3]))
        townhall = TOWNHALL_LEVELS if split[4] == "None" else [int(split[-1])]
        guild_icon = guild.icon.url if guild.icon else bot.user.avatar.url

    embed = None
    if "donationfam_" in custom_id:
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


    elif "receivedfam_" in custom_id:
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans: List[coc.Clan] = await bot.get_clans(tags=clan_tags)
        member_tags = get_clan_member_tags(clans=clans)

        top_50 = await bot.player_stats.find({"$and": [{"tag": {"$in": member_tags}}, {"townhall": {"$in": townhall}}]}, {"tag": 1}).sort(f"donations.{season}.received", -1).limit(limit).to_list(length=50)
        players = await bot.get_players(tags=[p["tag"] for p in top_50])
        graph, total_donos, total_received = await graph_creator.create_clan_donation_graph(bot=bot, clans=clans,
                                                                                            season=season,
                                                                                            type="received",
                                                                                            townhalls=townhall)
        embed = await shared_embeds.donation_board(bot=bot, players=players, season=season,
                                                   title_name=f"{guild.name}", type="received",
                                                   footer_icon=ctx.guild.icon.url if ctx.guild.icon is not None else bot.user.avatar.url,
                                                   total_donos=total_donos, total_received=total_received)
        embed.set_image(file=graph)


    elif "fmp_" in custom_id:
        type = split[-1]
        season = split[1]
        limit = int(split[2])
        guild = await bot.getch_guild(int(split[3]))
        guild_icon = guild.icon.url if guild.icon else bot.user.avatar.url

        footer_icon = guild.icon.url if guild.icon is not None else bot.user.avatar.url
        member_tags = await bot.get_family_member_tags(guild_id=guild.id)
        if type == "lootprogress":
            embed = await shared_embeds.loot_progress(bot=bot,
                                                      player_tags=member_tags,
                                                      season=season,
                                                      footer_icon=footer_icon,
                                                      title_name=f"{guild.name} Loot Progress",
                                                      limit=limit)
        elif type == "heroes":
            embed = await shared_embeds.hero_progress(bot=bot,
                                                      player_tags=member_tags,
                                                      season=season,
                                                      footer_icon=footer_icon,
                                                      title_name=f"{guild.name} Heroes & Pets Progress",
                                                      limit=limit)
        elif type == "troopsspells":
            embed = await shared_embeds.troops_spell_siege_progress(bot=bot,
                                                                    player_tags=member_tags,
                                                                    season=season,
                                                                    footer_icon=footer_icon,
                                                                    title_name=f"{guild.name} Troops, Spells, & Sieges Progress",
                                                                    limit=limit)


    elif "famboardact_" in custom_id:
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans: List[coc.Clan] = await bot.get_clans(tags=clan_tags)
        member_tags = get_clan_member_tags(clans=clans)
        top_50 = await bot.player_stats.find({"tag": {"$in": member_tags}}, {"tag": 1}).sort(
            f"donations.{bot.gen_season_date()}.donated", -1).limit(30).to_list(length=50)
        players = await bot.get_players(tags=[p["tag"] for p in top_50], custom=True)
        players.sort(key=lambda x: x.donos().donated, reverse=True)

        embed = await shared_embeds.image_board(bot=bot, players=players, logo_url=guild_icon, title=f'{guild.name} Activity/Donation Board', type="activities", season=bot.gen_season_date())


    elif "famboardlegend_" in custom_id:
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
        top_30 = await bot.player_stats.find(
            {"$and": [{"clan_tag": {"$in": clan_tags}}, {"league": "Legend League"}]}).sort(f"trophies", -1).limit(30).to_list(length=30)
        players = await bot.get_players(tags=[p["tag"] for p in top_30], found_results=top_30, custom=True)
        players.sort(key=lambda x: x.trophies, reverse=True)
        embed = await shared_embeds.image_board(bot=bot, players=players, logo_url=guild_icon, title=f'{guild.name} Legend Board', type="legend")


    elif "famboardtrophies_" in custom_id:
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
        top_30 = await bot.player_stats.find({"clan_tag": {"$in": clan_tags}}).sort(f"trophies", -1).limit(30).to_list(length=30)
        players = await bot.get_players(tags=[p["tag"] for p in top_30], found_results=top_30, custom=True)
        players.sort(key=lambda x: x.trophies, reverse=True)
        embed = await shared_embeds.image_board(bot=bot, players=players, logo_url=guild_icon,
                                               title=f'{guild.name} Trophy Board', type="trophies")


    elif "famclans_" in custom_id:
        embed = await family_embeds.create_family_clans(bot=bot, guild=guild)


    elif "famcompo_" in custom_id:
        member_tags = await bot.get_family_member_tags(guild_id=guild.id)
        embed = await shared_embeds.th_composition(bot=bot, player_tags=member_tags, title=f"{guild.name} Townhall Composition", thumbnail=guild_icon)


    elif "famhrcompo_" in custom_id:
        member_tags = await bot.get_family_member_tags(guild_id=guild.id)
        embed = await shared_embeds.th_hitrate(bot=bot, player_tags=member_tags, title=f"{guild.name} TH Hitrate Compo" ,thumbnail=guild_icon)


    elif "famwars_" in custom_id:
        embed = await family_embeds.create_wars(bot=bot, guild=guild)


    elif "cwlleaguesfam_" in custom_id:
        embed = await family_embeds.create_leagues(bot=bot, guild=guild, type="CWL")


    elif "capitalleaguesfam_" in custom_id:
        embed = await family_embeds.create_leagues(bot=bot, guild=guild, type="Capital")


    elif "famcapd_" in custom_id:
        member_tags = await bot.get_family_member_tags(guild_id=guild.id)
        distinct = await bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
        players = await bot.get_players(tags=distinct)
        embed: disnake.Embed = await shared_embeds.capital_donation_board(bot=bot,
                                                                          players=[player for player in players if
                                                                                   player.town_hall in townhall],
                                                                          week=season,
                                                                          title_name=f"{guild.name} Top",
                                                                          footer_icon=guild.icon.url if guild.icon is not None else None,
                                                                          limit=limit)

    elif "famcapr_" in custom_id:
        member_tags = await bot.get_family_member_tags(guild_id=guild.id)
        distinct = await bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
        players = await bot.get_players(tags=distinct)
        embed: disnake.Embed = await shared_embeds.capital_raided_board(bot=bot,
                                                                          players=[player for player in players if
                                                                                   player.town_hall in townhall],
                                                                          week=season,
                                                                          title_name=f"{guild.name} Top",
                                                                          footer_icon=guild.icon.url if guild.icon is not None else None,
                                                                          limit=limit)

    elif "clangamesfam_" in custom_id:
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
        members = await bot.player_stats.distinct("tag", filter={f"clan_tag": {"$in": clan_tags}})
        did_games_in_clan = await bot.player_stats.distinct("tag", filter={
            f"clan_games.{season}.clan": {"$in": clan_tags}})

        all_tags = members + did_games_in_clan
        all_tags = [r["tag"] for r in (
            await bot.player_stats.find({"tag": {"$in": all_tags}}).sort(f"clan_games.{season}.clan", -1).limit(
                limit).to_list(length=limit))]

        players = await bot.get_players(tags=all_tags)
        embed = await shared_embeds.create_clan_games(bot=bot, players=players, season=season, clan_tags=clan_tags,
                                                      title_name=f"{guild.name} Top {limit} Clan Games Points",
                                                      limit=limit)
        embed = await family_embeds.create_trophies(bot=bot, guild=guild, sort_type=TrophySort.home)

    elif "hometrophiesfam_" in custom_id:
        embed = await family_embeds.create_trophies(bot=bot, guild=guild, sort_type=TrophySort.home)
        buttons = disnake.ui.ActionRow()
        sort_type = TrophySort.home
        buttons.append_item(disnake.ui.Button(label="Home", emoji=bot.emoji.trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                              custom_id=f"hometrophiesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Versus", emoji=bot.emoji.versus_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                              custom_id=f"versustrophiesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Capital", emoji=bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                              custom_id=f"capitaltrophiesfam_{guild.id}"))
        await ctx.edit_original_message(components=buttons)

    elif "versustrophiesfam_" in custom_id:
        embed = await family_embeds.create_trophies(bot=bot, guild=guild, sort_type=TrophySort.versus)
        buttons = disnake.ui.ActionRow()
        sort_type = TrophySort.versus
        buttons.append_item(disnake.ui.Button(label="Home", emoji=bot.emoji.trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                              custom_id=f"hometrophiesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Versus", emoji=bot.emoji.versus_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                              custom_id=f"versustrophiesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Capital", emoji=bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                              custom_id=f"capitaltrophiesfam_{guild.id}"))
        await ctx.edit_original_message(components=buttons)

    elif "capitaltrophiesfam_" in custom_id:
        embed = await family_embeds.create_trophies(bot=bot, guild=guild, sort_type=TrophySort.capital)
        buttons = disnake.ui.ActionRow()
        sort_type = TrophySort.capital
        buttons.append_item(disnake.ui.Button(label="Home", emoji=bot.emoji.trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                              custom_id=f"hometrophiesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Versus", emoji=bot.emoji.versus_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                              custom_id=f"versustrophiesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Capital", emoji=bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                              custom_id=f"capitaltrophiesfam_{guild.id}"))
        await ctx.edit_original_message(components=buttons)

    return embed


async def top_parser(bot: CustomClient, ctx: disnake.MessageInteraction, custom_id: str):
    if str(ctx.data.custom_id) == "topdonatedplayer_":
        season = bot.gen_season_date()
        players = await bot.player_stats.find({}, {"tag": 1}).sort(f"donations.{season}.donated", -1).limit(
            50).to_list(length=50)
        players = await bot.get_players(tags=[result.get("tag") for result in players])

        footer_icon = bot.user.avatar.url
        embed: disnake.Embed = await shared_embeds.donation_board(bot=bot, players=players, season=season,
                                                                   footer_icon=footer_icon, title_name="ClashKing",
                                                                   type="donations")
        await ctx.edit_original_message(embed=embed)

    elif str(ctx.data.custom_id) == "topreceivedplayer_":
        season = bot.gen_season_date()
        players = await bot.player_stats.find({}, {"tag": 1}).sort(f"donations.{season}.received", -1).limit(
            50).to_list(length=50)
        players = await bot.get_players(tags=[result.get("tag") for result in players])

        footer_icon = bot.user.avatar.url
        embed: disnake.Embed = await shared_embeds.donation_board(bot=bot, players=players, season=season,
                                                                   footer_icon=footer_icon, title_name="ClashKing",
                                                                   type="received")
        await ctx.edit_original_message(embed=embed)

    elif "topcapitaldonatedplayer_" in str(ctx.data.custom_id):
        week = str(ctx.data.custom_id).split("_")[-1]
        if week == "None":
            week = bot.gen_raid_date()
        pipeline = [{"$project": {"tag": "$tag",
                                  "capital_sum": {"$sum": {"$ifNull": [f"$capital_gold.{week}.donate", []]}}}},
                    {"$sort": {"capital_sum": -1}}, {"$limit": 50}]
        players = await bot.player_stats.aggregate(pipeline).to_list(length=None)
        players = await bot.get_players(tags=[result.get("tag") for result in players])
        embed: disnake.Embed = await shared_embeds.capital_donation_board(bot=bot, players=players, week=week,
                                                                           title_name="Top",
                                                                           footer_icon=bot.user.avatar.url)
        await ctx.edit_original_message(embed=embed)

    elif "topcapitalraidplayer_" in str(ctx.data.custom_id):
        week = str(ctx.data.custom_id).split("_")[-1]
        if week == "None":
            week = bot.gen_raid_date()
        pipeline = [{"$project": {"tag": "$tag",
                                  "capital_sum": {"$sum": {"$ifNull": [f"$capital_gold.{week}.raid", []]}}}},
                    {"$sort": {"capital_sum": -1}}, {"$limit": 50}]
        players = await bot.player_stats.aggregate(pipeline).to_list(length=None)
        players = await bot.get_players(tags=[result.get("tag") for result in players])
        embed: disnake.Embed = await shared_embeds.capital_raided_board(bot=bot, players=players, week=week,
                                                                         title_name="Top",
                                                                         footer_icon=bot.user.avatar.url)
        await ctx.edit_original_message(embed=embed)

    elif "topactivityplayer_" in str(ctx.data.custom_id):
        season = str(ctx.data.custom_id).split("_")[-1]
        if season == "None":
            season = bot.gen_raid_date()
        pipeline = [
            {"$project": {"tag": "$tag",
                          "activity_len": {"$size": {"$ifNull": [f"last_online_times.{season}", 0]}}}},
            {"$sort": {"activity_len": -1}}, {"$limit": 50}]
        players = await bot.player_stats.aggregate(pipeline).to_list(length=None)
        players = await bot.get_players(tags=[result.get("tag") for result in players])

        footer_icon = bot.user.avatar.url
        embed: disnake.Embed = await shared_embeds.activity_board(bot=bot, players=players, season=season,
                                                                   footer_icon=footer_icon, title_name="ClashKing")
        await ctx.edit_original_message(embed=embed)


async def player_parser(bot: CustomClient, ctx: disnake.MessageInteraction, custom_id: str):
    split = custom_id.split("_")
    embed = None
    if len(split) == 3:
        season = split[1]
        discord_user = split[2]
        players = await search_results(bot, str(discord_user))
        discord_user = await bot.getch_user(int(discord_user))

    if "donatedplayer_" in custom_id:
        footer_icon = discord_user.display_avatar.url
        embed: disnake.Embed = await shared_embeds.donation_board(bot=bot, players=players, season=season,
                                                                  footer_icon=footer_icon,
                                                                  title_name=f"{discord_user.display_name}",
                                                                  type="donations")
    elif "receivedplayer_" in custom_id:
        footer_icon = discord_user.display_avatar.url
        embed: disnake.Embed = await shared_embeds.donation_board(bot=bot, players=players, season=season,
                                                                  footer_icon=footer_icon,
                                                                  title_name=f"{discord_user.display_name}",
                                                                  type="received")

    return embed