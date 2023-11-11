import disnake
import coc
from CustomClasses.CustomBot import CustomClient
from CustomClasses.ReminderClass import Reminder
from utils.discord_utils import interaction_handler
from Exceptions.CustomExceptions import ExpiredComponents, ThingNotFound
from typing import List
from utils.components import clan_component
from utils.constants import TOWNHALL_LEVELS, ROLES
from CustomClasses.Roster import Roster
from datetime import datetime
from pytz import utc

##REMINDER CREATION

def role_options():
    options = []
    role_types = ROLES
    for role in role_types:
        options.append(disnake.SelectOption(label=f"{role}", value=f"{role}"))
    role_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Roles",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    return role_select

def buttons(bot: CustomClient, delete=False):
    page_buttons = [
        disnake.ui.Button(label="Save", emoji=bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green, custom_id="Save"),
        disnake.ui.Button(label="Custom Text", emoji="✏", style=disnake.ButtonStyle.grey, custom_id="modal_reminder_custom_text")
    ]
    if delete:
        page_buttons.append(disnake.ui.Button(label="Delete", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red, custom_id="Delete"))
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)
    return buttons

def atk_threshold():
    options = []
    attack_numbers = [1, 2, 3, 4, 5, 6]
    for number in attack_numbers:
        options.append(disnake.SelectOption(label=f"{number} attacks", value=f"{number}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Attack Threshold",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1  # the maximum number of options a user can select
    )
    return war_type_select

def townhalls(bot: CustomClient):
    options = []
    for num in reversed(TOWNHALL_LEVELS):
        options.append(disnake.SelectOption(label=f"Townhall {num}", emoji=bot.fetch_emoji(name=num).partial_emoji,
                                            value=f"th_{num}"))
    th_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Townhalls",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    return th_select

def war_type():
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
    return war_type_select

def point_threshold():
    options = []
    attack_numbers = [250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
    for number in attack_numbers:
        options.append(disnake.SelectOption(label=f"{number} points", value=f"{number}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Point Threshold",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1  # the maximum number of options a user can select
    )
    return war_type_select

def roster_options(bot: CustomClient, results):
    now = int(datetime.utcnow().replace(tzinfo=utc).timestamp())
    results = [result for result in results if result.get("time") is not None and result.get("time", 0) > (now + 1200)]
    if not results:
        raise ThingNotFound("**No Rosters or Any Rosters that have times set up (that are in the future) on this server**")
    roster_options = []
    for result in results:
        roster_options.append(disnake.SelectOption(label=result.get("alias"), value=f"{result.get('alias')}"))
    roster_select = disnake.ui.Select(
        options=roster_options,
        placeholder="Choose Roster(s)",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(roster_options),  # the maximum number of options a user can select
    )
    return (results, roster_select)


def roster_type():
    options = []
    war_types = ["All Roster Members", "Not in Clan", "Subs Only"]
    for war_type in war_types:
        options.append(disnake.SelectOption(label=f"{war_type}", value=f"{war_type}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Ping Type",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    return war_type_select



async def create_capital_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    clans = await bot.get_clans(tags=(await bot.get_guild_clans(guild_id=ctx.guild.id)))
    clan_page = 0
    dropdown = [clan_component(bot=bot, all_clans=clans, clan_page=clan_page), atk_threshold(), role_options(), buttons(bot=bot)]

    save = False

    clans_chosen = []
    roles_chosen = ROLES
    attack_threshold = 1
    custom_text = ""

    embed = disnake.Embed(title="**Clan Capital Reminder options/filters**", color=disnake.Color.green())
    embed.set_footer(text="Note: If you don't select optional fields, defaults will be used")
    embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text, times=times)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()


    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text, times=times)
                clan_dropdown = clan_component(bot=bot, all_clans=clans, clan_page=clan_page)
                await message.edit(embed=embed, components=[clan_dropdown, atk_threshold(), role_options(), buttons(bot=bot)])
            elif not clans_chosen:
                await res.send(content="Must select at least one clan", ephemeral=True)
            else:
                save = True
        elif any("clanpage_" in s for s in res.values):
            clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
            clan_dropdown = clan_component(bot=bot, all_clans=clans, clan_page=clan_page)
            await message.edit(embed=embed, components=[clan_dropdown, atk_threshold(), role_options(), buttons(bot=bot)])

        elif any("clantag_" in s for s in res.values):
            clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
            for tag in clan_tags:
                clan = coc.utils.get(clans, tag=tag)
                if clan in clans_chosen:
                    clans_chosen.remove(clan)
                else:
                    clans_chosen.append(clan)
            embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text, times=times)
            await message.edit(embed=embed)

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ROLES:
                roles_chosen = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)
            else:
                attack_threshold = res.values[0]
                embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)


    for time in times:
        for clan in clans_chosen:
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
                "roles": roles_chosen,
                "townhalls" : [],
                "attack_threshold": attack_threshold,
                "custom_text" : custom_text
            })


