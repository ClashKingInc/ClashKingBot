import disnake
import coc
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from utils.discord_utils import interaction_handler
from Exceptions.CustomExceptions import ExpiredComponents
from typing import List

##REMINDER CREATION

settings_text = {
    "capital": f"**Choose settings:**\n"
               "> - Clans\n"
               "> - (optional) Game Roles to Ping | default all roles\n"
               "> - (optional) Attack Threshold - Ping people with this many or more attacks left | default 1\n"
               "*Note: If you don't select the optional fields, defaults will be used*",
    "clangames": f"**Choose settings:**\n"
                 "> - Clans\n"
                 "> - (optional) Game Roles to Ping | default all roles\n"
                 "> - (optional) Point Threshold - Ping people with less than this many points | default 4000\n"
                 "*Note: If you don't select the optional fields, defaults will be used*",
    "war": f"**Choose settings:**\n"
           "> - Clans\n"
           "> - (optional) Townhall Levels to Ping | default all\n"
           "> - (optional) Game Roles to Ping | default all\n"
           "> - (optional) War Types to Remind for | default all\n"
           "*Note: If you don't select the optional fields, defaults will be used*",
    "inactivity": f"**Choose settings:**\n"
                  "> - Clans\n"
                  "> - (optional) Townhall Levels to Ping | default all\n"
                  "> - (optional) Game Roles to Ping | default all\n"
                  "*Note: If you don't select the optional fields, defaults will be used*",
}

def role_options():
    options = []
    role_types = ["Member", "Elder", "Co-Leader", "Leader"]
    for role in role_types:
        options.append(disnake.SelectOption(label=f"{role}", value=f"{role}"))
    role_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Roles",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    return role_select

def attack_threshold():
    options = []
    attack_numbers = [1, 2, 3, 4, 5]
    for number in attack_numbers:
        options.append(disnake.SelectOption(label=f"{number} attacks", value=f"{number}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Attack Threshold",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1  # the maximum number of options a user can select
    )


async def create_reminder(reminder_type: str, bot: CustomClient, ctx: disnake.MessageInteraction,
                          channel: disnake.TextChannel, times: List[str]):
    content = settings_text[reminder_type]


async def create_clan_capital_reminder(bot: CustomClient, ctx: disnake.MessageInteraction, clan: coc.Clan,
                                       channel: disnake.TextChannel):






    page_buttons = [
        disnake.ui.Button(label="Save", emoji=bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green,
                          custom_id="Save"),
    ]
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    dropdown = [disnake.ui.ActionRow(time_select), disnake.ui.ActionRow(role_select),
                disnake.ui.ActionRow(war_type_select), buttons]

    await ctx.edit_original_message(content=content, components=dropdown)
    save = False

    times = []
    townhalls = reversed([x for x in range(2, 16)])
    roles = role_types
    attack_threshold = 1
    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if not times:
                await res.send(content="Must select reminder times", ephemeral=True)
            else:
                save = True
        elif "string_select" in str(res.data.component_type):
            if "th_" in res.values[0]:
                townhalls = [int(th.split("_")[-1]) for th in res.values]
            elif "hr" in res.values[0]:
                times = res.values
            elif res.values[0] in role_types:
                roles = res.values
            else:
                attack_threshold = res.values[0]

    for time in times:
        await bot.reminders.delete_one({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "Clan Capital"},
            {"time": time}
        ]})
        await bot.reminders.insert_one({
            "server": ctx.guild.id,
            "type": "Clan Capital",
            "clan": clan.tag,
            "channel": channel.id,
            "time": time,
            "townhalls": list(townhalls),
            "roles": roles,
            "attack_threshold": attack_threshold
        })

    reminders_created = ", ".join(times)
    content = f"**`{reminders_created}` Clan Capital Reminders created for {clan.name}**"

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                          custom_id="custom_text"),
        disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    await ctx.edit_original_message(content=content, components=button)

    async def get_custom_text(res: disnake.MessageInteraction):
        if res.data.custom_id == "new_reminder" or res.data.custom_id == "go_to_finish":
            await res.response.defer()
            return res.data.custom_id
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
        button = [disnake.ui.ActionRow(
            disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                              style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
            disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                              custom_id="go_to_finish"))
        ]
        await res.edit_original_message(components=button)

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            raise ExpiredComponents
        await modal_inter.response.defer(ephemeral=True)
        await modal_inter.send(content="Custom Text Stored")
        custom_text = modal_inter.text_values["custom_text"]
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)

    if custom_text in ["new_reminder", "go_to_finish"]:
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "Clan Capital",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    return custom_text


