import disnake
import coc
from main import scheduler
from CustomClasses.CustomBot import CustomClient


##REMINDER CREATION

async def create_clan_capital_reminder(bot, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel,
                                       clan: coc.Clan, attack_threshold: int):
    embed = disnake.Embed(description="**Choose reminder times from list**", color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    options = [  # the options in your dropdown
        disnake.SelectOption(label="1 hour remaining", emoji=bot.emoji.clock.partial_emoji, value="1 hr"),
        disnake.SelectOption(label="6 hours remaining", emoji=bot.emoji.clock.partial_emoji, value="6 hr"),
        disnake.SelectOption(label="12 hours remaining", emoji=bot.emoji.clock.partial_emoji, value="12 hr"),
        disnake.SelectOption(label="24 hours remaining", emoji=bot.emoji.clock.partial_emoji, value="24 hr"),
        disnake.SelectOption(label="Remove All", emoji=bot.emoji.no.partial_emoji, value="remove")
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
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
    except:
        return await msg.edit(components=[])

    await res.response.defer()
    # delete any previously set ones, so we don't get ones in different channels or times
    await bot.reminders.delete_many({"$and": [
        {"clan": clan.tag},
        {"server": ctx.guild.id},
        {"type": "Clan Capital"}
    ]})
    if "remove" in res.values:
        embed = disnake.Embed(description=f"**All clan capital reminders removed for {clan.name}**",
                              color=disnake.Color.green())
        return await res.edit_original_message(embed=embed, components=[])
    for value in res.values:
        await bot.reminders.insert_one({
            "server": ctx.guild.id,
            "type": "Clan Capital",
            "clan": clan.tag,
            "channel": channel.id,
            "time": value,
            "attack_threshold" : attack_threshold
        })

    reminders_created = ", ".join(res.values)
    embed = disnake.Embed(description=f"**`{reminders_created}` Clan Capital Reminders created for {ctx.guild.name}**",
                          color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                          custom_id="custom_text"))]

    await res.edit_original_message(embed=embed, components=button)

    try:
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
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
        modal_inter: disnake.ModalInteraction = await bot.wait_for(
            "modal_submit",
            check=check,
            timeout=300,
        )
    except:
        return await msg.edit(components=[])

    await modal_inter.response.defer()
    custom_text = modal_inter.text_values["custom_text"]
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "Clan Capital",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    ping_reminder = f"**6 Hours Remaining - Example Clan Capital Raids**\n" \
                    f"2 raids- Linked Player | {ctx.author.mention}\n" \
                    f"4 raids- Unlinked Player | #playertag\n{custom_text}"
    return await modal_inter.edit_original_message(content=ping_reminder)


async def create_clan_games_reminder(bot, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel,
                                     clan: coc.Clan, point_threshold: int):
    embed = disnake.Embed(description="**Choose reminder times from list**", color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    options = [  # the options in your dropdown
        disnake.SelectOption(label="1 hour remaining", emoji=bot.emoji.clock.partial_emoji, value="1 hr"),
        disnake.SelectOption(label="2 hours remaining", emoji=bot.emoji.clock.partial_emoji, value="2 hr"),
        disnake.SelectOption(label="4 hours remaining", emoji=bot.emoji.clock.partial_emoji, value="4 hr"),
        disnake.SelectOption(label="6 hours remaining", emoji=bot.emoji.clock.partial_emoji, value="6 hr"),
        disnake.SelectOption(label="12 hours remaining", emoji=bot.emoji.clock.partial_emoji, value="12 hr"),
        disnake.SelectOption(label="24 hours remaining", emoji=bot.emoji.clock.partial_emoji, value="24 hr"),
        disnake.SelectOption(label="2 days remaining", emoji=bot.emoji.clock.partial_emoji, value="48 hr"),
        disnake.SelectOption(label="3 days remaining", emoji=bot.emoji.clock.partial_emoji, value="72 hr"),
        disnake.SelectOption(label="4 days remaining", emoji=bot.emoji.clock.partial_emoji, value="96 hr"),
        disnake.SelectOption(label="5 days remaining", emoji=bot.emoji.clock.partial_emoji, value="120 hr"),
        disnake.SelectOption(label="6 days remaining", emoji=bot.emoji.clock.partial_emoji, value="144 hr"),
        disnake.SelectOption(label="Remove All", emoji=bot.emoji.no.partial_emoji, value="remove")
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
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
    except:
        return await msg.edit(components=[])

    await res.response.defer()
    # delete any previously set ones, so we don't get ones in different channels or times
    await bot.reminders.delete_many({"$and": [
        {"clan": clan.tag},
        {"server": ctx.guild.id},
        {"type": "Clan Games"}
    ]})
    if "remove" in res.values:
        embed = disnake.Embed(description=f"**All clan games reminders removed for {clan.name}**",
                              color=disnake.Color.green())
        return await res.edit_original_message(embed=embed, components=[])
    for value in res.values:
        await bot.reminders.insert_one({
            "server": ctx.guild.id,
            "type": "Clan Games",
            "clan": clan.tag,
            "channel": channel.id,
            "time": value,
            "point_threshold": point_threshold
        })

    reminders_created = ", ".join(res.values)
    embed = disnake.Embed(description=f"**`{reminders_created}` Clan Games Reminders created for {ctx.guild.name}**",
                          color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                          custom_id="custom_text"))]

    await res.edit_original_message(embed=embed, components=button)

    try:
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
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
        modal_inter: disnake.ModalInteraction = await bot.wait_for(
            "modal_submit",
            check=check,
            timeout=300,
        )
    except:
        return await msg.edit(components=[])

    await modal_inter.response.defer()
    custom_text = modal_inter.text_values["custom_text"]
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "Clan Games",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    ping_reminder = f"**6 Hours Remaining - Example Clan Games**\n" \
                    f"*Amount remaining to hit {point_threshold} points*\n" \
                    f"1050 points - Linked Player | {ctx.author.mention}\n" \
                    f"500 points - Unlinked Player | #playertag\n{custom_text}"
    return await modal_inter.edit_original_message(content=ping_reminder)


