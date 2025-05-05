import coc
import disnake
import pendulum as pd

from classes.bot import CustomClient
from utility.components import basic_clan_dropdown
from utility.discord_utils import interaction_handler, register_button


@register_button('discordlinks', parser='_:clan:server')
async def linked_players(bot: CustomClient, clan: coc.Clan, server: disnake.Guild, embed_color: disnake.Color):
    player_links = await bot.link_client.get_links(*[member.tag for member in clan.members])
    embeds = []
    embed_description = f'{bot.emoji.discord}`Name          ` **Discord**\n'

    player_link_count = 0
    player_link_dict = dict(player_links)

    for player in clan.members:
        player_link = player_link_dict[f'{player.tag}']
        # user not linked to player
        if player_link is None:
            continue

        name = bot.clean_string(player.name)[:14]
        if len(name) <= 2:
            name = player.name

        player_link_count += 1
        member = await server.getch_member(int(player_link))
        # member not found in server
        if member is None:
            member = ''

        embed_description += f'\u200e{bot.emoji.green_check}`{name:14}` \u200e{member}\n'

    # no players were linked
    if player_link_count == 0:
        embed_description = 'No players linked.'

    embed = disnake.Embed(description=embed_description, color=embed_color)
    embed.set_author(name=f'{clan.name} Discord Links', icon_url=clan.badge.url)
    embeds.append(embed)

    embed_description = f'{bot.emoji.discord}`Name          ` **Player Tag**\n'
    unlinked_player_count = 0
    player_link_dict = dict(player_links)
    for player in clan.members:
        player_link = player_link_dict[f'{player.tag}']
        # linked player found
        if player_link is not None:
            continue
        name = bot.clean_string(player.name)[:14]
        if len(name) <= 2:
            name = player.name
        unlinked_player_count += 1
        embed_description += f'\u200e{bot.emoji.red_tick}`{name:14}` \u200e{player.tag}\n'

    if unlinked_player_count == 0:
        embed_description = 'No players unlinked.'

    embed = disnake.Embed(description=embed_description, color=embed_color)
    embed.set_footer(text=f'{player_link_count}✓ | {unlinked_player_count}✘')
    embed.timestamp = pd.now(tz=pd.UTC)
    embeds.append(embed)

    return embeds


@register_button('discordlinkschoose', parser='_:ctx', ephemeral=True, no_embed=True)
async def discord_link_clan_choose(bot: CustomClient, ctx: disnake.MessageInteraction, embed_color: disnake.Color):
    clans = await bot.get_guild_clans(guild_id=ctx.guild_id)
    clans = await bot.get_clans(tags=clans)
    dropdown = await basic_clan_dropdown(clans=clans, max_choose=1)
    og_message = await ctx.original_message()
    msg = await ctx.followup.send(components=[dropdown], ephemeral=True)

    res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, msg=msg, timeout=30)
    clan = await bot.getClan(clan_tag=res.values[0])
    embeds = await linked_players(bot=bot, clan=clan, server=ctx.guild, embed_color=embed_color)

    buttons = disnake.ui.ActionRow()
    buttons.add_button(
        label='',
        emoji=bot.emoji.refresh.partial_emoji,
        style=disnake.ButtonStyle.grey,
        custom_id=f'discordlinks:{clan.tag}:{ctx.guild_id}:refresh',
    )
    buttons.add_button(
        label='',
        emoji=bot.emoji.gear.partial_emoji,
        style=disnake.ButtonStyle.grey,
        custom_id=f'discordlinkschoose:ctx',
    )
    await og_message.edit(embeds=embeds, components=[buttons])
    await res.delete_original_message()
