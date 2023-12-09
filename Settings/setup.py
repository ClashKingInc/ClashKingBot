import disnake
import coc

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from utils.general import calculate_time
from main import check_commands
from typing import Union
from utils.discord_utils import get_webhook_for_channel
from Exceptions.CustomExceptions import *
from utils.discord_utils import  interaction_handler, basic_embed_modal
from CustomClasses.CustomServer import DatabaseClan
from utils.components import clan_component
from Discord.autocomplete import Autocomplete as autocomplete
from Discord.converters import Convert as convert

class SetupCommands(commands.Cog , name="Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.color = disnake.Color.dark_theme()

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan


    @commands.slash_command(name="setup")
    async def setup(self, ctx: disnake.ApplicationCommandInteraction):
        pass


    @commands.message_command(name="Refresh Board", dm_permission=False)
    async def refresh_board(self, ctx: disnake.MessageCommandInteraction, message: disnake.Message):
        check = await self.bot.white_list_check(ctx, "setup server-settings")
        await ctx.response.defer(ephemeral=True)
        if not check and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(content="You cannot use this command. Missing Permissions. Must have `Manage Server` permissions or be whitelisted for `/setup server-settings`", ephemeral=True)
        custom_id = None
        if message.components:
            custom_id = message.components[0].children[0].custom_id
        result = await self.bot.button_store.find_one({"button_id": custom_id})
        if result is None:
            raise MessageException("Error Occurred")
        webhook = await get_webhook_for_channel(channel=message.channel, bot=self.bot)
        thread = None
        if isinstance(message.channel, disnake.Thread):
            await message.channel.add_user(self.bot.user)
            thread = message.channel.id

        if thread:
            thread = await self.bot.getch_channel(thread)
            webhook_message = await webhook.send(embeds=message.embeds, thread=thread, wait=True)
        else:
            webhook_message = await webhook.send(embeds=message.embeds, wait=True)

        await self.bot.button_store.update_one({"button_id" : custom_id}, {"$set" : {"webhook_id" : webhook.id, "thread_id" : thread, "message_id" : webhook_message.id}})
        await message.delete()
        await ctx.send("Refresh Board Created", ephemeral=True)




    @setup.sub_command(name="server-settings", description="Set settings for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def server_settings(self, ctx: disnake.ApplicationCommandInteraction, banlist_channel: Union[disnake.TextChannel, disnake.Thread] = None,
                              change_nicknames: str = commands.Param(default=None, choices=["On", "Off"]),
                              nickname_convention: str = commands.Param(default=None),
                              api_token: str = commands.Param(default=None, choices=["Use", "Don't Use"]),
                              leadership_eval: str = commands.Param(default=None, choices=["True", "False"]),
                              tied_stats_only: str = commands.Param(default=None, choices=["True", "False"]),
                              embed_color: str = commands.Param(default=None, converter=convert.hex_code)):
        await ctx.response.defer()
        db_server = await self.bot.get_custom_server(guild_id=ctx.guild_id)
        changed_text = ""
        if banlist_channel is not None:
            await db_server.set_banlist_channel(id=banlist_channel.id)
            changed_text += f"- **Banlist Channel:** {banlist_channel.mention}\n"
        if api_token is not None:
            await db_server.set_api_token(status=(api_token == "Use"))
            changed_text += f"- **Api Token:** `{api_token}`\n"
        if leadership_eval is not None:
            await db_server.set_leadership_eval(status=(leadership_eval == "True"))
            changed_text += f"- **Leadership Eval:** `{leadership_eval}`\n"
        if tied_stats_only is not None:
            await db_server.set_tied_stats(state=(tied_stats_only == "True"))
            changed_text += f"- **Tied Stats Only:** `{tied_stats_only}`\n"
        if embed_color is not None:
            await db_server.set_hex_code(hex_code=embed_color)
            changed_text += f"- **Embed Color:** `{embed_color}`\n"
        if change_nicknames is not None:
            await db_server.set_change_nickname(status=(change_nicknames == "On"))
            changed_text += f"- **Change Nicknames:** `{change_nicknames}`\n"
        if nickname_convention is not None:
            await db_server.set_nickname_convention(rule=nickname_convention)
            changed_text += f"- **Nickname Convention:** `{nickname_convention}`\n"


        if changed_text == "":
            changed_text = "No Changes Made!"
        embed = disnake.Embed(title=f"{ctx.guild.name} Settings Changed", description=changed_text, color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.edit_original_message(embed=embed)



    @setup.sub_command(name="clan-settings", description="Set settings for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clan_settings(self, ctx: disnake.ApplicationCommandInteraction,
                            clan: coc.Clan = commands.Param(converter=clan_converter, autocomplete=autocomplete.clan),
                            member_role: disnake.Role = None,
                            leadership_role: disnake.Role = None, clan_channel: Union[disnake.TextChannel, disnake.Thread] = None, greeting: str = None,
                            category: str = commands.Param(default=None, autocomplete=autocomplete.category),
                            ban_alert_channel: Union[disnake.TextChannel, disnake.Thread] = None,
                            nickname_label: str = None,
                            strike_button=commands.Param(default=None, choices=["True", "False"]),
                            ban_button=commands.Param(default=None, choices=["True", "False"]),
                            profile_button=commands.Param(default=None, choices=["True", "False"])):

        await ctx.response.defer()
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            raise ThingNotFound("**This clan is not set up on this server. Use `/addclan` to get started.**")
        db_clan = DatabaseClan(bot=self.bot, data=results)
        changed_text = ""
        if member_role is not None:
            await db_clan.set_member_role(id=member_role.id)
            changed_text += f"- **Member Role:** {member_role.mention}\n"
        if leadership_role is not None:
            await db_clan.set_leadership_role(id=leadership_role.id)
            changed_text += f"- **Leadership Role:** {leadership_role.mention}\n"
        if clan_channel is not None:
            await db_clan.set_clan_channel(id=clan_channel.id)
            changed_text += f"- **Clan Channel:** {clan_channel.mention}\n"
        if greeting is not None:
            await db_clan.set_greeting(text=greeting)
            changed_text += f"- **Greeting:** {greeting}\n"
        if category is not None:
            await db_clan.set_category(category=category)
            changed_text += f"- **Category:** `{category}`\n"
        if ban_alert_channel is not None:
            await db_clan.set_ban_alert_channel(id=ban_alert_channel.id)
            changed_text += f"- **Ban Alert Channel:** {ban_alert_channel.mention}\n"
        if nickname_label is not None:
            await db_clan.set_nickname_label(abbreviation=nickname_label[:16])
            changed_text += f"- **Nickname Label:** `{nickname_label[:16]}`\n"
        if strike_button is not None:
            await db_clan.set_strike_button(set=(strike_button == "True"))
            changed_text += f"- **Strike Button:** `{strike_button}`\n"
        if ban_button is not None:
            await db_clan.set_ban_button(set=(ban_button == "True"))
            changed_text += f"- **Ban Button:** `{ban_button}`\n"
        if profile_button is not None:
            await db_clan.set_profile_button(set=(profile_button == "True"))
            changed_text += f"- **Profile Button:** `{profile_button}`\n"
        if changed_text == "":
            changed_text = "No Changes Made!"
        embed = disnake.Embed(title=f"{clan.name} Settings Changed", description=changed_text, color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.edit_original_message(embed=embed)


    @setup.sub_command(name="user-settings", description="Set bot settings for yourself like main account or timezone")
    async def user_settings(self, ctx: disnake.ApplicationCommandInteraction,
                            main_account: str, timezone: str):
        pass


    @setup.sub_command(name="list", description="List of setup & settings")
    async def settings_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        db_server = await self.bot.get_custom_server(guild_id=ctx.guild_id)

        clans = await self.bot.get_clans(tags=(await self.bot.get_guild_clans(guild_id=ctx.guild.id)))

        embed = disnake.Embed(title=f"{ctx.guild.name} Server Settings", color=disnake.Color.green())
        banlist_channel = f"<#{db_server.banlist_channel}>" if db_server.banlist_channel is not None else None
        reddit_feed = f"<#{db_server.reddit_feed}>" if db_server.reddit_feed is not None else None

        embed.add_field(name="Banlist Channel:", value=banlist_channel, inline=True)
        embed.add_field(name="Reddit Feed:", value=reddit_feed, inline=True)
        embed.add_field(name="Leadership Eval:", value=f"{db_server.leadership_eval}", inline=True)
        embed.add_field(name="Use API Token:", value=f"{db_server.use_api_token}", inline=True)
        embed.add_field(name="Nickname Setting:", value=f"{db_server.auto_nickname}", inline=True)

        dropdown = [clan_component(bot=self.bot, all_clans=clans, clan_page=0, max_choose=1)]

        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embeds = [embed]
        tag_to_spot = {}
        spot = 1
        for clan in db_server.clans: #type: DatabaseClan
            got_clan = await self.bot.getClan(clan.tag)
            tag_to_spot[clan.tag] = spot
            spot += 1
            if got_clan is None:
                continue
            embed = disnake.Embed(title=f"{clan.name}", color=disnake.Color.green())
            embed.set_thumbnail(url=got_clan.badge.url)
            member_role = f"<@&{clan.member_role}>" if clan.member_role is not None else None
            leader_role = f"<@&{clan.leader_role}>" if clan.leader_role is not None else None
            clan_channel = f"<#{clan.clan_channel}>" if clan.clan_channel is not None else None
            embed.add_field(name="Member Role:", value=member_role, inline=True)
            embed.add_field(name="Leadership Role:", value=leader_role, inline=True)
            embed.add_field(name="Clan Channel:", value=clan_channel, inline=True)
            if clan.greeting:
                embed.add_field(name="Greeting:", value=f"{clan.greeting}", inline=True)


            embed.add_field(name="Join Log:", value=f"{(await clan.join_log.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Leave Log:", value=f"{(await clan.leave_log.get_webhook_channel_mention())}", inline=True)

            embed.add_field(name="War Log:", value=f"{(await clan.war_log.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="War Panel:", value=f"{(await clan.war_panel.get_webhook_channel_mention())}", inline=True)


            embed.add_field(name="Capital Dono Log:", value=f"{(await clan.capital_donations.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Capital Atk Log:", value=f"{(await clan.capital_attacks.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Capital Weekly Summary:", value=f"{(await clan.capital_weekly_summary.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Capital Raid Panel:", value=f"{(await clan.raid_panel.get_webhook_channel_mention())}", inline=True)

            embed.add_field(name="Donation Log:", value=f"{(await clan.donation_log.get_webhook_channel_mention())}", inline=True)

            embed.add_field(name="Super Troop Boost Log:", value=f"{(await clan.super_troop_boost_log.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Role Change Log:", value=f"{(await clan.role_change.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Troop Upgrade Log:", value=f"{(await clan.troop_upgrade.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="TH Upgrade Log:", value=f"{(await clan.th_upgrade.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="League Change Log:", value=f"{(await clan.league_change.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Spell Upgrade Log:", value=f"{(await clan.spell_upgrade.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Hero Upgrade Log:", value=f"{(await clan.hero_upgrade.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Name Change Log:", value=f"{(await clan.name_change.get_webhook_channel_mention())}", inline=True)

            embed.add_field(name="Legend Atk Log:", value=f"{(await clan.legend_log_attacks.get_webhook_channel_mention())}", inline=True)
            embed.add_field(name="Legend Def Log:", value=f"{(await clan.legend_log_defenses.get_webhook_channel_mention())}", inline=True)

            embeds.append(embed)

        await ctx.edit_original_message(embed=embeds[0], components=dropdown)
        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            clan_tag = res.values[0].split("_")[-1]
            spot = tag_to_spot.get(clan_tag)
            await res.edit_original_message(embed=embeds[spot])



    @setup.sub_command(name="autoeval", description="Turn autoeval on/off")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autoeval(self, ctx: disnake.ApplicationCommandInteraction, option=commands.Param(choices=["On", "Off"]),
                       log: Union[disnake.TextChannel, disnake.Thread] = commands.Param(default=None, name="log")):
        await ctx.response.defer()

        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"autoeval": option == "On"}})

        log_text = ""
        if log is not None:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"autoeval_log": log.id}})
            log_text = f"and will log in {log.mention}"
        await ctx.edit_original_message(f"**Autoeval is now turned {option} {log_text}**", allowed_mentions=disnake.AllowedMentions.none())

    @setup.sub_command(name="logs", description="Set a variety of different clan logs for your server!")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_log_add(self, ctx: disnake.ApplicationCommandInteraction,
                          clan: coc.Clan = commands.Param(converter=clan_converter), mode:str = commands.Param(choices=["Add/Edit", "Remove"]),
                          channel: Union[disnake.TextChannel, disnake.Thread] = commands.Param(default=None)):
        await ctx.response.defer()

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            raise ThingNotFound("**This clan is not set up on this server. Use `/addclan` to get started.**")

        db_clan = DatabaseClan(bot=self.bot, data=results)
        channel = ctx.channel if channel is None else channel

        log_types = {"Member Join" : db_clan.join_log, "Member Leave" : db_clan.leave_log, "War Log" : db_clan.war_log, "War Panel" : db_clan.war_panel,
                     "Capital Donations" : db_clan.capital_donations, "Capital Attacks" : db_clan.capital_attacks, "Capital Panel" : db_clan.raid_panel,
                     "Capital Weekly Summary" : db_clan.capital_weekly_summary, "Donation Log" : db_clan.donation_log, "Super Troop Boosts" : db_clan.super_troop_boost_log,
                     "Role Change" : db_clan.role_change, "Troop Upgrade" : db_clan.troop_upgrade, "Townhall Upgrade" : db_clan.th_upgrade, "League Change" : db_clan.league_change,
                     "Spell Upgrade" : db_clan.spell_upgrade, "Hero Upgrade" : db_clan.hero_upgrade, "Name Change" : db_clan.name_change,
                     "Legend Attacks" : db_clan.legend_log_attacks, "Legend Defenses" : db_clan.legend_log_defenses}

        if mode == "Remove":
            for log_type, log in log_types.copy().items():
                if log.webhook is None:
                    del log_types[log_type]

        options = []
        for log_type in log_types.keys():
            options.append(disnake.SelectOption(label=log_type, emoji=self.bot.emoji.clock.partial_emoji, value=log_type))

        select = disnake.ui.Select(
            options=options,
            placeholder="Select logs!",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        channel_text = "" if mode == "Remove" else f"in {channel.mention}"
        embed = disnake.Embed(
            description=f"Choose the logs that you would like to {mode.lower()} for {clan.name} {channel_text}\n"
                        f"Visit https://docs.clashking.xyz/clan-setups/log-setup for more info", color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=dropdown)

        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
        if mode == "Add/Edit":
            webhook = await get_webhook_for_channel(channel=channel, bot=self.bot)
            thread = None
            if isinstance(channel, disnake.Thread):
                await channel.add_user(self.bot.user)
                thread = channel.id


        text = ""
        for value in res.values:
            log = log_types[value]
            if mode == "Add/Edit":
                await log.set_webhook(id=webhook.id)
                await log.set_thread(id=thread)
                mention = webhook.channel.mention if thread is None else f"<#{thread}>"
                text += f'{self.bot.emoji.yes}{value} | {mention}\n'
            elif mode == "Remove":
                await log.set_webhook(id=None)
                await log.set_thread(id=None)
                text += f'{self.bot.emoji.yes}{value} Removed\n'


        embed = disnake.Embed(title=f"Logs for {clan.name}", description=text, color=disnake.Color.green())
        await res.edit_original_message(embed=embed, components=[])


    @setup.sub_command(name="reddit-recruit-feed", description="Feed of searching for a clan posts on the recruiting subreddit")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def reddit_recruit(self, ctx: disnake.ApplicationCommandInteraction, channel: Union[disnake.TextChannel, disnake.Thread],
                             role_to_ping: disnake.Role = None,
                             remove=commands.Param(default=None, choices=["Remove Feed"])):
        """
            Parameters
            ----------
            channel: channel to set the feed to
            role_to_ping: role to ping when a new recruit appears
            remove: option to remove this feed
        """
        await ctx.response.defer()

        if remove is None:
            role_id = None if role_to_ping is None else role_to_ping.id
            await self.bot.server_db.update_one({"server": ctx.guild.id},
                                                {"$set": {"reddit_feed": channel.id, "reddit_role": role_id}})

            embed = disnake.Embed(description=f"**Reddit Recruit feed set to {channel.mention}**",
                                  color=disnake.Color.green())

        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id},
                                                {"$set": {"reddit_feed": None, "reddit_role": None}})

            embed = disnake.Embed(description="**Reddit Recruit feed removed**", color=disnake.Color.green())

        return await ctx.edit_original_message(embed=embed)


    @setup.sub_command(name="countdowns", description="Create countdowns for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def voice_setup(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(default=None, converter=clan_converter)):
        """
            Parameters
            ----------
            clan: for war countdowns
        """
        await ctx.response.defer()

        types = ["CWL", "Clan Games", "Raid Weekend", "EOS", "Clan Member Count", "War"]
        emojis = [self.bot.emoji.cwl_medal, self.bot.emoji.clan_games, self.bot.emoji.raid_medal, self.bot.emoji.trophy, self.bot.emoji.person, self.bot.emoji.war_star]
        if clan is None:
            types = types[:-1]
            emojis = emojis[:-1]
        else:
            types = types[-1:]
            emojis = emojis[-1:]
        options = []
        for type, emoji in zip(types, emojis):
            options.append(disnake.SelectOption(label=type if type != "EOS" else "EOS (End of Season)", emoji=emoji.partial_emoji, value=type))

        select = disnake.ui.Select(
            options=options,
            placeholder="Select Options",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(content="**Select Countdowns/Statbars to Create Below**", components=dropdown)

        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)


        results_list = []
        for type in res.values:
            try:
                if type == "Clan Games":
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f"CG {time_}")
                elif type == "Raid Weekend":
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f"Raids {time_}")
                elif type == "Clan Member Count":
                    clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
                    results = await self.bot.player_stats.count_documents(filter={"clan_tag": {"$in": clan_tags}})
                    channel = await ctx.guild.create_voice_channel(name=f"{results} Clan Members")
                elif type == "EOS":
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f"EOS {time_}")
                elif type == "War":
                    war = await self.bot.get_clanwar(clanTag=clan.tag)
                    time_ = await calculate_time(type, war=war)
                    channel = await ctx.guild.create_voice_channel(name=f"{clan.name}: {time_}")
                else:
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f"{type} {time_}")

                overwrite = disnake.PermissionOverwrite()
                overwrite.view_channel = True
                overwrite.connect = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                results_list.append((type, channel))
            except disnake.Forbidden:
                embed = disnake.Embed(description="Bot requires admin to create & set permissions for channel. **Channel will not update**",
                                      color=disnake.Color.red())
                return await ctx.send(embed=embed)

        for type, channel in results_list:
            if type == "CWL":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"cwlCountdown": channel.id}})
            elif type == "Clan Games":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"gamesCountdown": channel.id}})
            elif type == "Raid Weekend":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"raidCountdown": channel.id}})
            elif type == "Clan Member Count":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"memberCount": channel.id}})
            elif type == "War":
                await self.bot.clan_db.update_one({"$and": [{"tag": clan.tag}, {"server": ctx.guild.id}]}, {"$set" : {"warCountdown" : channel.id}})
            else:
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"eosCountdown": channel.id}})


        embed = disnake.Embed(description=f"`{', '.join(res.values)}` Stat Bars Created", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await res.edit_original_message(content="", embed=embed, components=[])


    '''@setup.sub_command(name="autoboards", description="Create family autoboards for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autoboard_create(self, ctx: disnake.ApplicationCommandInteraction):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})

        if not clan_tags:
            embed = disnake.Embed(description="**No clans set up on this server, use `/setup clan-add` to get started.**", color=disnake.Color.red())
            await ctx.edit_original_message(embed=embed)

        content = "**What kind of autoboards would you like to create?**"
        page_buttons = [
            disnake.ui.Button(label="Family", style=disnake.ButtonStyle.grey, custom_id="family"),
            disnake.ui.Button(label="Location", style=disnake.ButtonStyle.grey, custom_id="location"),
            disnake.ui.Button(label="Clan", style=disnake.ButtonStyle.grey, custom_id="clan")
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)
        await ctx.edit_original_message(content=content, components=[buttons])

        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

        scope_type = res.data.custom_id

        page_buttons = [
            disnake.ui.Button(label="Save", emoji=self.bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green, custom_id="Save"),
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        family_types = ["Troop Donations", "Capital Donations", "Player Trophies", "Clan Trophies", "Summary Leaderboard", "Legend Leaderboard"]
        location_types = ["Player Trophies Lb", "Clan Trophies Lb", "Clan Capital Lb"]
        clan_types = ["Capital Donations", "Player Trophies", "Summary Leaderboard", "Legend Leaderboard", "Clan Games"]

        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Clan Games End", "EOS"]
        day_options = []
        for day in days:
            day_options.append(disnake.SelectOption(label=day, value=day, emoji=self.bot.emoji.calendar.partial_emoji))

        day_select = disnake.ui.Select(
            options=day_options,
            placeholder="Days to Post",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(day_options),  # the maximum number of options a user can select
        )

        if scope_type == "family":
            options = []
            for type in family_types:
                options.append(disnake.SelectOption(label=type, value=type))
            select = disnake.ui.Select(
                options=options,
                placeholder="Board Type",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            channel = disnake.ui.ChannelSelect(placeholder="Choose Channel", max_values=1, channel_types=[disnake.ChannelType.text, disnake.ChannelType.public_thread])
            dropdown = [disnake.ui.ActionRow(select), disnake.ui.ActionRow(day_select), disnake.ui.ActionRow(channel), buttons]
        elif scope_type == "location":
            clans = await self.bot.get_clans(tags=clan_tags)
            locations = []
            for clan in clans:
                try:
                    locations.append(str(clan.location))
                except:
                    pass

            locations = ["Global"] + list(set(locations))[:24]
            options = []
            for country in locations:
                options.append(disnake.SelectOption(label=f"{country}", value=f"{country}"))
            country_select = disnake.ui.Select(
                options=options,
                placeholder="Locations",
                min_values=1,  # the minimum number of options a user must select
                max_values=1  # the maximum number of options a user can select
            )

            options = []
            for type in location_types:
                options.append(disnake.SelectOption(label=type, value=type))

            select = disnake.ui.Select(
                options=options,
                placeholder="Board Type",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            channel = disnake.ui.ChannelSelect(placeholder="Choose Channel", max_values=1, channel_types=[disnake.ChannelType.text, disnake.ChannelType.public_thread])
            dropdown = [disnake.ui.ActionRow(select), disnake.ui.ActionRow(country_select), disnake.ui.ActionRow(day_select), disnake.ui.ActionRow(channel), buttons]

        elif scope_type == "clan":
            options = []
            for type in clan_types:
                options.append(disnake.SelectOption(label=type, value=type))
            select = disnake.ui.Select(
                options=options,
                placeholder="Board Type",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            clans: list[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            clans = [clan for clan in clans if clan is not None and clan.member_count != 0]
            clans = sorted(clans, key=lambda x: x.member_count, reverse=True)
            options = []
            for clan in clans:
                try:
                    options.append(disnake.SelectOption(label=clan.name, value=clan.tag))
                except:
                    pass
            clan_select = disnake.ui.Select(
                options=options[:25],
                placeholder="Clan",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            channel = disnake.ui.ChannelSelect(placeholder="Choose Channel", max_values=1, channel_types=[disnake.ChannelType.text, disnake.ChannelType.public_thread])
            dropdown = [disnake.ui.ActionRow(select), disnake.ui.ActionRow(clan_select), disnake.ui.ActionRow(day_select), disnake.ui.ActionRow(channel), buttons]

        await ctx.edit_original_message(content="**Choose board type & Settings**\n- All Boards will post between 4:50 - 5:00 am UTC on the days you select", components=dropdown)

        location = None
        board_type = None
        days_to_post = []
        channel = None
        clan = None
        save = False
        while not save:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            if "button" in str(res.data.component_type):
                if channel is None:
                    await res.send(content="Must select a channel", ephemeral=True)
                elif board_type is None:
                    await res.send(content="Must select a board type", ephemeral=True)
                elif scope_type == "clan" and clan is None:
                    await res.send(content="Must select a clan", ephemeral=True)
                elif scope_type == "location" and location is None:
                    await res.send(content="Must select a location", ephemeral=True)
                elif not days_to_post:
                    await res.send(content="Must select days to post this autoboard on", ephemeral=True)
                else:
                    save = True
            elif "string_select" in str(res.data.component_type):
                if res.values[0] in location_types + clan_types + family_types:
                    board_type = res.values[0]
                elif "#" in res.values[0]:
                    clan = res.values[0]
                elif res.values[0] in days:
                    days_to_post = res.values
                else:
                    location = res.values[0]
            else:
                channel = res.values[0]

        await self.bot.autoboard_db.insert_one({
            "scope" : scope_type,
            "board_type" : board_type,
            "location" : location,
            "days" : days_to_post,
            "channel" : channel
        })

        embed= disnake.Embed(description="**Autoboard Successfully Created**", color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=[], content="")'''

    @setup.sub_command(name="welcome-link", description="Create a custom welcome message that can include linking buttons")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def welcome_message(self, ctx: disnake.ApplicationCommandInteraction, channel: Union[disnake.TextChannel, disnake.Thread], custom_embed = commands.Param(default="False", choices=["True", "False"]),
                              embed_link: str = None, remove = commands.Param(default="No", choices=["Yes"])):
        if remove == "Yes":
            await ctx.response.defer()
            await self.bot.server_db.update_one({"server": ctx.guild_id},
                                            {"$set": {"welcome_link_channel": None}})
            return await ctx.edit_original_message(content="Welcome Message Removed!")

        if custom_embed != "False":
            if embed_link is None:
                modal_inter, embed = await basic_embed_modal(bot=self.bot, ctx=ctx)
                ctx = modal_inter
            else:
                await ctx.response.defer()
                try:
                    if "discord.com" not in embed_link:
                        return await ctx.send(content="Not a valid message link", ephemeral=True)
                    link_split = embed_link.split("/")
                    message_id = link_split[-1]
                    channel_id = link_split[-2]

                    channel = await self.bot.getch_channel(channel_id=int(channel_id))
                    if channel is None:
                        return await ctx.send(content="Cannot access the channel this embed is in", ephemeral=True)
                    message = await channel.fetch_message(int(message_id))
                    if not message.embeds:
                        return await ctx.send(content="Message has no embeds", ephemeral=True)
                    embed = message.embeds[0]
                except:
                    return await ctx.send(content=f"Something went wrong :/ An error occured with the message link.", ephemeral=True)
        else:
            await ctx.response.defer()
            embed = None



        stat_buttons = [disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.green, disabled=True,
                                          custom_id="LINKDEMO"),
                        disnake.ui.Button(label="Help", emoji="❓", style=disnake.ButtonStyle.grey, disabled=True,
                                          custom_id="LINKDEMOHELP")]
        if embed is not None:
            await self.bot.server_db.update_one({"server" : ctx.guild_id}, {"$set" : {"welcome_link_channel" : channel.id, "welcome_link_embed" : embed.to_dict()}})
        else:
            await self.bot.server_db.update_one({"server": ctx.guild_id}, {"$set": {"welcome_link_channel": channel.id, "welcome_link_embed": None}})
        if embed is None:
            embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                          description=f"To link your account, press the link button below to get started.",
                          color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.edit_original_message(content=f"Welcome Message Set in {channel.mention}\n||(buttons for demo & will work on the live version)||", embed=embed, components=stat_buttons)




    @set_log_add.autocomplete("clan")
    @voice_setup.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]




def setup(bot: CustomClient):
    bot.add_cog(SetupCommands(bot))