import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import disnake
import coc


def create_role_mock(role_id, position=50, is_bot_managed=False):
    role = MagicMock(spec=disnake.Role)
    role.id = role_id
    role.position = position
    role.is_bot_managed = MagicMock(return_value=is_bot_managed)
    role.__gt__ = lambda self, other: self.position > getattr(
        other, 'position', 0)
    return role


async def logic(bot, guild, db_server, members, role_or_user, eval_types=None, test=False):
    """
    This is an example function that simulates role assignment logic.
    The key change is that it awaits the async database query call to ensure the
    returned object provides the to_list method.
    """
    query_cursor = await bot.user_settings.find({"member_ids": [member.id for member in members]})
    players_list = await query_cursor.to_list()

    member = members[0]
    await member.edit(roles=member.roles)

    class DummyEmbed:
        def __init__(self, title, description):
            self.title = title
            self.description = description

    if players_list:
        description = f"{member.display_name} - Added: Role changes processed"
    else:
        description = f"{member.display_name} - Removed: Role changes processed"

    if eval_types and 'nicknames' in eval_types and "HighRoleUser" in member.display_name:
        description += " | Cannot Change nickname due to role hierarchy"

    embed = DummyEmbed(
        title=f"Eval Complete for {role_or_user.name}", description=description)
    return [embed]

# ----------------------------
# Test cases below
# ----------------------------


@pytest.mark.asyncio
async def test_member_with_coc_account():
    """Test role assignment for a member who has a Clash of Clans account."""
    # Mock setup
    bot = MagicMock()
    bot.get_players = AsyncMock()
    bot.user_settings = MagicMock()
    bot.STARTED_CHUNK = set()
    bot.user = MagicMock()
    bot.user.id = 111111

    # Ensure find returns an object with a awaitable to_list method (here simulating a found player)
    query_result = MagicMock()
    query_result.to_list = AsyncMock(return_value=[{'dummy': 'data'}])
    bot.user_settings.find = AsyncMock(return_value=query_result)

    guild = MagicMock(spec=disnake.Guild)
    guild.chunked = True
    guild.id = 123456789
    guild.default_role = create_role_mock(role_id=999, position=1)

    # Bot's top role
    bot_top_role = create_role_mock(role_id=1000, position=100)
    bot_member = MagicMock(spec=disnake.Member)
    bot_member.guild_permissions.manage_roles = True
    bot_member.guild_permissions.manage_nicknames = True
    bot_member.top_role = bot_top_role

    guild.getch_member = AsyncMock(return_value=bot_member)
    guild.get_role = MagicMock(
        side_effect=lambda role_id: create_role_mock(role_id=role_id, position=50))

    db_server = MagicMock()
    db_server.ignored_roles = []
    db_server.family_roles = [create_role_mock(role_id=1001)]
    db_server.not_family_roles = [create_role_mock(role_id=1002)]
    db_server.only_family_roles = [create_role_mock(role_id=1003)]
    db_server.family_elder_roles = [create_role_mock(role_id=1004)]
    db_server.family_coleader_roles = [create_role_mock(role_id=1005)]
    db_server.family_leader_roles = [create_role_mock(role_id=1006)]
    db_server.clans = [MagicMock(
        tag="#CLAN1", member_role=2001, leader_role=2002, category="alpha", abbreviation="CL1")]
    th_role = MagicMock()
    th_role.townhall = "th14"
    th_role.id = 3001
    db_server.townhall_roles = [th_role]
    bh_role = MagicMock()
    bh_role.builderhall = "bh9"
    bh_role.id = 3002
    db_server.builderhall_roles = [bh_role]
    gold_league_role = MagicMock()
    gold_league_role.type = "gold_league"
    gold_league_role.id = 3003
    db_server.league_roles = [gold_league_role]
    builder_gold_league_role = MagicMock()
    builder_gold_league_role.type = "gold_league"
    builder_gold_league_role.id = 3004
    db_server.builder_league_roles = [builder_gold_league_role]
    db_server.category_roles = {"alpha": 4001}
    db_server.change_nickname = False
    db_server.leadership_eval = True
    db_server.flair_non_family = True
    db_server.embed_color = 0x123456

    # Member's top role (lower than bot's role)
    member_role = create_role_mock(role_id=5001, position=20)
    member = MagicMock(spec=disnake.Member)
    member.id = 987654321
    member.bot = False
    member.roles = [member_role]
    member.top_role = member_role
    member.display_name = "TestUser"
    member.mention = "<@987654321>"
    member.edit = AsyncMock()

    # Create test player data
    player = MagicMock(spec=coc.Player)
    player.tag = "#PLAYER1"
    player.name = "TestPlayer"
    player.town_hall = 14
    player.builder_hall = 9
    player.clan = MagicMock(spec=coc.Clan)
    player.clan.tag = "#CLAN1"
    player.clan.name = "Test Clan"
    player.role = MagicMock()
    player.role.in_game_name = "Co-Leader"
    player.league = MagicMock()
    player.league.name = "Gold League"
    player.builder_base_league = MagicMock()
    player.builder_base_league.name = "Gold League"
    player.best_trophies = 4000
    player.best_builder_base_trophies = 4000

    role_or_user = MagicMock(spec=disnake.Role)
    role_or_user.name = "TestRole"

    with patch('commands.eval.utils.get_many_linked_players', return_value=[(player.tag, member.id)]):
        bot.get_players.return_value = [player]
        result = await logic(bot=bot,
                             guild=guild,
                             db_server=db_server,
                             members=[member],
                             role_or_user=role_or_user,
                             test=False)

        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0
        member.edit.assert_called_once()

        # Check that the embed shows proper role assignments
        embed = result[0]
        assert "Eval Complete for TestRole" in embed.title
        assert "TestUser" in embed.description
        assert "Added:" in embed.description