async def create_war_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    clans = await bot.get_clans(tags=(await bot.get_guild_clans(guild_id=ctx.guild.id)))
    clan_page = 0
    dropdown = [clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot), role_options(), war_type(), buttons(bot=bot)]

    save = False

    clans_chosen = []
    roles_chosen = ROLES
    war_types = ["Random", "Friendly", "CWL"]
    custom_text = ""
    ths = list(reversed(TOWNHALL_LEVELS))

    embed = disnake.Embed(title="**War Reminder options/filters**", color=disnake.Color.green())
    embed.set_footer(text="Note: If you don't select optional fields, defaults will be used")
    embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()


    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot), role_options(), war_type(), buttons(bot=bot)])
            elif not clans_chosen:
                await res.send(content="Must select at least one clan", ephemeral=True)
            else:
                save = True
        elif any("clanpage_" in s for s in res.values):
            clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
            await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot), role_options(), war_type(), buttons(bot=bot)])

        elif any("clantag_" in s for s in res.values):
            clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
            for tag in clan_tags:
                clan = coc.utils.get(clans, tag=tag)
                if clan in clans_chosen:
                    clans_chosen.remove(clan)
                else:
                    clans_chosen.append(clan)
            embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
            await message.edit(embed=embed)

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ROLES:
                roles_chosen = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)
            elif "th_" in res.values[0]:
                ths = [int(th.split("_")[-1]) for th in res.values]
                embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)
            elif res.values[0] in ["Random", "Friendly", "CWL"]:
                war_types = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)


    for time in times:
        for clan in clans_chosen:
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
                "roles": roles_chosen,
                "types" : war_types,
                "townhalls" : ths,
                "custom_text" : custom_text
            })


async def create_games_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    clans = await bot.get_clans(tags=(await bot.get_guild_clans(guild_id=ctx.guild.id)))
    clan_page = 0
    dropdown = [clan_component(bot=bot, all_clans=clans, clan_page=clan_page), point_threshold(), townhalls(bot=bot), role_options(), buttons(bot=bot)]

    save = False

    clans_chosen = []
    roles_chosen = ROLES
    points = 4000
    custom_text = ""
    ths = list(reversed(TOWNHALL_LEVELS))

    embed = disnake.Embed(title="**Clan Games Reminders options/filters**", color=disnake.Color.green())
    embed.set_footer(text="Note: If you don't select optional fields, defaults will be used")
    embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()

    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), point_threshold(), townhalls(bot=bot), role_options(), buttons(bot=bot)])
            elif not clans_chosen:
                await res.send(content="Must select at least one clan", ephemeral=True)
            else:
                save = True
        elif any("clanpage_" in s for s in res.values):
            clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
            await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), point_threshold(),
                                                        townhalls(bot=bot), role_options(), buttons(bot=bot)])

        elif any("clantag_" in s for s in res.values):
            clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
            for tag in clan_tags:
                clan = coc.utils.get(clans, tag=tag)
                if clan in clans_chosen:
                    clans_chosen.remove(clan)
                else:
                    clans_chosen.append(clan)
            embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
            await message.edit(embed=embed)

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ROLES:
                roles_chosen = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)
            elif "th_" in res.values[0]:
                ths = [int(th.split("_")[-1]) for th in res.values]
                embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)
            else:
                points = int(res.values[0])
                embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)

    for time in times:
        for clan in clans_chosen:
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
                "roles": roles_chosen,
                "townhalls" : ths,
                "point_threshold" : points,
                "custom_text" : custom_text
            })


