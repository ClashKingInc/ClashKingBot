import coc
import disnake
import asyncio
import string
import random

from main import scheduler
from FamilyManagement.Reminders import SendReminders
from CustomClasses.CustomServer import DatabaseClan
from CustomClasses.CustomBot import CustomClient
from BoardCommands.Utils.War import main_war_page, missed_hits
from ImageGen.WarEndResult import generate_war_result_image
from utils.discord_utils import get_webhook_for_channel
from Exceptions.CustomExceptions import MissingWebhookPerms

async def create_reminders(bot: CustomClient, times, clan_tag):
    for time in times:
        try:
            reminder_time = time[0] / 3600
            if reminder_time.is_integer():
                reminder_time = int(reminder_time)
            send_time = time[1]
            scheduler.add_job(SendReminders.war_reminder, 'date', run_date=send_time, args=[bot, clan_tag, reminder_time],id=f"{reminder_time}_{clan_tag}", name=f"{clan_tag}", misfire_grace_time=None)
        except:
            pass


async def schedule_war_boards(bot:CustomClient, war: coc.ClanWar):
    if war.state == "preparation" or war.state == "inWar":
        if war.state == "preparation":
            try:
                scheduler.add_job(send_or_update_war_start, 'date', run_date=war.start_time.time,
                                       args=[bot, war.clan.tag], id=f"war_start_{war.clan.tag}",
                                       name=f"{war.clan.tag}_war_start", misfire_grace_time=None)
            except:
                pass
        try:
            scheduler.add_job(send_or_update_war_end, 'date', run_date=war.end_time.time,
                                       args=[bot, war.clan.tag, int(war.preparation_start_time.time.timestamp())],
                                       id=f"war_end_{war.clan.tag}",
                                       name=f"{war.clan.tag}_war_end", misfire_grace_time=None)
        except:
            pass

        
async def send_or_update_war_start(bot: CustomClient, clan_tag:str):
    war: coc.ClanWar = await bot.get_clanwar(clanTag=clan_tag)
    war.state = "inWar"
    if war is None:
        return

    clan = None
    if war.type == "cwl":
        clan = await bot.getClan(war.clan.tag)

    for cc in await bot.clan_db.find({"$and": [{"tag": clan_tag}, {"logs.war_log.webhook": {"$ne": None}}]}).to_list(length=None):
        db_clan = DatabaseClan(bot=bot, data=cc)
        if db_clan.server_id not in bot.OUR_GUILDS:
            continue

        log = db_clan.war_log

        embed = war_start_embed(new_war=war)
        try:
            webhook = await bot.fetch_webhook(log.webhook)
            if log.thread is not None:
                thread = await bot.getch_channel(log.thread)
                if thread.locked:
                    continue
                await webhook.send(embed=embed, thread=thread)
            else:
                await webhook.send(embed=embed)
        except (disnake.NotFound, disnake.Forbidden):
            await log.set_thread(id=None)
            await log.set_webhook(id=None)
            continue


    for cc in await bot.clan_db.find({"$and": [{"tag": clan_tag}, {"logs.war_panel.webhook": {"$ne": None}}]}).to_list(length=None):
        db_clan = DatabaseClan(bot=bot, data=cc)
        if db_clan.server_id not in bot.OUR_GUILDS:
            continue
        await update_war_message(bot=bot, war=war, db_clan=db_clan, clan=clan)


