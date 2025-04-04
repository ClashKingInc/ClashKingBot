import coc
import disnake
from disnake.ext import commands

from background.logs.events import clan_ee
from classes.bot import CustomClient
from classes.DatabaseClient.Classes.settings import DatabaseClan
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.constants import SHORT_PLAYER_LINK
from utility.discord_utils import get_webhook_for_channel


class Donations(commands.Cog, name='Donations'):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on('all_member_donations', self.donations)

    async def donations(self, event):
        clan = coc.Clan(data=event['new_clan'], client=self.bot.coc_client)
        old_clan = coc.Clan(data=event['old_clan'], client=self.bot.coc_client)

        tag_to_member = {member.tag: member for member in clan.members}
        donated = []
        received = []

        for old_member in old_clan.members:
            new_member: coc.ClanMember = tag_to_member.get(old_member.tag)
            if new_member is None:
                continue
            change_dono = new_member.donations - old_member.donations
            change_rec = new_member.received - old_member.received
            if change_dono > 0:
                donated.append((new_member, change_dono))
            if change_rec > 0:
                received.append((new_member, change_rec))

        embed = disnake.Embed(description=f'[**{clan.name}**]({clan.share_link})')
        embed.set_thumbnail(url=clan.badge.url)

        donation_text = ''
        for member, donation in donated:
            donation = f'{donation}'.ljust(3)
            donation_text += f'{self.bot.emoji.up_green_arrow}`{donation}` [**{member.name}**]({SHORT_PLAYER_LINK + member.tag.replace("#","")})\n'
        if donation_text != '':
            embed.add_field(name='Donated', value=donation_text, inline=False)
        received_text = ''
        for member, donation in received:
            donation = f'{donation}'.ljust(3)
            received_text += f'{self.bot.emoji.down_red_arrow}`{donation}` [**{member.name}**]({SHORT_PLAYER_LINK + member.tag.replace("#","")})\n'
        if received_text != '':
            embed.add_field(name='Received', value=received_text, inline=False)

        if donation_text == '' and received_text == '':
            return

        for cc in await self.bot.clan_db.find({'$and': [{'tag': clan.tag}, {f'logs.donation_log.webhook': {'$ne': None}}]}).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = clan.donation_log
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread, raise_exception=True)
                    if thread.locked:
                        continue
                    await webhook.send(embed=embed, thread=thread)
                else:
                    await webhook.send(embed=embed)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


def setup(bot: CustomClient):
    bot.add_cog(Donations(bot))
