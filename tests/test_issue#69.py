import pytest
from unittest.mock import AsyncMock, MagicMock
import disnake

from commands.strikes.commands import Strikes

@pytest.mark.asyncio
async def test_strike_clear_strikes():
    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 1234
    mock_ctx.send = AsyncMock()

    mock_clan = MagicMock()
    mock_clan.tag = "test313"

    cog = Strikes(bot=MagicMock())
    cog.bot.strikelist.find_one = AsyncMock(return_value={"strike_id": "abc"})

    mock_delete_result = MagicMock()
    mock_delete_result.deleted_count = 3
    cog.bot.strikelist.delete_many = AsyncMock(return_value=mock_delete_result)

    await cog.strike_clear_all.callback(cog, mock_ctx, clan=mock_clan)

    cog.bot.strikelist.delete_many.assert_awaited_once_with({
        "$and": [{"clan": "test313"}, {"server": 1234}]
    })

    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get("embed") or (args[0] if args else None)
    assert isinstance(embed, disnake.Embed)
    assert f"Cleared {mock_delete_result.deleted_count} strikes" in embed.description

@pytest.mark.asyncio
async def test_strike_clear_deletes_strikes():
    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 1234
    mock_ctx.send = AsyncMock()

    mock_clan = MagicMock()
    mock_clan.tag = "testy33"

    cog = Strikes(bot=MagicMock())
    cog.bot.strikelist.find_one = AsyncMock(return_value={"strike_id": "abc"})
    mock_delete_result = MagicMock(deleted_count=5)
    cog.bot.strikelist.delete_many = AsyncMock(return_value=mock_delete_result)

    await cog.strike_clear_all.callback(cog, mock_ctx, clan=mock_clan)

    cog.bot.strikelist.delete_many.assert_awaited_once_with({
        "$and": [{"clan": "testy33"}, {"server": 1234}]
    })

    embed = mock_ctx.send.call_args.kwargs.get("embed")
    assert isinstance(embed, disnake.Embed)
    assert f"Cleared {mock_delete_result.deleted_count} strikes" in embed.description

@pytest.mark.asyncio
async def test_strike_clear_no_strikes():
    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 5678
    mock_ctx.send = AsyncMock()

    mock_clan = MagicMock()
    mock_clan.tag = "xyz849"

    cog = Strikes(bot=MagicMock())
    cog.bot.strikelist.find_one = AsyncMock(return_value=None)

    await cog.strike_clear_all.callback(cog, mock_ctx, clan=mock_clan)

    cog.bot.strikelist.find_one.assert_awaited_once()
    cog.bot.strikelist.delete_many.assert_not_called()

    embed = mock_ctx.send.call_args.kwargs.get("embed")
    assert isinstance(embed, disnake.Embed)
    assert "All strikes in" in embed.description
    assert embed.color == disnake.Color.red()

@pytest.mark.asyncio
async def test_strike_clear_db_error_handling():
    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 1357
    mock_ctx.send = AsyncMock()

    mock_clan = MagicMock()
    mock_clan.tag = "error33"

    cog = Strikes(bot=MagicMock())
    cog.bot.strikelist.find_one = AsyncMock(side_effect=Exception("DB failed"))

    with pytest.raises(Exception, match="DB failed"):
        await cog.strike_clear_all.callback(cog, mock_ctx, clan=mock_clan)


@pytest.mark.asyncio
async def test_strike_clear_deletes_zero():
    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 2468
    mock_ctx.send = AsyncMock()

    mock_clan = MagicMock()
    mock_clan.tag = "ee34"

    cog = Strikes(bot=MagicMock())
    cog.bot.strikelist.find_one = AsyncMock(return_value={"strike_id": "abc"})
    mock_result = MagicMock(deleted_count=0)
    cog.bot.strikelist.delete_many = AsyncMock(return_value=mock_result)

    await cog.strike_clear_all.callback(cog, mock_ctx, clan=mock_clan)

    embed = mock_ctx.send.call_args.kwargs.get("embed")
    assert "Cleared 0 strikes" in embed.description

@pytest.mark.asyncio
async def test_strike_clear_date_deletes_strikes():

    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 777
    mock_ctx.send = AsyncMock()

    mock_clan = MagicMock()
    mock_clan.__str__.return_value = "TestClan"

    cog = Strikes(bot=MagicMock())
    cog.bot.strikelist.find_one = AsyncMock(return_value={"strike_id": "abc"})

    delete_result = MagicMock(deleted_count=2)
    cog.bot.strikelist.delete_many = AsyncMock(return_value=delete_result)

    await cog.strike_clear_date.callback(cog, mock_ctx, clan=mock_clan, time_range="Last Week")

    embed = mock_ctx.send.call_args.kwargs.get("embed")
    assert isinstance(embed, disnake.Embed)
    assert "Deleted 2 strikes from TestClan from the last week." in embed.description
    assert embed.color == disnake.Color.green()

@pytest.mark.asyncio
async def test_strike_clear_date_no_strikes():
    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 888
    mock_ctx.send = AsyncMock()

    mock_clan = MagicMock()
    mock_clan.__str__.return_value = "EmptyClan"

    cog = Strikes(bot=MagicMock())
    cog.bot.strikelist.find_one = AsyncMock(return_value=None)

    await cog.strike_clear_date.callback(cog, mock_ctx, clan=mock_clan, time_range="Last 90 Days")

    cog.bot.strikelist.delete_many.assert_not_called()

    embed = mock_ctx.send.call_args.kwargs.get("embed")
    assert "no strikes found" in embed.description.lower()
    assert embed.color == disnake.Color.red()

@pytest.mark.asyncio
async def test_strike_clear_date_invalid_range():
    mock_ctx = MagicMock(spec=disnake.ApplicationCommandInteraction)
    mock_ctx.guild.id = 999
    mock_ctx.send = AsyncMock()

    mock_clan = MagicMock()
    mock_clan.__str__.return_value = "EdgeClan"

    cog = Strikes(bot=MagicMock())
    cog.bot.strikelist.find_one = AsyncMock(return_value={"strike_id": "abc"})
    cog.bot.strikelist.delete_many = AsyncMock(return_value=MagicMock(deleted_count=1))

    await cog.strike_clear_date.callback(cog, mock_ctx, clan=mock_clan, time_range="invalid range")

    embed = mock_ctx.send.call_args.kwargs.get("embed")
    assert "Deleted 1 strikes from EdgeClan from the invalid range." in embed.description
