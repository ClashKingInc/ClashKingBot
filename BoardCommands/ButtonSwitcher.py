from .Utils import Clan as clan_embeds
from .Utils import Family as family_embeds
from .Utils import Graphs as graph_creator
from .Utils import Player as player_embeds
from .Utils import Shared as shared_embeds
from CustomClasses.CustomBot import CustomClient
import disnake

clan_triggers = {
    "clanoverview",
    "clanwarcwlhist",
    "clanwaropt",
    "clanlinked",
    "clansort",
    "clanwarlog",
    "clanstroops"
}

async def button_click_to_embed(bot: CustomClient, ctx: disnake.MessageInteraction):
    custom_id = str(ctx.data.custom_id)
    embed = None
    first = custom_id.split("_")[0]
    if first in clan_triggers:
        await ctx.response.defer()
        embed = await clan_parser(bot, ctx, custom_id)
    return embed

async def clan_parser(bot: CustomClient, ctx: disnake.MessageInteraction, custom_id: str):
    split = custom_id.split("_")
    clan_tag = split[1]
    clan = await bot.getClan(clan_tag=clan_tag)
    embed = None
    if "clanoverview_" in custom_id:
        image = split[-1]
        if split[-2] == "True":
            embed = await clan_embeds.simple_clan_embed(bot, clan)
        else:
            embed = await clan_embeds.clan_overview(bot=bot, clan=clan, guild=ctx.guild)
        if image != "None":
            embed.set_image(file=disnake.File(f"TemplateStorage/{image}.png"))
    elif "clanwarcwlhist_" in custom_id:
        war_log_embed = await clan_embeds.war_log(bot=bot, clan=clan)
        cwl_history = await clan_embeds.cwl_performance(bot=bot, clan=clan)
        embed = [war_log_embed, cwl_history]
    elif "clanwaropt_" in custom_id:
        embed = await clan_embeds.opt_status(bot=bot, clan=clan)
    elif "clanlinked_" in custom_id:
        player_links = await bot.link_client.get_links(*[member.tag for member in clan.members])
        linked_players_embed = await clan_embeds.linked_players(bot=bot, clan=clan, player_links=player_links, guild=ctx.guild)
        unlinked_players_embed = await clan_embeds.unlinked_players(bot=bot, clan=clan, player_links=player_links)
        embed = [linked_players_embed, unlinked_players_embed]
    elif "clansort_" in custom_id:
        sort_by = split[-1]
        limit = int(split[-2])
        embed = await shared_embeds.player_sort(bot=bot, player_tags=[member.tag for member in clan.members],
                                                sort_by=sort_by,
                                                footer_icon=clan.badge.url,
                                                title_name=f"{clan.name} sorted by {sort_by}", limit=limit)
    elif "clanstroops_" in custom_id:
        embed = await clan_embeds.super_troop_list(bot=bot, clan=clan)

    return embed


def family_parser():
    pass

def top_parser():
    pass

def player_parser():
    pass