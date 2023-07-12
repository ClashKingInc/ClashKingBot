from disnake.ext import commands
import disnake
import coc

from CustomClasses.CustomServer import DatabaseClan
from CustomClasses.CustomBot import CustomClient
from Background.Logs.event_websockets import player_ee
from datetime import datetime
from pytz import utc
from coc.raid import RaidLogEntry, RaidAttack

class clan_capital_events(commands.Cog, name="Clan Capital Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("Most Valuable Clanmate", self.cg_dono_event)


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
                description=f"[**{new_player.name}**]({new_player.share_link}) donated <:capitalgold:987861320286216223>{dono_change}",
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

    @coc.RaidEvents.raid_attack()
    async def member_attack(self, old_member: coc.RaidMember, member: coc.RaidMember, raid: RaidLogEntry):
        channel = await self.bot.getch_channel(1071566470137511966)
        previous_loot = old_member.capital_resources_looted if old_member is not None else 0
        looted_amount = member.capital_resources_looted - previous_loot
        if looted_amount == 0:
            return
        embed = disnake.Embed(
            description=f"[**{member.name}**]({member.share_link}) raided {self.bot.emoji.capital_gold}{looted_amount} | {self.bot.emoji.thick_sword} Attack #{member.attack_count}/{member.attack_limit + member.bonus_attack_limit}\n"
            , color=disnake.Color.green())
        clan_name = await self.bot.clan_db.find_one({"tag": raid.clan_tag})
        embed.set_author(name=f"{clan_name['name']}")
        off_medal_reward = calc_raid_medals(raid.attack_log)
        embed.set_footer(text=f"{numerize.numerize(raid.total_loot, 2)} Total CG | Calc Medals: {off_medal_reward}")
        await channel.send(embed=embed)


    @coc.RaidEvents.state()


def setup(bot: CustomClient):
    bot.add_cog(clan_capital_events(bot))