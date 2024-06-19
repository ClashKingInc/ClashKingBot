import disnake
import re
import pytz
import coc
from typing import List
from classes.bot import CustomClient
from datetime import datetime
from classes.player.stats import StatsPlayer
from classes.tickets import TicketPanel, Ticket_Buttons, OpenTicket, ApproveMessages

tiz = pytz.utc
from utility.clash.other import heros


async def ask_questions(bot: CustomClient, ctx: disnake.MessageInteraction, questions: List[str]):
    components = [
        disnake.ui.TextInput(
            label=f"Question #{count + 1}:",
            placeholder=f"{question[:100]}",
            custom_id=f"{count}",
            required=True,
            style=disnake.TextInputStyle.paragraph,
            max_length=500,
        )
        for count, question in enumerate(questions)
        if question != ""
    ]
    made_id = f"Answers-{ctx.user.id}-{int(datetime.now().timestamp())}"
    await ctx.response.send_modal(title="Questionnaire ", custom_id=made_id, components=components)

    def check(res: disnake.ModalInteraction):
        return ctx.author.id == res.author.id and res.custom_id == made_id

    modal_inter: disnake.ModalInteraction = await bot.wait_for(
        "modal_submit",
        check=check,
        timeout=300,
    )
    await modal_inter.response.defer(ephemeral=True)
    message = await modal_inter.followup.send(content="Answers Submitted!")
    answers = [modal_inter.text_values[f"{x}"] for x in range(0, len(components))]

    description = ""
    if answers:
        for count, answer in enumerate(answers, 1):
            description += f"**{count}. {questions[count - 1]}**\n> {answer}\n"

    embed = disnake.Embed(title="**Questionnaire**", description=description, color=disnake.Color(2829617))
    return (message, embed)


async def open_ticket(
    bot: CustomClient,
    ticket_panel: TicketPanel,
    button: Ticket_Buttons,
    ctx: disnake.MessageInteraction,
    coc_account: StatsPlayer = None,
):
    overwrite = disnake.PermissionOverwrite()
    overwrite.view_channel = False
    overwrite.external_emojis = True
    overwrite_dict = {}
    overwrite_dict.update({ctx.guild.default_role: overwrite})

    mod_overwrite = disnake.PermissionOverwrite()
    mod_overwrite.view_channel = True
    mod_overwrite.external_emojis = True
    mod_overwrite.add_reactions = True
    mod_overwrite.read_message_history = True
    mod_overwrite.send_messages = True
    mod_overwrite.manage_messages = True
    mod_overwrite.attach_files = True
    mod_overwrite.manage_channels = True
    mod_overwrite.send_messages_in_threads = True
    mod_overwrite.manage_channels = True
    mod_overwrite.use_application_commands = True

    user_overwrite = disnake.PermissionOverwrite()
    user_overwrite.view_channel = True
    user_overwrite.external_emojis = True
    user_overwrite.add_reactions = True
    user_overwrite.read_message_history = True
    user_overwrite.send_messages = True
    user_overwrite.attach_files = True

    no_ping_roles = [disnake.utils.get(ctx.guild.roles, id=int(role)) for role in button.no_ping_staff_roles]
    ping_roles = [disnake.utils.get(ctx.guild.roles, id=int(role)) for role in button.ping_staff_roles]

    for role in no_ping_roles + ping_roles:
        if role is not None:
            overwrite_dict.update({role: mod_overwrite})

    member = await ctx.guild.getch_member(ctx.user.id)
    overwrite_dict.update({member: user_overwrite})

    category = None
    if ticket_panel.open_category is not None:
        category = await bot.getch_channel(ticket_panel.open_category)
    if category is None:
        category: disnake.CategoryChannel = ctx.channel.category

    channel_name = await naming_convention_convertor(
        bot=bot,
        user=ctx.user,
        naming_convention=button.naming_convention,
        coc_account=coc_account,
        guild=ctx.guild,
    )
    channel = await ctx.guild.create_text_channel(
        name=channel_name,
        reason=channel_name,
        overwrites=overwrite_dict,
        category=category,
    )

    text = " ".join([role.mention for role in ping_roles if role is not None]) + member.mention
    if text.replace(" ", "") != "":
        await channel.send(content=text)

    channels = [channel]

    if button.private_thread:
        thread = await channel.create_thread(
            name=f"Private | {channel_name.replace('-', ' ')}",
            type=disnake.ChannelType.private_thread,
        )
        text = " ".join([role.mention for role in no_ping_roles + ping_roles if role is not None])
        if text.replace(" ", "") != "":
            await thread.send(content=text)
        channels.append(thread)

    return channels


