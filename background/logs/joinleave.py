import coc
import disnake
import ujson

from disnake.ext import commands
from utility.clash.other import leagueAndTrophies, basic_heros
from classes.bot import CustomClient
from classes.server import DatabaseClan
from background.logs.events import clan_ee
from utility.discord_utils import get_webhook_for_channel
from exceptions.CustomExceptions import MissingWebhookPerms


class join_leave_events(commands.Cog, name="Clan Join & Leave Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("members_join_leave", self.player_join_leave)

    async def player_join_leave(self, event):
        clan = coc.Clan(data=event["new_clan"], client=self.bot.coc_client)

        if members_joined := event.get("joined", []):
            tracked = await self.bot.clan_db.find(
                {"$and": [{"tag": clan.tag}, {"logs.join_log.webhook": {"$ne": None}}]}
            ).to_list(length=None)
            if tracked:
                members_joined = [
                    coc.ClanMember(data=member, client=self.bot.coc_client, clan=clan)
                    for member in members_joined
                ]
                player_pull = await self.bot.get_players(
                    tags=[m.tag for m in members_joined], use_cache=False, custom=False
                )
                player_map = {p.tag: p for p in player_pull}

                embeds = []
                for member in members_joined:
                    player = player_map.get(member.tag)
                    if player is None:
                        continue
                    hero = basic_heros(bot=self.bot, player=player)

                    th_emoji = self.bot.fetch_emoji(player.town_hall)
                    embed = disnake.Embed(
                        description=f"[**{player.name}** ({player.tag})]({player.share_link})\n"
                        + f"**{th_emoji}{player.town_hall}{leagueAndTrophies(player)}<:star:825571962699907152>{player.war_stars}{hero}**\n",
                        color=disnake.Color.green(),
                    )
                    embed.set_footer(
                        icon_url=clan.badge.url,
                        text=f"Joined {clan.name} [{clan.member_count}/50]",
                    )
                    embeds.append(embed)
                embeds = [embeds[i : i + 10] for i in range(0, len(embeds), 10)]

                for cc in tracked:
                    db_clan = DatabaseClan(bot=self.bot, data=cc)
                    if db_clan.server_id not in self.bot.OUR_GUILDS:
                        continue

                    if db_clan.auto_greet_option != "Never":
                        greet_message = await self.bot.custom_embeds.find_one(
                            {
                                "$and": [
                                    {"server": db_clan.server_id},
                                    {"name": db_clan.greeting},
                                ]
                            }
                        )
                        if greet_message is None:
                            greet_message = {
                                "content": "Welcome {user_mention} to **{clan_name}**",
                                "embeds": [],
                            }

                        for player in player_pull:
                            send = True
                            if db_clan.auto_greet_option == "First Join":
                                join_result = await self.bot.clan_join_leave.find_one(
                                    {"$and": [{"tag": player.tag}, {"clan": clan.tag}]}
                                )
                                if join_result is not None:
                                    send = False

                            if send:
                                linked = await self.bot.link_client.get_link(player.tag)
                                discord_user = None
                                if linked is not None:
                                    discord_user = await self.bot.getch_user(linked)

                                local_greet_message = str(greet_message)
                                types = {
                                    "{user_mention}": (
                                        discord_user.mention if discord_user else ""
                                    ),
                                    "{user_display_name}": (
                                        discord_user.display_name
                                        if discord_user
                                        else ""
                                    ),
                                    "{clan_name}": clan.name,
                                    "{clan_link}": clan.share_link,
                                    "{clan_leader_name}": coc.utils.get(
                                        clan.members, role=coc.Role.leader
                                    ),
                                    "{player_name}": player.name,
                                    "{player_link}": player.share_link,
                                    "{player_townhall}": player.town_hall,
                                    "{player_townhall_emoji}": self.bot.fetch_emoji(
                                        player.town_hall
                                    ).emoji_string,
                                    "{player_league}": player.league.name,
                                    "{player_league_emoji}": self.bot.fetch_emoji(
                                        player.league.name
                                    ).emoji_string,
                                    "{player_trophies}": player.trophies,
                                }

                                for type, replace in types.items():
                                    local_greet_message = local_greet_message.replace(
                                        type, str(replace)
                                    )

                                local_greet_message = ujson.loads(local_greet_message)

                                channel = await self.bot.getch_channel(
                                    db_clan.clan_channel
                                )
                                if channel is not None:
                                    try:
                                        await channel.send(
                                            content=local_greet_message.get(
                                                "content", ""
                                            ),
                                            embeds=[
                                                disnake.Embed.from_dict(data=e)
                                                for e in local_greet_message.get(
                                                    "embeds", []
                                                )
                                            ],
                                        )
                                    # WE NEED TO HANDLE THIS EVENTUALLY
                                    except Exception:
                                        pass

                    if not embeds:
                        continue

                    log = db_clan.join_log

                    components = []
                    if log.profile_button:
                        stat_buttons = [
                            disnake.ui.Button(
                                label="",
                                emoji=self.bot.emoji.troop.partial_emoji,
                                style=disnake.ButtonStyle.green,
                                custom_id=f"redditplayer_{player.tag}",
                            )
                        ]
                        buttons = disnake.ui.ActionRow()
                        for button in stat_buttons:
                            buttons.append_item(button)
                        components = [buttons]
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
                            for embed_chunk in embeds:
                                await webhook.send(
                                    embeds=embed_chunk,
                                    thread=thread,
                                    components=components,
                                )
                        else:
                            for embed_chunk in embeds:
                                await webhook.send(
                                    embeds=embed_chunk, components=components
                                )
                    except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                        await log.set_thread(id=None)
                        await log.set_webhook(id=None)
                        continue

        if members_left := event.get("left", []):
            tracked = await self.bot.clan_db.find(
                {"$and": [{"tag": clan.tag}, {"logs.leave_log.webhook": {"$ne": None}}]}
            ).to_list(length=None)
            if tracked:
                members_left = [
                    coc.ClanMember(data=member, client=self.bot.coc_client, clan=clan)
                    for member in members_left
                ]
                player_pull = await self.bot.get_players(
                    tags=[m.tag for m in members_left], use_cache=False, custom=False
                )
                player_map = {p.tag: p for p in player_pull}

                embeds = []
                for member in members_left:
                    player = player_map.get(member.tag)
                    if player is None:
                        continue
                    hero = basic_heros(bot=self.bot, player=player)

                    th_emoji = self.bot.fetch_emoji(player.town_hall)
                    embed = disnake.Embed(
                        description=f"[**{player.name}** ({player.tag})]({player.share_link})\n"
                        + f"**{th_emoji}{player.town_hall}{leagueAndTrophies(player)}<:star:825571962699907152>{player.war_stars}{hero}**\n",
                        color=disnake.Color.red(),
                    )
                    if player.clan is not None and player.clan.tag != clan.tag:
                        embed.set_footer(
                            icon_url=player.clan.badge.url,
                            text=f"Left {clan.name} [{clan.member_count}/50] and Joined {player.clan.name}",
                        )
                    else:
                        embed.set_footer(
                            icon_url=clan.badge.url,
                            text=f"Left {clan.name} [{clan.member_count}/50]",
                        )
                    embeds.append(embed)
                embeds = [embeds[i : i + 10] for i in range(0, len(embeds), 10)]

                for cc in tracked:
                    db_clan = DatabaseClan(bot=self.bot, data=cc)
                    if db_clan.server_id not in self.bot.OUR_GUILDS:
                        continue

                    if not embeds:
                        continue

                    log = db_clan.leave_log

                    components = []
                    if log.ban_button or log.strike_button:
                        stat = []
                        if log.ban_button:
                            stat += [
                                disnake.ui.Button(
                                    label="Ban",
                                    emoji="🔨",
                                    style=disnake.ButtonStyle.red,
                                    custom_id=f"jlban_{player.tag}",
                                )
                            ]
                        if log.strike_button:
                            stat += [
                                disnake.ui.Button(
                                    label="Strike",
                                    emoji="✏️",
                                    style=disnake.ButtonStyle.grey,
                                    custom_id=f"jlstrike_{player.tag}",
                                )
                            ]
                        buttons = disnake.ui.ActionRow()
                        for button in stat:
                            buttons.append_item(button)
                        components = [buttons]
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
                            for embed_chunk in embeds:
                                await webhook.send(
                                    embeds=embed_chunk,
                                    thread=thread,
                                    components=components,
                                )
                        else:
                            for embed_chunk in embeds:
                                await webhook.send(
                                    embeds=embed_chunk, components=components
                                )
                    except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                        await log.set_thread(id=None)
                        await log.set_webhook(id=None)
                        continue

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "jlban_" in ctx.data.custom_id:
            check = await self.bot.white_list_check(ctx, "ban add")
            if not check and not ctx.author.guild_permissions.manage_guild:
                await ctx.send(
                    content="You cannot use this component. Missing Permissions.",
                    ephemeral=True,
                )
            player = ctx.data.custom_id.split("_")[-1]
            player = await self.bot.getPlayer(player_tag=player)
            components = [
                disnake.ui.TextInput(
                    label=f"Reason to ban {player.name}",
                    placeholder="Ban Reason (i.e. missed 25 war attacks)",
                    custom_id=f"ban_reason",
                    required=True,
                    style=disnake.TextInputStyle.single_line,
                    max_length=100,
                )
            ]
            await ctx.response.send_modal(
                title="Ban Form", custom_id="banform-", components=components
            )

            def check(res):
                return ctx.author.id == res.author.id

            try:
                modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                    "modal_submit",
                    check=check,
                    timeout=300,
                )
            except:
                return

            # await modal_inter.response.defer()
            ban_reason = modal_inter.text_values["ban_reason"]
            ban_cog = self.bot.get_cog(name="Bans")
            embed = await ban_cog.ban_player(ctx, player, ban_reason)
            await modal_inter.send(embed=embed)

        if "jlstrike_" in ctx.data.custom_id:
            check = await self.bot.white_list_check(ctx, "strike add")
            if not check and not ctx.author.guild_permissions.manage_guild:
                await ctx.send(
                    content="You cannot use this component. Missing Permissions.",
                    ephemeral=True,
                )
            player = ctx.data.custom_id.split("_")[-1]
            player = await self.bot.getPlayer(player_tag=player)
            components = [
                disnake.ui.TextInput(
                    label=f"Reason for strike on {player.name}",
                    placeholder="Strike Reason (i.e. low donation ratio)",
                    custom_id=f"strike_reason",
                    required=True,
                    style=disnake.TextInputStyle.single_line,
                    max_length=100,
                ),
                disnake.ui.TextInput(
                    label=f"Rollover Days",
                    placeholder="In how many days you want this to expire",
                    custom_id=f"rollover_days",
                    required=False,
                    style=disnake.TextInputStyle.single_line,
                    max_length=3,
                ),
                disnake.ui.TextInput(
                    label=f"Strike Weight",
                    placeholder="Weight you want for this strike (default is 1)",
                    custom_id=f"strike_weight",
                    required=False,
                    style=disnake.TextInputStyle.single_line,
                    max_length=2,
                ),
            ]
            await ctx.response.send_modal(
                title="Strike Form", custom_id="strikeform-", components=components
            )

            def check(res):
                return ctx.author.id == res.author.id

            try:
                modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                    "modal_submit",
                    check=check,
                    timeout=300,
                )
            except:
                return

            # await modal_inter.response.defer()
            strike_reason = modal_inter.text_values["strike_reason"]
            rollover_days = modal_inter.text_values["rollover_days"]
            if rollover_days != "":
                if not str(rollover_days).isdigit():
                    return await modal_inter.send(
                        content="Rollover Days must be an integer", ephemeral=True
                    )
                else:
                    rollover_days = int(rollover_days)
            else:
                rollover_days = None
            strike_weight = modal_inter.text_values["strike_weight"]
            if strike_weight != "":
                if not str(strike_weight).isdigit():
                    return await modal_inter.send(
                        content="Strike Weight must be an integer", ephemeral=True
                    )
                else:
                    strike_weight = int(strike_weight)
            else:
                strike_weight = 1
            strike_cog = self.bot.get_cog(name="Strikes")
            embed = await strike_cog.strike_player(
                ctx, player, strike_reason, rollover_days, strike_weight
            )
            await modal_inter.send(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(join_leave_events(bot))