async def create_clan_games_reminder(bot: CustomClient, ctx: disnake.MessageInteraction, clan: coc.Clan,
                                     channel: disnake.TextChannel):
    content = f"**Choose settings ({clan.name}):**\n" \
              "> - Times to remind\n" \
              "> - (optional) Game Roles to Ping | default all roles\n" \
              "> - (optional) Point Threshold - Ping people with less than this many points | default 4000\n" \
              "*Note: If you don't select the optional fields, defaults will be used*"

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
    time_select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )

    options = []
    role_types = ["Member", "Elder", "Co-Leader", "Leader"]
    for role in role_types:
        options.append(disnake.SelectOption(label=f"{role}", value=f"{role}"))
    role_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Roles",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )

    options = []
    attack_numbers = [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
    for number in attack_numbers:
        options.append(disnake.SelectOption(label=f"{number} points", value=f"{number}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Point Threshold",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1  # the maximum number of options a user can select
    )

    page_buttons = [
        disnake.ui.Button(label="Save", emoji=bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green,
                          custom_id="Save"),
    ]
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    dropdown = [disnake.ui.ActionRow(time_select), disnake.ui.ActionRow(role_select),
                disnake.ui.ActionRow(war_type_select), buttons]

    await ctx.edit_original_message(content=content, components=dropdown)

    save = False

    times = []
    townhalls = reversed([x for x in range(2, 16)])
    roles = role_types
    point_threshold = 4000
    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if not times:
                await res.send(content="Must select reminder times", ephemeral=True)
            else:
                save = True
        elif "string_select" in str(res.data.component_type):
            if "th_" in res.values[0]:
                townhalls = [int(th.split("_")[-1]) for th in res.values]
            elif "hr" in res.values[0]:
                times = res.values
            elif res.values[0] in role_types:
                roles = res.values
            else:
                point_threshold = res.values[0]

    for time in times:
        await bot.reminders.delete_one({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "Clan Games"},
            {"time": time}
        ]})
        await bot.reminders.insert_one({
            "server": ctx.guild.id,
            "type": "Clan Games",
            "clan": clan.tag,
            "channel": channel.id,
            "time": time,
            "townhalls": list(townhalls),
            "roles": roles,
            "point_threshold": point_threshold
        })

    reminders_created = ", ".join(times)
    content = f"**`{reminders_created}` Clan Game Reminders created for {clan.name}**"

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                          custom_id="custom_text"),
        disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    await ctx.edit_original_message(content=content, components=button)

    async def get_custom_text(res: disnake.MessageInteraction):
        if res.data.custom_id == "new_reminder" or res.data.custom_id == "go_to_finish":
            await res.response.defer()
            return res.data.custom_id
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
        button = [disnake.ui.ActionRow(
            disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                              style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
            disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                              custom_id="go_to_finish"))
        ]
        await res.edit_original_message(components=button)

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            raise ExpiredComponents
        await modal_inter.response.defer(ephemeral=True)
        await modal_inter.send(content="Custom Text Stored")
        custom_text = modal_inter.text_values["custom_text"]
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)

    if custom_text in ["new_reminder", "go_to_finish"]:
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "Clan Games",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    return custom_text


