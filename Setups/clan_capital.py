
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


class clan_capital_log(commands.Cog, name="Clan Capital Log"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        coc_client.add_events(self.foo3)

    @coc.PlayerEvents.achievement_change()
    async def foo3(self, old_player: coc.Player, new_player:coc.Player, achievement:coc.Achievement):
        if achievement.name == "Most Valuable Clanmate" or achievement.name == "Aggressive Capitalism":
            #print(achievement.name)
            bot = self.bot

            old_ach = old_player.achievement_cls
            new_ach = new_player.achievement_cls

            old_capital_dono = old_player.get_achievement("Most Valuable Clanmate")
            new_capital_dono = new_player.get_achievement("Most Valuable Clanmate")

            old_raid = old_player.get_achievement("Aggressive Capitalism")
            new_raid = new_player.get_achievement("Aggressive Capitalism")

            clan = new_player.clan
            if clan is None:
                return

            if old_capital_dono.value != new_capital_dono.value and achievement.name == "Most Valuable Clanmate":
                #print(f"{new_player.name} donated {new_capital_dono.value - old_capital_dono.value}")
                tracked = clans.find({"tag": f"{clan.tag}"})
                limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
                for cc in await tracked.to_list(length=limit):
                    server = cc.get("server")
                    try:
                        server = await bot.fetch_guild(server)
                    except:
                        continue
                    clancapital_channel = cc.get("clan_capital")
                    if clancapital_channel is None:
                        continue
                    clancapital_channel = await server.fetch_channel(clancapital_channel)
                    if clancapital_channel is None:
                        continue

                    embed = disnake.Embed(
                        description=f"[**{new_player.name}**]({new_player.share_link}) donated <:capitalgold:987861320286216223>{new_capital_dono.value - old_capital_dono.value}"
                        , color=disnake.Color.green())

                    await clancapital_channel.send(embed=embed)

            if old_raid.value != new_raid.value and achievement.name == "Aggressive Capitalism":
                #print(f"{new_player.name} | {new_raid.value - old_raid.value}")
                tracked = clans.find({"tag": f"{clan.tag}"})
                limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
                for cc in await tracked.to_list(length=limit):
                    server = cc.get("server")
                    try:
                        server = await bot.fetch_guild(server)
                    except:
                        continue
                    clancapital_channel = cc.get("clan_capital")
                    if clancapital_channel is None:
                        continue
                    clancapital_channel = await server.fetch_channel(clancapital_channel)
                    if clancapital_channel is None:
                        continue

                    embed = disnake.Embed(
                        description=f"[**{new_player.name}**]({new_player.share_link}) raided for <:capitalgold:987861320286216223>{new_raid.value - old_raid.value}"
                        , color=disnake.Color.green())

                    await clancapital_channel.send(embed=embed)






def setup(bot: commands.Bot):
    bot.add_cog(clan_capital_log(bot))