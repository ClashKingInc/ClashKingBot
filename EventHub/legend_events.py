import coc
import disnake
import calendar
import pytz

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import player_ee
from CustomClasses.CustomPlayer import MyCustomPlayer
from datetime import datetime
utc = pytz.utc

class LegendEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("trophies", self.legend_event)

    async def legend_event(self, event):
        trophy_change = event["new_player"]["trophies"] - event["old_player"]["trophies"]

        dt = datetime.now(utc)
        utc_time = dt.replace(tzinfo=utc)
        utc_timestamp = utc_time.timestamp()
        discord_time = f"<t:{int(utc_timestamp)}:R>"

        player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if player.clan is None:
            return

        if trophy_change >= 1:
            color = disnake.Color.green()
            change = f"{self.bot.emoji.sword} +{trophy_change} trophies\n Current Trophies:{self.bot.emoji.legends_shield}{player.trophies}"
        elif trophy_change <= -1:
            color = disnake.Color.red()
            change = f"{self.bot.emoji.shield} {trophy_change} trophies\n Current Trophies:{self.bot.emoji.legends_shield}{player.trophies}"

        embed = disnake.Embed(title=f"{player.name} | {player.clan.name}",
                              description=f"{change}\n{discord_time} | [profile]({player.share_link})",
                              color=color)

        clan_tag = player.clan.tag
        tracked = self.bot.clan_db.find({"$and": [{"tag": clan_tag}, {"legend_log.webhook": {"$ne" : None}}]})
        limit = await self.bot.clan_db.count_documents(filter={"$and": [{"tag": clan_tag}, {"legend_log.webhook": {"$ne" : None}}]})
        for cc in await tracked.to_list(length=limit):
            try:
                server_id = cc.get("server")
                legendlog = cc.get("legend_log")
                webhook_id = legendlog.get("webhook")
                thread_id = legendlog.get("thread")
                try:
                    webhook = await self.bot.fetch_webhook(webhook_id)
                    if thread_id is not None:
                        thread = await self.bot.getch_channel(thread_id)
                        if thread.locked:
                            continue
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.clan_db.update_one({"$and": [{"tag": clan_tag}, {"server": server_id}]}, {'$set': {"legend_log.webhook": None}})
                    await self.bot.clan_db.update_one({"$and": [{"tag": clan_tag}, {"server": server_id}]}, {'$set': {"legend_log.thread": None}})
                    continue

                if thread_id is None:
                    await webhook.send(embed=embed, avatar_url=self.bot.user.display_avatar.url)
                else:
                    await webhook.send(embed=embed, avatar_url=self.bot.user.display_avatar.url, thread=thread)
            except:
                continue


    @commands.Cog.listener()
    async def on_message_interaction(self, res: disnake.MessageInteraction):
        if "feed_" in res.data.custom_id:
            await self.bot.legend_profile.update_one({'discord_id': res.author.id},
                                                     {'$set': {"feed_tags": []}})
            await res.send(content="You have removed all players from your dm feed", ephemeral=True)


def setup(bot: CustomClient):
    bot.add_cog(LegendEvents(bot))