import disnake
import coc
import bisect

import math
from classes.bot import CustomClient
from utility.discord_utils import register_button

@register_button('besteos', parser="_:server_id:type:country")
async def best_eos(
        bot: CustomClient,
        server_id: int | None,
        type: str,
        country: str | None,
        embed_color: disnake.Color) -> disnake.Embed:

    type_map: dict[str, callable] = {
        'Home Village': bot.coc_client.get_location_players,
        'Builder Base': bot.coc_client.get_location_players_builder_base,
        'Home Village Clans': bot.coc_client.get_location_clans,
        'Builder Base Clans': bot.coc_client.get_location_clans_builder_base,
    }

    if not country:
        db_server = await bot.ck_client.get_server_settings(server_id=server_id)
        clans = await bot.get_clans(tags=[c.tag for c in db_server.clans])

        if not clans:
            return disnake.Embed(
                description="No clans linked to this server or command was run in DM",
                color=disnake.Color.red(),
            )

        members: list[coc.ClanMember] = []
        for clan in clans:
            members.extend(clan.members)
        members.sort(key=lambda x: x.trophies, reverse=True)
        footer_text = f"Compiled from {len(clans)} Clans & {len(members)} Members"
    else:
        if country == 'Global':
            country_id = 'global'
        else:
            locations: list[coc.Location] = await bot.get_country_names()
            country_obj = coc.utils.get(locations, name=country, is_country=country != 'International')
            country_id = country_obj.id
        rankings = await type_map.get(type)(location_id=country_id)
        members: list[coc.RankedPlayer] = rankings
        footer_text = f"Compiled from Top 200 in {country}"

    max_clans = min(math.floor(len(members) / 50), 20)
    global_rankings: list[coc.RankedClan] = await type_map.get(f"{type} Clans")(location_id="global")
    trophy_list = [-clan.points if type == 'Home Village' else -clan.builder_base_points for clan in global_rankings]

    text = ''
    clan_num = 0
    for clan in range(clan_num, max_clans):
        total_score = 0
        member_chunk = members[(50 * clan): ((50 * clan) + 50)]
        for rank, member in enumerate(member_chunk):
            trophies = member.trophies if type == 'Home Village' else member.builder_base_trophies
            if 1 <= rank <= 10:
                total_score += int(trophies * 0.50)
            elif 11 <= rank <= 20:
                total_score += int(trophies * 0.25)
            elif 21 <= rank <= 30:
                total_score += int(trophies * 0.12)
            elif 31 <= rank <= 40:
                total_score += int(trophies * 0.10)
            elif 41 <= rank <= 50:
                total_score += int(trophies * 0.03)
        trophy = bot.emoji.trophy if type == "Home Village" else bot.emoji.versus_trophy
        calc_global_rank = bisect.bisect_right(trophy_list, -total_score) + 1
        rank_text = ""
        if calc_global_rank <= 200:
            rank_text = f"(#{calc_global_rank} Global)"
        text += f'{bot.get_number_emoji(color="gold", number=clan + 1)} {trophy}{total_score:,} {rank_text}\n'

    embed = disnake.Embed(
        title=f'Best Possible EOS ({type})',
        description=text,
        color=embed_color,
    )
    league_type = "Legend League" if type == "Home Village" else "Diamond"
    embed.set_thumbnail(url=bot.fetch_emoji(league_type).partial_emoji.url)
    embed.set_footer(text=footer_text)
    return embed

@register_button('rankedplayers', parser="_:server_id:type:country")
async def ranked_players():
    server_players = {}
    names = {}
    trophies = {}
    tracked = self.bot.clan_db.find({'server': ctx.guild.id})
    limit = await self.bot.clan_db.count_documents(filter={'server': ctx.guild.id})
    tags = []
    for clan in await tracked.to_list(length=limit):
        tag = clan.get('tag')
        tags.append(tag)

    async for clan in self.bot.coc_client.get_clans(tags):
        for player in clan.members:
            try:
                server_players[player.tag] = player.trophies
                trophies[player.tag] = player.trophies
                names[player.tag] = player.name
            except:
                continue

    sorted(server_players, key=server_players.get, reverse=True)
    server_players = {key: rank for rank, key in
                      enumerate(sorted(server_players, key=server_players.get, reverse=True), 1)}
    server_players_list = list(server_players.keys())

    embeds = []
    num = 0
    text = ''
    # [loc, rank, country, clantag, clanname, trophies, playername]
    for tag in server_players_list:
        result_ranking = await self.bot.leaderboard_db.find_one({'tag': tag})
        ranking = LegendRanking(result_ranking)
        if ranking.global_ranking != '<:status_offline:910938138984206347>':
            num += 1
            text += f'<:trophy:956417881778815016>`{trophies[tag]}` | <a:earth:861321402909327370> `{ranking.global_ranking}` | {names[tag]}\n'

        if ranking.local_ranking != '<:status_offline:910938138984206347>':
            num += 1
            text += f'<:trophy:956417881778815016>`{trophies[tag]}` | {ranking.flag} {ranking.country} | {names[tag]}\n'

        if num == 25:
            embed = disnake.Embed(
                title=f'**{ctx.guild.name} Player Country LB Rankings**',
                description=text,
            )
            embeds.append(embed)
            num = 0
            text = ''

    if text != '':
        embed = disnake.Embed(
            title=f'**{ctx.guild.name} Player Country LB Rankings**',
            description=text,
        )
        embeds.append(embed)

    if embeds == []:
        return await ctx.edit_original_message(content='No ranked players on this server.')


async def ranked_clans():
    server_clans = []
    tracked = self.bot.clan_db.find({'server': ctx.guild.id})
    limit = await self.bot.clan_db.count_documents(filter={'server': ctx.guild.id})
    for clan in await tracked.to_list(length=limit):
        tag = clan.get('tag')
        server_clans.append(tag)

    num = 0
    text = ''
    for tag in server_clans:
        result_ranking = await self.bot.clan_leaderboard_db.find_one({'tag': tag})
        ranking = LegendRanking(result_ranking)

        clan = None
        if ranking.global_ranking != '<:status_offline:910938138984206347>':
            num += 1
            clan = await self.bot.getClan(tag)
            text += f'<a:earth:861321402909327370> `{ranking.global_ranking}` | {clan.name}\n'

        if ranking.local_ranking != '<:status_offline:910938138984206347>':
            num += 1
            if clan is None:
                clan = await self.bot.getClan(tag)
            text += f'{ranking.flag} `{ranking.local_ranking}` | {ranking.country} | {clan.name}\n'

    if text == '':
        text = 'No ranked clans'
    embed = disnake.Embed(
        title=f'**{ctx.guild.name} Clan Country Rankings (Top 200)**',
        description=text,
        color=disnake.Color.green(),
    )
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)