async def create_war_reminder(bot: CustomClient, ctx: disnake.MessageInteraction, clan: coc.Clan,
                              channel: disnake.TextChannel):
    content = f"**Choose settings ({clan.name}):**\n" \
              "> - Times to remind\n" \
              "> - (optional) Townhall Levels to Ping\n" \
              "> - (optional) Game Roles to Ping\n" \
              "> - (optional) War Types to Remind for\n" \
              "*Note: If you don't select the optional fields, all options will be used (i.e ping every townhall)*"

    options = []
    nums = [x * 0.5 for x in range(1, 25)]
    for num in nums:
        if num.is_integer():
            num = int(num)
        if num == 11.5:
            continue
        options.append(disnake.SelectOption(label=f"{num} hours remaining", emoji=bot.emoji.clock.partial_emoji,
                                            value=f"{num} hr"))
    options.insert(0,
                   disnake.SelectOption(label=f"0.25 hours remaining", emoji=bot.emoji.clock.partial_emoji,
                                        value=f"0.25 hr"))
    options.append(
        disnake.SelectOption(label=f"24 hours remaining", emoji=bot.emoji.clock.partial_emoji, value=f"24 hr"))
    time_select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=25,  # the maximum number of options a user can select
    )

    options = []
    nums = reversed([x for x in range(2, 16)])
    for num in nums:
        options.append(disnake.SelectOption(label=f"Townhall {num}", emoji=bot.fetch_emoji(name=num).partial_emoji,
                                            value=f"th_{num}"))
    th_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Townhalls",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )

    options = []
    role_types = ["Member", "Elder", "Co-Leader", "Leader"]
    for role in role_types:
        options.append(disnake.SelectOption(label=f"{role}", value=f"{role}"))
    role_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Roles",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )

    options = []
    war_types = ["Random", "Friendly", "CWL"]
    for war_type in war_types:
        options.append(disnake.SelectOption(label=f"{war_type}", value=f"{war_type}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select War Types",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )

    page_buttons = [
        disnake.ui.Button(label="Save", emoji=bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green,
                          custom_id="Save"),
    ]
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    dropdown = [disnake.ui.ActionRow(time_select), disnake.ui.ActionRow(th_select), disnake.ui.ActionRow(role_select),
                disnake.ui.ActionRow(war_type_select), buttons]

    await ctx.edit_original_message(content=content, components=dropdown)

    save = False

    times = []
    townhalls = list(reversed([x for x in range(2, 16)]))
    roles = role_types
    wars = war_types
    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if not times:
                await res.send(content="Must select reminder times", ephemeral=True)
            else:
                save = True
        elif "string_select" in str(res.data.component_type):
            if "th_" in res.values[0]:
                townhalls = [int(th.split("_")[-1]) for th in res.values]
            elif "hr" in res.values[0]:
                times = res.values
            elif res.values[0] in role_types:
                roles = res.values
            else:
                wars = res.values

    for time in times:
        await bot.reminders.delete_one({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "War"},
            {"time": time}
        ]})
        await bot.reminders.insert_one({
            "server": ctx.guild.id,
            "type": "War",
            "clan": clan.tag,
            "channel": channel.id,
            "time": time,
            "townhalls": townhalls,
            "roles": roles,
            "war_types": wars
        })

    reminders_created = ", ".join(times)
    content = f"**`{reminders_created}` War Reminders created for {clan.name}**"

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                          custom_id="custom_text"),
        disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

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
            remcog = bot.get_cog(name="Reminder Cron")
            try:
                scheduler.add_job(remwar_reminder, 'date', run_date=send_time, args=[tag, reminder_time],
                                  id=f"{reminder_time}_{tag}", name=f"{tag}")
            except:
                continue

    await ctx.edit_original_message(content=content, components=button)

    async def get_custom_text(res: disnake.MessageInteraction):
        if res.data.custom_id == "new_reminder" or res.data.custom_id == "go_to_finish":
            await res.response.defer()
            return res.data.custom_id
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
        button = [disnake.ui.ActionRow(
            disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                              style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
            disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                              custom_id="go_to_finish"))
        ]
        await res.edit_original_message(components=button)

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            raise ExpiredComponents
        await modal_inter.response.defer(ephemeral=True)
        await modal_inter.send(content="Custom Text Stored")
        custom_text = modal_inter.text_values["custom_text"]
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)

    if custom_text in ["new_reminder", "go_to_finish"]:
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "War",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    return custom_text


