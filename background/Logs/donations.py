import coc
import disnake

from disnake.ext import commands
from Utils.clash import heros
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import DatabaseClan
from background.Logs.event_websockets import clan_ee
from Utils.clash import leagueAndTrophies
from pymongo import UpdateOne
from Utils.discord_utils import get_webhook_for_channel
from exceptions.CustomExceptions import MissingWebhookPerms

class Donations(commands.Cog, name="Donations"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("all_member_donations", self.donations)

    async def donations(self, event):

        clan = coc.Clan(data=event["new_clan"], client=self.bot.coc_client)
        old_clan = coc.Clan(data=event["old_clan"], client=self.bot.coc_client)

        tag_to_member = {member.tag : member for member in clan.members}
        donated = []
        received = []
        changes = []
        for old_member in old_clan.members:
            new_member: coc.ClanMember = tag_to_member.get(old_member.tag)
            if new_member is None:
                continue
            change_dono = new_member.donations - old_member.donations
            change_rec = new_member.received - old_member.received
            if change_dono > 0:
                change_amount = 0.05 if new_member.donations > 100000 else 0.25
                donated.append((new_member, change_dono))
                changes.append(UpdateOne({"tag": new_member.tag}, {"$inc": {f"points": change_amount * change_dono}}, upsert=True))
            if change_rec > 0:
                received.append((new_member, change_rec))

        if changes:
            await self.bot.player_stats.bulk_write(changes)
        embed = disnake.Embed(description=f"[**{clan.name}**]({clan.share_link})")
        embed.set_thumbnail(url=clan.badge.url)

        donation_text = ""
        for member, donation in donated:
            donation = f"{donation}".ljust(3)
            donation_text += f"<:warwon:932212939899949176>`{donation}` | [**{member.name}**]({member.share_link})\n"
        if donation_text != "":
            embed.add_field(name="Donated", value=donation_text, inline=False)
        received_text = ""
        for member, donation in received:
            donation = f"{donation}".ljust(3)
            received_text += f"<:warlost:932212154164183081>`{donation}` | [**{member.name}**]({member.share_link})\n"
        if received_text != "":
            embed.add_field(name="Received", value=received_text, inline=False)

        if donation_text == "" and received_text == "":
            return

        for cc in await self.bot.clan_db.find({"$and": [{"tag": clan.tag}, {f"logs.donation_log.webhook": {"$ne" : None}}]}).to_list(length=None):
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
                    thread = await self.bot.getch_channel(log.thread)
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

