import discord
from discord.ext import commands
from HelperMethods.clashClient import client, getClan, link_client
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

usafam = client.usafam
clans = usafam.clans
server = usafam.server

from coc import utils
import coc

import re

class getClans(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.command(name="getclan", aliases=["getclans", "clan"])
    async def getclan(self, ctx, clan=None):
        members = ctx.guild.members
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

        leader = utils.get(clan.members, role=coc.Role.leader)

        if clan.public_war_log:
            warwin = clan.war_wins
            warloss = clan.war_losses
            if warloss == 0:
                warloss = 1
            winstreak = clan.war_win_streak
            winrate = round((warwin/warloss),2)
        else:
            warwin = clan.war_wins
            warloss = "Hidden Log"
            winstreak = clan.war_win_streak
            winrate = "Hidden Log"

        embed = discord.Embed(title=f"**{clan.name}**",description="**Clan Overview**\n"
                              f"Tag: [{clan.tag}]({clan.share_link})\n"
                              f"Leader: {leader.name}\n"
                              f"Level: {clan.level} \n"
                              f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
                              f"CWL: {self.leagueAndTrophies(str(clan.war_league))}{str(clan.war_league)}\n"
                              f"Wars Won: <:warwon:932212939899949176>{warwin}\nWars Lost: <:warlost:932212154164183081>{warloss}\n"
                              f"War Streak: <:warstreak:932212939983847464>{winstreak}\nWinratio: <:winrate:932212939908337705>{winrate}\n\n"
                              f"Description: {clan.description}",
                              color=discord.Color.green())

        embed.set_thumbnail(url=clan.badge.large)

        disc = "<:discord:840749695466864650>"
        emoji = ''.join(filter(str.isdigit, disc))
        emoji = self.bot.get_emoji(int(emoji))
        emoji = discord.PartialEmoji(name=emoji.name, id=emoji.id)
        stat_buttons = [create_button(label="Linked", emoji =emoji, style=ButtonStyle.blue, custom_id="Discord", disabled=False)]
        stat_buttons = create_actionrow(*stat_buttons)
        msg = await ctx.reply(embed=embed, components=[stat_buttons],
                        mention_author=False)

        while True:

            res = None
            try:
                res = await wait_for_component(self.bot, components=stat_buttons,
                                               messages=msg, timeout=600)
            except:
                return await msg.edit(components=[])

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)


            await res.edit_origin()

            # print(res.custom_id)
            if res.custom_id == "Discord":

                gch = "<:greentick:601900670823694357>"
                rx = "<:redtick:601900691312607242>"

                stats = disc + "`Name           ` **Discord (if one)**\n"
                y = 0
                for player in clan.members:
                    link = await link_client.get_link(player.tag)
                    notLinked = (link == None)
                    name = player.name
                    linkE = gch
                    if (notLinked):
                        linkE = rx

                    ol_name = name
                    name = re.split("[^A-Za-z0-9!@#$%^&*()+=~:;<>åæ.]", name)
                    name = "".join(name)
                    name = name[0:15]
                    if len(name) <= 2:
                        name = ol_name
                    for x in range(15 - len(name)):
                        name += " "

                    member = ""
                    if not notLinked:
                        y += 1
                        member = discord.utils.get(members, id=link)
                        member = str(member)
                        if member == "None":
                            member = ""
                    else:
                        member = player.tag

                    stats += f'{linkE}`{name}` {member}' + "\n"
                embed = discord.Embed(title=f"{clan.name} : {str(y)}/{str(clan.member_count)} linked", description=stats,
                                      color=discord.Color.green())
                await msg.edit(embed=embed, components=[])

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
    bot.add_cog(getClans(bot))