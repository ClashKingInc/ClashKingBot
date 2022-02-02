import coc
import discord
from discord.ext import commands
from HelperMethods.clashClient import client, getClan, coc_client
from datetime import datetime

from discord_slash.utils.manage_components import wait_for_component, create_select, create_select_option, create_actionrow

import aiohttp


usafam = client.usafam
clans = usafam.clans

leagues = ["Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]


class Cwl(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="cwl", pass_context=True, invoke_without_command=True)
    async def cwl_co(self, ctx):
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")

        same = "<:dash:933150462818021437>"
        up = "<:warwon:932212939899949176>"
        down = "<:warlost:932212154164183081>"
        cwl_list = []
        for tClan in await tracked.to_list(length=limit):
            c = []
            tag = tClan.get("tag")
            clan = await getClan(tag)
            c.append(clan.name)
            c.append(clan.war_league.name)
            cwl_list.append(c)

        clans_list = sorted(cwl_list, key=lambda l: l[0], reverse=False)

        main_embed = discord.Embed(title=f"__**{ctx.guild.name} CWL Leagues**__",
                                     color=discord.Color.green())
        main_embed.set_thumbnail(url=ctx.guild.icon_url_as())

        print(clans_list)

        embeds = []
        leagues_present = ["All"]
        for league in leagues:
            #print(league)
            text = ""
            for clan in clans_list:
                #print(clan)
                if clan[1] == league:
                    text += clan[0] + "\n"
                if (clan[0] == clans_list[len(clans_list)-1][0]) and (text !=""):
                    leagues_present.append(league)
                    league_emoji = self.leagueAndTrophies(league)
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                    embed = discord.Embed(title=f"__**{ctx.guild.name} {league} Clans**__", description=text,
                                               color=discord.Color.green())
                    embed.set_thumbnail(url=ctx.guild.icon_url_as())
                    embeds.append(embed)

        embeds.append(main_embed)

        options = []
        for league in leagues_present:
            if league == "All":
                league_emoji = "<:LeagueMedal:858424820857307176>"
            else:
                league_emoji = self.leagueAndTrophies(league)
            emoji = league_emoji.split(":", 2)
            emoji = emoji[2]
            emoji = emoji[0:len(emoji) - 1]
            emoji = self.bot.get_emoji(int(emoji))
            emoji = discord.PartialEmoji(name=emoji.name, id=emoji.id)
            options.append(create_select_option(f"{league}", value=f"{league}", emoji=emoji))

        select1 = create_select(
            options=options,
            placeholder="Choose clan category",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = create_actionrow(select1)

        msg = await ctx.reply(embed=embeds[len(embeds) - 1], components=[action_row],
                              mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=action_row,
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()
            value = res.values[0]

            current_page = leagues_present.index(value) - 1

            await msg.edit(embed=embeds[current_page],
                           components=[action_row])

    @cwl_co.group(name="status", pass_context=True, invoke_without_command=True)
    async def cwl_status(self, ctx):
        now = datetime.utcnow()
        year = now.year
        month = now.month
        if month <= 9:
            month = f"0{month}"
        dt = f"{year}-{month}"
        #print(dt)
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")

        embed = discord.Embed(
            description="<a:loading:884400064313819146> Loading Family CWL Status...",
            color=discord.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)

        spin_list = []
        for tClan in await tracked.to_list(length=limit):
            c = []
            tag = tClan.get("tag")
            name = tClan.get("name")
            c.append(name)
            clan = await getClan(tag)
            c.append(clan.war_league.name)
            c.append(clan.tag)
            try:
                league = await coc_client.get_league_group(tag)
                state = league.state
                if str(state) == "preparation":
                    c.append("- Matched, Prep")
                elif str(state) == "ended":
                    c.append("")
                elif str(state) == "inWar":
                    c.append("- Matched, In War")
            except coc.errors.NotFound:
                c.append("")
            except:
                c.append("- Spinning")
            spin_list.append(c)

        #print(spin_list)
        clans_list = sorted(spin_list, key=lambda l: l[1], reverse=False)

        main_embed = discord.Embed(title=f"__**{ctx.guild.name} CWL Status**__",
                                   color=discord.Color.green())
        main_embed.set_thumbnail(url=ctx.guild.icon_url_as())
        main_embed.set_footer(text="Blank = Not Spun Yet")

        embeds = []
        leagues_present = ["All"]
        for league in leagues:
            text = ""
            for clan in clans_list:
                if clan[1] == league:
                    text += f"{clan[0]} {clan[3]}\n"
                if (clan[2] == clans_list[len(clans_list) - 1][2]) and (text != ""):
                    leagues_present.append(league)
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                    embed = discord.Embed(title=f"__**{ctx.guild.name} {league} Clans**__", description=text,
                                          color=discord.Color.green())
                    embed.set_thumbnail(url=ctx.guild.icon_url_as())
                    embeds.append(embed)

        embeds.append(main_embed)

        options = []
        for league in leagues_present:
            if league == "All":
                league_emoji = "<:LeagueMedal:858424820857307176>"
            else:
                league_emoji = self.leagueAndTrophies(league)
            emoji = league_emoji.split(":", 2)
            emoji = emoji[2]
            emoji = emoji[0:len(emoji) - 1]
            emoji = self.bot.get_emoji(int(emoji))
            emoji = discord.PartialEmoji(name=emoji.name, id=emoji.id)
            options.append(create_select_option(f"{league}", value=f"{league}", emoji=emoji))

        select1 = create_select(
            options=options,
            placeholder="Choose cwl league",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = create_actionrow(select1)



        await msg.edit(embed=main_embed, components=[action_row],
                              mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=action_row,
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()
            value = res.values[0]

            current_page = leagues_present.index(value) - 1

            await msg.edit(embed=embeds[current_page],
                           components=[action_row])


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
    bot.add_cog(Cwl(bot))