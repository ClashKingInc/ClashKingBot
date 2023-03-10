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
        self.clan_ee.on("all_member_donations", self.donations)

    async def player_join(self, event):
        clan = coc.Clan(data=event["clan"], client=self.bot.coc_client)
        member = coc.ClanMember(data=event["member"], client=self.bot.coc_client, clan=clan)

        if clan.tag not in self.bot.clan_list:
            return

        tracked = self.bot.clan_db.find({"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=10000):
            server = cc.get("server")
            cache_server = self.bot.get_guild(server)
            if cache_server is None:
                continue

            try:
                s_data = await self.bot.server_db.find_one({"server": server})
                if s_data.get("autoeval", False) is False:
                    raise Exception
                link = await self.bot.link_client.get_link(member.tag)
                if link is not None:
                    evalua = self.bot.get_cog("Eval")
                    user = await cache_server.getch_member(link)
                    embed = await evalua.eval_logic(guild=cache_server, members_to_eval=[user], role_or_user=user,
                                                    test=False,
                                                    change_nick="Off", return_embed=True)
                    log_channel = s_data.get("autoeval_log")
                    if log_channel is not None:
                        try:
                            log_channel = await self.bot.getch_channel(log_channel)
                            await log_channel.send(embed=embed)
                        except:
                            pass
            except:
                pass

            joinlog_channel = cc.get("joinlog")
            strike_ban_buttons = cc.get("strike_ban_buttons")
            auto_eval = cc.get("auto_eval")
            if joinlog_channel is None:
                continue
            try:
                joinlog_channel: disnake.TextChannel = await self.bot.getch_channel(joinlog_channel)
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




    async def player_leave(self, event):
        clan = coc.Clan(data=event["clan"], client=self.bot.coc_client)
        member = coc.ClanMember(data=event["member"], client=self.bot.coc_client, clan=clan)

        tracked = self.bot.clan_db.find({"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=10000):
            server = cc.get("server")
            cache_server = self.bot.get_guild(server)
            if cache_server is None:
                continue
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

            link = await self.bot.link_client.get_link(player.tag)
            global autoroles_enabled
            if link is not None and joinlog_channel.guild.id in autoroles_enabled:
                evalua = self.bot.get_cog("Eval")
                user = await joinlog_channel.guild.getch_member(link)
                embed = await evalua.eval_logic(guild=joinlog_channel.guild, members_to_eval=[user], role_or_user=user,
                                                test=False,
                                                change_nick="Off", return_embed=True)
                log_channel = await self.bot.getch_channel(1080683358721425478)
                await log_channel.send(embed=embed)

    async def donations(self, event):
        previous_members = event["old_clan"]["memberList"]
        current_members = event["new_clan"]["memberList"]
        clan_tag = event["new_clan"]["tag"]
        if not (clan_tag in self.bot.clan_list):
            return
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
        if limit == 0:
            return
        tag_to_name = {}
        tag_to_share_link = {}
        current_donated_dict = {}
        current_received_dict = {}
        for member in current_members:
            tag_to_share_link[member[
                "tag"]] = f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=%23{member['tag'].strip('#')}"
            tag_to_name[member["tag"]] = member["name"]
            current_donated_dict[member["tag"]] = member["donations"]
            current_received_dict[member["tag"]] = member["donationsReceived"]
        donated = {}
        received = {}
        changes = []
        for member in previous_members:
            if member["tag"] in list(tag_to_name.keys()):
                current_donation = current_donated_dict[member["tag"]]
                current_received = current_received_dict[member["tag"]]
                change_dono = current_donation - member["donations"]
                change_rec = current_received - member["donationsReceived"]
                if change_dono > 0:
                    change_amount = 0.25
                    if member["donations"] > 100000:
                        change_amount = 0.05
                    donated[member["tag"]] = change_dono
                    changes.append(UpdateOne({"tag": member["tag"]}, {"$inc": {f"points": change_amount * change_dono}},
                                             upsert=True))
                if change_rec > 0:
                    received[member["tag"]] = change_rec

        await self.bot.player_stats.bulk_write(changes)
        if changes:
            await self.bot.player_stats.bulk_write(changes)
        clan_share_link = f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{event['new_clan']['tag'].strip('#')}"
        embed = disnake.Embed(description=f"[**{event['new_clan']['name']}**]({clan_share_link})")
        embed.set_thumbnail(url=event['new_clan']["badgeUrls"]["large"])
        donation_text = ""
        for tag, donation in donated.items():
            donation = f"{donation}".ljust(3)
            donation_text += f"<:warwon:932212939899949176>`{donation}` | [**{tag_to_name[tag]}**]({tag_to_share_link[tag]})\n"
        if donation_text != "":
            embed.add_field(name="Donated", value=donation_text, inline=False)
        received_text = ""
        for tag, donation in received.items():
            donation = f"{donation}".ljust(3)
            received_text += f"<:warlost:932212154164183081>`{donation}` | [**{tag_to_name[tag]}**]({tag_to_share_link[tag]})\n"
        if received_text != "":
            embed.add_field(name="Received", value=received_text, inline=False)
        if donation_text != "" or received_text != "":
            tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
            for cc in await tracked.to_list(length=limit):
                server = cc.get("server")
                donolog_channel = cc.get("donolog")
                if donolog_channel is None:
                    continue
                try:
                    donolog_channel = await self.bot.getch_channel(donolog_channel)
                except (disnake.Forbidden, disnake.NotFound):
                    await self.bot.clan_db.update_one({"$and": [
                        {"tag": clan_tag},
                        {"server": server}
                    ]}, {'$set': {"donolog": None}})
                if donolog_channel is None:
                    continue
                try:
                    await donolog_channel.send(embed=embed)
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