import coc
import disnake
import pendulum as pend

from background.logs.events import war_ee
from classes.bot import CustomClient
from classes.server import DatabaseClan
from classes.DatabaseClient.Classes.settings import DatabaseClan
from commands.war.utils import main_war_page, missed_hits, attacks_embed, defenses_embed
from disnake.ext import commands
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.discord_utils import get_webhook_for_channel
from utility.general import create_superscript
from utility.imagegen import WarEndResult as war_gen
from utility.war import war_start_embed, update_war_message


class War_Log(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.war_ee = war_ee
        self.war_ee.on("new_attacks", self.war_attacks)
        self.war_ee.on("war_state", self.war_state_change)

    async def war_attacks(self, event):
        cwl_group = event.get("league_group")
        if cwl_group:
            war = coc.ClanWar(
                data=event["war"],
                client=self.bot.coc_client,
                league_group=coc.ClanWarLeagueGroup(
                    data=cwl_group, client=self.bot.coc_client
                ),
                clan_tag=event.get("clan_tag"),
            )
        else:
            war = coc.ClanWar(
                data=event["war"],
                client=self.bot.coc_client,
                clan_tag=event.get("clan_tag"),
            )

        attacks = [
            coc.WarAttack(data=a, client=self.bot.coc_client, war=war)
            for a in event.get("attacks", [])
        ]

        hit_text = ""
        for attack in attacks:
            if attack.attacker.clan.tag == war.clan.tag:
                find_result = await self.bot.player_stats.find_one(
                    {"tag": attack.attacker.tag}
                )
                if find_result is not None:
                    season = self.bot.gen_season_date()
                    _time = int(pend.now(tz=pend.UTC).timestamp())
                    await self.bot.player_stats.update_one(
                        {"tag": attack.attacker.tag}, {"$set": {"last_online": _time}}
                    )
                    await self.bot.player_stats.update_one(
                        {"tag": attack.attacker.tag},
                        {"$push": {f"last_online_times.{season}": _time}},
                    )

            star_str = ""
            stars = attack.stars
            for x in range(0, stars):
                star_str += self.bot.emoji.war_star.emoji_string
            for x in range(0, 3 - stars):
                star_str += self.bot.emoji.no_star.emoji_string

            if attack.attacker.clan.tag == war.clan.tag:
                hit_text += (
                    f"{self.bot.emoji.thick_sword} {self.bot.fetch_emoji(attack.attacker.town_hall)}**{attack.attacker.name}{create_superscript(num=attack.attacker.map_position)}**"
                    f" {star_str} **{attack.destruction}%** {self.bot.fetch_emoji(attack.defender.town_hall)}{create_superscript(num=attack.defender.map_position)}\n"
                )
            else:
                # is a defense
                hit_text += (
                    f"{self.bot.emoji.shield} {self.bot.fetch_emoji(attack.defender.town_hall)}**{attack.defender.name}{create_superscript(num=attack.defender.map_position)}**"
                    f" {star_str} **{attack.destruction}%** {self.bot.fetch_emoji(attack.attacker.town_hall)}{create_superscript(num=attack.attacker.map_position)}\n"
                )

        for cc in await self.bot.clan_db.find(
            {"$and": [{"tag": war.clan.tag}, {"logs.war_log.webhook": {"$ne": None}}]}
        ).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.war_log

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(
                        bot=self.bot, channel=webhook.channel
                    )
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=hit_text, thread=thread)
                else:
                    await webhook.send(content=hit_text)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

        for cc in await self.bot.clan_db.find(
            {"$and": [{"tag": war.clan.tag}, {"logs.war_panel.webhook": {"$ne": None}}]}
        ).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            clan = None
            if war.type == "cwl":
                clan = await self.bot.getClan(war.clan.tag)
            await update_war_message(bot=self.bot, war=war, db_clan=db_clan, clan=clan)

    async def war_state_change(self, event):
        cwl_group = event.get("new_league_group")
        if cwl_group:
            new_war = coc.ClanWar(
                data=event["new_war"],
                client=self.bot.coc_client,
                league_group=coc.ClanWarLeagueGroup(
                    data=cwl_group, client=self.bot.coc_client
                ),
                clan_tag=event.get("clan_tag"),
            )
        else:
            new_war = coc.ClanWar(
                data=event["new_war"],
                client=self.bot.coc_client,
                clan_tag=event.get("clan_tag"),
            )

        clan = None
        if new_war.type == "cwl":
            clan = await self.bot.getClan(new_war.clan.tag)
        war_league = clan.war_league if clan is not None else None

        for cc in await self.bot.clan_db.find(
            {"$and": [{"tag": new_war.clan.tag}, {"events.war": {"$eq": True}}]}
        ).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            if new_war.state == "preparation":
                with open("assets/warmap.png", "rb") as image_file:
                    image_bytes = image_file.read()

                war_type = new_war.type if new_war.type != "random" else "regular"
                guild = await self.bot.getch_guild(guild_id=db_clan.server_id)
                try:
                    await guild.create_scheduled_event(
                        name=f"{war_type.capitalize()} Clan War",
                        description="Details:\n"
                        f"Start Time: {self.bot.timestamper(unix_time=new_war.preparation_start_time.time.timestamp()).cal_date}\n"
                        f"War Size: ({new_war.team_size} v {new_war.team_size})\n"
                        f"Clans: [{new_war.clan.name}]({new_war.clan.share_link}) | [{new_war.opponent.name}]({new_war.opponent.share_link})",
                        scheduled_start_time=pend.now(tz=pend.UTC).add(seconds=30),
                        scheduled_end_time=new_war.end_time.time,
                        image=image_bytes,
                        entity_type=disnake.GuildScheduledEventEntityType.external,
                        entity_metadata=disnake.GuildScheduledEventMetadata(
                            location=f"{new_war.clan.name} vs {new_war.opponent.name}"
                        ),
                    )
                except disnake.Forbidden:
                    await db_clan.set_server_event_creation_status(
                        type="war", status=False
                    )

        for cc in await self.bot.clan_db.find(
            {
                "$and": [
                    {"tag": new_war.clan.tag},
                    {"logs.war_log.webhook": {"$ne": None}},
                ]
            }
        ).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.war_log

            thread = None
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(
                        bot=self.bot, channel=webhook.channel
                    )
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        raise MissingWebhookPerms
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

            if new_war.state == "preparation":
                embed = await main_war_page(
                    bot=self.bot, war=new_war, war_league=war_league
                )
                embed.set_footer(text=f"{new_war.type.capitalize()} War")
                await self.bot.webhook_send(webhook=webhook, thread=thread, embed=embed)

            elif new_war.state == "inWar":
                embed = war_start_embed(new_war=new_war)
                await self.bot.webhook_send(webhook=webhook, thread=thread, embed=embed)

            elif new_war.state == "warEnded":
                embed = await main_war_page(
                    bot=self.bot, war=new_war, war_league=war_league
                )
                embed.set_footer(text=f"{new_war.type.capitalize()} War")
                await self.bot.webhook_send(webhook=webhook, thread=thread, embed=embed)

                file = await war_gen.generate_war_result_image(new_war)
                await self.bot.webhook_send(webhook=webhook, thread=thread, file=file)

                missed_hits_embed = await missed_hits(bot=self.bot, war=new_war)
                if len(missed_hits_embed.fields) != 0:
                    await self.bot.webhook_send(
                        webhook=webhook, thread=thread, embed=missed_hits_embed
                    )

        for cc in await self.bot.clan_db.find(
            {
                "$and": [
                    {"tag": new_war.clan.tag},
                    {"logs.war_panel.webhook": {"$ne": None}},
                ]
            }
        ).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.war_panel
            thread = None
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(
                        bot=self.bot, channel=webhook.channel
                    )
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        raise MissingWebhookPerms
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

            await update_war_message(
                bot=self.bot, war=new_war, db_clan=db_clan, clan=clan
            )

            if new_war.state == "warEnded":
                file = await war_gen.generate_war_result_image(new_war)
                await self.bot.webhook_send(webhook=webhook, thread=thread, file=file)

                missed_hits_embed = await missed_hits(bot=self.bot, war=new_war)
                if len(missed_hits_embed.fields) != 0:
                    await self.bot.webhook_send(
                        webhook=webhook, thread=thread, embed=missed_hits_embed
                    )

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "listwarattacks_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True)
            war_id = (str(ctx.data.custom_id).split("_"))[-1]
            clan_tag = (str(ctx.data.custom_id).split("_"))[1]
            war_data = await self.bot.clan_wars.find_one({"war_id": war_id})
            war = None
            if war_data is not None:
                war = coc.ClanWar(
                    data=war_data["data"], client=self.bot.coc_client, clan_tag=clan_tag
                )
            if war is None:
                war = await self.bot.get_clanwar(clanTag=clan_tag)
            if war is None:
                return await ctx.send(content="No War Found", ephemeral=True)
            attack_embed: disnake.Embed = await attacks_embed(bot=self.bot, war=war)
            await ctx.send(embed=attack_embed, ephemeral=True)

        elif "listwardefenses_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True)
            war_id = (str(ctx.data.custom_id).split("_"))[-1]
            clan_tag = (str(ctx.data.custom_id).split("_"))[1]
            war_data = await self.bot.clan_wars.find_one({"war_id": war_id})
            war = None
            if war_data is not None:
                war = coc.ClanWar(
                    data=war_data["data"], client=self.bot.coc_client, clan_tag=clan_tag
                )
            if war is None:
                war = await self.bot.get_clanwar(clanTag=clan_tag)
            if war is None:
                return await ctx.send(content="No War Found", ephemeral=True)
            attack_embed = await defenses_embed(bot=self.bot, war=war)
            await ctx.send(embed=attack_embed, ephemeral=True)

        elif "warpanelrefresh_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            war_id = (str(ctx.data.custom_id).split("_"))[-1]
            clan_tag = (str(ctx.data.custom_id).split("_"))[1]
            war_data = await self.bot.clan_wars.find_one({"war_id": war_id})
            war = None
            if war_data is not None:
                war = coc.ClanWar(
                    data=war_data["data"], client=self.bot.coc_client, clan_tag=clan_tag
                )
            if war is None:
                war = await self.bot.get_clanwar(clanTag=clan_tag)
            if war is None:
                return await ctx.send(content="No War Found", ephemeral=True)
            embed = await main_war_page(bot=self.bot, war=war)
            # NEED TO EDIT FOR CWL
            await ctx.message.edit(embed=embed)

        elif "menuforwar_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True)
            war_id = (str(ctx.data.custom_id).split("_"))[-1]
            clan_tag = (str(ctx.data.custom_id).split("_"))[1]
            war_data = await self.bot.clan_wars.find_one({"war_id": war_id})
            war = None
            if war_data is not None:
                war = coc.ClanWar(
                    data=war_data["data"], client=self.bot.coc_client, clan_tag=clan_tag
                )
            if war is None:
                war = await self.bot.get_clanwar(clanTag=clan_tag)
            if war is None:
                return await ctx.send(content="No War Found", ephemeral=True)

            button = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Opponent Link",
                        style=disnake.ButtonStyle.url,
                        url=war.opponent.share_link,
                    ),
                    disnake.ui.Button(
                        label="Clash Of Stats",
                        style=disnake.ButtonStyle.url,
                        url=f"https://www.clashofstats.com/clans/{war.opponent.tag.strip('#')}/summary",
                    ),
                    disnake.ui.Button(
                        label="Chocolate Clash",
                        style=disnake.ButtonStyle.url,
                        url=f"https://fwa.chocolateclash.com/cc_n/clan.php?tag={war.opponent.tag.strip('#')}",
                    ),
                )
            ]
            await ctx.send(components=button, ephemeral=True)


def setup(bot: CustomClient):
    bot.add_cog(War_Log(bot))
