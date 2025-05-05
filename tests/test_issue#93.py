import pytest
import disnake
from unittest.mock import AsyncMock, MagicMock, patch
from commands.war.commands import War
from coc.errors import NotFound

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.getClan = AsyncMock()
    bot.fetch_emoji = MagicMock()
    return bot

@pytest.fixture
def ctx():
    ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    ctx.send = AsyncMock()
    return ctx

@pytest.fixture
def clan_valid():
    clan = MagicMock()
    clan.name = "Legendary Lite"
    clan.tag = "#2CLQVGC2"
    clan.share_link = "https://link.clashofclans.com/en?action=OpenClanProfile&tag=2CLQVGC2"
    clan.badge.large = "https://badge.url"
    return clan

@pytest.fixture
def clan_not_in_group():
    clan = MagicMock()
    clan.name = "Divine Kingdom"
    clan.tag = "#LCQR002"
    clan.share_link = "https://link.clashofclans.com/en?action=OpenClanProfile&tag=LCQR002"
    clan.badge.large = "https://badge.url"
    return clan

@pytest.mark.asyncio
@patch("commands.war.commands.get_cwl_wars")
async def test_cwl_compo_success(mock_get_cwl_wars, bot, ctx, clan_valid):
    clan1 = MagicMock(tag="#2CLQVGC2", name="Legendary Lite")
    group = MagicMock()
    group.clans = [clan1]

    mock_get_cwl_wars.return_value = (group, [], clan_valid, MagicMock())

    comp_clan = MagicMock(name="Legendary Lite")
    comp_clan.members = [
        MagicMock(town_hall=15, role="leader"),
        MagicMock(town_hall=14, role="member"),
    ]
    bot.getClan.return_value = comp_clan

    emoji15 = MagicMock(emoji_string="<:th15:1>")
    emoji14 = MagicMock(emoji_string="<:th14:2>")
    bot.fetch_emoji.side_effect = lambda th: {15: emoji15, 14: emoji14}[th]

    cog = War(bot)
    await cog.cwl_compo.callback(cog, ctx, clan=clan_valid, season="2023-10")

    ctx.send.assert_awaited_once()
    embed = ctx.send.call_args.kwargs['embed']
    assert "Legendary Lite" in embed.fields[0].name
    assert "<:th15:1> 1" in embed.fields[0].value
    assert "<:th14:2> 1" in embed.fields[0].value

@pytest.mark.asyncio
@patch("commands.war.commands.get_cwl_wars")
async def test_cwl_compo_not_in_group(mock_get_cwl_wars, bot, ctx, clan_not_in_group):
    mock_get_cwl_wars.return_value = (None, None, clan_not_in_group, None)

    cog = War(bot)
    await cog.cwl_compo.callback(cog, ctx, clan=clan_not_in_group, season="2023-10")

    ctx.send.assert_awaited_once()
    embed = ctx.send.call_args.kwargs['embed']
    assert "not in CWL" in embed.description
    assert embed.color == disnake.Color.red()

@pytest.mark.asyncio
async def test_cwl_compo_invalid_clan(bot, ctx):
    invalid_clan = MagicMock()
    invalid_clan.tag = "#INVALID"

    bot.getClan.side_effect = NotFound("Invalid clan tag")

    cog = War(bot)
    await cog.cwl_compo.callback(cog, ctx, clan=invalid_clan, season="2023-10")

    ctx.send.assert_awaited_once()
    embed = ctx.send.call_args.kwargs['embed']
    assert "#INVALID is not a valid clan tag" in embed.description
    assert embed.color == disnake.Color.red()
