import asyncio
import pytest
import disnake
import nest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import coc
from commands.war.utils import create_cwl_status

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Constants for testing
SERVER_ID = 1355584329526280293
WAR_CLAN_NAME = "Legendary Lite"
WAR_CLAN_TAG = "#2CLQVGC2"
GENERAL_CLAN_NAME = "Divine Kingdom"
GENERAL_CLAN_TAG = "#LCQR002"

# Create mock classes for testing


class MockEmoji:
    def __init__(self, name):
        self.emoji_string = f":{name}:"


class MockBot:
    def __init__(self):
        self.emoji = MagicMock()
        self.emoji.green_check = MockEmoji("green_check")
        self.emoji.square_x_deny = MockEmoji("square_x_deny")
        self.emoji.wood_swords = MockEmoji("wood_swords")
        self.emoji.animated_clash_swords = MockEmoji("animated_clash_swords")
        self.clan_db = AsyncMock()
        self.coc_client = AsyncMock()
        self.gen_season_date = MagicMock(return_value="Season 2025-04")

    async def get_clans(self, tags):
        # Create mock clans based on tags
        mock_clans = []
        for tag in tags:
            if tag == WAR_CLAN_TAG:
                clan = MagicMock()
                clan.name = WAR_CLAN_NAME
                clan.tag = WAR_CLAN_TAG
                clan.war_league = MagicMock()
                clan.war_league.name = "Champion I"
                mock_clans.append(clan)
            elif tag == GENERAL_CLAN_TAG:
                clan = MagicMock()
                clan.name = GENERAL_CLAN_NAME
                clan.tag = GENERAL_CLAN_TAG
                clan.war_league = MagicMock()
                clan.war_league.name = "Master I"
                mock_clans.append(clan)
        return mock_clans


class MockGuild:
    def __init__(self):
        self.id = SERVER_ID
        self.name = "Test Server"


@pytest.fixture
def mock_bot():
    return MockBot()


@pytest.fixture
def mock_guild():
    return MockGuild()


@pytest.mark.asyncio
async def test_create_cwl_status_no_category(mock_bot, mock_guild):
    # Set up the database to return both clan tags
    mock_bot.clan_db.distinct.return_value = [WAR_CLAN_TAG, GENERAL_CLAN_TAG]

    # Mock league responses
    mock_league = MagicMock()
    mock_league.state = "preparation"
    mock_bot.coc_client.get_league_group.return_value = mock_league

    # Call the function
    embed = await create_cwl_status(bot=mock_bot, guild=mock_guild, categories=None)

    # Assert results
    assert embed.title == f"__**{mock_guild.name} CWL Status**__"
    assert embed.color == disnake.Color.green()
    assert len(embed.fields) >= 2  # At least one league + Legend
    assert embed.fields[-1].name == "Legend"
    field_values = " ".join(
        field.value for field in embed.fields if field.name != "Legend")
    assert WAR_CLAN_NAME in field_values
    assert GENERAL_CLAN_NAME in field_values


@pytest.mark.asyncio
async def test_create_cwl_status_general_category(mock_bot, mock_guild):
    # Set up the database to return only the General clan tag
    mock_bot.clan_db.distinct.return_value = [GENERAL_CLAN_TAG]

    # Mock league responses
    mock_league = MagicMock()
    mock_league.state = "preparation"
    mock_bot.coc_client.get_league_group.return_value = mock_league

    # Call the function
    embed = await create_cwl_status(bot=mock_bot, guild=mock_guild, categories=["General"])

    # Assert results
    assert embed.title == f"__**{mock_guild.name} CWL Status - General**__"
    assert embed.color == disnake.Color.green()
    assert len(embed.fields) >= 2  # At least one league + Legend
    field_values = " ".join(
        field.value for field in embed.fields if field.name != "Legend")
    assert GENERAL_CLAN_NAME in field_values
    assert WAR_CLAN_NAME not in field_values


