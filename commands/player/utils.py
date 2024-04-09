import coc
import disnake

from classes.bot import CustomClient
from utility.clash.other import heros, heroPets
from assets.thPicDictionary import thDictionary


async def basic_player_board(bot: CustomClient, player: coc.Player, embed_color: disnake.Color):
    clan = player.clan.name if player.clan else "No Clan"
    hero = heros(bot=bot, player=player)
    pets = heroPets(bot=bot, player=player)

    hero = f"**Heroes:**\n{hero}\n" if hero is None else ""
    pets = f"**Pets:**\n{pets}\n" if pets is None else ""

    embed = disnake.Embed(title=f"**Invite {player.name} to your clan:**",
                          description=f"{player.name} - TH{player.town_hall}\n" +
                                      f"Tag: {player.tag}\n" +
                                      f"Clan: {clan}\n" +
                                      f"Trophies: {player.trophies}\n"
                                      f"War Stars: {player.war_stars}\n"
                                      f"{hero}{pets}",
                          color=embed_color)

    embed.set_thumbnail(url=thDictionary(player.town_hall))
    return embed