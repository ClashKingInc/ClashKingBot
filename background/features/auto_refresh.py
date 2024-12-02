import disnake
import pendulum as pend
from disnake.ext import commands

from classes.bot import CustomClient


class AutoEvalBackground(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.scheduler.add_job(self.status_roles, 'interval', minutes=60)

    async def status_roles(self):
        servers_with_status_roles = await self.bot.server_db.find({'status_roles.discord': {'$exists': True, '$ne': {}}}).to_list(length=None)

        for server_config in servers_with_status_roles:
            if server_config.get('server') not in self.bot.OUR_GUILDS:
                continue

            status_roles = server_config.get('status_roles', {}).get('discord', [])

            guild = await self.bot.getch_guild(guild_id=server_config.get('server'))
            if guild is None:
                continue

            if not guild.chunked:
                if guild.id not in self.bot.STARTED_CHUNK:
                    await guild.chunk(cache=True)
                else:
                    self.bot.STARTED_CHUNK.add(guild.id)

            status_roles.sort(key=lambda role: role['months'], reverse=True)
            status_roles_map: dict[int, tuple[dict, disnake.Role]] = {
                role['id']: (role, disnake.utils.get(guild.roles, id=role['id'])) for role in status_roles}

            bot_member = guild.me

            for count, member in enumerate(guild.members, start=1):
                if member.bot:
                    continue

                # Calculate the number of months the member has been in the server
                joined_at = member.joined_at
                now = pend.now(tz=pend.UTC)
                num_months = (now.year - joined_at.year) * 12 + (now.month - joined_at.month)

                current_roles = set(member.roles)

                role_to_add = None
                roles_to_remove = []
                for role, role_obj in status_roles_map.values():
                    if bot_member.top_role <= role_obj:
                        continue

                    # if they have earned it, and role to be added leads to false, but they dont have it yet
                    if num_months >= role['months'] and role_to_add is None:
                        if role_obj not in current_roles:
                            role_to_add = role_obj
                        else:
                            role_to_add = True
                    # once it has found 1 role to add, any others should be removed, if they have them
                    elif role_obj in current_roles:
                        if role_obj in current_roles:
                            roles_to_remove.append(role_obj)

                try:
                    if isinstance(role_to_add, disnake.Role):
                        await member.add_roles(*[role_to_add], reason="Tenure Roles")
                    if roles_to_remove:
                        await member.remove_roles(*roles_to_remove, reason="Tenure Roles")
                except Exception as e:
                    continue


def setup(bot: CustomClient):
    bot.add_cog(AutoEvalBackground(bot))
