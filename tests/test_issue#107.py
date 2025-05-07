import pytest
import time

from unittest.mock import AsyncMock, MagicMock, patch
from commands.components.buttons import button_logic, user_refresh_cooldowns

@pytest.mark.asyncio
async def test_cooldown():
    user_refresh_cooldowns.clear()

    mock_ctx = AsyncMock()
    mock_ctx.author.id = 12345
    mock_ctx.guild = MagicMock(id=67890)
    mock_ctx.response.defer = AsyncMock()
    mock_ctx.message = MagicMock()
    mock_ctx.message.interaction = MagicMock()
    mock_ctx.message.interaction.author.id = 12345

    mock_bot = MagicMock()
    mock_bot.ck_client.get_server_embed_color = AsyncMock(return_value=0x000000)

    dummy_embed = MagicMock()
    dummy_func = AsyncMock(return_value=dummy_embed)

    with patch("commands.components.buttons.registered_functions", {
        "someprefix": (dummy_func, "", False, False, False)
    }):
        result1 = await button_logic("someprefix:refresh", mock_bot, mock_ctx.guild, "en-US", mock_ctx)
        assert result1[0] == dummy_embed

        result2 = await button_logic("someprefix:refresh", mock_bot, mock_ctx.guild, "en-US", mock_ctx)
        assert result2 == (None, 0)

        time.sleep(2.1)
        result3 = await button_logic("someprefix:refresh", mock_bot, mock_ctx.guild, "en-US", mock_ctx)
        assert result3[0] == dummy_embed

@pytest.mark.asyncio
async def test_no_ctx():
    user_refresh_cooldowns.clear()

    bot = MagicMock()
    bot.ck_client.get_server_embed_color = AsyncMock(return_value=0x000000)

    result = await button_logic(
        button_data="someprefix:refresh",
        bot=bot,
        guild=MagicMock(id=123),
        locale="en-US",
        ctx=None,
    )
    assert result is not None


@pytest.mark.asyncio
async def test_unknown_function():
    user_refresh_cooldowns.clear()

    mock_ctx = AsyncMock()
    mock_ctx.author.id = 222
    mock_ctx.response.defer = AsyncMock()
    mock_ctx.guild = MagicMock()
    mock_ctx.message = MagicMock()
    mock_ctx.message.interaction.author.id = 222

    result = await button_logic(
        button_data="notregistered:refresh",
        bot=MagicMock(),
        guild=MagicMock(id=123),
        locale="en-US",
        ctx=mock_ctx,
    )
    assert result == (None, 0)

