import pytest
import disnake
from unittest.mock import AsyncMock, MagicMock, patch
from commands.war.commands import War

MOCK_WAR_LEAGUES = {
    "leagues": [
        {"name": "Master League I", "id": 1}
    ]
}


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
def clan():
    clan = MagicMock()
    clan.name = "Test Clan"
    clan.tag = "#TEST"
    clan.share_link = "https://link.clashofclans.com/test"
    clan.badge.large = "https://badge.url"
    return clan


@pytest.mark.asyncio
@patch("commands.war.commands.get_cwl_wars")
async def test_cwl_compo_success(mock_get_cwl_wars, bot, ctx, clan):
    # Setup mock group and fetched clans
    clan1 = MagicMock()
    clan1.tag = "#CLAN1"
    clan1.name = "Clan One"
    clan2 = MagicMock()
    clan2.tag = "#CLAN2"
    clan2.name = "Clan Two"

    group = MagicMock()
    group.clans = [clan1, clan2]

    fetched_clan = clan
    war_league = MagicMock()
    clan_league_wars = []

    mock_get_cwl_wars.return_value = (group, clan_league_wars, fetched_clan, war_league)

    # Mock bot.getClan
    comp_clan1 = MagicMock()
    comp_clan1.name = "Clan One"
    comp_clan1.members = [
        MagicMock(town_hall=15, role="leader"),
        MagicMock(town_hall=14, role="member")
    ]

    comp_clan2 = MagicMock()
    comp_clan2.name = "Clan Two"
    comp_clan2.members = [
        MagicMock(town_hall=13, role="coLeader"),
    ]

    bot.getClan.side_effect = [comp_clan1, comp_clan2]

    # Mock fetch_emoji
    emoji15 = MagicMock(emoji_string="<:th15:1>")
    emoji14 = MagicMock(emoji_string="<:th14:2>")
    emoji13 = MagicMock(emoji_string="<:th13:3>")
    bot.fetch_emoji.side_effect = lambda th: {15: emoji15, 14: emoji14, 13: emoji13}[th]

    # Call the method
    cog = War(bot)
    await cog.cwl_compo(ctx, clan=clan, season="2023-10")

    ctx.send.assert_awaited_once()
    embed = ctx.send.call_args.kwargs['embed']

    assert embed.title == f"CWL TH Compositions - {clan.name}"
    assert embed.description == "Season: **2023-10**"
    assert embed.color == disnake.Color.green()
    assert embed.fields[0].name == "Clan One"
    assert "<:th15:1> 1" in embed.fields[0].value
    assert "<:th14:2> 1" in embed.fields[0].value
    assert embed.fields[1].name == "Clan Two"
    assert embed.fields[1].value == "<:th13:3> 1"
    assert embed.thumbnail.url == clan.badge.large


@pytest.mark.asyncio
@patch("commands.war.commands.get_cwl_wars")
async def test_cwl_compo_no_group(mock_get_cwl_wars, bot, ctx, clan):
    # No group returned
    mock_get_cwl_wars.return_value = (None, None, clan, None)

    cog = War(bot)
    await cog.cwl_compo(ctx, clan=clan, season="2023-10")

    ctx.send.assert_awaited_once()
    embed = ctx.send.call_args.kwargs['embed']
    assert "is not in CWL" in embed.description
    assert embed.color == disnake.Color.red()
    assert embed.thumbnail.url == clan.badge.large
