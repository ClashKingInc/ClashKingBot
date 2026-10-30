import coc
import disnake
from disnake import ApplicationCommandInteraction, ButtonStyle, Color, Embed, MessageInteraction
from disnake.ui import ActionRow, Button

from classes.bot import CustomClient
from utility.discord_utils import interaction_handler


async def add_clan(bot: CustomClient, clan: coc.Clan, ctx: ApplicationCommandInteraction):
    embed = Embed(
        description=f"{clan.name} [{clan.tag}] isn't added to the server. Do you want to add it?",
        color=Color.red(),
    )
    embed.set_thumbnail(url=clan.badge.large)

    page_buttons = [
        Button(
            label='Yes',
            emoji='✅',
            style=ButtonStyle.green,
            custom_id='Yes',
        ),
        Button(label='No', emoji='❌', style=ButtonStyle.red, custom_id='No'),
    ]
    buttons = ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    await ctx.edit_original_message(embed=embed, components=[buttons])

    res: MessageInteraction = await interaction_handler(bot=bot, ctx=ctx)

    if res.data.custom_id == 'Yes':
        await bot.clan_db.insert_one(
            {
                'name': clan.name,
                'tag': clan.tag,
                'generalRole': None,
                'leaderRole': None,
                'category': 'General',
                'server': ctx.guild.id,
                'clanChannel': None,
            }
        )
        embed = disnake.Embed(
            title=f'{clan.name} successfully added.',
            description=f'Run `/setup clan` again to edit settings for this clan.',
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=clan.badge.large)
        return await ctx.edit_original_message(embed=embed, components=None)
    else:
        embed = disnake.Embed(
            description=f'Sorry to hear that. Canceling the command now.',
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=clan.badge.large)
        return await res.response.edit_message(embed=embed, components=None)