async def create_inactivity_reminder(bot: CustomClient, ctx: disnake.MessageInteraction, clan: coc.Clan,
                                     channel: disnake.TextChannel):
    content = f"**Choose settings ({clan.name}):**\n" \
              "> - Times to remind\n" \
              "> - (optional) Game Roles to Ping | default all roles\n" \
              "> - (optional) Point Threshold - Ping people with less than this many points | default 4000\n" \
              "*Note: If you don't select the optional fields, defaults will be used*"

    options = [  # the options in your dropdown
        disnake.SelectOption(label="24 hours of inactivity", emoji=bot.emoji.clock.partial_emoji, value="24 hr"),
        disnake.SelectOption(label="48 hours of inactivity", emoji=bot.emoji.clock.partial_emoji, value="48 hr"),
        disnake.SelectOption(label="3 days of inactivity", emoji=bot.emoji.clock.partial_emoji, value="72 hr"),
        disnake.SelectOption(label="1 week of inactivity", emoji=bot.emoji.clock.partial_emoji, value="168 hr"),
        disnake.SelectOption(label="2 weeks of inactivity", emoji=bot.emoji.clock.partial_emoji, value="336 hr"),
        disnake.SelectOption(label="Remove All", emoji=bot.emoji.no.partial_emoji, value="remove")
    ]
    time_select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=4,  # the maximum number of options a user can select
    )

    options = []
    role_types = ["Member", "Elder", "Co-Leader", "Leader"]
    for role in role_types:
        options.append(disnake.SelectOption(label=f"{role}", value=f"{role}"))
    role_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Roles",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )

    page_buttons = [
        disnake.ui.Button(label="Save", emoji=bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green,
                          custom_id="Save"),
    ]
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    dropdown = [disnake.ui.ActionRow(time_select), disnake.ui.ActionRow(role_select), buttons]

    await ctx.edit_original_message(content=content, components=dropdown)

    save = False

    times = []
    roles = role_types
    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if not times:
                await res.send(content="Must select reminder times", ephemeral=True)
            else:
                save = True
        elif "string_select" in str(res.data.component_type):
            if "hr" in res.values[0]:
                times = res.values
            elif res.values[0] in role_types:
                roles = res.values

    for time in times:
        await bot.reminders.delete_one({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "inactivity"},
            {"time": time}
        ]})
        await bot.reminders.insert_one({
            "server": ctx.guild.id,
            "type": "inactivity",
            "clan": clan.tag,
            "channel": channel.id,
            "time": time,
            "roles": roles,
        })

    reminders_created = ", ".join(times)
    content = f"**`{reminders_created}` Inactivity Reminders created for {clan.name}**"

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                          custom_id="custom_text"),
        disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    await ctx.edit_original_message(content=content, components=button)

    async def get_custom_text(res: disnake.MessageInteraction):
        if res.data.custom_id == "new_reminder" or res.data.custom_id == "go_to_finish":
            await res.response.defer()
            return res.data.custom_id
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
        button = [disnake.ui.ActionRow(
            disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                              style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
            disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                              custom_id="go_to_finish"))
        ]
        await res.edit_original_message(components=button)

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            raise ExpiredComponents
        await modal_inter.response.defer(ephemeral=True)
        await modal_inter.send(content="Custom Text Stored")
        custom_text = modal_inter.text_values["custom_text"]
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)

    if custom_text in ["new_reminder", "go_to_finish"]:
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "inactivity",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    return custom_text


