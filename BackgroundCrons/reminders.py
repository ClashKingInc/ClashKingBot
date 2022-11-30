import datetime
import asyncio
import coc
import disnake
import math

from main import check_commands
from disnake.ext import commands
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from typing import Union
from collections import defaultdict
from utils.clash import create_weekend_list, weekend_timestamps

class reminders(commands.Cog, name="Reminders"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        #ends at 7 am monday
        scheduler.add_job(self.send_boards, "cron", day_of_week="mon", hour=6, minute=55)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["1 hr"], day_of_week="mon", hour=6)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["6 hr"], day_of_week="mon", hour=1)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["12 hr"], day_of_week="sun", hour=19)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["24 hr"], day_of_week="sun", hour=7)


    @commands.slash_command(name="reminders")
    async def reminder(self, ctx):
        pass

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan


    @reminder.sub_command(name="create", description="Set a reminder for clan games, raid weekend, wars, & more")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def reminder_create(self, ctx: disnake.ApplicationCommandInteraction, channel: Union[disnake.TextChannel, disnake.Thread], type:str = commands.Param(choices=["Clan Capital", "War", "Clan Games", "Inactivity"]), clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            type: Type of reminder you would like to create
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the join/leave log to
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        if type == "Clan Capital":
            await self.create_clan_capital_reminder(ctx=ctx, channel=channel, clan=clan)
        elif type == "War":
            await self.create_war_reminder(ctx=ctx, channel=channel, clan=clan)
        else:
            await ctx.send(content="Coming Soon :)", ephemeral=True)

    async def create_clan_capital_reminder(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, clan: coc.Clan):
        embed = disnake.Embed(description="**Choose reminder times from list**", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        options = [  # the options in your dropdown
            disnake.SelectOption(label="1 hour remaining", emoji=self.bot.emoji.clock.partial_emoji, value="1 hr"),
            disnake.SelectOption(label="6 hours remaining", emoji=self.bot.emoji.clock.partial_emoji, value="6 hr"),
            disnake.SelectOption(label="12 hours remaining", emoji=self.bot.emoji.clock.partial_emoji, value="12 hr"),
            disnake.SelectOption(label="24 hours remaining", emoji=self.bot.emoji.clock.partial_emoji, value="24 hr"),
            disnake.SelectOption(label="Remove All", emoji=self.bot.emoji.no.partial_emoji, value="remove")
        ]
        select = disnake.ui.Select(
            options=options,
            placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=4,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.send(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        #delete any previously set ones, so we don't get ones in different channels or times
        await self.bot.reminders.delete_many({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "Clan Capital"}
        ]})
        if "remove" in res.values:
            embed = disnake.Embed(description=f"**All clan capital reminders removed for {clan.name}**", color=disnake.Color.green())
            return await res.edit_original_message(embed=embed, components=[])
        for value in res.values:
            await self.bot.reminders.insert_one({
                "server" : ctx.guild.id,
                "type" : "Clan Capital",
                "clan" : clan.tag,
                "channel" : channel.id,
                "time" : value
            })

        reminders_created = ", ".join(res.values)
        embed = disnake.Embed(description=f"**`{reminders_created}` Clan Capital Reminders created for {ctx.guild.name}**", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        button = [disnake.ui.ActionRow(disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green, custom_id="custom_text"))]

        await res.edit_original_message(embed=embed, components=button)

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.send_modal(
            title="Customize your text",
            custom_id="customtext-",
            components=[
                disnake.ui.TextInput(
                    label="Extra Custom Text",
                    placeholder="Extra text to send when reminder is sent (gifs, rules, etc)",
                    custom_id=f"custom_text",
                    required=True,
                    style=disnake.TextInputStyle.paragraph,
                    max_length=300,
                )
            ])

        msg = await res.original_message()
        await msg.edit(components=[])

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            return await msg.edit(components=[])

        await modal_inter.response.defer()
        custom_text = modal_inter.text_values["custom_text"]
        await self.bot.reminders.update_many({
            "server": ctx.guild.id,
            "type": "Clan Capital",
            "clan": clan.tag,
            "channel": channel.id,
        }, {"$set" : {"custom_text" : custom_text}})
        ping_reminder = f"**6 Hours Remaining - Example Clan Capital Raids**\n" \
                        f"2 raids- Linked Player | {ctx.author.mention}\n" \
                        f"4 raids- Unlinked Player | #playertag\n{custom_text}"
        return await modal_inter.edit_original_message(content=ping_reminder)

    async def create_war_reminder(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, clan: coc.Clan):
        embed = disnake.Embed(description="**Choose reminder times from list**", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        options = []
        nums = [x * 0.5 for x in range(1, 25)]
        for num in nums:
            if num.is_integer():
                num = int(num)
            options.append(disnake.SelectOption(label=f"{num} hours remaining", emoji=self.bot.emoji.clock.partial_emoji, value=f"{num} hr"))
        options.append(disnake.SelectOption(label=f"24 hours remaining", emoji=self.bot.emoji.clock.partial_emoji, value=f"24 hr"))
        select = disnake.ui.Select(
            options=options,
            placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=25,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.send(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        # delete any previously set ones where channel is not equal
        await self.bot.reminders.delete_many({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "War"},
            {"channel" : {"$ne" : channel.id}}
        ]})

        jobs = scheduler.get_jobs()
        for job in jobs:
            if clan.tag == job.name:
                job.remove()

        if "remove" in res.values:
            await self.bot.reminders.delete_many({"$and": [
                {"clan": clan.tag},
                {"server": ctx.guild.id},
                {"type": "War"}
            ]})
            embed = disnake.Embed(description=f"**All war reminders removed for {clan.name}**", color=disnake.Color.green())
            return await res.edit_original_message(embed=embed, components=[])
        for value in res.values:
            await self.bot.reminders.delete_one({"$and": [
                {"clan": clan.tag},
                {"server": ctx.guild.id},
                {"type": "War"},
                {"time" : value}
            ]})
            await self.bot.reminders.insert_one({
                "server": ctx.guild.id,
                "type": "War",
                "clan": clan.tag,
                "channel": channel.id,
                "time": value
            })

        reminders_created = ", ".join(res.values)
        embed = disnake.Embed(
            description=f"**`{reminders_created}` War Reminders created for {ctx.guild.name}**",
            color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        button = [disnake.ui.ActionRow(
            disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                              custom_id="custom_text"))]

        current_war_times = await self.bot.get_current_war_times(tags=[clan.tag])
        for tag in current_war_times.keys():
            war_end_time = current_war_times[tag]
            reminder_times = await self.bot.get_reminder_times(clan_tag=tag)
            acceptable_times = self.bot.get_times_in_range(reminder_times=reminder_times, war_end_time=war_end_time)
            if not acceptable_times:
                continue
            for time in acceptable_times:
                reminder_time = time[0] / 3600
                if reminder_time.is_integer():
                    reminder_time = int(reminder_time)
                send_time = time[1]
                scheduler.add_job(self.war_reminder, 'date', run_date=send_time, args=[tag, reminder_time], id=f"{reminder_time}_{tag}", name=f"{tag}")

        await res.edit_original_message(embed=embed, components=button)

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.send_modal(
            title="Customize your text",
            custom_id="customtext-",
            components=[
                disnake.ui.TextInput(
                    label="Extra Custom Text",
                    placeholder="Extra text to send when reminder is sent (gifs, rules, etc)",
                    custom_id=f"custom_text",
                    required=True,
                    style=disnake.TextInputStyle.paragraph,
                    max_length=300,
                )
            ])

        msg = await res.original_message()
        await msg.edit(components=[])

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            return await msg.edit(components=[])

        await modal_inter.response.defer()
        custom_text = modal_inter.text_values["custom_text"]
        await self.bot.reminders.update_many({
            "server": ctx.guild.id,
            "type": "War",
            "clan": clan.tag,
            "channel": channel.id,
        }, {"$set": {"custom_text": custom_text}})
        ping_reminder = f"**4 Hours Remaining - Example War Reminder**\n" \
                        f"1/2 hits- Linked Player | {ctx.author.mention}\n" \
                        f"0/2 hits- Unlinked Player | #playertag\n{custom_text}"
        return await modal_inter.edit_original_message(content=ping_reminder)



    @reminder.sub_command(name="remove", description="Remove a reminder set up on the server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def reminder_remove(self, ctx: disnake.ApplicationCommandInteraction, type:str = commands.Param(choices=["Clan Capital", "War"]), clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            type: Type of reminder you would like to remove
            clan: Use clan tag or select an option from the autocomplete
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        if type == "Clan Capital":
            await self.remove_clan_capital_reminder(ctx=ctx, clan=clan)
        elif type == "War":
            await self.remove_war_reminder(ctx=ctx, clan=clan)
        else:
            await ctx.send(content="Coming Soon :)", ephemeral=True)

    async def remove_clan_capital_reminder(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan):
        clan_capital_reminders = self.bot.reminders.find({"$and": [{"clan": clan.tag}, {"type": "Clan Capital"}, {"server": ctx.guild.id}]})
        options = []
        for reminder in await clan_capital_reminders.to_list(length=100):
            options.append(disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=self.bot.emoji.clock.partial_emoji, value=f"{reminder.get('time')}"))
        if not options:
            embed = disnake.Embed(description=f"**No clan capital reminders set up for {clan.name}**", color=disnake.Color.red())
            embed.set_thumbnail(url = clan.badge.url)
            return await ctx.send(embed)

        embed = disnake.Embed(description="**Choose reminder times to remove from list**", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        select = disnake.ui.Select(
            options=options,
            placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.send(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                      timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        for value in res.values:
            await self.bot.reminders.delete_one({
                "server": ctx.guild.id,
                "type": "Clan Capital",
                "clan": clan.tag,
                "time": value
            })

        reminders_removed = ", ".join(res.values)
        embed = disnake.Embed(
            description=f"**`{reminders_removed}` Clan Capital Reminders removed for {ctx.guild.name}**",
            color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.edit_original_message(embed=embed, components=[])

    async def remove_war_reminder(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan):
        war_reminders = self.bot.reminders.find({"$and": [{"clan": clan.tag}, {"type": "War"}, {"server": ctx.guild.id}]})
        options = []
        for reminder in await war_reminders.to_list(length=100):
            options.append(disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=self.bot.emoji.clock.partial_emoji, value=f"{reminder.get('time')}"))
        if not options:
            embed = disnake.Embed(description=f"**No war reminders set up for {clan.name}**", color=disnake.Color.red())
            embed.set_thumbnail(url = clan.badge.url)
            return await ctx.send(embed=embed)

        embed = disnake.Embed(description="**Choose reminder times to remove from list**", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        select = disnake.ui.Select(
            options=options,
            placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.send(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        for value in res.values:
            await self.bot.reminders.delete_one({
                "server": ctx.guild.id,
                "type": "War",
                "clan": clan.tag,
                "time": value
            })

        all_jobs = scheduler.get_jobs()
        for job in all_jobs:
            if job.name == clan.tag:
                time = str(job.id).split("_")
                time = time[0]
                if f"{time} hr" in res.values:
                    job.remove()

        reminders_removed = ", ".join(res.values)
        embed = disnake.Embed(
            description=f"**`{reminders_removed}` War Reminders removed for {ctx.guild.name}**",
            color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.edit_original_message(embed=embed, components=[])


    @reminder.sub_command(name="list", description="Get the list of reminders set up on the server")
    async def reminder_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        embed = disnake.Embed(title=f"**{ctx.guild.name} Reminders List**")
        all_reminders_tags = await self.bot.reminders.distinct("clan", filter={"$and": [{"server": ctx.guild.id}]})
        for tag in all_reminders_tags:
            clan = await self.bot.getClan(clan_tag=tag)
            if clan is None:
                continue
            reminder_text = ""
            clan_capital_reminders = self.bot.reminders.find({"$and": [{"clan": tag}, {"type": "Clan Capital"}, {"server": ctx.guild.id}]})
            cc_reminder_text = []
            for reminder in await clan_capital_reminders.to_list(length=100):
                cc_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if cc_reminder_text:
                reminder_text += "**Clan Capital:** \n" + "\n".join(cc_reminder_text) + "\n"
            war_reminders = self.bot.reminders.find({"$and": [{"clan": tag}, {"type": "War"}, {"server": ctx.guild.id}]})
            war_reminder_text = []
            for reminder in await war_reminders.to_list(length=100):
                war_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if war_reminder_text:
                reminder_text += "**War:** \n" + "\n".join(war_reminder_text) + "\n"
            emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            embed.add_field(name=f"{emoji}{clan.name}", value=reminder_text, inline=False)
        await ctx.edit_original_message(embed=embed)

    @reminder.sub_command(name="queue", description="Reminders in queue to be sent (war only)")
    async def reminder_queue(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        all_reminders_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        all_jobs = scheduler.get_jobs()
        job_list = ""
        clans = {}
        for job in all_jobs:
            if job.name in all_reminders_tags:
                time = str(job.id).split("_")
                tag = time[1]
                if tag not in clans:
                    clan = await self.bot.getClan(clan_tag=tag)
                    clans[tag] = clan
                else:
                    clan = clans[tag]
                if clan is None:
                    continue
                run_time = job.next_run_time.timestamp()
                job_list += f"<t:{int(run_time)}:R> - {clan.name}\n"
        embed = disnake.Embed(title=f"{ctx.guild.name} War Reminder Queue", description=job_list)
        await ctx.edit_original_message(embed=embed)

    @reminder_create.autocomplete("clan")
    @reminder_remove.autocomplete("clan")
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

    async def war_reminder(self, clan_tag, reminder_time):
        war = await self.bot.get_clanwar(clanTag=clan_tag)
        if war is None:
            return
        missing = {}; names = {}; ths = {}
        for player in war.members:
            if player not in war.opponent.members:
                if len(player.attacks) < war.attacks_per_member:
                    missing[player.tag] = war.attacks_per_member - len(player.attacks)
                    names[player.tag] = player.name
                    ths[player.tag] = player.town_hall

        tags= list(missing.keys())
        if not missing:
            return
        links = await self.bot.link_client.get_links(*tags)
        all_reminders = self.bot.reminders.find({"$and": [
            {"clan": clan_tag},
            {"type": "War"},
            {"time": f"{reminder_time} hr"}
        ]})
        limit = await self.bot.reminders.count_documents(filter={"$and": [
            {"clan": clan_tag},
            {"type": "War"},
            {"time": f"{reminder_time} hr"}
        ]})
        for reminder in await all_reminders.to_list(length=limit):
            custom_text = reminder.get("custom_text")
            if custom_text is None:
                custom_text = ""
            else:
                custom_text = "\n\n" + custom_text
            channel = reminder.get("channel")
            try:
                channel = await self.bot.fetch_channel(channel)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.reminders.delete_one({"$and": [
                    {"clan": clan_tag},
                    {"server": reminder.get("server")},
                    {"time" : f"{reminder_time} hr"},
                    {"type": "War"}
                ]})
            server = self.bot.get_guild(reminder.get("server"))
            if server is None:
                continue
            missing_text = ""
            for player_tag, discord_id in links:
                num_missing = missing[player_tag]
                name = names[player_tag]
                member = disnake.utils.get(server.members, id=discord_id)
                if member is None:
                    missing_text += f"{num_missing} hits- {self.bot.fetch_emoji(ths[player_tag])}{name} | {player_tag}\n"
                else:
                    missing_text += f"{num_missing} hits- {self.bot.fetch_emoji(ths[player_tag])}{name} | {member.mention}\n"
            badge = await self.bot.create_new_badge_emoji(url=war.clan.badge.url)
            reminder_text = f"**{reminder_time} Hours Remaining in War**\n" \
                            f"**{badge}{war.clan.name} vs {war.opponent.name}**\n\n" \
                            f"{missing_text}" \
                            f"{custom_text}"
            await channel.send(content=reminder_text)

    async def clan_capital_reminder(self, reminder_time):
        all_reminders = self.bot.reminders.find({"$and": [
            {"type": "Clan Capital"},
            {"time": reminder_time}
        ]})
        for reminder in await all_reminders.to_list(length=10000):
            custom_text = reminder.get("custom_text")
            if custom_text is None:
                custom_text = ""
            else:
                custom_text = "\n" + custom_text
            channel = reminder.get("channel")
            try:
                channel = await self.bot.fetch_channel(channel)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.reminders.delete_one({"$and": [
                    {"clan": reminder.get("clan")},
                    {"server": reminder.get("server")},
                    {"time": f"{reminder_time}"},
                    {"type": "Clan Capital"}
                ]})
            server = self.bot.get_guild(reminder.get("server"))
            if server is None:
                continue
            raid_weekend = await self.bot.get_raid(clan_tag=reminder.get("clan"))

            if raid_weekend is None:
                continue
            missing = {}
            names = {}
            max = {}
            for member in raid_weekend.members:
                if member.attack_count < (member.attack_limit + member.bonus_attack_limit):
                    names[member.tag] = member.name
                    missing[member.tag] = (member.attack_limit + member.bonus_attack_limit) - member.attack_count
                    max[member.tag] = (member.attack_limit + member.bonus_attack_limit)

            tags = list(missing.keys())
            if not missing:
                return
            links = await self.bot.link_client.get_links(*tags)
            missing_text = ""
            for player_tag, discord_id in links:
                num_missing = missing[player_tag]
                max_do = max[player_tag]
                name = names[player_tag]
                member = disnake.utils.get(server.members, id=discord_id)
                if member is None:
                    missing_text += f"{num_missing} raids- {name} | {player_tag}\n"
                else:
                    missing_text += f"{num_missing} raids- {name} | {member.mention}\n"
            time = str(reminder_time).replace("hr", "")
            clan = await self.bot.getClan(clan_tag=reminder.get("clan"))
            badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            reminder_text = f"**{badge}{clan.name}\n{time} Hours Remaining in Raid Weekend**\n" \
                            f"{missing_text}" \
                            f"{custom_text}"
            try:
                await channel.send(content=reminder_text)
            except:
                continue

    async def send_boards(self):
        tracked = self.bot.clan_db.find()
        limit = await self.bot.clan_db.count_documents(filter={})
        for cc in await tracked.to_list(length=limit):
            try:
                clancapital_channel = cc.get("clan_capital")
                if clancapital_channel is None:
                    continue
                try:
                    clancapital_channel = await self.bot.fetch_channel(clancapital_channel)
                    if clancapital_channel is None:
                        continue
                except:
                    continue
                clan_tag = cc.get("tag")
                clan = await self.bot.getClan(clan_tag=clan_tag)
                if clan is None:
                    continue
                weekend = "Current Week"
                choice_to_date = {"Current Week": [0], "Last Week": [1], "Last 4 Weeks (all)": [0, 1, 2, 3]}
                weekend_dates = create_weekend_list(option=weekend)
                member_tags = [member.tag for member in clan.members]

                embeds = {}
                other_tags = []
                donated_data = {}
                number_donated_data = {}

                for week in weekend_dates:
                    tags = await self.bot.player_stats.distinct("tag",
                                                                filter={f"capital_gold.{week}.raided_clan": clan.tag})
                    other_tags += tags
                all_tags = list(set(member_tags + other_tags))
                tasks = []
                for tag in all_tags:
                    results = await self.bot.player_stats.find_one({"tag": tag})
                    task = asyncio.ensure_future(
                        self.bot.coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=self.bot, results=results))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                donation_text = []
                for player in responses:
                    if isinstance(player, coc.errors.NotFound):
                        continue
                    player: MyCustomPlayer
                    for char in ["`", "*", "_", "~", "´", "`"]:
                        name = player.name.replace(char, "")
                    sum_donated = 0
                    len_donated = 0
                    for week in weekend_dates:
                        cc_stats = player.clan_capital_stats(week=week)
                        sum_donated += sum(cc_stats.donated)
                        len_donated += len(cc_stats.donated)
                    donation = f"{sum_donated}".ljust(6)

                    donated_data[player.tag] = sum_donated
                    number_donated_data[player.tag] = len_donated

                    if sum_donated == 0 and len(weekend_dates) > 1:
                        continue
                    if player.tag in member_tags:
                        donation_text.append([f"{self.bot.emoji.capital_gold}`{donation}`: {name}", sum_donated])
                    else:
                        donation_text.append([f"{self.bot.emoji.deny_mark}`{donation}`: {name}", sum_donated])

                donation_text = sorted(donation_text, key=lambda l: l[1], reverse=True)
                donation_text = [line[0] for line in donation_text]
                donation_text = "\n".join(donation_text)
                donation_embed = disnake.Embed(title=f"**{clan.name} Donation Totals**", description=donation_text,
                                               color=disnake.Color.green())
                donation_embed.set_footer(text=f"Donated: {'{:,}'.format(sum(donated_data.values()))}")
                embeds["donations"] = donation_embed

                raid_weekends = []
                raid_weekend = await self.bot.get_raid(clan_tag=clan.tag)
                raid_weekends.append(raid_weekend)

                total_medals = 0
                if not raid_weekends:
                    raid_embed = disnake.Embed(title=f"**{clan.name} Raid Totals**", description="No raids",
                                               color=disnake.Color.green())
                    embeds["raids"] = raid_embed
                else:
                    total_attacks = defaultdict(int);
                    total_looted = defaultdict(int);
                    attack_limit = defaultdict(int);
                    name_list = {}
                    members_not_looted = member_tags.copy()
                    for raid_weekend in raid_weekends:
                        for member in raid_weekend.members:
                            name_list[member.tag] = member.name
                            total_attacks[member.tag] += member.attack_count
                            total_looted[member.tag] += member.capital_resources_looted
                            attack_limit[member.tag] += (member.attack_limit + member.bonus_attack_limit)
                            if len(raid_weekends) == 1 and member.tag in members_not_looted:
                                members_not_looted.remove(member.tag)

                    district_dict = {1: 135, 2: 225, 3: 350, 4: 405, 5: 460}
                    capital_dict = {2: 180, 3: 360, 4: 585, 5: 810, 6: 1115, 7: 1240, 8: 1260, 9: 1375, 10: 1450}
                    attacks_done = sum(list(total_attacks.values()))
                    raids = raid_weekends[0].attack_log
                    for raid_clan in raids:
                        for district in raid_clan.districts:
                            if int(district.destruction) == 100:
                                if district.id == 70000000:
                                    total_medals += capital_dict[int(district.hall_level)]
                                else:
                                    total_medals += district_dict[int(district.hall_level)]
                            else:
                                # attacks_done -= len(district.attacks)
                                pass

                    total_medals = math.ceil(total_medals / attacks_done) * 6

                    raid_text = []
                    for tag, amount in total_looted.items():
                        raided_amount = f"{amount}".ljust(6)
                        name = name_list[tag]
                        for char in ["`", "*", "_", "~", "´"]:
                            name = name.replace(char, "")
                        # print(tag)
                        # print(member_tags)
                        if tag in member_tags:
                            raid_text.append([
                                                 f"\u200e{self.bot.emoji.capital_gold}`{total_attacks[tag]}/{attack_limit[tag]} {raided_amount}`: \u200e{name}",
                                                 amount])
                        else:
                            raid_text.append([
                                                 f"\u200e{self.bot.emoji.deny_mark}`{total_attacks[tag]}/{attack_limit[tag]} {raided_amount}`: \u200e{name}",
                                                 amount])

                    if len(raid_weekends) == 1:
                        for member in members_not_looted:
                            name = coc.utils.get(clan.members, tag=member)
                            raid_text.append(
                                [f"{self.bot.emoji.capital_gold}`{0}/{6 * len(raid_weekends)} {0}`: {name.name}", 0])

                    raid_text = sorted(raid_text, key=lambda l: l[1], reverse=True)
                    raid_text = [line[0] for line in raid_text]
                    raid_text = "\n".join(raid_text)
                    if len(raid_weekends) == 1:
                        rw = raid_weekends[0]
                        offensive_reward = rw.offensive_reward * 6
                        if total_medals > offensive_reward:
                            offensive_reward = total_medals
                        defensive_reward = rw.defensive_reward
                        raid_text += f"\n\n{self.bot.emoji.raid_medal}{offensive_reward} + {self.bot.emoji.raid_medal}{defensive_reward} = {self.bot.emoji.raid_medal}{offensive_reward + defensive_reward}"
                        raid_text += "\n`Offense + Defense = Total`"
                    raid_embed = disnake.Embed(title=f"**{clan.name} Raid Totals**", description=raid_text,
                                               color=disnake.Color.green())
                    raid_embed.set_footer(
                        text=f"Spots: {len(total_attacks.values())}/50 | Attacks: {sum(total_attacks.values())}/300 | Looted: {'{:,}'.format(sum(total_looted.values()))}")
                    embeds["raids"] = raid_embed

                    await clancapital_channel.send(embed=raid_embed)
                    await clancapital_channel.send(embed=donation_embed)
            except:
                continue

def setup(bot: CustomClient):
    bot.add_cog(reminders(bot))
