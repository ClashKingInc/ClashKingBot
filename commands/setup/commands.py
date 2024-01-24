import disnake
import coc
import secrets
import re
from disnake.ext import commands

from main import check_commands
from typing import Union
from exceptions.CustomExceptions import *

from classes.server import DatabaseClan
from classes.enum import LinkParseTypes
from classes.bot import CustomClient

from utility.discord_utils import  interaction_handler, basic_embed_modal, get_webhook_for_channel, registered_functions
from utility.general import calculate_time, get_guild_icon
from utility.components import clan_component

from discord import autocomplete, convert, options


class SetupCommands(commands.Cog , name="Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.color = disnake.Color.dark_theme()

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @commands.message_command(name="Refresh Board", dm_permission=False)
    async def refresh_board(self, ctx: disnake.MessageCommandInteraction, message: disnake.Message):
        check = await self.bot.white_list_check(ctx, "setup server-settings")
        await ctx.response.defer(ephemeral=True)
        if not check and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(content="You cannot use this command. Missing Permissions. Must have `Manage Server` permissions or be whitelisted for `/setup server-settings`",
                                  ephemeral=True)
        custom_id = None
        if message.components:
            custom_id = message.components[0].children[0].custom_id
        name = custom_id.split(":")[0]
        unallowed_refreshes = {"familygames", "familyheroprogress", "familytroopprogress", 'familysorted', "familydonos", "familyactivity"}
        if name in unallowed_refreshes:
            raise MessageException("This command does not support auto refreshing currently")
        if "ctx" in custom_id or registered_functions.get(name) is None:
            raise MessageException("Cannot auto-refresh this command")
        webhook = await get_webhook_for_channel(channel=message.channel, bot=self.bot)
        thread = None
        if isinstance(message.channel, disnake.Thread):
            await message.channel.add_user(self.bot.user)
            thread = message.channel.id

        if thread is not None:
            thread = await self.bot.getch_channel(thread)
            webhook_message = await webhook.send(embeds=message.embeds, thread=thread, wait=True)
            thread = thread.id
        else:
            webhook_message = await webhook.send(embeds=message.embeds, wait=True)

        await self.bot.button_store.update_one({"$and" : [{"button_id": custom_id}, {"server" : ctx.guild_id}]},
                                                {"$set": {"webhook_id": webhook.id, "thread_id": thread, "message_id": webhook_message.id}}, upsert=True)
        await message.delete()
        await ctx.send("Refresh Board Created", ephemeral=True)


    @commands.slash_command(name="setup")
    async def setup(self, ctx: disnake.ApplicationCommandInteraction):
        pass



    @setup.sub_command(name="server", description="Set settings for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def server_settings(self, ctx: disnake.ApplicationCommandInteraction,
                              banlist_channel: Union[disnake.TextChannel, disnake.Thread] = None,
                              change_nicknames: str = commands.Param(default=None, choices=["On", "Off"]),
                              nickname_convention: str = commands.Param(default=None),
                              api_token: str = commands.Param(default=None, choices=["Use", "Don't Use"]),
                              leadership_eval: str = commands.Param(default=None, choices=["True", "False"]),
                              embed_color: str = commands.Param(default=None, converter=convert.hex_code)):
        await ctx.response.defer()
        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
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



    @setup.sub_command(name="clan", description="Set settings for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clan_settings(self, ctx: disnake.ApplicationCommandInteraction,
                            clan: coc.Clan = options.clan,
                            member_role: disnake.Role = None,
                            leadership_role: disnake.Role = None,
                            clan_channel: Union[disnake.TextChannel, disnake.Thread] = None,
                            greeting: str = None,
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
                            default_main_account: str = None,
                            server_main_account: str= None,
                            timezone: str = None,
                            private_mode: str = commands.Param(default=None,choices=["True", "False"])):
        await ctx.response.defer()
        changed_text = ""
        if private_mode is not None:
            changed_text += f"Private mode set to {private_mode}\n"
            await self.bot.user_settings.update_one({"discord_user" : ctx.user.id}, {"$set" : {"private_mode" : (private_mode == "True")}}, upsert=True)

        embed = disnake.Embed(title=f"{ctx.user.name} Settings Changed", description=changed_text, color=disnake.Color.green())
        embed.set_thumbnail(url=ctx.user.display_avatar.url)
        await ctx.send(embed=embed)


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


    @setup.sub_command(name="api-token", description="Create an api token for use in the clashking api to access server resources")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def api_token(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer(ephemeral=True)
        token = secrets.token_urlsafe(20)
        pattern = "[^0-9a-zA-Z\s]+"
        token = re.sub(pattern, "", token)
        await self.bot.server_db.update_one({"server": ctx.guild.id}, {"$set": {"ck_api_token": token}})
        await ctx.send(token, ephemeral=True)
        await ctx.followup.send(content="Store the above token somewhere safe, token will be regenerated each time command is run", ephemeral=True)


    @setup.sub_command(name="link-parse", description="Turn link parsing types on/off")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def link_parse(self, ctx: disnake.ApplicationCommandInteraction,
                         army_links: str = commands.Param(default=None, choices=["On", "Off"]),
                         player_links: str = commands.Param(default=None, choices=["On", "Off"]),
                         clan_links: str = commands.Param(default=None, choices=["On", "Off"])):
        await ctx.response.defer()
        if army_links == player_links == clan_links is None:
            pass
        ck_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        link_types = [LinkParseTypes.army, LinkParseTypes.player, LinkParseTypes.clan]
        text = ""
        for link_type, option in zip(link_types,[army_links, player_links, clan_links]):
            if option is None:
                continue
            await ck_server.set_allowed_link_parse(type=link_type, status=(option == "On"))
            text += f"- {link_type.capitalize()} Link Parse - `{option}`\n"
        embed = disnake.Embed(title=f"Link Parse Settings Updated", description=text, color=ck_server.embed_color)
        embed.set_author(name=ctx.guild.name, icon_url=get_guild_icon(ctx.guild))
        await ctx.send(embed=embed)




    @commands.slash_command(name="addclan", description="Add a clan to the server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def addClan(self, ctx: disnake.ApplicationCommandInteraction,
                      clan: coc.Clan = options.clan,
                      category: str = commands.Param(autocomplete=autocomplete.new_categories),
                      member_role: disnake.Role = commands.Param(name="member_role"),
                      clan_channel: disnake.TextChannel = commands.Param(name="clan_channel"),
                      leadership_role: disnake.Role = None):
        """
            Parameters
            ----------
            clan_tag: clan to add to server
            category: choose a category or type your own
            member_role: role that all members of this clan receive
            leadership_role: role that co & leaders of this clan would receive
            clan_channel: channel where ban pings & welcome messages should go
        """
        await ctx.response.defer()
        if member_role.is_bot_managed():
            embed = disnake.Embed(description=f"Clan Roles cannot be bot roles.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and leadership_role.is_bot_managed():
            embed = disnake.Embed(description=f"Clan Roles cannot be bot roles.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if member_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(description=f"Member Role cannot be {ctx.guild.default_role.mention}.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and leadership_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(description=f"Leadership Role cannot be {ctx.guild.default_role.mention}.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and member_role.id == leadership_role.id:
            embed = disnake.Embed(description="Member Role & Leadership Role cannot be the same.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        # check if clan is already linked
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{clan.name} is already linked to this server.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        await self.bot.clan_db.insert_one({
            "name": clan.name,
            "tag": clan.tag,
            "generalRole": member_role.id,
            "leaderRole": None if leadership_role is None else leadership_role.id,
            "category": category,
            "server": ctx.guild.id,
            "clanChannel": None if clan_channel is None else clan_channel.id
        })

        embed = disnake.Embed(title=f"{clan.name} successfully added.",
                              description=f"Clan Tag: {clan.tag}\n"
                                          f"General Role: {member_role.mention}\n"
                                          f"Leadership Role: {None if leadership_role is None else leadership_role.mention}\n"
                                          f"Clan Channel: {None if clan_channel is None else clan_channel.mention}\n"
                                          f"Category: {category}",
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        await ctx.edit_original_message(embed=embed)



    @commands.slash_command(name="removeclan", description="Remove a clan from the server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def removeClan(self, ctx: disnake.ApplicationCommandInteraction,
                         clan: coc.Clan = commands.Param(converter=convert.clan_no_errors, autocomplete=autocomplete.clan)):
        """
            Parameters
            ----------
            clan: clan to add to server [clan tag, alias, or autocomplete]
        """
        await ctx.response.defer()
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = disnake.Embed(description=f"{clan.name} is not currently set-up as a family clan.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        embed = disnake.Embed(description=f"Are you sure you want to remove {clan.name} [{clan.tag}]?",
                              color=disnake.Color.red())
        embed.set_thumbnail(url=clan.badge.large)

        page_buttons = [
            disnake.ui.Button(label="Yes", emoji="✅", style=disnake.ButtonStyle.green,
                              custom_id="Yes"),
            disnake.ui.Button(label="No", emoji="❌", style=disnake.ButtonStyle.red,
                              custom_id="No")
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        await ctx.edit_original_message(embed=embed, components=[buttons])
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        chose = False
        while chose is False:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author.id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", ephemeral=True)
                continue

            chose = res.data.custom_id

            if chose == "No":
                embed = disnake.Embed(description=f"Sorry to hear that. Canceling the command now.",
                                      color=disnake.Color.green())
                embed.set_thumbnail(url=clan.badge.large)
                return await res.response.edit_message(embed=embed,
                                                       components=[])

        await self.bot.clan_db.find_one_and_delete({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})

        await self.bot.reminders.delete_many({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id}
        ]})
        embed = disnake.Embed(
            description=f"{clan.name} removed as a family clan.",
            color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return await msg.edit(embed=embed, components=[])






def setup(bot: CustomClient):
    bot.add_cog(SetupCommands(bot))