async def send_or_update_war_end(bot: CustomClient, clan_tag:str, preparation_start_time:int):
    await asyncio.sleep(60)
    try:
        war = await bot.war_client.war_result(clan_tag=clan_tag, preparation_start=preparation_start_time)
    except:
        war = None
    og_war = None
    if war is None:
        war = await bot.get_clanwar(clanTag=clan_tag)
        og_war = war
        if str(war.state) != "warEnded":
            for x in range(0, 5):
                try:
                    await asyncio.sleep(war._response_retry + 10)
                except:
                    await asyncio.sleep(60)
                war = await bot.get_clanwar(clanTag=clan_tag)
                if war is None or str(war.state) == "warEnded":
                   break


    if (war is None or int(war.preparation_start_time.time.timestamp()) != preparation_start_time or str(war.state) != "warEnded") and og_war is not None:
        og_war.state = "warEnded"
        war = og_war
    else:
        return

    await store_war(bot=bot, war=war)
    clan = None
    if war.type == "cwl":
        clan = await bot.getClan(war.clan.tag)
    war_league = clan.war_league if clan is not None else None

    for cc in await bot.clan_db.find({"$and": [{"tag": clan_tag}, {"logs.war_log.webhook": {"$ne": None}}]}).to_list(length=None):
        db_clan = DatabaseClan(bot=bot, data=cc)
        if db_clan.server_id not in bot.OUR_GUILDS:
            continue

        log = db_clan.war_log

        embed = await main_war_page(bot=bot, war=war, war_league=war_league)
        embed.set_footer(text=f"{war.type.capitalize()} War")
        file = await generate_war_result_image(war)
        missed_hits_embed = await missed_hits(bot=bot, war=war)

        try:
            webhook = await bot.getch_webhook(log.webhook)
            if isinstance(webhook.channel, disnake.ForumChannel) and log.thread is None:
                raise disnake.Forbidden
            if log.thread is not None:
                thread = await bot.getch_channel(log.thread)
                if thread.locked:
                    continue
                await webhook.send(embed=embed, thread=thread)
                await webhook.send(file=file, thread=thread)
                if len(missed_hits_embed.fields) != 0:
                    await webhook.send(embed=missed_hits_embed, thread=thread)
            else:
                await webhook.send(embed=embed)
                await webhook.send(file=file)
                if len(missed_hits_embed.fields) != 0:
                    await webhook.send(embed=missed_hits_embed)
        except (disnake.NotFound, disnake.Forbidden):
            await log.set_thread(id=None)
            await log.set_webhook(id=None)
            continue


    for cc in await bot.clan_db.find({"$and": [{"tag": clan_tag}, {"logs.war_panel.webhook": {"$ne": None}}]}).to_list(length=None):
        db_clan = DatabaseClan(bot=bot, data=cc)
        if db_clan.server_id not in bot.OUR_GUILDS:
            continue
        await update_war_message(bot=bot, war=war, db_clan=db_clan, clan=clan)
        missed_hits_embed = await missed_hits(bot=bot, war=war)
        log = db_clan.war_panel
        try:
            webhook = await bot.getch_webhook(log.webhook)
            if log.thread is not None:
                thread = await bot.getch_channel(log.thread)
                if thread.locked:
                    continue
                if len(missed_hits_embed.fields) != 0:
                    await webhook.send(embed=missed_hits_embed, thread=thread)
            else:
                if len(missed_hits_embed.fields) != 0:
                    await webhook.send(embed=missed_hits_embed)
        except (disnake.NotFound, disnake.Forbidden):
            await log.set_thread(id=None)
            await log.set_webhook(id=None)
            continue


async def update_war_message(bot: CustomClient, war: coc.ClanWar, db_clan: DatabaseClan, clan: coc.Clan = None):
    log = db_clan.war_panel
    webhook_id = log.webhook
    message_id = log.message_id
    if log.war_id != f"{war.clan.tag}v{war.opponent.tag}-{int(war.preparation_start_time.time.timestamp())}":
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

        war_id = f"{war.clan.tag}v{war.opponent.tag}-{int(war.preparation_start_time.time.timestamp())}"
        await bot.clan_db.update_one({"$and": [{"tag": war.clan.tag}, {"server": db_clan.server_id}]},
                                     {'$set': {"logs.war_panel.war_message": message.id, "logs.war_panel.war_id": war_id, "logs.war_panel.war_channel" : message.channel.id}})


async def store_war(bot: CustomClient, war: coc.ClanWar):
    is_stored = await bot.clan_wars.find_one({"war_id": f"{war.clan.tag}-{int(war.preparation_start_time.time.timestamp())}"})
    if is_stored is not None:
        return
    source = string.ascii_letters
    custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()

    is_used = await bot.clan_wars.find_one({"custom_id": custom_id})
    while is_used is not None:
        custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()
        is_used = await bot.clan_wars.find_one({"custom_id": custom_id})

    await bot.clan_wars.insert_one({
        "war_id" : f"{war.clan.tag}-{int(war.preparation_start_time.time.timestamp())}",
        "custom_id" : custom_id,
        "data" : war._raw_data
    })


def war_start_embed(new_war: coc.ClanWar):
    embed = disnake.Embed(description=f"[**{new_war.clan.name}**]({new_war.clan.share_link})",
                          color=disnake.Color.yellow())
    embed.add_field(name=f"**War Started Against**",
                    value=f"[**{new_war.opponent.name}**]({new_war.opponent.share_link})\n­",
                    inline=False)
    embed.set_thumbnail(url=new_war.clan.badge.large)
    embed.set_footer(text=f"{new_war.type.capitalize()} War")
    return embed


def war_buttons(bot:CustomClient, new_war: coc.ClanWar):
    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Attacks", emoji=bot.emoji.sword_clash.partial_emoji,
                          style=disnake.ButtonStyle.grey,
                          custom_id=f"listwarattacks_{int(new_war.preparation_start_time.time.timestamp())}_{new_war.clan.tag}"),
        disnake.ui.Button(label="Defenses", emoji=bot.emoji.shield.partial_emoji,
                          style=disnake.ButtonStyle.grey,
                          custom_id=f"listwardefenses_{int(new_war.preparation_start_time.time.timestamp())}_{new_war.clan.tag}"),
        disnake.ui.Button(label="", emoji=bot.emoji.menu.partial_emoji,
                          style=disnake.ButtonStyle.green,
                          disabled=False,
                          custom_id=f"menuforwar_{int(new_war.preparation_start_time.time.timestamp())}_{new_war.clan.tag}"))
    ]
    return button