from disnake.ext import commands
import disnake
import coc
import re

from CustomClasses.CustomServer import DatabaseClan
from CustomClasses.CustomBot import CustomClient
from Background.Logs.event_websockets import player_ee
from utils.clash import league_emoji
from pytz import utc

class UpgradeEvent(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("troops", self.troop_upgrade)
        self.player_ee.on("heroes", self.hero_upgrade)
        self.player_ee.on("spells", self.spells_upgrade)
        self.player_ee.on("townHallLevel", self.th_upgrade)
        self.player_ee.on("name", self.name_change)
        self.player_ee.on("league", self.league_change)

    async def league_change(self, event):
        new_player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if new_player.clan is None or new_player.league.id == 29000000:
            return

        old_player = coc.Player(data=event["old_player"], client=self.bot.coc_client)
        name = re.sub('[*_`~/]', '', new_player.name)
        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_player.clan.tag}, {f"logs.league_change.webhook": {"$ne": None}}]}).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue
            content = f"{self.bot.fetch_emoji(name=new_player.town_hall)}{name} moved from {league_emoji(old_player)}{old_player.league.name} to {league_emoji(new_player)}{new_player.league.name}"
            log = clan.league_change
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=content, thread=thread)
                else:
                    await webhook.send(content=content)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


    async def name_change(self, event):
        new_player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        new_name = re.sub('[*_`~/]', '', new_player.name)
        old_player = coc.Player(data=event["old_player"], client=self.bot.coc_client)
        old_name = re.sub('[*_`~/]', '', old_player.name)
        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_player.clan.tag}, {f"logs.name_change.webhook": {"$ne": None}}]}).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            content = f"{self.bot.fetch_emoji(name=new_player.town_hall)}{old_name} changed their name to {new_name}"

            log = clan.name_change
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=content, thread=thread)
                else:
                    await webhook.send(content=content)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


    async def th_upgrade(self, event):
        new_player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_player.clan.tag}, {f"logs.th_upgrade.webhook": {"$ne": None}}]}).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            content = f"{name} upgraded to {self.bot.fetch_emoji(name=new_player.town_hall)}Townhall {new_player.town_hall}"

            log = clan.th_upgrade
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=content, thread=thread)
                else:
                    await webhook.send(content=content)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


    async def troop_upgrade(self, event):

        new_player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        text = None
        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_player.clan.tag}, {f"logs.troop_upgrade.webhook": {"$ne": None}}]}).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = clan.troop_upgrade

            if text is None:
                old_player = coc.Player(data=event["old_player"], client=self.bot.coc_client)
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

                text = ""
                for troop in unlocked:
                    text += f"{self.bot.fetch_emoji(name=new_player.town_hall)}{name} unlocked {self.bot.fetch_emoji(name=troop.name)}{troop.name}\n"
                for troop in boosted:
                    text += f"{self.bot.fetch_emoji(name=new_player.town_hall)}{name} boosted {self.bot.fetch_emoji(name=troop.name)}{troop.name}\n"
                for troop in leveled_up:
                    text += f"{self.bot.fetch_emoji(name=new_player.town_hall)}{name} leveled up {self.bot.fetch_emoji(name=troop.name)}{troop.name} to lv{self.bot.get_number_emoji(color='white', number=troop.level)}\n"

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=text, thread=thread)
                else:
                    await webhook.send(content=text)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


    async def hero_upgrade(self, event):
        new_player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        text = None
        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_player.clan.tag}, {f"logs.hero_upgrade.webhook": {"$ne": None}}]}).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = clan.hero_upgrade

            if text is None:
                old_player = coc.Player(data=event["old_player"], client=self.bot.coc_client)
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
                text = ""
                for hero in unlocked:
                    text += f"{self.bot.fetch_emoji(name=new_player.town_hall)}{name} unlocked {self.bot.fetch_emoji(name=hero.name)}{hero.name}\n"
                for hero in leveled_up:
                    text += f"{self.bot.fetch_emoji(name=new_player.town_hall)}{name} leveled up {self.bot.fetch_emoji(name=hero.name)}{hero.name} to lv{self.bot.get_number_emoji(color='white', number=hero.level)}\n"

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=text, thread=thread)
                else:
                    await webhook.send(content=text)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


    async def spells_upgrade(self, event):
        new_player = coc.Player(data=event["new_player"], client=self.bot.coc_client)
        if new_player.clan is None:
            return

        name = re.sub('[*_`~/]', '', new_player.name)
        text = None
        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_player.clan.tag}, {f"logs.spell_upgrade.webhook": {"$ne": None}}]}).to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = clan.spell_upgrade

            if text is None:
                old_player = coc.Player(data=event["old_player"], client=self.bot.coc_client)
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
                text = ""
                for spell in unlocked:
                    text += f"{self.bot.fetch_emoji(name=new_player.town_hall)}{name} unlocked {self.bot.fetch_emoji(name=spell.name)}{spell.name}\n"
                for spell in leveled_up:
                    text += f"{self.bot.fetch_emoji(name=new_player.town_hall)}{name} leveled up {self.bot.fetch_emoji(name=spell.name)}{spell.name} to lv{self.bot.get_number_emoji(color='white', number=spell.level)}\n"

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=text, thread=thread)
                else:
                    await webhook.send(content=text)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


def setup(bot: CustomClient):
    bot.add_cog(UpgradeEvent(bot))