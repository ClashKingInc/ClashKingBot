import disnake
from disnake.ext import commands
import pendulum as pend
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

            status_roles.sort(key=lambda role: role['months'], reverse=True)

            bot_member = guild.me
            for x, member in enumerate(guild.members):
                if member.bot:
                    continue

                # Calculate the number of months the member has been in the server
                joined_at = member.joined_at
                now = pend.now(tz=pend.UTC)
                num_months = (now.year - joined_at.year) * 12 + (now.month - joined_at.month)

                # Sort the status roles by months in descending order

                current_roles = set(member.roles)

                # Determine which roles to add and remove
                roles_to_add = []
                roles_to_remove = []

                for role in status_roles:
                    role_obj = disnake.utils.get(guild.roles, id=role['id'])
                    if role_obj is None:
                        continue

                    if bot_member.top_role <= role_obj:
                        continue

                    if num_months >= role['months']:
                        if role_obj not in current_roles:
                            roles_to_add.append(role_obj)
                    else:
                        if role_obj in current_roles:
                            roles_to_remove.append(role_obj)

                # Add and remove roles accordingly
                try:
                    if roles_to_add:
                        await member.add_roles(*roles_to_add)
                    if roles_to_remove:
                        await member.remove_roles(*roles_to_remove)
                except:
                    continue




def setup(bot: CustomClient):
    bot.add_cog(AutoEvalBackground(bot))