async def create_war_reminder(bot, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, clan: coc.Clan):
    embed = disnake.Embed(description="**Choose reminder times from list**", color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    options = []
    nums = [x * 0.5 for x in range(1, 25)]
    for num in nums:
        if num.is_integer():
            num = int(num)
        options.append(disnake.SelectOption(label=f"{num} hours remaining", emoji=bot.emoji.clock.partial_emoji,
                                            value=f"{num} hr"))
    options.append(
        disnake.SelectOption(label=f"24 hours remaining", emoji=bot.emoji.clock.partial_emoji, value=f"24 hr"))
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
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
    except:
        return await msg.edit(components=[])

    await res.response.defer()
    # delete any previously set ones where channel is not equal
    await bot.reminders.delete_many({"$and": [
        {"clan": clan.tag},
        {"server": ctx.guild.id},
        {"type": "War"},
        {"channel": {"$ne": channel.id}}
    ]})

    jobs = scheduler.get_jobs()
    for job in jobs:
        if clan.tag == job.name:
            job.remove()

    if "remove" in res.values:
        await bot.reminders.delete_many({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "War"}
        ]})
        embed = disnake.Embed(description=f"**All war reminders removed for {clan.name}**", color=disnake.Color.green())
        return await res.edit_original_message(embed=embed, components=[])
    for value in res.values:
        await bot.reminders.delete_one({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "War"},
            {"time": value}
        ]})
        await bot.reminders.insert_one({
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

    current_war_times = await bot.get_current_war_times(tags=[clan.tag])
    for tag in current_war_times.keys():
        war_end_time = current_war_times[tag]
        reminder_times = await bot.get_reminder_times(clan_tag=tag)
        acceptable_times = bot.get_times_in_range(reminder_times=reminder_times, war_end_time=war_end_time)
        if not acceptable_times:
            continue
        for time in acceptable_times:
            reminder_time = time[0] / 3600
            if reminder_time.is_integer():
                reminder_time = int(reminder_time)
            send_time = time[1]
            cog = bot.get_cog(name="Reminder Cron")
            scheduler.add_job(cog.war_reminder, 'date', run_date=send_time, args=[tag, reminder_time],
                              id=f"{reminder_time}_{tag}", name=f"{tag}")

    await res.edit_original_message(embed=embed, components=button)

    try:
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
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
        modal_inter: disnake.ModalInteraction = await bot.wait_for(
            "modal_submit",
            check=check,
            timeout=300,
        )
    except:
        return await msg.edit(components=[])

    await modal_inter.response.defer()
    custom_text = modal_inter.text_values["custom_text"]
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "War",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    ping_reminder = f"**4 Hours Remaining - Example War Reminder**\n" \
                    f"1/2 hits- Linked Player | {ctx.author.mention}\n" \
                    f"0/2 hits- Unlinked Player | #playertag\n{custom_text}"
    return await modal_inter.edit_original_message(content=ping_reminder)


async def create_inactivity_reminder(bot, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, clan: coc.Clan):
    embed = disnake.Embed(description="**Choose reminder times from list**", color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    options = [  # the options in your dropdown
        disnake.SelectOption(label="24 hours of inactivity", emoji=bot.emoji.clock.partial_emoji, value="24 hr"),
        disnake.SelectOption(label="48 hours of inactivity", emoji=bot.emoji.clock.partial_emoji, value="48 hr"),
        disnake.SelectOption(label="3 days of inactivity", emoji=bot.emoji.clock.partial_emoji, value="72 hr"),
        disnake.SelectOption(label="1 week of inactivity", emoji=bot.emoji.clock.partial_emoji, value="168 hr"),
        disnake.SelectOption(label="2 weeks of inactivity", emoji=bot.emoji.clock.partial_emoji, value="336 hr"),
        disnake.SelectOption(label="Remove All", emoji=bot.emoji.no.partial_emoji, value="remove")
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
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
    except:
        return await msg.edit(components=[])

    await res.response.defer()
    # delete any previously set ones, so we don't get ones in different channels or times
    await bot.reminders.delete_many({"$and": [
        {"clan": clan.tag},
        {"server": ctx.guild.id},
        {"type": "inactivity"}
    ]})
    if "remove" in res.values:
        embed = disnake.Embed(description=f"**All inactivity reminders removed for {clan.name}**",
                              color=disnake.Color.green())
        return await res.edit_original_message(embed=embed, components=[])
    for value in res.values:
        await bot.reminders.insert_one({
            "server": ctx.guild.id,
            "type": "inactivity",
            "clan": clan.tag,
            "channel": channel.id,
            "time": value
        })

    reminders_created = ", ".join(res.values)
    embed = disnake.Embed(description=f"**`{reminders_created}` Inactivity Reminders created for {ctx.guild.name}**",
                          color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                          custom_id="custom_text"))]

    await res.edit_original_message(embed=embed, components=button)

    try:
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
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
        modal_inter: disnake.ModalInteraction = await bot.wait_for(
            "modal_submit",
            check=check,
            timeout=300,
        )
    except:
        return await msg.edit(components=[])

    await modal_inter.response.defer()
    custom_text = modal_inter.text_values["custom_text"]
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "inactivity",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    ping_reminder = f"**Player Name | #playertag | {ctx.author.mention}**\n" \
                    f"Has been inactive for 48 hours!\n{custom_text}"
    return await modal_inter.edit_original_message(content=ping_reminder)



##REMINDER DELETION

async def remove_clan_capital_reminder(bot, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "Clan Capital"}, {"server": ctx.guild.id}]})
    options = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))
    if not options:
        embed = disnake.Embed(description=f"**No clan capital reminders set up for {clan.name}**",
                              color=disnake.Color.red())
        embed.set_thumbnail(url=clan.badge.url)
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
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check,
                                                                  timeout=600)
    except:
        return await msg.edit(components=[])

    await res.response.defer()
    for value in res.values:
        await bot.reminders.delete_one({
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


async def remove_clan_games_reminder(bot, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "Clan Games"}, {"server": ctx.guild.id}]})
    options = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))
    if not options:
        embed = disnake.Embed(description=f"**No clan games reminders set up for {clan.name}**",
                              color=disnake.Color.red())
        embed.set_thumbnail(url=clan.badge.url)
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
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check,
                                                                  timeout=600)
    except:
        return await msg.edit(components=[])

    await res.response.defer()
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "Clan Games",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    embed = disnake.Embed(
        description=f"**`{reminders_removed}` Clan Games Reminders removed for {ctx.guild.name}**",
        color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    await ctx.edit_original_message(embed=embed, components=[])


async def remove_war_reminder(bot, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan):
    war_reminders = bot.reminders.find({"$and": [{"clan": clan.tag}, {"type": "War"}, {"server": ctx.guild.id}]})
    options = []
    for reminder in await war_reminders.to_list(length=100):
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))
    if not options:
        embed = disnake.Embed(description=f"**No war reminders set up for {clan.name}**", color=disnake.Color.red())
        embed.set_thumbnail(url=clan.badge.url)
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
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
    except:
        return await msg.edit(components=[])

    await res.response.defer()
    for value in res.values:
        await bot.reminders.delete_one({
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


async def remove_inactivity_reminder(bot, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "inactivity"}, {"server": ctx.guild.id}]})
    options = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))
    if not options:
        embed = disnake.Embed(description=f"**No inactivity reminders set up for {clan.name}**",
                              color=disnake.Color.red())
        embed.set_thumbnail(url=clan.badge.url)
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
        res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check,
                                                                  timeout=600)
    except:
        return await msg.edit(components=[])

    await res.response.defer()
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "inactivity",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    embed = disnake.Embed(
        description=f"**`{reminders_removed}` Inactivity Reminders removed for {ctx.guild.name}**",
        color=disnake.Color.green())
    if ctx.guild.icon is not None:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    await ctx.edit_original_message(embed=embed, components=[])