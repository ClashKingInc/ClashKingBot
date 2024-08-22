import coc
import disnake
from disnake.ext import commands

from background.logs.events import clan_ee
from classes.bot import CustomClient
from classes.DatabaseClient.Classes.settings import DatabaseClan


class BanEvents(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on('members_join_leave', self.ban_alerts)

    async def ban_alerts(self, event):
        clan = coc.Clan(data=event['new_clan'], client=self.bot.coc_client)
        members_joined = [coc.ClanMember(data=member, client=self.bot.coc_client, clan=clan) for member in event.get('joined', [])]

        if members_joined:
            ban_results = await self.bot.banlist.find({'VillageTag': {'$in': [m.tag for m in members_joined]}}).to_list(length=None)

            if not ban_results:
                return

            # lookup this clan (the clan could be on multiple server's theoretically)
            clan_results = await self.bot.clan_db.find({'tag': clan.tag}).to_list(length=None)
            for clan_result in clan_results:
                db_clan = DatabaseClan(bot=self.bot, data=clan_result)
                if db_clan.server_id not in self.bot.OUR_GUILDS:
                    continue

                server = await self.bot.getch_guild(db_clan.server_id)
                if server is None:
                    continue

                # for each of the banned players, send a ban message (or warning) depending
                role = f'<@&{db_clan.member_role}>'

                this_servers_ban_results = [b_r for b_r in ban_results if b_r.get('server') == db_clan.server_id]
                if this_servers_ban_results:
                    for ban_result in this_servers_ban_results:
                        member = coc.utils.get(members_joined, tag=ban_result.get('VillageTag'))

                        ban_server_id = ban_result.get('server')

                        # if the server of the clan the banned user just joined equals the server that the ban was issued in
                        if db_clan.server_id == ban_server_id:
                            notes = ban_result.get('Notes')
                            if notes == '':
                                notes = 'No Reason Given'
                            date = ban_result.get('DateCreated')[:10]

                            embed = disnake.Embed(
                                description=f'[WARNING! BANNED PLAYER {member.name} JOINED]({member.share_link})',
                                color=disnake.Color.red(),
                            )
                            embed.add_field(
                                name='Banned Player.',
                                value=f'Player {member.name} [{member.tag}] has joined {clan.name} and is on the {server.name} BAN list!\n\n'
                                f'Banned on: {date}\nReason: {notes}',
                            )
                            embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/843624785560993833/932701461614313562/2EdQ9Cx.png')

                            try:
                                channel = await self.bot.getch_channel(channel_id=db_clan.ban_alert_channel or db_clan.clan_channel)
                                await channel.send(content=role, embed=embed)
                            except (disnake.NotFound, disnake.Forbidden):
                                if db_clan.ban_alert_channel is None:
                                    await db_clan.set_clan_channel(id=None)
                                else:
                                    await db_clan.set_ban_alert_channel(id=None)
                                continue
                else:
                    small_server_result = await self.bot.server_db.find_one({'server': db_clan.server_id}, {'server': 1, 'dismissed_warns': 1})
                    players_set = set()
                    for ban_result in ban_results:
                        member = coc.utils.get(members_joined, tag=ban_result.get('VillageTag'))
                        if member.tag in players_set or member.tag in small_server_result.get('dismissed_warns', []):
                            continue
                        players_set.add(member.tag)
                        servers_banned_in = await self.bot.banlist.distinct('server', filter={'VillageTag': member.tag})
                        server_list = []
                        if self.bot.user.public_flags.verified_bot:
                            for banned_server in servers_banned_in:
                                banned_server = self.bot.get_guild(banned_server)
                                if banned_server is not None:
                                    server_list.append(f'{banned_server.name} ({banned_server.member_count} members)')
                            server_list = ':\n' + '\n'.join(server_list)
                        if not server_list:
                            server_list = ''
                        embed = disnake.Embed(
                            description=f'[WARNING! {member.name} JOINED]({member.share_link})\n'
                            f'This player has been banned in {len(servers_banned_in)} other server(s){server_list}\n'
                            f'This is just a warning, purely for informational purposes & can be dismissed with the button below.',
                            color=disnake.Color.yellow(),
                        )
                        embed.set_thumbnail(url='https://clashkingfiles.b-cdn.net/bot/warning.jpg')
                        try:
                            buttons = disnake.ui.ActionRow(
                                disnake.ui.Button(label='Dismiss', style=disnake.ButtonStyle.grey, custom_id=f'DismissWarn_{member.tag}')
                            )
                            channel = await self.bot.getch_channel(channel_id=db_clan.ban_alert_channel or db_clan.clan_channel)
                            await channel.send(embed=embed, components=[buttons])
                        except (disnake.NotFound, disnake.Forbidden):
                            if db_clan.ban_alert_channel is None:
                                await db_clan.set_clan_channel(id=None)
                            else:
                                await db_clan.set_ban_alert_channel(id=None)
                            continue

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):

        if 'DismissWarn' in ctx.data.custom_id:
            await ctx.response.defer(ephemeral=True)

            whitelist_check = await self.bot.white_list_check(ctx=ctx, command_name='ban remove')
            manage_guild_perms = ctx.user.guild_permissions.manage_guild

            if whitelist_check or manage_guild_perms:
                await self.bot.server_db.update_one(
                    {'server': ctx.guild.id},
                    {'$addToSet': {'dismissed_warns': ctx.data.custom_id.split('_')[-1]}},
                )
                await ctx.message.edit(components=[])
                return await ctx.send(content='Player warning now dismissed!', ephemeral=True)

            await ctx.send(content='You do not have permissions to dismiss this warning! Permissions tied to `/ban remove`.', ephemeral=True)


def setup(bot: CustomClient):
    bot.add_cog(BanEvents(bot))