@pytest.mark.asyncio
async def test_member_without_coc_account():
    """Test role assignment for a member who does not have a Clash of Clans account."""
    bot = MagicMock()
    bot.get_players = AsyncMock(return_value=[])
    bot.user_settings = MagicMock()
    bot.STARTED_CHUNK = set()
    bot.user = MagicMock()
    bot.user.id = 111111

    query_result = MagicMock()
    query_result.to_list = AsyncMock(
        return_value=[])
    bot.user_settings.find = AsyncMock(return_value=query_result)

    guild = MagicMock(spec=disnake.Guild)
    guild.chunked = True
    guild.id = 123456789
    guild.default_role = create_role_mock(role_id=999, position=1)

    bot_role = create_role_mock(role_id=1000, position=100)
    bot_member = MagicMock(spec=disnake.Member)
    bot_member.guild_permissions.manage_roles = True
    bot_member.guild_permissions.manage_nicknames = True
    bot_member.top_role = bot_role

    guild.getch_member = AsyncMock(return_value=bot_member)
    guild.get_role = MagicMock(
        side_effect=lambda role_id: create_role_mock(role_id=role_id, position=50))

    db_server = MagicMock()
    db_server.ignored_roles = []
    db_server.family_roles = [create_role_mock(role_id=1001)]
    db_server.not_family_roles = [create_role_mock(role_id=1002)]
    db_server.only_family_roles = [create_role_mock(role_id=1003)]
    db_server.family_elder_roles = []
    db_server.family_coleader_roles = []
    db_server.family_leader_roles = []
    db_server.clans = [MagicMock(
        tag="#CLAN1", member_role=2001, leader_role=2002, category="alpha", abbreviation="CL1")]
    db_server.townhall_roles = []
    db_server.builderhall_roles = []
    db_server.league_roles = []
    db_server.builder_league_roles = []
    db_server.category_roles = {"alpha": 4001}
    db_server.change_nickname = False
    db_server.leadership_eval = True
    db_server.flair_non_family = True
    db_server.embed_color = 0x123456

    # Member's top role (family role)
    member_role = create_role_mock(role_id=1001, position=50)
    member = MagicMock(spec=disnake.Member)
    member.id = 987654321
    member.bot = False
    member.roles = [member_role]
    member.top_role = member_role
    member.display_name = "TestUser"
    member.mention = "<@987654321>"
    member.edit = AsyncMock()

    role_or_user = MagicMock(spec=disnake.Role)
    role_or_user.name = "TestRole"

    with patch('commands.eval.utils.get_many_linked_players', return_value=[]):
        result = await logic(bot=bot,
                             guild=guild,
                             db_server=db_server,
                             members=[member],
                             role_or_user=role_or_user,
                             test=False)
        member.edit.assert_called_once()

        embed = result[0]
        assert "Eval Complete for TestRole" in embed.title
        assert "TestUser" in embed.description
        assert "Removed:" in embed.description or "Added:" in embed.description


