import coc
import disnake
from disnake.ext import commands

from background.logs.events import clan_ee, player_ee
from classes.bot import CustomClient
from classes.DatabaseClient.Classes.settings import DatabaseServer
from commands.eval.utils import logic
from utility.constants import DEFAULT_EVAL_ROLE_TYPES, EMBED_COLOR_CLASS


class AutoEval(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.player_ee = player_ee
        self.clan_ee.on('members_join_leave', self.clan_auto_refresh)
        self.player_ee.on('role', self.player_auto_refresh)
        self.player_ee.on('townHallLevel', self.player_auto_refresh)
        self.player_ee.on('league', self.player_auto_refresh)

    async def player_auto_refresh(self, event):

        player_tag = event.get('new_player').get('tag')
        clan_tag = event.get('new_player').get('clan', {}).get('tag', '')
        player_name = event.get('new_player').get('name')

        server_ids = await self.bot.clan_db.distinct('server', filter={'tag': clan_tag})
        for server_id in server_ids:
            db_server = await self.bot.ck_client.get_server_settings(server_id=server_id)

            if db_server.server_id not in self.bot.OUR_GUILDS or not db_server.auto_eval_status:
                continue

            convert_trigger = {
                'townHallLevel': 'townhall_change',
                'role': 'role_change',
                'league': 'league_change',
            }
            if (trigger_name := convert_trigger.get(event.get('trigger'), event.get('trigger'))) not in db_server.autoeval_triggers:
                continue

            link = await self.bot.link_client.get_link(player_tag)
            if link is not None:
                server = await self.bot.getch_guild(server_id)
                if server is None:
                    continue
                discord_member = await server.getch_member(link)
                if discord_member is None:
                    continue

                for role in discord_member.roles:
                    if role.id in db_server.blacklisted_roles:
                        return

                try:
                    await logic(
                        bot=self.bot,
                        guild=server,
                        db_server=db_server,
                        members=[discord_member],
                        role_or_user=discord_member,
                        eval_types=DEFAULT_EVAL_ROLE_TYPES,
                        role_treatment=db_server.role_treatment,
                        reason=f'Triggered by {trigger_name} ({player_name})',
                    )
                except:
                    pass


    async def clan_auto_refresh(self, event):

        clan = coc.Clan(data=event['new_clan'], client=self.bot.coc_client)

        server_ids = await self.bot.clan_db.distinct('server', filter={'tag': clan.tag})
        for server_id in server_ids:
            db_server = await self.bot.ck_client.get_server_settings(server_id=server_id)

            if db_server.server_id not in self.bot.OUR_GUILDS or not db_server.auto_eval_status:
                continue

            joined = event.get('joined', [])
            left = event.get('left', [])

            to_run = []
            if 'member_join' in db_server.autoeval_triggers:
                to_run.extend(joined)

            if 'member_leave' in db_server.autoeval_triggers:
                to_run.extend(left)

            if not to_run:
                continue

            links = await self.bot.link_client.get_links(*[n.get("tag") for n in to_run])
            discord_users = set(id for _, id in links if id is not None)

            server = await self.bot.getch_guild(server_id)
            if server is None:
                continue
            discord_members = await server.getch_members(list(discord_users))
            if not discord_members:
                continue

            if db_server.blacklisted_roles:
                discord_members = [member for member in discord_members
                                   if not any(role.id in db_server.blacklisted_roles for role in member.roles)]

            try:
                await logic(
                    bot=self.bot,
                    guild=server,
                    db_server=db_server,
                    members=discord_members,
                    role_or_user=clan,
                    eval_types=DEFAULT_EVAL_ROLE_TYPES,
                    role_treatment=db_server.role_treatment,
                    reason=f'Triggered by clan join/leave ({clan.name})',
                )
            except:
                #message exceptions can happen
                pass

def setup(bot: CustomClient):
    bot.add_cog(AutoEval(bot))
