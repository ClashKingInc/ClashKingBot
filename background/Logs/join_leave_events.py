import coc
import disnake

from disnake.ext import commands
from Utils.clash import heros
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import DatabaseClan
from background.Logs.event_websockets import clan_ee
from Utils.clash import leagueAndTrophies
from Utils.discord_utils import get_webhook_for_channel
from exceptions.CustomExceptions import MissingWebhookPerms

class join_leave_events(commands.Cog, name="Clan Join & Leave Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("member_join", self.player_join)
        self.clan_ee.on("member_leave", self.player_leave)

    async def player_join(self, event):
        clan = coc.Clan(data=event["clan"], client=self.bot.coc_client)
        member = coc.ClanMember(data=event["member"], client=self.bot.coc_client, clan=clan)

        tracked = self.bot.clan_db.find({"$and": [{"tag": clan.tag}, {"logs.join_log.webhook": {"$ne" : None}}]})
        for cc in await tracked.to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            if db_clan.member_count_warning.channel is not None and clan.member_count >= db_clan.member_count_warning.above:
                try:
                    channel = await self.bot.getch_channel(db_clan.member_count_warning.channel, raise_exception=True)
                    text = f"{clan.name} is at or above {db_clan.member_count_warning.above} members"
                    embed = disnake.Embed(description=text, color=disnake.Color.green())
                    embed.set_thumbnail(url=clan.badge.url)
                    content = None
                    if db_clan.member_count_warning.role is not None:
                        content = f"<@&{db_clan.member_count_warning.role}>"
                    if content is None:
                        await channel.send(embed=embed)
                    else:
                        await channel.send(embed=embed, content=content)
                except (disnake.NotFound, disnake.Forbidden):
                    await db_clan.member_count_warning.set_channel(id=None)

            join_result = await self.bot.clan_join_leave.count_documents({"$and" : [{"tag" : member.tag}, {"clan" : clan.tag}]})
            if join_result <= 1:
                linked = await self.bot.link_client.get_link(member.tag)
                if linked is not None:
                    greeting = db_clan.greeting
                    if greeting == "":
                        badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
                        greeting = f", welcome to {badge}{clan.name}!"
                    channel = await self.bot.getch_channel(db_clan.clan_channel)
                    if channel is not None:
                        try:
                            await channel.send(f"<@{linked}> {greeting}")
                        except:
                            pass
            log = db_clan.join_log

            player = await self.bot.getPlayer(player_tag=member.tag)
            hero = heros(bot=self.bot, player=player)
            hero = "" if hero is None else hero

            th_emoji = self.bot.fetch_emoji(player.town_hall)
            embed = disnake.Embed(description=f"[**{player.name}** ({player.tag})]({player.share_link})\n" +
                                              f"**{th_emoji}{player.town_hall}{leagueAndTrophies(player)}<:star:825571962699907152>{player.war_stars}{hero}**\n",
                                  color=disnake.Color.green())
            embed.set_footer(icon_url=clan.badge.url, text=f"Joined {clan.name} [{clan.member_count}/50]")
            components = []
            if log.profile_button:
                stat_buttons = [
                    disnake.ui.Button(label="", emoji=self.bot.emoji.troop.partial_emoji, style=disnake.ButtonStyle.green, custom_id=f"redditplayer_{player.tag}")]
                buttons = disnake.ui.ActionRow()
                for button in stat_buttons:
                    buttons.append_item(button)
                components = [buttons]
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(embed=embed, thread=thread, components=components)
                else:
                    await webhook.send(embed=embed, components=components)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


    async def player_leave(self, event):
        clan = coc.Clan(data=event["clan"], client=self.bot.coc_client)
        member = coc.ClanMember(data=event["member"], client=self.bot.coc_client, clan=clan)

        for cc in await self.bot.clan_db.find({"$and": [{"tag": clan.tag}, {"logs.leave_log.webhook": {"$ne" : None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            if db_clan.member_count_warning.channel is not None and clan.member_count <= db_clan.member_count_warning.below:
                try:
                    channel = await self.bot.getch_channel(db_clan.member_count_warning.channel, raise_exception=True)
                    text = f"{clan.name} is at or below {db_clan.member_count_warning.below} members"
                    embed = disnake.Embed(description=text, color=disnake.Color.red())
                    embed.set_thumbnail(url=clan.badge.url)
                    content = None
                    if db_clan.member_count_warning.role is not None:
                        content = f"<@&{db_clan.member_count_warning.role}>"
                    if content is None:
                        await channel.send(embed=embed)
                    else:
                        await channel.send(embed=embed, content=content)
                except (disnake.NotFound, disnake.Forbidden):
                    await db_clan.member_count_warning.set_channel(id=None)

            log = db_clan.leave_log

            player = await self.bot.getPlayer(player_tag=member.tag)
            hero = heros(bot=self.bot, player=player)
            hero = "" if hero is None else hero

            th_emoji = self.bot.fetch_emoji(player.town_hall)
            embed = disnake.Embed(description=f"[**{player.name}** ({player.tag})]({player.share_link})\n" +
                                              f"**{th_emoji}{player.town_hall}{leagueAndTrophies(player)}<:star:825571962699907152>{player.war_stars}{hero}**\n",
                                  color=disnake.Color.red())

            if player.clan is not None and player.clan.tag != clan.tag:
                embed.set_footer(icon_url=player.clan.badge.url,
                                 text=f"Left {clan.name} [{clan.member_count}/50] and Joined {player.clan.name}")
            else:
                embed.set_footer(icon_url=clan.badge.url,
                                 text=f"Left {clan.name} [{clan.member_count}/50]")
            components = []
            if log.ban_button or log.strike_button:
                stat = []
                if log.ban_button:
                    stat += [disnake.ui.Button(label="Ban", emoji="🔨", style=disnake.ButtonStyle.red,
                                      custom_id=f"jlban_{player.tag}")]
                if log.strike_button:
                    stat += [disnake.ui.Button(label="Strike", emoji="✏️", style=disnake.ButtonStyle.grey,
                                      custom_id=f"jlstrike_{player.tag}")]
                buttons = disnake.ui.ActionRow()
                for button in stat:
                    buttons.append_item(button)
                components = [buttons]
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(embed=embed, thread=thread, components=components)
                else:
                    await webhook.send(embed=embed, components=components)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "jlban_" in ctx.data.custom_id:
            check = await self.bot.white_list_check(ctx, "ban add")
            if not check and not ctx.author.guild_permissions.manage_guild:
                await ctx.send(content="You cannot use this component. Missing Permissions.", ephemeral=True)
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
                title="Ban Form",
                custom_id="banform-",
                components=components)

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

            #await modal_inter.response.defer()
            ban_reason = modal_inter.text_values["ban_reason"]
            ban_cog = self.bot.get_cog(name="Bans")
            embed = await ban_cog.ban_player(ctx, player, ban_reason)
            await modal_inter.send(embed=embed)

        if "jlstrike_" in ctx.data.custom_id:
            check = await self.bot.white_list_check(ctx, "strike add")
            if not check and not ctx.author.guild_permissions.manage_guild:
                await ctx.send(content="You cannot use this component. Missing Permissions.", ephemeral=True)
            player = ctx.data.custom_id.split("_")[-1]
            player = await self.bot.getPlayer(player_tag=player)
            components = [
                disnake.ui.TextInput(
                    label=f"Reason for strike on {player.name}",
                    placeholder="Strike Reason (i.e. low donation ratio)",
                    custom_id=f"strike_reason",
                    required=True,
                    style=disnake.TextInputStyle.single_line,
                    max_length=100
                ),
                disnake.ui.TextInput(
                    label=f"Rollover Days",
                    placeholder="In how many days you want this to expire",
                    custom_id=f"rollover_days",
                    required=False,
                    style=disnake.TextInputStyle.single_line,
                    max_length=3
                ),
                disnake.ui.TextInput(
                    label=f"Strike Weight",
                    placeholder="Weight you want for this strike (default is 1)",
                    custom_id=f"strike_weight",
                    required=False,
                    style=disnake.TextInputStyle.single_line,
                    max_length=2
                )
            ]
            await ctx.response.send_modal(
                title="Strike Form",
                custom_id="strikeform-",
                components=components)

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

            #await modal_inter.response.defer()
            strike_reason = modal_inter.text_values["strike_reason"]
            rollover_days = modal_inter.text_values["rollover_days"]
            if rollover_days != "":
                if not str(rollover_days).isdigit():
                    return await modal_inter.send(content="Rollover Days must be an integer", ephemeral=True)
                else:
                    rollover_days = int(rollover_days)
            else:
                rollover_days = None
            strike_weight = modal_inter.text_values["strike_weight"]
            if strike_weight != "":
                if not str(strike_weight).isdigit():
                    return await modal_inter.send(content="Strike Weight must be an integer", ephemeral=True)
                else:
                    strike_weight = int(strike_weight)
            else:
                strike_weight = 1
            strike_cog = self.bot.get_cog(name="Strikes")
            embed = await strike_cog.strike_player(ctx, player, strike_reason, rollover_days, strike_weight)
            await modal_inter.send(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(join_leave_events(bot))