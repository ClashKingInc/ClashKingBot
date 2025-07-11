import lightbulb

from api.client import ClashKingAPIClient
from utility.time import gen_season_date


@lightbulb.di.with_di
async def clan(ctx: lightbulb.AutocompleteContext[str], ck_client: ClashKingAPIClient) -> None:
    current_value: str = ctx.focused.value or ''
    results = await ck_client.search_for_clans(
        query=current_value,
        user_id=ctx.interaction.user.id,
        guild_id=ctx.interaction.guild_id,
    )
    returnable = []
    for clan in results[:25]:
        if clan.result_type == 'search_result':
            text = f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {clan.war_league.replace('League ', '')} | {clan.tag}"
        elif clan.result_type == 'guild_search':
            text = f'{clan.name} | {clan.tag}'
        elif clan.result_type == 'recent_search':
            text = f'(Recent) {clan.name} | {clan.tag}'
        elif clan.result_type == 'bookmarked':
            text = f'(Bookmark) {clan.name} | {clan.tag}'
        else:
            continue
        returnable.append(text)
    await ctx.respond(returnable)


async def season(ctx: lightbulb.AutocompleteContext[str]) -> None:
    seasons = gen_season_date(num_seasons=12, as_text=True)
    await ctx.respond([s for s in seasons if ctx.focused.value.lower() in s.lower()])


@lightbulb.di.with_di
async def banned_players(ctx: lightbulb.AutocompleteContext[str], ck_client: ClashKingAPIClient):
    results = await ck_client.search_for_bans(query=ctx.focused.value or '', guild_id=ctx.interaction.guild_id)
    await ctx.respond([f'{p.name} | {p.tag}' for p in results])
