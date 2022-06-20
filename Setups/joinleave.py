
from disnake.ext import commands
from utils.clash import getPlayer, client, pingToChannel, player_handle, coc_client, getClan
import disnake
from utils.components import create_components
from datetime import datetime
import coc
from Dictionaries.emojiDictionary import emojiDictionary
from utils.troop_methods import leagueAndTrophies
from utils.troop_methods import heros, heroPets

usafam = client.usafam
banlist = usafam.banlist
server = usafam.server
clans = usafam.clans


class join_leave_log(commands.Cog, name="Join & Leave Log"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        coc_client.add_events(self.foo)
        coc_client.add_events(self.foo2)

    @coc.ClanEvents.member_join()
    async def foo(self, player, clan: coc.Clan):
        bot = self.bot
        player = await getPlayer(player.tag)
        coc_client.add_player_updates(player.tag)

        tracked = clans.find({"tag": f"{clan.tag}"})
        limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await bot.fetch_guild(server)
            except:
                continue
            joinlog_channel = cc.get("joinlog")
            if joinlog_channel is None:
                continue
            joinlog_channel = await server.fetch_channel(joinlog_channel)
            if joinlog_channel is None:
                continue

            hero = heros(player)
            pets = heroPets(player)
            if hero == None:
                hero = ""
            else:
                hero = f"{hero}"

            if pets == None:
                pets = ""
            else:
                pets = f"{pets}"

            th_emoji = emojiDictionary(player.town_hall)
            embed = disnake.Embed(description=f"[**{player.name}** ({player.tag})]({player.share_link})\n" +
                    f"**{th_emoji}{player.town_hall} {leagueAndTrophies(player)} <:star:825571962699907152>{player.war_stars} {hero}**\n"
                                  ,color=disnake.Color.green())
            embed.set_footer(icon_url=clan.badge.url, text=f"Joined {clan.name} [{clan.member_count}/50]")

            await joinlog_channel.send(embed=embed)

    @coc.ClanEvents.member_leave()
    async def foo2(self, player, clan: coc.Clan):
        bot = self.bot
        player = await getPlayer(player.tag)
        coc_client.remove_player_updates(player.tag)
        tracked = clans.find({"tag": f"{clan.tag}"})
        limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await bot.fetch_guild(server)
            except:
                continue
            joinlog_channel = cc.get("joinlog")
            if joinlog_channel is None:
                continue
            joinlog_channel = await server.fetch_channel(joinlog_channel)
            if joinlog_channel is None:
                continue

            hero = heros(player)
            pets = heroPets(player)
            if hero == None:
                hero = ""
            else:
                hero = f"{hero}"

            if pets == None:
                pets = ""
            else:
                pets = f"{pets}"

            th_emoji = emojiDictionary(player.town_hall)
            embed = disnake.Embed(description=f"[**{player.name}** ({player.tag})]({player.share_link})\n" +
                                              f"**{th_emoji}{player.town_hall} {leagueAndTrophies(player)} <:star:825571962699907152>{player.war_stars} {hero}**\n"
                                  , color=disnake.Color.red())

            if player.clan is not None:
                rclan = await getClan(player.clan.tag)
                embed.set_footer(icon_url=player.clan.badge.url, text=f"Left {clan.name} and Joined {rclan.name} [{rclan.member_count}/50]")
            else:
                embed.set_footer(icon_url=clan.badge.url, text=f"Left {clan.name} [{clan.member_count}/50]")

            await joinlog_channel.send(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(join_leave_log(bot))