import coc
import disnake

from classes.bot import CustomClient
from classes.DatabaseClient.Classes.settings import DatabaseClan
from commands.war.utils import main_war_page
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.discord_utils import get_webhook_for_channel


async def update_war_message(bot: CustomClient, war: coc.ClanWar, db_clan: DatabaseClan, clan: coc.Clan = None):
    log = db_clan.war_panel
    webhook_id = log.webhook
    message_id = log.message_id
    if log.war_id != f'{war.clan.tag}v{war.opponent.tag}-{int(war.preparation_start_time.time.timestamp())}':
        message_id = None

    war_league = clan.war_league if clan is not None else None
    embed = await main_war_page(bot=bot, war=war, war_league=war_league)
    try:
        if message_id is None:
            raise Exception
        webhook: disnake.Webhook = await bot.getch_webhook(webhook_id)
        if webhook.user.id != bot.user.id:
            raise Exception
        if log.thread is not None:
            thread = await bot.getch_channel(log.thread, raise_exception=True)
            await webhook.edit_message(message_id, thread=thread, embed=embed)
        else:
            await webhook.edit_message(message_id, embed=embed)
    except Exception as e:
        button = war_buttons(bot=bot, new_war=war)
        log = db_clan.war_panel

        thread = None
        try:
            webhook = await bot.getch_webhook(webhook_id)
            if webhook.user.id != bot.user.id:
                webhook = await get_webhook_for_channel(bot=bot, channel=webhook.channel)
                await log.set_webhook(id=webhook.id)
            if log.thread is not None:
                thread = await bot.getch_channel(log.thread, raise_exception=True)
                if thread.locked:
                    raise MissingWebhookPerms
        except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
            await log.set_thread(id=None)
            await log.set_webhook(id=None)
            return

        if thread is None:
            message = await webhook.send(embed=embed, components=button, wait=True)
        else:
            message = await webhook.send(embed=embed, components=button, thread=thread, wait=True)

        war_id = f'{war.clan.tag}v{war.opponent.tag}-{int(war.preparation_start_time.time.timestamp())}'
        await bot.clan_db.update_one(
            {'$and': [{'tag': war.clan.tag}, {'server': db_clan.server_id}]},
            {
                '$set': {
                    'logs.war_panel.war_message': message.id,
                    'logs.war_panel.war_id': war_id,
                    'logs.war_panel.war_channel': message.channel.id,
                }
            },
        )


def war_start_embed(new_war: coc.ClanWar):
    embed = disnake.Embed(
        description=f'[**{new_war.clan.name}**]({new_war.clan.share_link})',
        color=disnake.Color.yellow(),
    )
    embed.add_field(
        name=f'**War Started Against**',
        value=f'[**{new_war.opponent.name}**]({new_war.opponent.share_link})\n­',
        inline=False,
    )
    embed.set_thumbnail(url=new_war.clan.badge.large)
    embed.set_footer(text=f'{new_war.type.capitalize()} War')
    return embed


def war_buttons(bot: CustomClient, new_war: coc.ClanWar):
    war_unique_id = '-'.join([new_war.clan_tag, new_war.opponent.tag]) + f'-{int(new_war.preparation_start_time.time.timestamp())}'
    button = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label='',
                emoji=bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f'warpanel_{new_war.clan.tag}_{war_unique_id}_refresh',
            ),
            disnake.ui.Button(
                label='',
                emoji=bot.emoji.animated_clash_swords.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f'listwarattacks_{new_war.clan.tag}_{war_unique_id}',
            ),
            disnake.ui.Button(
                label='',
                emoji=bot.emoji.shield.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f'listwardefenses_{new_war.clan.tag}_{war_unique_id}',
            ),
            disnake.ui.Button(
                label='',
                emoji=bot.emoji.wrench.partial_emoji,
                style=disnake.ButtonStyle.green,
                disabled=False,
                custom_id=f'menuforwar_{new_war.clan.tag}_{war_unique_id}',
            ),
        )
    ]
    return button