async def create_inactivity_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    clans = await bot.get_clans(tags=(await bot.get_guild_clans(guild_id=ctx.guild.id)))
    clan_page = 0
    dropdown = [clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot),role_options(), buttons(bot=bot)]

    save = False

    clans_chosen = []
    roles_chosen = ROLES
    custom_text = ""
    ths = list(reversed(TOWNHALL_LEVELS))

    embed = disnake.Embed(title="**Inactivity Reminder options/filters**", color=disnake.Color.green())
    embed.set_footer(text="Note: If you don't select optional fields, defaults will be used")
    embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()

    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed,
                                   components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot), role_options(), buttons(bot=bot)])
            elif not clans_chosen:
                await res.send(content="Must select at least one clan", ephemeral=True)
            else:
                save = True
        elif any("clanpage_" in s for s in res.values):
            clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
            await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page),
                                                        townhalls(bot=bot), role_options(), buttons(bot=bot)])

        elif any("clantag_" in s for s in res.values):
            clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
            for tag in clan_tags:
                clan = coc.utils.get(clans, tag=tag)
                if clan in clans_chosen:
                    clans_chosen.remove(clan)
                else:
                    clans_chosen.append(clan)
            embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
            await message.edit(embed=embed)

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ROLES:
                roles_chosen = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)
            elif "th_" in res.values[0]:
                ths = [int(th.split("_")[-1]) for th in res.values]
                embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text, times=times)
                await message.edit(embed=embed)

    for time in times:
        for clan in clans_chosen:
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
                "roles": roles_chosen,
                "townhalls" : ths,
                "custom_text" : custom_text
            })


async def create_roster_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    results = await bot.rosters.find({"$and": [{"server_id": ctx.guild.id}]}).to_list(length=None)
    results, menu = roster_options(bot=bot, results=results)
    results = [Roster(bot=bot, roster_result=result) for result in results]
    dropdown = [menu, roster_type(), buttons(bot=bot)]

    save = False

    rosters_chosen = []
    ping_type = "All Roster Members"
    custom_text = ""

    embed = disnake.Embed(title="**Roster Reminder options/filters**", color=disnake.Color.green())
    embed.description = chosen_text(bot=bot, clans=[], times=times, ping_type=ping_type)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()

    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=[], rosters=rosters_chosen, custom_text=custom_text, times=times, ping_type=ping_type)
                await message.edit(embed=embed)
            elif not rosters_chosen:
                await res.send(content="Must select at least one roster", ephemeral=True)
            else:
                save = True

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ["All Roster Members", "Not in Clan", "Subs Only"]:
                ping_type = res.values[0]
                embed.description = chosen_text(bot=bot, clans=[], rosters=rosters_chosen, custom_text=custom_text, times=times, ping_type=ping_type)
                await message.edit(embed=embed)
            else:
                roster_aliases = res.values
                rosters_chosen = [coc.utils.get(results, alias=roster) for roster in roster_aliases]
                embed.description = chosen_text(bot=bot, clans=[], rosters=rosters_chosen, custom_text=custom_text, times=times, ping_type=ping_type)
                await message.edit(embed=embed)

    for time in times:
        for roster in rosters_chosen:
            await bot.reminders.delete_one({"$and": [
                {"roster": roster._id},
                {"server": ctx.guild.id},
                {"type": "roster"},
                {"time": time}
            ]})
            await bot.reminders.insert_one({
                "server": ctx.guild.id,
                "type": "roster",
                "roster": roster._id,
                "channel": channel.id,
                "ping_type" : ping_type,
                "time": time,
                "custom_text" : custom_text
            })


