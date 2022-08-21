from disnake.ext import commands
import disnake

from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import player_ee


class clan_capital_events(commands.Cog, name="Clan Capital Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @player_ee.on("Aggressive Capitalism")
    async def raid_event(self, event):
        return print(event)

        if old_capital_dono.value != new_capital_dono.value and achievement.name == "Most Valuable Clanmate":
            # print(f"{new_player.name} donated {new_capital_dono.value - old_capital_dono.value}")
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

                try:
                    clancapital_channel = await server.fetch_channel(clancapital_channel)
                    if clancapital_channel is None:
                        continue
                except:
                    continue

                embed = disnake.Embed(
                    description=f"[**{new_player.name}**]({new_player.share_link}) donated <:capitalgold:987861320286216223>{new_capital_dono.value - old_capital_dono.value}"
                    , color=disnake.Color.green())

                embed.set_footer(icon_url=clan.badge.url, text=clan.name)

                try:
                    await clancapital_channel.send(embed=embed)
                except:
                    continue

    @player_ee.on("Most Valuable Clanmate")
    async def cg_dono_event(self, event):
        return print(event)


def setup(bot: CustomClient):
    bot.add_cog(clan_capital_events(bot))