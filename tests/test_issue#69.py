import os
import sys
import pytest
import importlib.util
from unittest.mock import AsyncMock, MagicMock
import disnake

# Add parent directory to path to access your bot files
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load commands.py as a module named "bot_commands" using importlib
spec = importlib.util.spec_from_file_location("bot_commands", os.path.join(sys.path[0], "commands.py"))
bot_commands = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_commands)

# Now you can access Strikes cog like this:
Strikes = bot_commands.Strikes

@pytest.mark.asyncio
async def test_strike_clear_deletes_strikes():
    # Create a mock context
    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 1234
    mock_ctx.send = AsyncMock()

    # Create a mock clan with a .tag property
    mock_clan = MagicMock()
    mock_clan.tag = "ABC123"

    # Initialize the cog with a mocked bot
    cog = Strikes(bot=MagicMock())

    # Simulate finding at least one strike
    cog.bot.strikelist.find_one = AsyncMock(return_value={"strike_id": "test"})

    # Simulate successful deletion
    mock_delete_result = MagicMock()
    mock_delete_result.deleted_count = 3
    cog.bot.strikelist.delete_many = AsyncMock(return_value=mock_delete_result)

    # Call the strike_clear method
    await cog.strike_clear(mock_ctx, clan=mock_clan)

    # Verify delete_many was called with correct query
    cog.bot.strikelist.delete_many.assert_awaited_once_with({
        "$and": [{"clan": "ABC123"}, {"server": 1234}]
    })

    # Verify ctx.send was called with a success embed
    args, kwargs = mock_ctx.send.call_args
    embed = args[0]
    assert isinstance(embed, disnake.Embed)
    assert f"Cleared {mock_delete_result.deleted_count} strikes" in embed.description