##REMINDER DELETION

async def remove_clan_capital_reminder(bot, ctx: disnake.MessageInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "Clan Capital"}, {"server": ctx.guild.id}]})

    reminders = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        reminders.append([reminder, float(str(reminder.get('time')).replace("hr", ""))])

    reminders = sorted(reminders, key=lambda l: l[1], reverse=False)

    options = []
    for reminder in reminders:
        reminder = reminder[0]
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Remove Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    if not options:
        content = f"**No clan capital reminders set up for {clan.name}**"
        await ctx.edit_original_message(content=content, components=button)
        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
        next_move = res.data.custom_id
        return next_move

    content = "**Choose reminder times to remove from list**"
    select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(select)]
    await ctx.edit_original_message(content=content, components=dropdown)

    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "Clan Capital",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    content = f"**`{reminders_removed}` Clan Capital Reminders removed for {ctx.guild.name}**"
    await ctx.edit_original_message(content=content, components=button)
    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    next_move = res.data.custom_id
    return next_move


async def remove_clan_games_reminder(bot, ctx: disnake.MessageInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "Clan Games"}, {"server": ctx.guild.id}]})

    reminders = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        reminders.append([reminder, float(str(reminder.get('time')).replace("hr", ""))])

    reminders = sorted(reminders, key=lambda l: l[1], reverse=False)

    options = []
    for reminder in reminders:
        reminder = reminder[0]
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Remove Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    if not options:
        content = f"**No clan games reminders set up for {clan.name}**"
        await ctx.edit_original_message(content=content, components=button)
        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
        next_move = res.data.custom_id
        return next_move

    content = "**Choose reminder times to remove from list**"
    select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(select)]
    await ctx.edit_original_message(content=content, components=dropdown)

    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "Clan Games",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    content = f"**`{reminders_removed}` Clan Games Reminders removed for {ctx.guild.name}**"
    await ctx.edit_original_message(content=content, components=button)
    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    next_move = res.data.custom_id
    return next_move


async def remove_war_reminder(bot, ctx: disnake.MessageInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "War"}, {"server": ctx.guild.id}]})

    reminders = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        reminders.append([reminder, float(str(reminder.get('time')).replace("hr", ""))])

    reminders = sorted(reminders, key=lambda l: l[1], reverse=False)

    options = []
    for reminder in reminders:
        reminder = reminder[0]
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Remove Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    if not options:
        content = f"**No war reminders set up for {clan.name}**"
        await ctx.edit_original_message(content=content, components=button)
        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
        next_move = res.data.custom_id
        return next_move

    content = "**Choose reminder times to remove from list**"
    select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(select)]
    await ctx.edit_original_message(content=content, components=dropdown)

    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "War",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    content = f"**`{reminders_removed}` War Reminders removed for {ctx.guild.name}**"
    await ctx.edit_original_message(content=content, components=button)
    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    next_move = res.data.custom_id
    return next_move


async def remove_inactivity_reminder(bot, ctx: disnake.MessageInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "inactivity"}, {"server": ctx.guild.id}]})

    reminders = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        reminders.append([reminder, float(str(reminder.get('time')).replace("hr", ""))])

    reminders = sorted(reminders, key=lambda l: l[1], reverse=False)

    options = []
    for reminder in reminders:
        reminder = reminder[0]
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Remove Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    if not options:
        content = f"**No inactivity reminders set up for {clan.name}**"
        await ctx.edit_original_message(content=content, components=button)
        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
        next_move = res.data.custom_id
        return next_move

    content = "**Choose reminder times to remove from list**"
    select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(select)]
    await ctx.edit_original_message(content=content, components=dropdown)

    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "inactivity",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    content = f"**`{reminders_removed}` Inactivity Reminders removed for {ctx.guild.name}**"
    await ctx.edit_original_message(content=content, components=button)
    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    next_move = res.data.custom_id
    return next_move