@pytest.mark.asyncio
async def test_create_cwl_status_war_category(mock_bot, mock_guild):
    # Set up the database to return only the War clan tag
    mock_bot.clan_db.distinct.return_value = [WAR_CLAN_TAG]

    # Mock league responses
    mock_league = MagicMock()
    mock_league.state = "preparation"
    mock_bot.coc_client.get_league_group.return_value = mock_league

    # Call the function
    embed = await create_cwl_status(bot=mock_bot, guild=mock_guild, categories=["War"])

    # Assert results
    assert embed.title == f"__**{mock_guild.name} CWL Status - War**__"
    assert embed.color == disnake.Color.green()
    assert len(embed.fields) >= 2  # At least one league + Legend
    field_values = " ".join(
        field.value for field in embed.fields if field.name != "Legend")
    assert WAR_CLAN_NAME in field_values
    assert GENERAL_CLAN_NAME not in field_values


@pytest.mark.asyncio
async def test_create_cwl_status_multiple_categories(mock_bot, mock_guild):
    # Set up the database to return both clan tags
    mock_bot.clan_db.distinct.return_value = [WAR_CLAN_TAG, GENERAL_CLAN_TAG]

    # Mock league responses
    mock_league = MagicMock()
    mock_league.state = "preparation"
    mock_bot.coc_client.get_league_group.return_value = mock_league

    # Call the function
    embed = await create_cwl_status(bot=mock_bot, guild=mock_guild, categories=["War", "General"])

    # Assert results
    assert embed.title == f"__**{mock_guild.name} CWL Status - War, General**__"
    assert embed.color == disnake.Color.green()
    assert len(embed.fields) >= 2  # At least one league + Legend
    field_values = " ".join(
        field.value for field in embed.fields if field.name != "Legend")
    assert WAR_CLAN_NAME in field_values
    assert GENERAL_CLAN_NAME in field_values


@pytest.mark.asyncio
async def test_create_cwl_status_invalid_category(mock_bot, mock_guild):
    # Set up the database to return no clan tags (no clans in the invalid category)
    mock_bot.clan_db.distinct.return_value = []

    # Call the function
    embed = await create_cwl_status(bot=mock_bot, guild=mock_guild, categories=["Invalid"])

    # Assert results
    assert "No clans found in categories Invalid" in embed.description
    assert embed.color == disnake.Color.red()
    assert len(embed.fields) == 0


@pytest.mark.asyncio
async def test_create_cwl_status_different_war_states(mock_bot, mock_guild):
    # Set up the database to return both clan tags
    mock_bot.clan_db.distinct.return_value = [WAR_CLAN_TAG, GENERAL_CLAN_TAG]

    # Set up different war states for each clan
    async def get_league_group_side_effect(tag):
        mock_league = MagicMock()
        if tag == WAR_CLAN_TAG:
            mock_league.state = "inWar"
        else:
            mock_league.state = "preparation"
        return mock_league

    mock_bot.coc_client.get_league_group.side_effect = get_league_group_side_effect

    # Call the function
    embed = await create_cwl_status(bot=mock_bot, guild=mock_guild, categories=None)

    # Assert results
    assert embed.title == f"__**{mock_guild.name} CWL Status**__"
    assert embed.color == disnake.Color.green()
    # Check that both clans are included with different statuses
    field_values = " ".join(
        field.value for field in embed.fields if field.name != "Legend")
    assert WAR_CLAN_NAME in field_values
    assert GENERAL_CLAN_NAME in field_values
    assert ":wood_swords:" in field_values  # For inWar
    assert ":green_check:" in field_values  # For preparation


@pytest.mark.asyncio
async def test_create_cwl_status_coc_not_found_exception(mock_bot, mock_guild):
    # Set up the database to return both clan tags
    mock_bot.clan_db.distinct.return_value = [WAR_CLAN_TAG]

    # Mock the coc.NotFound exception
    mock_bot.coc_client.get_league_group.side_effect = coc.NotFound

    # Call the function
    embed = await create_cwl_status(bot=mock_bot, guild=mock_guild, categories=None)

    # Assert results
    assert embed.title == f"__**{mock_guild.name} CWL Status**__"
    assert embed.color == disnake.Color.green()
    field_values = " ".join(
        field.value for field in embed.fields if field.name != "Legend")
    assert WAR_CLAN_NAME in field_values
    assert ":square_x_deny:" in field_values  # For NotFound
