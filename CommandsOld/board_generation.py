
import disnake
from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from CustomClasses.ClashKingAPI.Classes import ActivityResponse, DonationResponse, ClanGamesResponse
from utils.general import create_superscript


def donation_board(bot: CustomClient, result: DonationResponse, title_name: str, footer_icon: str, embed_color: disnake.Color = disnake.Color.green()):
    text = "` # DON     REC    NAME     `\n"
    for player in result.players:
        text += f"`{player.rank:2} {player.donations:5} {player.donations_received:5} {player.clear_name[:13]:13}`[{create_superscript(player.townhall)}]({player.share_link})\n"

    embed = disnake.Embed(description=f"{text}", color=embed_color)
    embed.set_author(name=f"{title_name} Top {len(result.players)} {result.sort_field.capitalize()}",
                     icon_url=bot.emoji.clan_castle.partial_emoji.url)
    embed.set_footer(icon_url=footer_icon,
                     text=f"Donations: {'{:,}'.format(result.total_donations)} | Received : {'{:,}'.format(result.total_donations)} | {result.season}")
    embed.timestamp = datetime.now()
    if result.clan_length >= 2 and result.total_donations >= 5000:
        embed.set_image(file=result.comparison_graph)
    else:
        embed.set_image(None)
    return embed


def activity_board(bot: CustomClient, result: ActivityResponse, title_name: str, footer_icon: str, embed_color: disnake.Color = disnake.Color.green()):
    text = "` #  ACT LO      NAME        `\n"
    for player in result.players:
        text += f"`{player.rank:2} {player.activity:4} {player.last_online_text:7} {player.clear_name[:14]:14}`[{create_superscript(player.townhall)}]({player.share_link})\n"
    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name=f"{title_name} Top {len(result.players)} {result.sort_field.capitalize()}",
                     icon_url=bot.emoji.clock.partial_emoji.url)
    embed.set_footer(icon_url=footer_icon, text=f"Activities: {'{:,}'.format(result.total_activity)} | {result.season}")
    embed.timestamp = datetime.now()
    if result.clan_length >= 2 and result.total_activity >= 250:
        embed.set_image(file=result.comparison_graph)
    else:
        embed.set_image(None)
    return embed


def games_board(bot: CustomClient, result: ClanGamesResponse, title_name: str, footer_icon: str, embed_color: disnake.Color = disnake.Color.green()):
    text = "` # Point Time      NAME        `\n"
    for player in result.players:
        text += f"`{player.rank:2} {player.points:4} {player.time_taken_text:7} {player.clear_name[:13]:13}`[{create_superscript(player.townhall)}]({player.share_link})\n"
    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name=f"{title_name} Top {len(result.players)} {result.sort_field.capitalize()}",
                     icon_url=bot.emoji.clock.partial_emoji.url)
    embed.set_footer(icon_url=footer_icon, text=f"Points: {'{:,}'.format(result.total_points)} | {result.season}")
    embed.timestamp = datetime.now()
    if result.clan_length >= 2 and result.total_points >= 5000:
        embed.set_image(file=result.comparison_graph)
    else:
        embed.set_image(None)
    return embed