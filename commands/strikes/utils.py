import coc
import disnake
import random
import pendulum as pend
import string

from datetime import timedelta
from typing import List

def chosen_text(self, clans: List[coc.Clan], ths, roles):
    text = ""
    if clans:
        text += "**CLANS:**\n"
        for clan in clans:
            text += f"• {clan.name} ({clan.tag})\n"
    if ths:
        text += "**THS:**\n"
        for th in ths:
            text += f"• {self.bot.fetch_emoji(name=th)} TH{th}\n"
    if roles:
        text += "**ROLES:**\n"
        for role in roles:
            text += f"• {role}\n"
    return text


def gen_percent(self):
    return [f"{x}%" for x in range(1, 101)]


def gen_capital_gold(self):
    return [f"Under {x} Capital Gold" for x in range(5000, 105000, 5000)]


def gen_missed_hits_war(self):
    return ["Per Missed Hit"]


def gen_missed_hits_capital(self):
    return ["1+ hit", "2+ hits", "3+ hits", "4+ hits", "5+ hits"]


def gen_days(self):
    return [f"{x} days" for x in range(1, 31)]


def gen_points(self):
    return [f"Under {x} points" for x in range(500, 4500, 500)]


async def add_autostrike(self, guild: disnake.Guild, autostrike_type: str, basic_filter: float, weight: int,
                         rollover_days: int):
    pass


async def strike_player(self, ctx, player: coc.Player, reason: str, rollover_days, strike_weight):
    now = pend.now(tz=pend.UTC)
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")

    source = string.ascii_letters
    strike_id = str(''.join((random.choice(source) for i in range(5)))).upper()

    is_used = await self.bot.strikelist.find_one({"strike_id": strike_id})
    while is_used is not None:
        strike_id = str(''.join((random.choice(source) for i in range(5)))).upper()
        is_used = await self.bot.strikelist.find_one({"strike_id": strike_id})

    if rollover_days is not None:
        now = pend.now(tz=pend.UTC)
        rollover_days = now + timedelta(rollover_days)
        rollover_days = int(rollover_days.timestamp())

    await self.bot.strikelist.insert_one({
        "tag": player.tag,
        "date_created": dt_string,
        "reason": reason,
        "server": ctx.guild.id,
        "added_by": ctx.author.id,
        "strike_weight": strike_weight,
        "rollover_date": rollover_days,
        "strike_id": strike_id
    })

    results = await self.bot.strikelist.find({"$and": [
        {"tag": player.tag},
        {"server": ctx.guild.id}
    ]}).to_list(length=100)
    num_strikes = sum([result.get("strike_weight") for result in results])

    if rollover_days is not None:
        rollover_days = f"<t:{rollover_days}:f>"
    else:
        rollover_days = "Never"
    embed = disnake.Embed(
        description=f"**Strike added to [{player.name}]({player.share_link}) by {ctx.author.mention}.**\n"
                    f"Strike Weight: {strike_weight}, Total Strikes Now: {num_strikes}\n"
                    f"Rollover: {rollover_days}\n"
                    f"Reason: {reason}",
        color=disnake.Color.green())
    embed.set_footer(text=f"Strike ID: {strike_id}")
    return embed


async def create_embeds(self, ctx, strike_clan, view, strike_amount, strike_player=None):
    text = []
    hold = ""
    num = 0
    tags = await self.bot.strikelist.distinct("tag", filter={"server": ctx.guild.id})
    all = self.bot.strikelist.find({"server": ctx.guild.id}).sort("date_created", 1)
    limit = await self.bot.strikelist.count_documents(filter={"server": ctx.guild.id})
    if limit == 0:
        return []

    players = await self.bot.get_players(tags=tags, custom=False)
    if view == "Strike View":
        for strike in await all.to_list(length=limit):
            tag = strike.get("tag")
            player = coc.utils.get(players, tag=tag)
            if player is None:
                continue
            if strike_clan is not None:
                if player.clan is None:
                    continue
                if player.clan.tag != strike_clan.tag:
                    continue
            if strike_player is not None:
                if strike_player.tag != player.tag:
                    continue
            name = player.name
            for char in ["`", "*", "_", "~", "´"]:
                name = name.replace(char, "", len(player.name))
            date = strike.get("date_created")
            date = date[:10]
            reason = strike.get("reason")

            added_by = ""
            if strike.get("added_by") is not None:
                user = await self.bot.getch_user(strike.get("added_by"))
                added_by = f"{user}"
            clan = f"{player.clan.name}, {str(player.role)}" if player.clan is not None else "No Clan"

            rollover_days = strike.get("rollover_date")
            if rollover_days is not None:
                rollover_days = f"<t:{rollover_days}:f>"
            else:
                rollover_days = "Never"

            hold += f"{self.bot.fetch_emoji(player.town_hall)}[{name}]({player.share_link}) | {player.tag}\n" \
                    f"{clan} | ID: {strike.get('strike_id')}\n" \
                    f"Added on: {date}, by {added_by}\n" \
                    f"Rollover Date: {rollover_days}\n" \
                    f"*{reason}*\n\n"
            num += 1
            if num == 10:
                text.append(hold)
                hold = ""
                num = 0

    elif view == "Player View":
        for tag in tags:
            player = coc.utils.get(players, tag=tag)
            if player is None:
                continue
            if strike_clan is not None:
                if player.clan is None:
                    continue
                if player.clan.tag != strike_clan.tag:
                    continue
            if strike_player is not None:
                if strike_player.tag != player.tag:
                    continue
            name = player.name
            for char in ["`", "*", "_", "~", "´"]:
                name = name.replace(char, "", len(player.name))

            results = await self.bot.strikelist.find({"$and": [
                {"tag": tag},
                {"server": ctx.guild.id}
            ]}).sort("date_created", 1).to_list(length=100)

            total_strike_weight = sum([result.get("strike_weight") for result in results if
                                       (r := (result.get("rollover_date") if result.get("rollover_date") is not None else 9999999999999)) >= int(
                                           pend.now(tz=pend.UTC).timestamp())])
            num_strikes = len(results)
            if num_strikes < strike_amount:
                continue
            strike_reason_ids = "\n".join(
                [f"`{result.get('strike_id')}` - {result.get('reason')}" for result in results])
            most_recent = results[0].get("date_created")[:10]
            clan = f"{player.clan.name}, {str(player.role)}" if player.clan is not None else "No Clan"

            hold += f"{self.bot.fetch_emoji(player.town_hall)}[{name}]({player.share_link}) | {clan}\n" \
                    f"Most Recent Strike: {most_recent}\n" \
                    f"\# of Strikes: {num_strikes}, Weight: {total_strike_weight}\nStrikes:\n" \
                    f"{strike_reason_ids}\n\n"
            num += 1
            if num == 10:
                text.append(hold)
                hold = ""
                num = 0

    if num != 0:
        text.append(hold)

    embeds = []
    for t in text:
        embed = disnake.Embed(title=f"{ctx.guild.name} Strike List",
                              description=t,
                              color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embeds.append(embed)

    return embeds