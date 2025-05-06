import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pendulum as pend
from datetime import datetime
from disnake.ext import commands
import disnake
from classes.bot import CustomClient
# Adjust import based on your file structure
from background.features.auto_refresh import AutoEvalBackground


class TestAutoEvalBackground(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = MagicMock(spec=CustomClient)
        self.bot.scheduler = MagicMock()
        self.bot.OUR_GUILDS = {12345}
        self.bot.STARTED_CHUNK = set()

        # Mock server_db.find to return a mock query object
        self.bot.server_db = MagicMock()
        self.find_mock = AsyncMock()
        self.bot.server_db.find = MagicMock(return_value=self.find_mock)

        self.cog = AutoEvalBackground(self.bot)

        # Mock guild and roles
        self.guild = MagicMock()
        self.guild.id = 12345
        self.guild.chunked = True
        self.guild.me = MagicMock()
        # Configure top_role with position and comparison support
        self.guild.me.top_role = MagicMock(position=10)
        self.guild.me.top_role.__le__.side_effect = lambda other: self.guild.me.top_role.position <= other.position
        self.bot.getch_guild = AsyncMock(return_value=self.guild)

        # Mock pendulum.now for consistent time
        self.mock_now = pend.datetime(2025, 4, 12, tz="UTC")
        self.pendulum_patcher = patch(
            "pendulum.now", return_value=self.mock_now)
        self.pendulum_patcher.start()

    def tearDown(self):
        self.pendulum_patcher.stop()

    async def test_status_roles_no_servers(self):
        """Test when no servers have status roles configured."""
        self.find_mock.to_list = AsyncMock(return_value=[])

        await self.cog.status_roles()

        self.bot.getch_guild.assert_not_called()
        self.assertFalse(self.bot.STARTED_CHUNK)

    async def test_status_roles_invalid_guild(self):
        """Test when the guild is not in OUR_GUILDS."""
        server_config = {"server": 99999, "status_roles": {
            "discord": [{"id": 1, "months": 6}]}}
        self.find_mock.to_list = AsyncMock(return_value=[server_config])

        await self.cog.status_roles()

        self.bot.getch_guild.assert_not_called()
        self.assertFalse(self.bot.STARTED_CHUNK)

    async def test_status_roles_none_role(self):
        """Test handling of NoneType roles to prevent TypeError."""
        server_config = {
            "server": 12345,
            "status_roles": {
                "discord": [
                    {"id": 1, "months": 6},  # Role exists
                    {"id": 2, "months": 3},  # Role does not exist
                ]
            }
        }
        self.find_mock.to_list = AsyncMock(return_value=[server_config])

        # Mock roles
        role1 = MagicMock(position=5)
        role1.id = 1
        role1.__le__.side_effect = lambda other: role1.position <= other.position
        role1.__class__ = disnake.Role
        self.guild.roles = [role1]
        self.guild.members = []

        # Mock disnake.utils.get
        def mock_get(roles, id):
            return role1 if id == 1 else None

        with patch("disnake.utils.get", side_effect=mock_get):
            await self.cog.status_roles()

        # Ensure no TypeError occurs and processing continues
        self.bot.getch_guild.assert_called_once_with(guild_id=12345)
        self.assertFalse(self.bot.STARTED_CHUNK)

    async def test_status_roles_assign_and_remove(self):
        """Test assigning a role and removing others based on tenure."""
        server_config = {
            "server": 12345,
            "status_roles": {
                "discord": [
                    {"id": 1, "months": 6},
                    {"id": 2, "months": 3},
                ]
            }
        }
        self.find_mock.to_list = AsyncMock(return_value=[server_config])

        # Mock roles
        role1 = MagicMock(position=5)
        role1.id = 1
        role1.__le__.side_effect = lambda other: role1.position <= other.position
        role1.__class__ = disnake.Role
        role2 = MagicMock(position=3)
        role2.id = 2
        role2.__le__.side_effect = lambda other: role2.position <= other.position
        role2.__class__ = disnake.Role
        self.guild.roles = [role1, role2]

        # Mock member
        member = MagicMock()
        member.bot = False
        member.joined_at = pend.datetime(
            2024, 10, 12, tz="UTC")  # 6 months ago
        member.roles = [role2]  # Has lower role
        member.add_roles = AsyncMock()
        member.remove_roles = AsyncMock()
        self.guild.members = [member]

        # Mock disnake.utils.get
        def mock_get(roles, id):
            return role1 if id == 1 else role2 if id == 2 else None

        with patch("disnake.utils.get", side_effect=mock_get):
            await self.cog.status_roles()

        # Verify role1 is added, role2 is removed
        member.add_roles.assert_called_once_with(role1, reason="Tenure Roles")
        member.remove_roles.assert_called_once_with(
            role2, reason="Tenure Roles")

    async def test_status_roles_bot_member_higher_role(self):
        """Test when bot's top role is lower than or equal to the role."""
        server_config = {
            "server": 12345,
            "status_roles": {
                "discord": [
                    {"id": 1, "months": 6},  # Role higher than bot
                ]
            }
        }
        self.find_mock.to_list = AsyncMock(return_value=[server_config])

        # Mock roles
        role1 = MagicMock(position=10)  # Same position as bot's top role
        role1.id = 1
        role1.__le__.side_effect = lambda other: role1.position <= other.position
        role1.__class__ = disnake.Role
        self.guild.roles = [role1]
        self.guild.me.top_role.position = 10  # Bot's top role position

        # Mock member
        member = MagicMock()
        member.bot = False
        member.joined_at = pend.datetime(
            2024, 10, 12, tz="UTC")  # 6 months ago
        member.roles = []
        member.add_roles = AsyncMock()
        self.guild.members = [member]

        # Mock disnake.utils.get
        with patch("disnake.utils.get", return_value=role1):
            await self.cog.status_roles()

        # Verify no roles are added due to hierarchy
        member.add_roles.assert_not_called()

    async def test_status_roles_already_has_correct_role(self):
        """Test when member already has the correct role."""
        server_config = {
            "server": 12345,
            "status_roles": {
                "discord": [
                    {"id": 1, "months": 6},
                    {"id": 2, "months": 3},
                ]
            }
        }
        self.find_mock.to_list = AsyncMock(return_value=[server_config])

        # Mock roles
        role1 = MagicMock(position=5)
        role1.id = 1
        role1.__le__.side_effect = lambda other: role1.position <= other.position
        role1.__class__ = disnake.Role
        role2 = MagicMock(position=3)
        role2.id = 2
        role2.__le__.side_effect = lambda other: role2.position <= other.position
        role2.__class__ = disnake.Role
        self.guild.roles = [role1, role2]

        # Mock member
        member = MagicMock()
        member.bot = False
        member.joined_at = pend.datetime(
            2024, 10, 12, tz="UTC")  # 6 months ago
        member.roles = [role1]
        member.add_roles = AsyncMock()
        member.remove_roles = AsyncMock()
        self.guild.members = [member]

        # Mock disnake.utils.get
        def mock_get(roles, id):
            return role1 if id == 1 else role2 if id == 2 else None

        with patch("disnake.utils.get", side_effect=mock_get):
            await self.cog.status_roles()

        # Verify no roles are added or removed
        member.add_roles.assert_not_called()
        member.remove_roles.assert_not_called()

    async def test_status_roles_exception_handling(self):
        """Test exception handling during role assignment."""
        server_config = {
            "server": 12345,
            "status_roles": {
                "discord": [
                    {"id": 1, "months": 6},
                ]
            }
        }
        self.find_mock.to_list = AsyncMock(return_value=[server_config])

        # Mock roles
        role1 = MagicMock(position=5)
        role1.id = 1
        role1.__le__.side_effect = lambda other: role1.position <= other.position
        role1.__class__ = disnake.Role
        self.guild.roles = [role1]

        # Mock member
        member = MagicMock()
        member.bot = False
        member.joined_at = pend.datetime(
            2024, 10, 12, tz="UTC")  # 6 months ago
        member.roles = []
        member.add_roles = AsyncMock(side_effect=Exception("Permission error"))
        self.guild.members = [member]

        # Mock disnake.utils.get
        with patch("disnake.utils.get", return_value=role1):
            await self.cog.status_roles()

        # Verify exception is caught and processing continues
        member.add_roles.assert_called_once_with(role1, reason="Tenure Roles")


if __name__ == "__main__":
    unittest.main()
