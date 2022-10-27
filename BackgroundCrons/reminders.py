import coc
import disnake
import math

from disnake.ext import commands
from main import scheduler
from CustomClasses.CustomBot import CustomClient

class reminders(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        #ends at 7 am monday
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
    async def reminder_create(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, type:str = commands.Param(choices=["Clan Capital", "War", "Clan Games", "Inactivity"]), clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            type: Type of reminder you would like to create
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the join/leave log to
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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
        options.append(disnake.SelectOption(label="Remove All", emoji=self.bot.emoji.no.partial_emoji, value="remove"))
        select = disnake.ui.Select(
            options=options,
            placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(nums),  # the maximum number of options a user can select
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
        # delete any previously set ones, so we don't get ones in different channels or times
        await self.bot.reminders.delete_many({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "War"}
        ]})

        if "remove" in res.values:
            embed = disnake.Embed(description=f"**All war reminders removed for {clan.name}**", color=disnake.Color.green())
            return await res.edit_original_message(embed=embed, components=[])
        for value in res.values:
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

    '''
    @reminder.sub_command(name="remove", description="Remove a reminder set up on the server")
    async def reminder_remove(self, ctx: disnake.ApplicationCommandInteraction, type:str = commands.Param(choices=["Clan Capital", "Clan Games, War", "Inactivity"]), clan: coc.Clan = commands.Param(converter=clan_converter)):
        pass
    
    @reminder.sub_command(name="list", description="Get the list of reminders set up on the server")
    async def reminder_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass
    '''

    @reminder_create.autocomplete("clan")
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
        missing = {}; names = {}
        for player in war.members:
            if player not in war.opponent.members:
                if len(player.attacks) < war.attacks_per_member:
                    missing[player.tag] = war.attacks_per_member - len(player.attacks)
                    names[player.tag] = player.name

        tags= list(missing.keys())
        if not missing:
            return
        links = await self.bot.link_client.get_links(*tags)
        all_reminders = self.bot.reminders.find({"$and": [
            {"clan": clan_tag},
            {"type": "War"}
        ]})
        limit = await self.bot.reminders.count_documents(filter={"$and": [
            {"clan": clan_tag},
            {"type": "War"}
        ]})
        for reminder in await all_reminders.to_list(length=limit):
            custom_text = reminder.get("custom_text")
            if custom_text is None:
                custom_text = ""
            else:
                custom_text += "\n"
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
                if discord_id is None:
                    missing_text += f"{num_missing}/{war.attacks_per_member} hits- {name} | {player_tag}\n"
                member = disnake.utils.get(server.members, id=discord_id)
                if member is None:
                    missing_text += f"{num_missing}/{war.attacks_per_member} hits- {name} | {player_tag}\n"
                else:
                    missing_text += f"{num_missing}/{war.attacks_per_member} hits- {name} | {member.mention}\n"

            reminder_text = f"**{reminder_time} Hours Remaining in War**\n" \
                            f"{missing_text}" \
                            f"{custom_text}"

            await channel.send(content=reminder_text)

    async def clan_capital_reminder(self, reminder_time):
        all_reminders = self.bot.reminders.find({"$and": [
            {"type": "Clan Capital"},
            {"time" : reminder_time}
        ]})
        limit = await self.bot.reminders.count_documents(filter={"$and": [
            {"type": "Clan Capital"},
            {"time": reminder_time}
        ]})
        for reminder in await all_reminders.to_list(length=limit):
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

            tags = list(missing.values())
            if not missing:
                return
            links = await self.bot.link_client.get_links(*tags)
            missing_text = ""
            for player_tag, discord_id in links:
                num_missing = missing[player_tag]
                max_do = max[player_tag]
                name = names[player_tag]
                if discord_id is None:
                    missing_text += f"{num_missing}/{max_do} raids- {name} | {player_tag}\n"
                member = disnake.utils.get(server.members, id=discord_id)
                if member is None:
                    missing_text += f"{num_missing}/{max_do} raids- {name} | {player_tag}\n"
                else:
                    missing_text += f"{num_missing}/{max_do} raids- {name} | {member.mention}\n"
            time = str(reminder_time).replace("hr", "")
            reminder_text = f"**{time} Hours Remaining in Raid Weekend**\n" \
                            f"{missing_text}" \
                            f"{custom_text}"
            await channel.send(content=reminder_text)



def setup(bot: CustomClient):
    bot.add_cog(reminders(bot))