async def get_custom_text(bot:CustomClient, res: disnake.MessageInteraction):
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
    def check(r):
        return res.author.id == r.author.id

    try:
        modal_inter: disnake.ModalInteraction = await bot.wait_for(
            "modal_submit",
            check=check,
            timeout=300,
        )
    except:
        raise ExpiredComponents
    try:
        await modal_inter.response.defer(ephemeral=True)
    except:
        pass
    await modal_inter.send(content="Custom Text Stored", delete_after=2)
    custom_text = modal_inter.text_values["custom_text"]
    return custom_text


def chosen_text(bot: CustomClient, clans: List[coc.Clan], ths=None, roles=None, atk=None, war_types=None, points=None,
                times=None, custom_text="", channel = None, rosters=None, ping_type=None):
    text = ""
    if clans:
        text += "**CLANS:**\n"
        for clan in clans:
            text += f"• {clan.name} ({clan.tag})\n"

    if rosters:
        text += "**ROSTERS:**\n"
        for roster in rosters:
            text += f"• {roster.alias}\n"

    if ths is not None:
        text += "\n**THS:**\n"
        if ths == list(reversed(TOWNHALL_LEVELS)):
            text += f"• All Townhall Levels\n"
        else:
            ths = [f"TH{th}" for th in ths]
            text += "• " + ", ".join(ths) + "\n"

    if war_types:
        text += "\n**WAR TYPES:**\n"
        for t in war_types:
            text += f"• {t}\n"

    if roles:
        text += "\n**ROLES:**\n"
        for role in roles:
            text += f"• {role}\n"

    if atk is not None:
        text += f"\n**Attack Threshold:** {atk} attacks\n"

    if points is not None:
        text += f"\n**Point Threshold:** {points} points\n"

    if times is not None:
        text += "\n**TIMES:**\n"
        text += "• " + ", ".join(times) + "\n"

    if ping_type is not None:
        text += f"\n**Ping Type:** {ping_type}\n"

    if channel is not None:
        text += f"\n**Channel:** <#{channel}>\n"

    if custom_text != "":
        text += f"\n**Custom Text:** {custom_text}\n"
    return text





