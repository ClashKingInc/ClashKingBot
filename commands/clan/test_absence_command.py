import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import disnake


@pytest.fixture
def setup_bot():
    bot = MagicMock()
    bot.link_client = MagicMock()
    return bot


@pytest.fixture
def setup_ctx():
    ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    ctx.user = MagicMock()
    ctx.user.id = 123456789
    ctx.user.display_name = "TestUser"
    ctx.user.display_avatar.url = "https://example.com/avatar.jpg"
    ctx.edit_original_response = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_absence_command_success(setup_bot, setup_ctx):
    mock_clan_commands = MagicMock()

    async def mock_absence(ctx, player, start_date, end_date, reason):
        await ctx.edit_original_response(
            content=f"✅ Absence recorded for {player} from {start_date} to {end_date}\nReason: {reason}"
        )

    mock_clan_commands.absence = AsyncMock(side_effect=mock_absence)
    setup_bot.link_client.get_linked_players = AsyncMock(return_value=["#TEST123"])

    await mock_clan_commands.absence(
        ctx=setup_ctx,
        player="#TEST123",
        start_date="2024-03-20",
        end_date="2024-03-25",
        reason="Vacation"
    )

    setup_ctx.edit_original_response.assert_called_once_with(
        content="✅ Absence recorded for #TEST123 from 2024-03-20 to 2024-03-25\nReason: Vacation"
    )


@pytest.mark.asyncio
async def test_absence_command_no_linked_accounts(setup_bot, setup_ctx):
    mock_clan_commands = MagicMock()

    async def mock_absence(ctx, player, start_date, end_date, reason):
        await ctx.edit_original_response(
            content="❌ You don't have any Clash accounts linked to your Discord profile."
        )

    mock_clan_commands.absence = AsyncMock(side_effect=mock_absence)
    setup_bot.link_client.get_linked_players = AsyncMock(return_value=[])

    await mock_clan_commands.absence(
        ctx=setup_ctx,
        player="#TEST123",
        start_date="2024-03-20",
        end_date="2024-03-25",
        reason="Vacation"
    )

    setup_ctx.edit_original_response.assert_called_once_with(
        content="❌ You don't have any Clash accounts linked to your Discord profile."
    )


@pytest.mark.asyncio
async def test_absence_command_start_date_in_past(setup_ctx):
    mock_clan_commands = MagicMock()

    async def mock_absence(ctx, player, start_date, end_date, reason):
        await ctx.edit_original_response(
            content="❌ Start date cannot be in the past!"
        )

    mock_clan_commands.absence = AsyncMock(side_effect=mock_absence)

    await mock_clan_commands.absence(
        ctx=setup_ctx,
        player="#TEST123",
        start_date="2023-03-20",
        end_date="2024-03-25",
        reason="Vacation"
    )

    setup_ctx.edit_original_response.assert_called_once_with(
        content="❌ Start date cannot be in the past!"
    )


@pytest.mark.asyncio
async def test_absence_command_invalid_date_format(setup_ctx):
    mock_clan_commands = MagicMock()

    async def mock_absence(ctx, player, start_date, end_date, reason):
        await ctx.edit_original_response(
            content="❌ Invalid date format! Please use YYYY-MM-DD format."
        )

    mock_clan_commands.absence = AsyncMock(side_effect=mock_absence)

    await mock_clan_commands.absence(
        ctx=setup_ctx,
        player="#TEST123",
        start_date="03-20-2024",
        end_date="03-25-2024",
        reason="Vacation"
    )

    setup_ctx.edit_original_response.assert_called_once_with(
        content="❌ Invalid date format! Please use YYYY-MM-DD format."
    )


@pytest.mark.asyncio
async def test_absence_command_end_date_before_start_date(setup_ctx):
    mock_clan_commands = MagicMock()

    async def mock_absence(ctx, player, start_date, end_date, reason):
        await ctx.edit_original_response(
            content="❌ End date cannot be before start date!"
        )

    mock_clan_commands.absence = AsyncMock(side_effect=mock_absence)

    await mock_clan_commands.absence(
        ctx=setup_ctx,
        player="#TEST123",
        start_date="2024-03-25",
        end_date="2024-03-20",
        reason="Vacation"
    )

    setup_ctx.edit_original_response.assert_called_once_with(
        content="❌ End date cannot be before start date!"
    )


@pytest.mark.asyncio
async def test_absence_command_dates_exceed_one_year(setup_ctx):
    mock_clan_commands = MagicMock()

    async def mock_absence(ctx, player, start_date, end_date, reason):
        await ctx.edit_original_response(
            content="❌ Dates cannot be more than one year in the future!"
        )

    mock_clan_commands.absence = AsyncMock(side_effect=mock_absence)

    await mock_clan_commands.absence(
        ctx=setup_ctx,
        player="#TEST123",
        start_date="2025-03-20",
        end_date="2025-03-25",
        reason="Vacation"
    )

    setup_ctx.edit_original_response.assert_called_once_with(
        content="❌ Dates cannot be more than one year in the future!"
    )