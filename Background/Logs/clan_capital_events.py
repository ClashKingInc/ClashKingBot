from disnake.ext import commands
import disnake
import coc

from CustomClasses.CustomServer import DatabaseClan
from CustomClasses.CustomBot import CustomClient
from Background.Logs.event_websockets import player_ee, raid_ee
from datetime import datetime
from pytz import utc
from coc.raid import RaidLogEntry, RaidAttack, RaidMember
from numerize import numerize
from ImageGen.ClanCapitalResult import calc_raid_medals
from BoardCommands.Utils import Clan as clan_embeds
from Exceptions.CustomExceptions import MissingWebhookPerms

class clan_capital_events(commands.Cog, name="Clan Capital Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("Most Valuable Clanmate", self.cg_dono_event)
        self.raid_ee = raid_ee
        self.raid_ee.on("raid_attacks", self.member_attack_log)

    async def cg_dono_event(self, event):
        new_player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if new_player.clan.tag is None:
            return
        old_player = coc.Player(data=event["old_player"], client=self.bot.coc_client)
        dono_change = new_player.clan_capital_contributions - old_player.clan_capital_contributions

        utc_time = datetime.now(utc).replace(tzinfo=utc)
        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_player.clan.tag}, {"logs.capital_donations.webhook": {"$ne" : None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.capital_donations
            embed = disnake.Embed(
                description=f"[**{new_player.name}**]({new_player.share_link}) donated {self.bot.emoji.capital_gold}{dono_change}",
                color=disnake.Color.green())
            embed.set_footer(icon_url=new_player.clan.badge.url, text=new_player.clan.name)
            embed.timestamp = utc_time

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(embed=embed, thread=thread)
                else:
                    await webhook.send(embed=embed)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


    '''@coc.RaidEvents.new_offensive_opponent()
    async def new_opponent(self, clan: coc.RaidClan, raid: RaidLogEntry):
        channel = await self.bot.getch_channel(1071566470137511966)
        district_text = ""
        for district in clan.districts:
            name = "District"
            if district.id == 70000000:
                name = "Capital"
            name = f"{name}_Hall{district.hall_level}"
            district_emoji = self.bot.fetch_emoji(name=name)
            district_text += f"{district_emoji}`Level {district.hall_level:<2}` - {district.name}\n"
        detailed_clan = await self.bot.getClan(clan.tag)
        embed = disnake.Embed(title=f"**New Opponent : {clan.name}**",
                              description=f"Raid Clan # {len(raid.attack_log)}\n"
                                          f"Location: {detailed_clan.location.name}\n"
                                          f"Get their own raid details & put some averages here",
                              color=disnake.Color.green())
        embed.add_field(name="Districts", value=district_text)
        embed.set_thumbnail(url=clan.badge.url)
        await channel.send(embed=embed)'''


    async def member_attack_log(self, event):
        raid = RaidLogEntry(data=event["raid"], client=self.bot.coc_client, clan_tag=event["clan_tag"])
        old_member = RaidMember(data=event["old_member"], client=self.bot.coc_client, raid_log_entry=raid)
        new_member = RaidMember(data=event["new_member"], client=self.bot.coc_client, raid_log_entry=raid)

        clan = await self.bot.clan_cache.find_one({"tag": raid.clan_tag})
        if clan is None:
            return
        clan = coc.Clan(data=clan.get("data"), client=self.bot.coc_client)

        for cc in await self.bot.clan_db.find({"$and": [{"tag": raid.clan_tag}, {"logs.capital_attacks.webhook": {"$ne" : None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.capital_attacks

            previous_loot = old_member.capital_resources_looted if old_member is not None else 0
            looted_amount = new_member.capital_resources_looted - previous_loot

            embed = disnake.Embed(
                description=f"[**{new_member.name}**]({new_member.share_link}) raided {self.bot.emoji.capital_gold}{looted_amount}",
                color=disnake.Color.green())
            embed.set_author(name=f"{clan.name}", icon_url=clan.badge.url)

            off_medal_reward = calc_raid_medals(raid.attack_log)
            embed.set_footer(text=f"{numerize.numerize(raid.total_loot, 2)} Total CG | Calc Medals: {off_medal_reward}")

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(embed=embed, thread=thread)
                else:
                    await webhook.send(embed=embed)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


        for cc in await self.bot.clan_db.find({"$and": [{"tag": raid.clan_tag}, {"logs.new_raid_panel.webhook": {"$ne": None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.raid_panel
            embed = await clan_embeds.clan_capital_overview(bot=self.bot, clan=clan, raid_log_entry=raid)

            try:
                if log.message_id is None:
                    raise Exception
                webhook = await self.bot.getch_webhook(log.webhook)
                await webhook.edit_message(log.message_id, embed=embed)
            except:
                thread = None
                message = None
                try:
                    webhook = await self.bot.getch_webhook(log.webhook)
                    if log.thread is not None:
                        thread = await self.bot.getch_channel(log.thread, raise_exception=True)
                        if thread.locked:
                            raise MissingWebhookPerms
                    if thread is None:
                        message = await webhook.send(embed=embed, wait=True)
                    else:
                        message = await webhook.send(embed=embed, thread=thread, wait=True)
                except (disnake.NotFound, disnake.Forbidden):
                    await log.set_thread(id=None)
                    await log.set_webhook(id=None)
                    continue

                await log.set_raid_id(raid=raid)
                await log.set_message_id(id=message.id)







def setup(bot: CustomClient):
    bot.add_cog(clan_capital_events(bot))