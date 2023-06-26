from disnake.ext import commands
import disnake
import coc

from coc import RaidLogEntry
from CustomClasses.CustomBot import CustomClient
from Background.Logs.event_websockets import player_ee

class clan_capital_events(commands.Cog, name="Clan Capital Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("Most Valuable Clanmate", self.cg_dono_event)


    async def cg_dono_event(self, event):
        #print(event["new_player"])
        #print(event["new_player"]["achievements"][-2]["value"])
        new_player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        old_player = coc.Player(data=event["old_player"], client=self.bot.coc_client)
        dono_change = new_player.get_achievement(name="Most Valuable Clanmate", default_value=0).value - old_player.get_achievement(name="Most Valuable Clanmate", default_value=0).value
        clan_tag = event["new_player"].get("clan", {}).get("tag")
        if clan_tag is None:
            return

        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
        if limit == 0:
            return
        tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            if server not in self.bot.OUR_GUILDS:
                continue
            clancapital_channel = cc.get("clan_capital")
            if clancapital_channel is None:
                continue
            try:
                clancapital_channel = await self.bot.getch_channel(clancapital_channel, raise_exception=True)
            except (disnake.Forbidden, disnake.NotFound):
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan_tag},
                    {"server": cc.get("server")}
                ]}, {'$set': {"clan_capital": None}})
                continue

            tag = event['new_player']['tag']
            embed = disnake.Embed(
                description=f"[**{event['new_player']['name']}**]({self.bot.create_link(tag=tag)}) donated <:capitalgold:987861320286216223>{dono_change}"
                , color=disnake.Color.green())

            embed.set_footer(icon_url=event["new_player"]["clan"]["badgeUrls"]["large"],
                             text=event["new_player"]["clan"]["name"])

            try:
                await clancapital_channel.send(embed=embed)
            except (disnake.Forbidden, disnake.NotFound):
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan_tag},
                    {"server": cc.get("server")}
                ]}, {'$set': {"clan_capital": None}})
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
        await channel.send(embed=embed)

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

    @coc.RaidEvents.defense_district_destruction_change()
    async def district_destruction(self, previous_district: coc.RaidDistrict, district: coc.RaidDistrict):
        if self.count >= 20:
            return
        self.count += 1
        channel = await self.bot.getch_channel(1071566470137511966)
        # print(district.destruction)
        name = "District"
        if district.id == 70000000:
            name = "Capital"
        name = f"{name}_Hall{district.hall_level}"
        district_emoji = self.bot.fetch_emoji(name=name).partial_emoji
        color = disnake.Color.yellow()
        if district.destruction == 100:
            color = disnake.Color.red()

        if previous_district is None:
            previous_destr = 0
            previous_gold = 0
        else:
            previous_destr = previous_district.destruction
            previous_gold = previous_district.looted

        added = ""
        cg_added = ""
        if district.destruction - previous_destr != 0:
            added = f" (+{district.destruction - previous_destr}%)"
            cg_added = f" (+{district.looted - previous_gold})"

        embed = disnake.Embed(
            description=f"{self.bot.emoji.thick_sword}{district.destruction}%{added} | {self.bot.emoji.capital_gold}{district.looted}{cg_added} | Atk #{district.attack_count}\n"
            , color=color)
        clan_name = await self.bot.clan_db.find_one({"tag": district.raid_clan.raid_log_entry.clan_tag})
        embed.set_author(icon_url=district_emoji.url, name=f"{district.name} Defense | {clan_name['name']}")
        embed.set_footer(icon_url=district.raid_clan.badge.url,
                         text=f"{district.raid_clan.name} | {district.raid_clan.destroyed_district_count}/{len(district.raid_clan.districts)} Districts Destroyed")
        await channel.send(embed=embed)'''


def setup(bot: CustomClient):
    bot.add_cog(clan_capital_events(bot))