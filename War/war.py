import coc
from discord.ext import commands
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow, wait_for_component
from Dictionaries.emojiDictionary import emojiDictionary
import discord
from utils.clashClient import getClan, client, coc_client
usafam = client.usafam
clans = usafam.clans

import pytz
tiz = pytz.utc

from coc import utils
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]

class War(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name = "war")
    async def clan_war(self, ctx, clan=None):
        if clan is None:
            return await ctx.reply("Provide a clan to lookup",
                            mention_author=False)

        clan = clan.lower()
        results = await clans.find_one({"$and": [
            {"alias": clan},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(clan)

        if clan is None:
            return await ctx.reply("Not a valid clan tag.",
                            mention_author=False)

        try:
            war = await coc_client.get_clan_war(clan.tag)
        except coc.PrivateWarLog:
            embed = discord.Embed(description=f"[**{clan.name}**]({clan.share_link}) has a private war log.",
                                  color=discord.Color.green())
            embed.set_thumbnail(url=clan.badge.large)
            return await ctx.reply(embed=embed,
                                   mention_author=False)

        war_time = war.start_time.seconds_until
        war_state = "In Prep"
        war_pos = "Starting"
        if war_time >= 0:
            war_time = war.start_time.time.replace(tzinfo=tiz).timestamp()
        else:
            war_time = war.end_time.seconds_until
            if war_time <= 0:
                war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                war_pos = "Ended"
                war_state = "War Over"
            else:
                war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                war_pos = "Ending"
                war_state = "In War"

        stats = await self.calculate_stars_percent(war)
        team_stars = str(stats[2]).ljust(7)
        opp_stars = str(stats[0]).rjust(7)
        team_per = (str(stats[3])+ "%").ljust(7)
        opp_per = (str(stats[1])+ "%").rjust(7)
        team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(7)
        opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)

        th_comps = await self.war_th_comps(war)

        embed = discord.Embed(description=f"[**{clan.name}**]({clan.share_link})",
                              color=discord.Color.green())
        embed.add_field(name=f"**War Against**", value=f"[**{war.opponent.name}**]({war.opponent.share_link})\n­\n", inline=False)
        embed.add_field(name=f"**War State**",
                        value=f"{war_state} ({war.team_size} vs {war.team_size})\n"
                              f"{war_pos}: <t:{int(war_time)}:R>\n­\n", inline=False)
        embed.add_field(name="**War Stats**",
                        value=f"`{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                              f"`{team_stars}`<:star:825571962699907152>`{opp_stars}`\n"
                              f"`{team_per}`<:broken_sword:944896241429540915>`{opp_per}`\n­\n"
                              , inline=False)

        embed.add_field(name="War Composition", value=f"{war.clan.name}\n{th_comps[0]}\n"
                                                     f"{war.opponent.name}\n{th_comps[1]}", inline=False)

        embed.set_thumbnail(url=clan.badge.large)
        main = embed

        disc = "<:map:944913638500761600>"
        emoji = ''.join(filter(str.isdigit, disc))
        emoji = self.bot.get_emoji(int(emoji))
        emoji = discord.PartialEmoji(name=emoji.name, id=emoji.id)


        troop = "<:troop:861797310224400434>"
        troop = ''.join(filter(str.isdigit, troop))
        troop = self.bot.get_emoji(int(troop))
        troop = discord.PartialEmoji(name=troop.name, id=troop.id)

        swords = "<a:swords:944894455633297418>"
        swords = ''.join(filter(str.isdigit, swords))
        swords = self.bot.get_emoji(int(swords))
        swords = discord.PartialEmoji(name=swords.name, id=swords.id, animated=True)

        shield = "<:clash:877681427129458739>"
        shield = ''.join(filter(str.isdigit, shield))
        shield = self.bot.get_emoji(int(shield))
        shield = discord.PartialEmoji(name=shield.name, id=shield.id)

        magnify = "<:magnify:944914253171810384>"
        magnify = ''.join(filter(str.isdigit, magnify))
        magnify = self.bot.get_emoji(int(magnify))
        magnify = discord.PartialEmoji(name=magnify.name, id=magnify.id)

        surr = "<:surrender:947978096034869249>"
        surr = ''.join(filter(str.isdigit, surr))
        surr = self.bot.get_emoji(int(surr))
        surr = discord.PartialEmoji(name=surr.name, id=surr.id)

        main = embed

        select = create_select(
            options=[  # the options in your dropdown
                create_select_option("War Overview", emoji=emoji, value="war"),
                create_select_option("Clan Roster", emoji=troop, value="croster"),
                create_select_option("Opponent Roster", emoji=troop, value="oroster"),
                create_select_option("Attacks", emoji=swords, value="attacks"),
                create_select_option("Defenses", emoji=shield, value="defenses"),
                create_select_option("Opponent Defenses", emoji=surr, value="odefenses"),
                create_select_option("Opponent Clan Overview", emoji=magnify, value="opp_over")
            ],
            placeholder="Choose a page",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [create_actionrow(select)]

        msg = await ctx.reply(embed=embed, components=dropdown,
                              mention_author=False)

        while True:

            try:
                res = await wait_for_component(self.bot, components=dropdown,
                                               messages=msg, timeout=600)
            except:
                return await msg.edit(components=[])

            await res.edit_origin()

            if res.selected_options[0] == "war":
                await msg.edit(embed=main)
            elif res.selected_options[0] == "croster":
                embed = await self.roster_embed(war)
                await msg.edit(embed=embed)
            elif res.selected_options[0] == "oroster":
                embed = await self.opp_roster_embed(war)
                await msg.edit(embed=embed)
            elif res.selected_options[0] == "attacks":
                embed = await self.attacks_embed(war)
                await msg.edit(embed=embed)
            elif res.selected_options[0] == "defenses":
                embed = await self.defenses_embed(war)
                await msg.edit(embed=embed)
            elif res.selected_options[0] == "opp_over":
                embed = await self.opp_overview(war)
                await msg.edit(embed=embed)
            elif res.selected_options[0] == "odefenses":
                embed = await self.opp_defenses_embed(war)
                await msg.edit(embed=embed)

    async def roster_embed(self, war):
        roster = ""
        tags = []
        lineup = []
        for player in war.members:
            if player not in war.opponent.members:
                tags.append(player.tag)
                lineup.append(player.map_position)

        x = 0
        async for player in coc_client.get_players(tags):
            th = player.town_hall
            th_emoji = emojiDictionary(th)
            place = str(lineup[x]) + "."
            place = place.ljust(3)
            roster += f"`{place}` {th_emoji} {player.name}\n"
            x+=1

        embed = discord.Embed(title=f"{war.clan.name} War Roster", description=roster,
                              color=discord.Color.green())
        embed.set_thumbnail(url=war.clan.badge.large)
        return embed

    async def opp_roster_embed(self, war):
        roster = ""
        tags = []
        lineup = []
        for player in war.opponent.members:
            tags.append(player.tag)
            lineup.append(player.map_position)

        x = 0
        async for player in coc_client.get_players(tags):
            th = player.town_hall
            th_emoji = emojiDictionary(th)
            place = str(lineup[x]) + "."
            place = place.ljust(3)
            roster += f"`{place}` {th_emoji} {player.name}\n"
            x+=1

        embed = discord.Embed(title=f"{war.opponent.name} War Roster", description=roster,
                              color=discord.Color.green())
        embed.set_thumbnail(url=war.opponent.badge.large)
        return embed

    async def attacks_embed(self, war: coc.ClanWar):
        attacks = ""
        missing_attacks = ""
        for player in war.members:
            if player not in war.opponent.members:
                name = player.name
                rank = player.map_position
                rank = str(rank) + "."
                rank = rank.ljust(3)
                attack = f"**`{rank}` {name}**"
                if player.attacks == []:
                    missing_attacks += f"➼ {rank} {player.name}\n"
                    continue
                for a in player.attacks:
                    if a == player.attacks[0]:
                        attack += "\n➼ "
                    if a != player.attacks[-1]:
                        base = await self.create_superscript(a.defender.map_position)
                        attack += f"{a.stars}★ {a.destruction}%{base}, "
                    else:
                        base = await self.create_superscript(a.defender.map_position)
                        attack += f"{a.stars}★ {a.destruction}%{base}"

                attacks += f"{attack}\n"


        embed = discord.Embed(title=f"{war.clan.name} War Attacks", description=attacks,
                              color=discord.Color.green())
        if missing_attacks != "":
            embed.add_field(name="**No attacks done:**", value=missing_attacks)
        embed.set_thumbnail(url=war.clan.badge.large)
        return embed

    async def defenses_embed(self, war: coc.ClanWar):
        defenses = ""
        missing_defenses = ""
        for player in war.members:
            if player not in war.opponent.members:
                name = player.name
                defense = f"**{name}**"
                if player.defenses == []:
                    missing_defenses += f"➼ {player.name}\n"
                    continue
                for d in player.defenses:
                    if d == player.defenses[0]:
                        defense += "\n➼ "
                    if d != player.defenses[-1]:
                        defense += f"{d.stars}★ {d.destruction}%, "
                    else:
                        defense += f"{d.stars}★ {d.destruction}%"

                defenses += f"{defense}\n"


        embed = discord.Embed(title=f"{war.clan.name} Defenses Taken", description=defenses,
                              color=discord.Color.green())
        if missing_defenses != "":
            embed.add_field(name="**No defenses taken:**", value=missing_defenses)
        embed.set_thumbnail(url=war.clan.badge.large)
        return embed

    async def opp_defenses_embed(self, war: coc.ClanWar):
        defenses = ""
        missing_defenses = ""
        for player in war.opponent.members:
            name = player.name
            defense = f"**{name}**"
            if player.defenses == []:
                missing_defenses += f"➼ {player.name}\n"
                continue
            for d in player.defenses:
                if d == player.defenses[0]:
                    defense += "\n➼ "
                if d != player.defenses[-1]:
                    defense += f"{d.stars}★ {d.destruction}%, "
                else:
                    defense += f"{d.stars}★ {d.destruction}%"

            defenses += f"{defense}\n"


        embed = discord.Embed(title=f"{war.clan.name} Defenses Taken", description=defenses,
                              color=discord.Color.green())
        if missing_defenses != "":
            embed.add_field(name="**No defenses taken:**", value=missing_defenses)
        embed.set_thumbnail(url=war.clan.badge.large)
        return embed

    async def opp_overview(self, war: coc.ClanWar):
        clan = await getClan(war.opponent.tag)

        leader = utils.get(clan.members, role=coc.Role.leader)

        if clan.public_war_log:
            warwin = clan.war_wins
            warloss = clan.war_losses
            if warloss == 0:
                warloss = 1
            winstreak = clan.war_win_streak
            winrate = round((warwin / warloss), 2)
        else:
            warwin = clan.war_wins
            warloss = "Hidden Log"
            winstreak = clan.war_win_streak
            winrate = "Hidden Log"

        flag = ""
        if str(clan.location) == "International":
            flag = "<a:earth:861321402909327370>"
        else:
            flag = f":flag_{clan.location.country_code.lower()}:"
        embed = discord.Embed(title=f"**War Opponent: {clan.name}**", description=f"Tag: [{clan.tag}]({clan.share_link})\n"
                                                                    f"Trophies: <:trophy:825563829705637889> {clan.points} | <:vstrophy:944839518824058880> {clan.versus_points}\n"
                                                                    f"Required Trophies: <:trophy:825563829705637889> {clan.required_trophies}\n"
                                                                    f"Location: {flag} {clan.location}\n\n"
                                                                    f"Leader: {leader.name}\n"
                                                                    f"Level: {clan.level} \n"
                                                                    f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
                                                                    f"CWL: {self.leagueAndTrophies(str(clan.war_league))}{str(clan.war_league)}\n"
                                                                    f"Wars Won: <:warwon:932212939899949176>{warwin}\nWars Lost: <:warlost:932212154164183081>{warloss}\n"
                                                                    f"War Streak: <:warstreak:932212939983847464>{winstreak}\nWinratio: <:winrate:932212939908337705>{winrate}\n\n"
                                                                    f"Description: {clan.description}",
                              color=discord.Color.green())

        embed.set_thumbnail(url=clan.badge.large)
        return embed

    async def create_superscript(self, num):
        digits = [int(num) for num in str(num)]
        new_num = ""
        for d in digits:
            new_num += SUPER_SCRIPTS[d]

        return new_num

    async def calculate_stars_percent(self, war: coc.ClanWar):
        stars = 0
        destr = 0
        num_def = 0

        opp_stars = 0
        opp_destr = 0
        opp_num_def = 0

        for member in war.members:
            if member not in war.opponent.members:
                defenses = member.defenses
                num_def +=1
                largest_star = 0
                largest_per = 0
                for defense in defenses:
                    star = defense.stars
                    if star >= largest_star:
                        if defense.destruction > largest_per:
                            largest_star = star
                            largest_per = defense.destruction
                stars += largest_star
                destr += largest_per
            else:
                defenses = member.defenses
                opp_num_def += 1
                largest_star = 0
                largest_per = 0
                for defense in defenses:
                    star = defense.stars
                    if star >= largest_star:
                        if defense.destruction > largest_per:
                            largest_star = star
                            largest_per = defense.destruction
                opp_stars += largest_star
                opp_destr += largest_per

        avg_destr = round(destr/num_def, 2)
        avg_destr_opp = round(opp_destr / opp_num_def, 2)
        return [stars, avg_destr, opp_stars, avg_destr_opp]


    async def war_th_comps(self, war: coc.ClanWar):
        thcount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        opp_thcount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


        for player in war.members:
            th = player.town_hall

            if player not in war.opponent.members:
                count = thcount[th - 1]
                thcount[th - 1] = count + 1
            else:
                count = opp_thcount[th - 1]
                opp_thcount[th - 1] = count + 1

        stats = ""
        for x in reversed(range(len(thcount))):
            count = thcount[x]
            if count != 0:
                if (x + 1) <= 9:
                    th_emoji = emojiDictionary(x + 1)
                    stats += f"{th_emoji}`{count} `"
                else:
                    th_emoji = emojiDictionary(x + 1)
                    stats += f"{th_emoji}`{count} `"

        opp_stats = ""
        for x in reversed(range(len(opp_thcount))):
            count = opp_thcount[x]
            if count != 0:
                if (x + 1) <= 9:
                    th_emoji = emojiDictionary(x + 1)
                    opp_stats += f"{th_emoji}`{count} `"
                else:
                    th_emoji = emojiDictionary(x + 1)
                    opp_stats += f"{th_emoji}`{count} `"

        return [stats, opp_stats]


    def leagueAndTrophies(self, league):

        if (league == "Bronze League III"):
            emoji = "<:BronzeLeagueIII:601611929311510528>"
        elif (league == "Bronze League II"):
            emoji = "<:BronzeLeagueII:601611942850986014>"
        elif (league == "Bronze League I"):
            emoji = "<:BronzeLeagueI:601611950228635648>"
        elif (league == "Silver League III"):
            emoji = "<:SilverLeagueIII:601611958067920906>"
        elif (league == "Silver League II"):
            emoji = "<:SilverLeagueII:601611965550428160>"
        elif (league == "Silver League I"):
            emoji = "<:SilverLeagueI:601611974849331222>"
        elif (league == "Gold League III"):
            emoji = "<:GoldLeagueIII:601611988992262144>"
        elif (league == "Gold League II"):
            emoji = "<:GoldLeagueII:601611996290613249>"
        elif (league == "Gold League I"):
            emoji = "<:GoldLeagueI:601612010492526592>"
        elif (league == "Crystal League III"):
            emoji = "<:CrystalLeagueIII:601612021472952330>"
        elif (league == "Crystal League II"):
            emoji = "<:CrystalLeagueII:601612033976434698>"
        elif (league == "Crystal League I"):
            emoji = "<:CrystalLeagueI:601612045359775746>"
        elif (league == "Master League III"):
            emoji = "<:MasterLeagueIII:601612064913621002>"
        elif (league == "Master League II"):
            emoji = "<:MasterLeagueII:601612075474616399>"
        elif (league == "Master League I"):
            emoji = "<:MasterLeagueI:601612085327036436>"
        elif (league == "Champion League III"):
            emoji = "<:ChampionLeagueIII:601612099226959892>"
        elif (league == "Champion League II"):
            emoji = "<:ChampionLeagueII:601612113345249290>"
        elif (league == "Champion League I"):
            emoji = "<:ChampionLeagueI:601612124447440912>"
        elif (league == "Titan League III"):
            emoji = "<:TitanLeagueIII:601612137491726374>"
        elif (league == "Titan League II"):
            emoji = "<:TitanLeagueII:601612148325744640>"
        elif (league == "Titan League I"):
            emoji = "<:TitanLeagueI:601612159327141888>"
        elif (league == "Legend League"):
            emoji = "<:LegendLeague:601612163169255436>"
        else:
            emoji = "<:Unranked:601618883853680653>"

        return emoji


def setup(bot: commands.Bot):
    bot.add_cog(War(bot))