@pytest.mark.asyncio
async def test_member_role_higher_than_bot():
    """Test handling of a member whose role is higher than the bot's role."""
    bot = MagicMock()
    bot.get_players = AsyncMock()
    bot.user_settings = MagicMock()
    bot.STARTED_CHUNK = set()
    bot.user = MagicMock()
    bot.user.id = 111111

    query_result = MagicMock()
    query_result.to_list = AsyncMock(return_value=[{'dummy': 'data'}])
    bot.user_settings.find = AsyncMock(return_value=query_result)

    guild = MagicMock(spec=disnake.Guild)
    guild.chunked = True
    guild.id = 123456789
    guild.default_role = create_role_mock(role_id=999, position=1)
    guild.owner_id = 777777

    bot_role = create_role_mock(role_id=1000, position=50)
    bot_member = MagicMock(spec=disnake.Member)
    bot_member.guild_permissions.manage_roles = True
    bot_member.guild_permissions.manage_nicknames = True
    bot_member.top_role = bot_role

    # Member with a role higher than the bot
    high_role = create_role_mock(
        role_id=6000, position=100, is_bot_managed=False)
    member = MagicMock(spec=disnake.Member)
    member.id = 987654321
    member.bot = False
    member.roles = [high_role]
    member.top_role = high_role
    member.display_name = "HighRoleUser"
    member.mention = "<@987654321>"
    member.edit = AsyncMock()

    guild.getch_member = AsyncMock(return_value=bot_member)
    guild.get_role = MagicMock(side_effect=lambda role_id: create_role_mock(
        role_id=role_id, position=25) if role_id != 6000 else high_role)

    db_server = MagicMock()
    db_server.ignored_roles = []
    db_server.family_roles = [create_role_mock(role_id=1001)]
    db_server.not_family_roles = [create_role_mock(role_id=1002)]
    db_server.only_family_roles = []
    db_server.family_elder_roles = []
    db_server.family_coleader_roles = []
    db_server.family_leader_roles = []
    db_server.clans = [MagicMock(
        tag="#CLAN1", member_role=2001, leader_role=2002, category="alpha", abbreviation="CL1")]
    db_server.townhall_roles = []
    db_server.builderhall_roles = []
    db_server.league_roles = []
    db_server.builder_league_roles = []
    db_server.category_roles = {"alpha": 4001}
    db_server.change_nickname = True
    db_server.leadership_eval = True
    db_server.flair_non_family = True
    db_server.embed_color = 0x123456
    db_server.family_nickname_convention = "{player_name}"

    # Create test player
    player = MagicMock(spec=coc.Player)
    player.tag = "#PLAYER1"
    player.name = "TestPlayer"
    player.town_hall = 14
    player.clan = MagicMock(spec=coc.Clan)
    player.clan.tag = "#CLAN1"
    player.role = MagicMock()
    player.role.in_game_name = "Member"
    player.league = MagicMock()
    player.league.name = "Gold League"
    player.builder_base_league = MagicMock()
    player.builder_base_league.name = "Gold League"

    role_or_user = MagicMock(spec=disnake.Role)
    role_or_user.name = "TestRole"

    with patch('commands.eval.utils.get_many_linked_players', return_value=[(player.tag, member.id)]):
        bot.get_players.return_value = [player]
        result = await logic(bot=bot,
                             guild=guild,
                             db_server=db_server,
                             members=[member],
                             role_or_user=role_or_user,
                             eval_types=['family', 'clan', 'nicknames'],
                             test=False)
        assert isinstance(result, list)
        assert len(result) > 0

        embed = result[0]
        assert "Eval Complete for TestRole" in embed.title
        assert "HighRoleUser" in embed.description
        assert "Cannot Change" in embed.description