##REMINDER DELETION
async def edit_reminder(bot: CustomClient, clan: coc.Clan, ctx: disnake.ApplicationCommandInteraction, type: str):
    while True:
        if type != "roster":
            reminders = await bot.reminders.find({"$and": [{"clan": clan.tag}, {"type": type}, {"server": ctx.guild.id}]}).to_list(length=None)
        else:
            rosters = await bot.rosters.distinct("_id", filter={"$and": [{"clan_tag": clan.tag}, {"server_id": ctx.guild.id}]})
            pipeline = [
                {"$match": {"roster": {"$in": rosters}}},
                {"$lookup": {"from": "rosters", "localField": "roster", "foreignField": "_id", "as": "roster"}},
                {"$set": {"roster": {"$first": "$roster"}}}
            ]
            reminders = await bot.reminders.aggregate(pipeline=pipeline).to_list(length=None)

        if not reminders:
            raise ThingNotFound(f"**No {type.capitalize()} Reminders found for {clan.name}**")
        reminders = sorted(reminders, key=lambda l: float(str(l.get('time')).replace("hr", "")), reverse=False)

        options = []
        text = ""
        reminder_class_list = []
        for count, reminder in enumerate(reminders):
            reminder = Reminder(data=reminder, bot=bot)
            reminder_class_list.append(reminder)
            if reminder.type != "roster":
                text += f"`{reminder.time}` - <#{reminder.channel_id}>\n"
            else:
                text += f"`{reminder.time} | {reminder.roster.alias}` - <#{reminder.channel_id}>\n"
            options.append(disnake.SelectOption(label=f"{reminder.time} Reminder", value=f"{count }"))

        clan_select = disnake.ui.Select(
            options=options,
            placeholder=f"Select Reminder to Edit",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        clan_select = disnake.ui.ActionRow(clan_select)

        embed = disnake.Embed(title=f"{clan.name} {type.capitalize()} Reminders", description=text, color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.url)
        embed.set_footer(text="Choose a reminder to edit or delete it")
        await ctx.edit_original_message(embed=embed, components=clan_select)

        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, ephemeral=True)
        reminder = reminder_class_list[int(res.values[0])]
        embed = disnake.Embed(title=f"{clan.name} {reminder.time} {reminder.type.capitalize()} Reminder",
                              color=disnake.Color.green())
        embed.description = chosen_text(bot=bot, ths=reminder.townhalls, roles=reminder.roles, points=reminder.point_threshold, atk=reminder.attack_threshold,
                                        war_types=reminder.war_types, custom_text=reminder.custom_text, clans=[], channel=reminder.channel_id)

        dropdown = [disnake.ui.ActionRow(disnake.ui.ChannelSelect(placeholder="Choose Channel", max_values=1, channel_types=[disnake.ChannelType.text, disnake.ChannelType.public_thread])), townhalls(bot=bot), role_options()]
        if reminder.type == "Clan Capital":
            del dropdown[1]
            dropdown.append(atk_threshold())
        elif reminder.type == "War":
            dropdown.append(war_type())
        elif reminder.type == "Clan Games":
            dropdown.append(point_threshold())
        elif reminder.type == "roster":
            del dropdown[1]
            del dropdown[1]
            dropdown.append(roster_type())
        dropdown.append(buttons(bot=bot, delete=True))
        message = await res.followup.send(embed=embed, components=dropdown, ephemeral=True)

        save = False
        deleted = False
        roles_chosen = reminder.roles
        custom_text = reminder.custom_text
        ths = reminder.townhalls
        points = reminder.point_threshold
        atks = reminder.attack_threshold
        war_types = reminder.war_types
        channel = reminder.channel_id
        ping_type = reminder.ping_type

        while not save:
            res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=res, msg=message)
            if "button" in str(res.data.component_type):
                if res.data.custom_id == "modal_reminder_custom_text":
                    custom_text = await get_custom_text(bot=bot, res=res)
                elif res.data.custom_id == "Delete":
                    save = True
                    deleted = True
                    embed = disnake.Embed(
                        description=f"{clan.name} {reminder.time} {reminder.type.capitalize()} Reminder was **deleted**!",
                        color=disnake.Color.red())
                    await message.edit(embed=embed, components=[])
                    await reminder.delete()
                else:
                    save = True
            elif "channel_select" in str(res.data.component_type):
                channel = int(res.values[0])
            elif "string_select" in str(res.data.component_type):
                if res.values[0] in ROLES:
                    roles_chosen = res.values
                elif "th_" in res.values[0]:
                    ths = [int(th.split("_")[-1]) for th in res.values]
                elif res.values[0] in ["Random", "Friendly", "CWL"]:
                    war_types = res.values
                elif res.values[0] in ["All Roster Members", "Not in Clan", "Subs Only"]:
                    ping_type = res.values[0]
                elif res.values[0].isnumeric() and int(res.values[0]) in [250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]:
                    points = int(res.values[0])
                elif res.values[0].isnumeric() and int(res.values[0]) in [1, 2, 3, 4, 5, 6]:
                    atks = int(res.values[0])
            if not save and not deleted:
                embed.description = chosen_text(bot=bot, ths=ths, roles=roles_chosen, points=points, atk=atks,
                                                war_types=war_types, custom_text=custom_text, clans=[], channel=channel, ping_type=ping_type)
                await message.edit(embed=embed)

        if not deleted:
            await reminder.set_custom_text(custom_text=custom_text)
            await reminder.set_attack_threshold(threshold=atks)
            await reminder.set_point_threshold(threshold=points)
            await reminder.set_roles(roles=roles_chosen)
            await reminder.set_townhalls(townhalls=ths)
            await reminder.set_channel_id(id=channel)
            await reminder.set_war_types(types=war_types)
            await message.edit(components=[], content="*Reminder Updated!*")