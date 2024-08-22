import re

import coc
import disnake
from disnake.ext import commands

from background.logs.events import player_ee
from classes.bot import CustomClient
from classes.DatabaseClient.Classes.settings import DatabaseClan
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.clash.other import league_emoji
from utility.constants import ROLES
from utility.discord_utils import get_webhook_for_channel


# from BoardCommands.Utils.Player import upgrade_embed


class UpgradeEvent(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on('troops', self.troop_upgrade)
        self.player_ee.on('heroes', self.hero_upgrade)
        self.player_ee.on('spells', self.spells_upgrade)
        self.player_ee.on('townHallLevel', self.th_upgrade)
        self.player_ee.on('name', self.name_change)
        self.player_ee.on('league', self.league_change)
        self.player_ee.on('role', self.role_change)
        self.player_ee.on('heroEquipment', self.gear_upgrade)

    async def league_change(self, event):
        new_player = coc.Player(data=event['new_player'], client=self.bot.coc_client)
        if new_player.clan is None or new_player.league.id == 29000000:
            return

        old_player = coc.Player(data=event['old_player'], client=self.bot.coc_client)
        name = re.sub('[*_`~/]', '', new_player.name)
        for cc in await self.bot.clan_db.find(
            {
                '$and': [
                    {'tag': new_player.clan.tag},
                    {f'logs.league_change.webhook': {'$ne': None}},
                ]
            }
        ).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue
            content = f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) moved from {league_emoji(bot=bot, player=old_player)}{old_player.league.name} to {league_emoji(bot=bot, player=new_player)}{new_player.league.name}'
            log = clan.league_change
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=content, thread=thread)
                else:
                    await webhook.send(content=content)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    async def name_change(self, event):
        new_player = coc.Player(data=event['new_player'], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        new_name = re.sub('[*_`~/]', '', new_player.name)
        old_player = coc.Player(data=event['old_player'], client=self.bot.coc_client)
        old_name = re.sub('[*_`~/]', '', old_player.name)
        for cc in await self.bot.clan_db.find(
            {
                '$and': [
                    {'tag': new_player.clan.tag},
                    {f'logs.name_change.webhook': {'$ne': None}},
                ]
            }
        ).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            content = f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{old_name}](<{new_player.share_link}>) changed their name to {new_name}'

            log = clan.name_change
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=content, thread=thread)
                else:
                    await webhook.send(content=content)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    async def role_change(self, event):
        new_player = coc.Player(data=event['new_player'], client=self.bot.coc_client)
        if new_player.clan is None or new_player.role is None:
            return

        new_name = re.sub('[*_`~/]', '', new_player.name)
        old_player = coc.Player(data=event['old_player'], client=self.bot.coc_client)

        if old_player.role is None:
            return

        for cc in await self.bot.clan_db.find(
            {
                '$and': [
                    {'tag': new_player.clan.tag},
                    {f'logs.role_change.webhook': {'$ne': None}},
                ]
            }
        ).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            direction = 'promoted' if ROLES.index(new_player.role.in_game_name) > ROLES.index(old_player.role.in_game_name) else 'demoted'
            content = (
                f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{new_name}](<{new_player.share_link}>)'
                f' was {direction} from {old_player.role.in_game_name} to {new_player.role.in_game_name}'
            )

            log = clan.role_change
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=content, thread=thread)
                else:
                    await webhook.send(content=content)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    async def th_upgrade(self, event):
        new_player = coc.Player(data=event['new_player'], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        for cc in await self.bot.clan_db.find(
            {
                '$and': [
                    {'tag': new_player.clan.tag},
                    {f'logs.th_upgrade.webhook': {'$ne': None}},
                ]
            }
        ).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            content = (
                f'[{name}](<{new_player.share_link}>) upgraded to {self.bot.fetch_emoji(name=new_player.town_hall)}Townhall {new_player.town_hall}'
            )

            log = clan.th_upgrade
            try:
                buttons = disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label='',
                        emoji=self.bot.emoji.troop.partial_emoji,
                        style=disnake.ButtonStyle.green,
                        custom_id=f'logrushed_{new_player.tag}',
                    )
                )
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=content, thread=thread, components=buttons)
                else:
                    await webhook.send(content=content, components=buttons)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    async def troop_upgrade(self, event):

        new_player = coc.Player(data=event['new_player'], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        text = None
        for cc in await self.bot.clan_db.find(
            {
                '$and': [
                    {'tag': new_player.clan.tag},
                    {f'logs.troop_upgrade.webhook': {'$ne': None}},
                ]
            }
        ).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)

            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = clan.troop_upgrade

            if text is None:
                old_player = coc.Player(data=event['old_player'], client=self.bot.coc_client)
                unlocked = []
                leveled_up = []
                boosted = []
                for troop in new_player.troops:
                    old_troop = old_player.get_troop(name=troop.name, is_home_troop=troop.is_home_base)
                    if old_troop is None:
                        if troop.is_super_troop:
                            boosted.append(troop)
                        else:
                            unlocked.append(troop)
                    elif troop.level > old_troop.level:
                        leveled_up.append(troop)

                for pet in new_player.pets:
                    old_pet = coc.utils.get(old_player.pets, name=pet.name)
                    if old_pet is None:
                        unlocked.append(pet)
                    elif pet.level > old_pet.level:
                        leveled_up.append(pet)

                if not unlocked and not leveled_up and not boosted:
                    return

                text = ''
                for troop in unlocked:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) unlocked {self.bot.fetch_emoji(name=troop.name)}{troop.name}\n'
                for troop in boosted:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) boosted {self.bot.fetch_emoji(name=troop.name)}{troop.name}\n'
                for troop in leveled_up:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) leveled up {self.bot.fetch_emoji(name=troop.name)}{troop.name} to lv{troop.level}\n'

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=text, thread=thread)
                else:
                    await webhook.send(content=text)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    async def hero_upgrade(self, event):
        new_player = coc.Player(data=event['new_player'], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        text = None
        for cc in await self.bot.clan_db.find(
            {
                '$and': [
                    {'tag': new_player.clan.tag},
                    {f'logs.hero_upgrade.webhook': {'$ne': None}},
                ]
            }
        ).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue
            log = clan.hero_upgrade
            if text is None:
                old_player = coc.Player(data=event['old_player'], client=self.bot.coc_client)
                unlocked = []
                leveled_up = []
                for hero in new_player.heroes:
                    old_hero = old_player.get_hero(name=hero.name)
                    if old_hero is None:
                        unlocked.append(hero)
                    elif hero.level > old_hero.level:
                        leveled_up.append(hero)
                if not unlocked and not leveled_up:
                    return
                text = ''
                for hero in unlocked:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) unlocked {self.bot.fetch_emoji(name=hero.name)}{hero.name}\n'
                for hero in leveled_up:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) leveled up {self.bot.fetch_emoji(name=hero.name)}{hero.name} to lv{hero.level}\n'

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=text, thread=thread)
                else:
                    await webhook.send(content=text)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    async def gear_upgrade(self, event):
        new_player = coc.Player(data=event['new_player'], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        text = None
        for cc in await self.bot.clan_db.find(
            {
                '$and': [
                    {'tag': new_player.clan.tag},
                    {f'logs.hero_equipment_upgrade.webhook': {'$ne': None}},
                ]
            }
        ).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue
            log = clan.hero_equipment_upgrade
            if text is None:
                old_player = coc.Player(data=event['old_player'], client=self.bot.coc_client)
                unlocked = []
                leveled_up = []
                for gear in new_player.equipment:
                    old_gear = old_player.get_equipment(name=gear.name)
                    if old_gear is None:
                        unlocked.append(gear)
                    elif gear.level > old_gear.level:
                        leveled_up.append(gear)
                if not unlocked and not leveled_up:
                    return
                text = ''
                for gear in unlocked:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) unlocked {self.bot.fetch_emoji(name=gear.name)}{gear.name}\n'
                for gear in leveled_up:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) leveled up {self.bot.fetch_emoji(name=gear.name)}{gear.name} to lv{gear.level}\n'

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=text, thread=thread)
                else:
                    await webhook.send(content=text)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    async def spells_upgrade(self, event):
        new_player = coc.Player(data=event['new_player'], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        text = None
        for cc in await self.bot.clan_db.find(
            {
                '$and': [
                    {'tag': new_player.clan.tag},
                    {f'logs.spell_upgrade.webhook': {'$ne': None}},
                ]
            }
        ).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = clan.spell_upgrade

            if text is None:
                old_player = coc.Player(data=event['old_player'], client=self.bot.coc_client)
                unlocked = []
                leveled_up = []
                for spell in new_player.spells:
                    old_spell = old_player.get_spell(name=spell.name)
                    if old_spell is None:
                        unlocked.append(spell)
                    elif spell.level > old_spell.level:
                        leveled_up.append(spell)
                if not unlocked and not leveled_up:
                    return
                text = ''
                for spell in unlocked:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) unlocked {self.bot.fetch_emoji(name=spell.name)}{spell.name}\n'
                for spell in leveled_up:
                    text += f'{self.bot.fetch_emoji(name=new_player.town_hall)}[{name}](<{new_player.share_link}>) leveled up {self.bot.fetch_emoji(name=spell.name)}{spell.name} to lv{spell.level}\n'

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=text, thread=thread)
                else:
                    await webhook.send(content=text)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if 'logrushed_' in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True, with_message=True)
            tag = (str(ctx.data.custom_id).split('_'))[-1]
            player = await self.bot.getPlayer(player_tag=tag, custom=True)
            if player is None:
                return await ctx.edit_original_response(content='No player found.')
            # embeds = await upgrade_embed(self.bot, player)
            # await ctx.edit_original_response(embeds=embeds)


def setup(bot: CustomClient):
    bot.add_cog(UpgradeEvent(bot))
