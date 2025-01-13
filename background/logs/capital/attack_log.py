import disnake

from classes.bot import CustomClient
from classes.database.models.settings import Join_Log
from utility.clash.other import basic_heros, leagueAndTrophies

from classes.events import log_event, CapitalAttacksEvent
from background.logs.utils import get_available_logs, send_logs
from functools import partial
from utility.clash.capital import calc_raid_medals


@log_event(cls=CapitalAttacksEvent.attack_log)
async def capital_attack_log(bot: CustomClient, event: CapitalAttacksEvent):

    if not event.attackers or not event._data.get('clan'):
        return
    """
    there was a check for the clan field here before, so leaving it, just in case
    we should double check on the event side, to see why this might be
    """

    logs = await get_available_logs(bot=bot, event=event)


    if not logs:
        return

    log = db_clan.capital_attacks

    embeds = []
    for member_tag in attacked_list:
        old_member = old_raid.get_member(tag=member_tag)
        new_member = raid.get_member(tag=member_tag)

        previous_loot = old_member.capital_resources_looted if old_member is not None else 0
        looted_amount = new_member.capital_resources_looted - previous_loot

        embed = disnake.Embed(
            description=f'[**{new_member.name}**]({new_member.share_link}) raided {self.bot.emoji.capital_gold}{looted_amount}',
            color=disnake.Color.green(),
        )
        embed.set_author(name=f'{clan.name}', icon_url=clan.badge.url)
        embed.set_footer(text=f'{numerize.numerize(raid.total_loot, 2)} Total CG | Calc Medals: {off_medal_reward}')

        embeds.append(embed)

    embeds = [embeds[i : i + 10] for i in range(0, len(embeds), 10)]

    try:
        webhook = await self.bot.getch_webhook(log.webhook)
        if log.thread is not None:
            thread = await self.bot.getch_channel(log.thread)
            if thread.locked:
                continue
            for embed_chunk in embeds:
                await webhook.send(embeds=embed_chunk, thread=thread)
        else:
            for embed_chunk in embeds:
                await webhook.send(embeds=embed_chunk)
    except (disnake.NotFound, disnake.Forbidden, disnake.WebhookTokenMissing):
        await log.set_thread(id=None)
        await log.set_webhook(id=None)
        continue


"""for cc in await self.bot.clan_db.find({"$and": [{"tag": raid.clan_tag}, {"logs.new_raid_panel.webhook": {"$ne": None}}]}).to_list(length=None):
    db_clan = DatabaseClan(bot=self.bot, data=cc)
    if db_clan.server_id not in self.bot.OUR_GUILDS:
        continue

    log = db_clan.raid_panel
    embed = await clan_embeds.clan_capital_overview(bot=self.bot, clan=clan, raid_log_entry=raid)

    message_id = log.message_id
    if f"{raid.clan_tag}v{int(raid.start_time.time.timestamp())}" != log.raid_id:
        message_id = None
    try:
        if message_id is None:
            raise Exception
        webhook = await self.bot.getch_webhook(log.webhook)
        if log.thread is not None:
            thread = await self.bot.getch_channel(log.thread, raise_exception=True)
            await webhook.edit_message(message_id, thread=thread, embed=embed)
        else:
            await webhook.edit_message(message_id, embed=embed)
    except:
        thread = None
        try:
            webhook = await self.bot.getch_webhook(log.webhook)
            if log.thread is not None:
                thread = await self.bot.getch_channel(log.thread, raise_exception=True)
                if thread.locked:
                    raise MissingWebhookPerms
            if thread is None:
                message = await webhook.send(embed=embed, wait=True)
            else:
                message = await webhook.send(embed=embed, thread=thread, wait=True)
        except (disnake.NotFound, disnake.Forbidden):
            await log.set_thread(id=None)
            await log.set_webhook(id=None)
            continue

        await log.set_raid_id(raid=raid)
        await log.set_message_id(id=message.id)"""
