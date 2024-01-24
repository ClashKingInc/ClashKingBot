import disnake
from disnake.ext import commands
from assets.thPicDictionary import thDictionary
from utility.clash import heros, heroPets
from classes.bot import CustomClient
from utility.clash import cwl_league_emojis
import coc
from CommandsOlder.Utils import Clan as clan_embeds

class LinkParsing(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.Cog.listener()
    async def on_message(self, message : disnake.Message):
        if message.webhook_id is not None:
            return
        if message.guild.id in self.bot.OUR_GUILDS:
            if "https://link.clashofclans.com/" in message.content and "action=OpenPlayerProfile&tag=" in message.content:
                m = message.content.replace("\n", " ")
                spots = m.split(" ")
                s = ""
                for spot in spots:
                    if "https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=" in spot:
                        s = spot
                        break
                tag = s.replace("https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=", "")
                if "%23" in tag:
                    tag = tag.replace("%23", "")
                player = await self.bot.getPlayer(tag)

                try:
                    clan = player.clan.name
                    clan = f"{clan}"
                except:
                    clan = "None"
                hero = heros(bot=self.bot, player=player)
                pets = heroPets(bot=self.bot, player=player)
                if hero is None:
                    hero = ""
                else:
                    hero = f"**Heroes:**\n{hero}\n"

                if pets is None:
                    pets = ""
                else:
                    pets = f"**Pets:**\n{pets}\n"

                embed = disnake.Embed(title=f"**Invite {player.name} to your clan:**",
                                      description=f"{player.name} - TH{player.town_hall}\n" +
                                                  f"Tag: {player.tag}\n" +
                                                  f"Clan: {clan}\n" +
                                                  f"Trophies: {player.trophies}\n"
                                                  f"War Stars: {player.war_stars}\n"
                                                  f"{hero}{pets}",
                                      color=disnake.Color.green())

                embed.set_thumbnail(url=thDictionary(player.town_hall))

                stat_buttons = [
                    disnake.ui.Button(label=f"Open In-Game",
                                      url=player.share_link),
                    disnake.ui.Button(label=f"Clash of Stats",
                                      url=f"https://www.clashofstats.com/players/{player.tag.strip('#')}/summary"),
                    disnake.ui.Button(label=f"Clash Ninja",
                                      url=f"https://www.clash.ninja/stats-tracker/player/{player.tag.strip('#')}")]
                buttons = disnake.ui.ActionRow()
                for button in stat_buttons:
                    buttons.append_item(button)
                await message.channel.send(embed=embed, components=[buttons])

            elif "https://link.clashofclans.com/" in message.content and "OpenClanProfile" in message.content:
                return
                m = message.content.replace("\n", " ")
                spots = m.split(" ")
                s = ""
                for spot in spots:
                    if "https://link.clashofclans.com/en?action=OpenClanProfile&tag=" in spot:
                        s = spot
                        break
                tag = s.replace("https://link.clashofclans.com/en?action=OpenClanProfile&tag=", "").replace("%23", "")

                clan = await self.bot.getClan(tag)

                leader = coc.utils.get(clan.members, role=coc.Role.leader)

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
                embed = disnake.Embed(title=f"**{clan.name}**",
                                      description=f"Tag: [{clan.tag}]({clan.share_link})\n"
                                                  f"Trophies: <:trophy:825563829705637889> {clan.points} | <:vstrophy:944839518824058880> {clan.versus_points}\n"
                                                  f"Required Trophies: <:trophy:825563829705637889> {clan.required_trophies}\n"
                                                  f"Location: {flag} {clan.location}\n\n"
                                                  f"Leader: {leader.name}\n"
                                                  f"Level: {clan.level} \n"
                                                  f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
                                                  f"CWL: {cwl_league_emojis(str(clan.war_league))}{str(clan.war_league)}\n"
                                                  f"Wars Won: <:warwon:932212939899949176>{warwin}\nWars Lost: <:warlost:932212154164183081>{warloss}\n"
                                                  f"War Streak: <:warstreak:932212939983847464>{winstreak}\nWinratio: <:winrate:932212939908337705>{winrate}\n\n"
                                                  f"Description: {clan.description}",
                                      color=disnake.Color.green())

                embed.set_thumbnail(url=clan.badge.large)

                stat_buttons = [
                    disnake.ui.Button(label=f"Open In-Game",
                                      url=clan.share_link),
                    disnake.ui.Button(label=f"Clash of Stats",
                                      url=f"https://www.clashofstats.com/clans/{clan.tag.strip('#')}/summary"),]
                buttons = disnake.ui.ActionRow()
                for button in stat_buttons:
                    buttons.append_item(button)
                await message.channel.send(embed=embed, components=[buttons])

            elif message.content.startswith("-show "):
                clans = message.content.replace("-show ",  "")
                if clans == "":
                    return
                if "," not in clans:
                    clans = [clans]
                else:
                    clans = clans.split(", ")[:5]
                clan_tags = []
                for clan in clans:
                    results = await self.bot.clan_db.find_one({"$and": [
                        {"server": message.guild.id},
                        {"name": {"$regex": f"^(?i).*{clan}.*$"}}
                    ]})
                    if not results:
                        continue
                    clan_tags.append(results.get("tag"))

                if clan_tags:
                    embeds = []
                    clans = await self.bot.get_clans(tags=clan_tags)
                    for clan in clans:
                        embed = await clan_embeds.simple_clan_embed(bot=self.bot, clan=clan)
                        embeds.append(embed)
                    await message.channel.send(embeds=embeds)


def setup(bot: CustomClient):
    bot.add_cog(LinkParsing(bot))