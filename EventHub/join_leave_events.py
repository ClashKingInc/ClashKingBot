import coc
from disnake.ext import commands
import disnake
from utils.troop_methods import heros, heroPets
from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import clan_ee
from utils.troop_methods import leagueAndTrophies
from pymongo import UpdateOne

class join_leave_events(commands.Cog, name="Clan Join & Leave Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("member_join", self.player_join)
        self.clan_ee.on("member_leave", self.player_leave)


    async def player_join(self, event):
        clan = coc.Clan(data=event["clan"], client=self.bot.coc_client)
        member = coc.ClanMember(data=event["member"], client=self.bot.coc_client, clan=clan)


        tracked = self.bot.clan_db.find({"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=10000):
            server = cc.get("server")
            joinlog_channel = cc.get("joinlog")
            strike_ban_buttons = cc.get("strike_ban_buttons")
            auto_eval = cc.get("auto_eval")
            if joinlog_channel is None:
                continue
            try:
                joinlog_channel = await self.bot.getch_channel(joinlog_channel)
            except (disnake.Forbidden, disnake.NotFound):
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan.tag},
                    {"server": server}
                ]}, {'$set': {"joinlog": None}})

            if joinlog_channel is None:
                continue

            player = await self.bot.getPlayer(player_tag=member.tag)
            hero = heros(bot=self.bot, player=player)
            #pets = heroPets(bot=self.bot, player=player)
            if hero is None:
                hero = ""
            else:
                hero = f"{hero}"

            th_emoji = self.bot.fetch_emoji(player.town_hall)
            embed = disnake.Embed(description=f"[**{player.name}** ({player.tag})]({player.share_link})\n" +
                                              f"**{th_emoji}{player.town_hall}{leagueAndTrophies(player)}<:star:825571962699907152>{player.war_stars}{hero}**\n"
                                  , color=disnake.Color.green())
            embed.set_footer(icon_url=clan.badge.url, text=f"Joined {clan.name} [{clan.member_count}/50]")
            try:
                await joinlog_channel.send(embed=embed)
            except:
                continue



            """if auto_eval:
                role_mode = cc.get("role_mode")
                all_tags = new_tags + left_tags
                links = await self.bot.link_client.get_links(*all_tags)
                links = dict(links)
                for tag in all_tags:
                    evalua = self.bot.get_cog("Eval")
                    embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[ctx.author], role_or_user=ctx.author,
                                                    test=False,
                                                    change_nick="Off", return_embed=True)"""

    async def player_leave(self, event):
        clan = coc.Clan(data=event["clan"], client=self.bot.coc_client)
        member = coc.ClanMember(data=event["member"], client=self.bot.coc_client, clan=clan)

        tracked = self.bot.clan_db.find({"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=10000):
            server = cc.get("server")
            joinlog_channel = cc.get("joinlog")
            strike_ban_buttons = cc.get("strike_ban_buttons")
            auto_eval = cc.get("auto_eval")
            if joinlog_channel is None:
                continue
            try:
                joinlog_channel = await self.bot.getch_channel(joinlog_channel)
            except (disnake.Forbidden, disnake.NotFound):
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan.tag},
                    {"server": server}
                ]}, {'$set': {"joinlog": None}})

            if joinlog_channel is None:
                continue

            player = await self.bot.getPlayer(player_tag=member.tag)
            hero = heros(bot=self.bot, player=player)
            # pets = heroPets(bot=self.bot, player=player)
            if hero is None:
                hero = ""
            else:
                hero = f"{hero}"

            th_emoji = self.bot.fetch_emoji(player.town_hall)
            embed = disnake.Embed(description=f"[**{player.name}** ({player.tag})]({player.share_link})\n" +
                                              f"**{th_emoji}{player.town_hall}{leagueAndTrophies(player)}<:star:825571962699907152>{player.war_stars}{hero}**\n"
                                  , color=disnake.Color.red())
            if player.clan is not None:
                embed.set_footer(icon_url=player.clan.badge.url,
                                 text=f"Left {clan.name} [{clan.member_count}/50] and Joined {player.clan.name}")
            else:
                embed.set_footer(icon_url=event["new_clan"]["badgeUrls"]["large"],
                                 text=f"Left {clan.name} [{clan.member_count}/50] ")
            try:
                components = []
                if strike_ban_buttons:
                    stat_buttons = [
                        disnake.ui.Button(label="Ban", emoji="🔨", style=disnake.ButtonStyle.red,
                                          custom_id=f"jlban_{player.tag}"),
                        disnake.ui.Button(label="Strike", emoji="✏️", style=disnake.ButtonStyle.grey,
                                          custom_id=f"jlstrike_{player.tag}")]
                    buttons = disnake.ui.ActionRow()
                    for button in stat_buttons:
                        buttons.append_item(button)
                    components = [buttons]
                await joinlog_channel.send(embed=embed, components=components)
            except:
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