async def naming_convention_convertor(
    bot: CustomClient,
    guild: disnake.Guild,
    user: disnake.User,
    naming_convention: str,
    number: int = None,
    status: str = "open",
    coc_account: StatsPlayer = None,
):
    if number is None:
        all_ticket_nums = await bot.open_tickets.distinct("number", filter={"server": guild.id})
        if not all_ticket_nums:
            all_ticket_nums = [0]
        number = max(all_ticket_nums) + 1
    status_emoji = {"open": "✅", "sleep": "🌙", "closed": "❌"}
    types = {
        "{ticket_count}": number,
        "{user}": user.name,
        "{account_name}": coc_account.name if coc_account is not None else "",
        "{account_th}": coc_account.town_hall if coc_account is not None else "",
        "{ticket_status}": status,
        "{emoji_status}": status_emoji[status],
    }

    for type, replace in types.items():
        naming_convention = naming_convention.replace(type, str(replace))
    return naming_convention


async def message_convertor(
    bot: CustomClient,
    ctx: disnake.MessageInteraction,
    ticket: OpenTicket,
    message: str,
    custom_field: dict = None,
):
    status_emoji = {"open": "✅", "sleep": "🌙", "closed": "❌"}
    user = await bot.getch_user(ticket.user)

    coc_account = None
    if ticket.apply_account is not None:
        coc_account = await bot.getPlayer(player_tag=ticket.apply_account, custom=True, cache_data=False)

    coc_clan = None
    clan_badge = None
    if ticket.clan is not None:
        coc_clan = await bot.getClan(clan_tag=ticket.clan)
        clan_badge = await bot.create_new_badge_emoji(url=coc_clan.badge.url)
    clm = ""
    if coc_clan is not None:
        leader_tag = coc.utils.get(coc_clan.members, role=coc.Role.leader).tag
        leader_mention = await bot.link_client.get_link(leader_tag)
        if leader_mention is not None:
            clm = f"<@{leader_mention}>"
    types = {
        "{ticket_count}": ticket.number,
        "{ticket_status}": ticket.status,
        "{ticket_emoji_status}": status_emoji[ticket.status],
        "{ticket_channel_mention}": ctx.channel.mention,
        "{user_name}": user.name,
        "{user_mention}": user.mention,
        "{server_name}": ctx.guild.name,
        "{server_member_count}": ctx.guild.member_count,
        "{account_name}": coc_account.name if coc_account is not None else "",
        "{account_th}": coc_account.town_hall if coc_account is not None else "",
        "{account_heroes}": (heros(bot=bot, player=coc_account) if coc_account is not None else ""),
        "{clan_name}": coc_clan.name if coc_clan is not None else "",
        "{clan_level}": coc_clan.level if coc_clan is not None else "",
        "{clan_badge_emoji}": clan_badge if coc_clan is not None else "",
        "{clan_link}": coc_clan.share_link if coc_clan is not None else "",
        "{clan_location}": coc_clan.location if coc_clan is not None else "",
        "{clan_member_count}": coc_clan.member_count if coc_clan is not None else "",
        "{clan_leader}": (coc.utils.get(coc_clan.members, role=coc.Role.leader).name if coc_clan is not None else ""),
        "{clan_leader_mention}": clm,
        "{clan_tag}": coc_clan.tag if coc_clan is not None else "",
        "{clan_war_league}": coc_clan.war_league if coc_clan is not None else "",
        "{clan_capital_league}": (coc_clan.capital_league if coc_clan is not None else ""),
    }

    for type, replace in types.items():
        message = message.replace(type, str(replace))

    if custom_field is not None:
        for type, replace in custom_field.items():
            message = message.replace(type, str(replace))

    left_over = []
    if custom_field is None:
        left_over = re.findall(r"{.*?}", message)

    return (message, left_over)
