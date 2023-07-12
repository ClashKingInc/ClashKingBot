import coc
import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import DatabaseClan
from Background.Logs.event_websockets import player_ee
from datetime import datetime
from pytz import utc
from utils.discord_utils import get_webhook_for_channel
from Exceptions.CustomExceptions import MissingWebhookPerms

class LegendEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("trophies", self.legend_event)

    async def legend_event(self, event):
        player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if player.clan is None:
            return
        old_player = coc.Player(data=event["old_player"], client=self.bot.coc_client)
        trophy_change = player.trophies - old_player.trophies

        utc_time = datetime.now(utc).replace(tzinfo=utc)

        if trophy_change >= 1:
            color = disnake.Color.green()
            change = f"{self.bot.emoji.sword} +{trophy_change} trophies"
            type = "logs.legend_log_attacks.webhook"
        else: #trophy_change <= -1
            color = disnake.Color.red()
            change = f"{self.bot.emoji.shield} {trophy_change} trophies"
            type = "logs.legend_log_defenses.webhook"

        embed = disnake.Embed(description=f"{change} | [profile]({player.share_link})", color=color)
        embed.set_author(name=f"{player.name} | {player.clan.name}", icon_url=player.clan.badge.url)
        embed.set_footer(text=f"{player.trophies}", icon_url=self.bot.emoji.legends_shield.partial_emoji.url)
        embed.timestamp = utc_time

        tracked = self.bot.clan_db.find({"$and": [{"tag": player.clan.tag}, {f"{type}": {"$ne" : None}}]})
        for cc in await tracked.to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue
            if trophy_change >= 1:
                log = clan.legend_log_attacks
            else:
                log = clan.legend_log_defenses
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
    bot.add_cog(LegendEvents(bot))