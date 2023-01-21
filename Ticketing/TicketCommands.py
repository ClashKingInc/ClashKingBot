from disnake.ext.commands.cog import _cog_special_method
from typing import List
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from coc import utils
import coc
import disnake
import asyncio
from datetime import datetime
import pytz
tiz = pytz.utc
from Exceptions import PanelNotFound, ButtonNotFound, ButtonAlreadyExists, PanelAlreadyExists, FaultyJson
import chat_exporter
import io
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from SetupNew.SetupCog import SetupCog
    cog_class = SetupCog
else:
    cog_class = commands.Cog

from Utility.profile_embeds import create_profile_stats, create_profile_troops, history

class TicketCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="ticket")
    async def ticket(self, ctx: disnake.ApplicationCommandInteraction):
        pass


    #PANELS
    @ticket.sub_command(name="panel-create", description="Get started here! Create your first ticket panel")
    async def ticket_panel_create(self, ctx: disnake.ApplicationCommandInteraction, panel_name:str, custom_embed:str = None):
        """
            Parameters
            ----------
            panel_name: name for panel
            custom_embed: create a custom embed (/ticket help for more info)
        """

        panel_name = panel_name.lower()
        await ctx.response.defer(ephemeral=False)

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is not None:
            raise PanelAlreadyExists

        if custom_embed is None:
            embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**", description="To create a ticket, use the button(s) below", color=disnake.Color.from_rgb(255, 255, 255))
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
        else:
            try:
                embed = self.bot.parse_to_embed(custom_json=custom_embed, guild=ctx.guild)
            except:
                raise FaultyJson

        button = disnake.ui.Button(label="Open Ticket", emoji="📩", style=disnake.ButtonStyle.grey, custom_id=f"{panel_name}_0")

        await self.bot.tickets.insert_one({
            "name" : panel_name,
            "server_id" : ctx.guild.id,
            "components" : [button.to_component_dict()],
            "embed" : embed.to_dict(),
            f"{panel_name}_0_settings" : {
                "message" : None,
                "questions" : None,
                "mod_role" : None,
                "private_thread" : False,
                "roles_to_add" : None,
                "roles_to_remove" : None,
                "apply_clans" : None,
                "account_apply" : False,
                "player_info" : False
            }
        })

        await ctx.edit_original_message(content="This is what your panel will look like. (You can change it later with `/ticket panel-edit`)", embed=embed, components=None)

    @ticket.sub_command(name="panel-post", description="Post your created ticket panels anywhere!")
    async def ticket_panel_post(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str):
        """
            Parameters
            ----------
            panel_name: name of panel
        """
        await ctx.response.defer(ephemeral=True)
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound

        embed = disnake.Embed.from_dict(data=result.get("embed"))

        action_buttons = []
        for component in result.get("components"):
            emoji = component.get("emoji")
            if emoji is not None:
                if emoji.get("id") is not None:
                    emoji = self.bot.partial_emoji_gen(f"<:{emoji.get('name')}:{emoji.get('id')}>")
                else:
                    emoji = emoji.get('name')
            style = {1 : disnake.ButtonStyle.primary,
                     2: disnake.ButtonStyle.secondary,
                     3 : disnake.ButtonStyle.success,
                     4 : disnake.ButtonStyle.danger}
            action_buttons.append(disnake.ui.Button(label=component.get("label"), emoji=emoji, style=style[component.get("style")], custom_id=component.get("custom_id")))

        buttons = disnake.ui.ActionRow()
        for button in action_buttons:
            buttons.append_item(button)

        await ctx.channel.send(embed=embed, components=buttons)
        await ctx.edit_original_response(content="Panel Posted!")


    @ticket.sub_command(name="panel-edit", description="Edit the embed portion of your existing panels")
    async def ticket_panel_edit(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, custom_embed: str):
        """
            Parameters
            ----------
            panel_name: name for panel
            custom_embed: create a custom embed (/ticket help for more info)
        """
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound

        try:
            embed = self.bot.parse_to_embed(custom_json=custom_embed, guild=ctx.guild)
        except:
            raise FaultyJson

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$set" : {"embed" : embed.to_dict()}})
        await ctx.edit_original_message(
            content="This is what your panel will look like. (You can change it later with `/ticket panel-edit`)",
            embed=embed, components=None)


    #BUTTONS
    @ticket.sub_command(name="button-add", description="Add a button to a ticket panel")
    async def ticket_button_add(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button_text: str,
                                button_color=commands.Param(choices=["Blue", "Green", "Grey", "Red"]),
                                button_emoji: str = None):
        """
            Parameters
            ----------
            panel_name: name of panel
            button_text: Text that shows up on button
            button_color: Color for button
            button_emoji: (optional) default discord emoji or one from *your* server
        """
        panel_name = panel_name.lower()
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button_text), None)
        if button_id is not None:
            raise ButtonAlreadyExists

        style = {"Blue": disnake.ButtonStyle.primary,
                 "Grey": disnake.ButtonStyle.secondary,
                 "Green": disnake.ButtonStyle.success,
                 "Red": disnake.ButtonStyle.danger}

        button_id = f"{panel_name}_{int(datetime.utcnow().timestamp())}"
        button = disnake.ui.Button(label=button_text, emoji=button_emoji, style=style[button_color],
                                   custom_id=button_id)

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$push": {"components": button.to_component_dict()}})
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id}_settings": {
                                              "message": None,
                                              "questions": None,
                                              "mod_role": None,
                                              "private_thread": False,
                                              "roles_to_add": None,
                                              "roles_to_remove": None,
                                              "apply_clans": None,
                                              "account_apply": False,
                                              "player_info": False
                                          }}})

        await ctx.edit_original_message(content="**Button Created!**", components=[])



    @ticket.sub_command(name="button-remove", description="Remove a button from a ticket panel")
    async def ticket_button_remove(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str):
        """
            Parameters
            ----------
            panel_name: name of panel
            button: button to remove
        """
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$pull": {"components": {"label" : button}}})
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$unset": {f"{button_id.get('custom_id')}_settings": {}}})

        await ctx.send(embed=disnake.Embed(description=f"{button} button removed from {panel_name} panel", color=disnake.Color.red()))


    #ACTIONS
    @ticket.sub_command(name="questions")
    async def ticket_questionaire(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str, remove=commands.Param(default="False", choices=["True"])):
        if remove == "True":
            await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        if remove == "True":
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$set": {f"{button_id.get('custom_id')}_settings.questions": []}})
            return await ctx.send(embed=disnake.Embed(description=f"Questionnaire removed for {button} button on {panel_name} panel", color=disnake.Color.green()))

        components = [
            disnake.ui.TextInput(
                label=f"Question {x}",
                placeholder="Question you would like to ask",
                custom_id=f"question_{x}",
                required=(x == 1),
                style=disnake.TextInputStyle.single_line,
                max_length=120,
            )
            for x in range(1, 6)
        ]
        #await ctx.send(content="Modal Opened", ephemeral=True)
        await ctx.response.send_modal(
            title="Questionnaire ",
            custom_id="questionnaire-",
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
        await modal_inter.response.defer()
        questions = [modal_inter.text_values[f"question_{x}"] for x in range(1, 6)]
        text = "\n".join([f"{count}. {question}" for count, question in enumerate(questions, 1) if question != ""])
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$set": {f"{button_id.get('custom_id')}_settings.questions": questions}})
        await modal_inter.send(embed=disnake.Embed(title=f"Questionnaire Created - {button}", description=f"Questions:\n{text}"))


    @ticket.sub_command(name="message")
    async def ticket_message(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str,  custom_embed: str):
        await ctx.response.defer()
        try:
            embed = self.bot.parse_to_embed(custom_json=custom_embed, guild=ctx.guild)
        except:
            # TO-DO Error, faulty embed json
            return

        await self.create_setting_if_none(ctx.guild_id)
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.message": embed.to_dict()}})

        await ctx.edit_original_message(content=f"**Custom Message to be Sent added to `{button}` button on `{panel_name}` panel**", embed=embed)

    @ticket.sub_command(name="mod-role")
    async def ticket_mods(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role,
                          type=commands.Param(choices=["Add", "Remove"])):
        pass

    @ticket.sub_command(name="apply-clans")
    async def ticket_apply_clans(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str):
        await ctx.response.defer()
        clan_tags = await self.bot.clan_db.distinct(
            "tag", filter={"server": ctx.guild.id})

        if not clan_tags:
            # TO-DO, use command id & new name
            await ctx.send(content="No clans set up on this server. Get started with `/addclan`", ephemeral=True)
        clans = await self.bot.get_clans(tags=clan_tags)
        select_menu_options = []
        clans = sorted(clans, key=lambda x: x.member_count, reverse=True)

        for count, clan in enumerate(clans):
            emoji = await self.bot.create_new_badge_emoji(
                url=clan.badge.url)

            if count < 25:
                select_menu_options.append(
                    disnake.SelectOption(label=clan.name, emoji=self.bot.partial_emoji_gen(emoji_string=emoji),
                                         value=clan.tag))

        select = disnake.ui.Select(
            options=select_menu_options,
            # the placeholder text to show when no options have been chosen
            placeholder="Select Clans",
            min_values=1,  # the minimum number of options a user must select
            # the maximum number of options a user can select
            max_values=len(select_menu_options),
        )

        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.edit_original_message(content="**Choose Clans That Users Can Apply For:**", components=dropdown)
        cog: cog_class = self.bot.get_cog(name="SetupCog")
        res: disnake.MessageInteraction = await cog.interaction_handler(ctx=ctx, function=None)
        apply_clans = res.values

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.apply_clans": apply_clans}})
        await res.edit_original_message(content="**Application Clans Saved!**", components=[])

    @ticket.sub_command(name="roles")
    async def ticket_roles(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str,
                           mode=commands.Param(choices=["Add Roles", "Remove Roles"])):
        await ctx.response.defer()
        role_select = disnake.ui.RoleSelect(placeholder="Choose Roles (max 10)", max_values=10)
        dropdown = [disnake.ui.ActionRow(role_select)]
        if mode == "Add Roles":
            await ctx.send(content="**Choose roles to be added on ticket open**", components=dropdown)
        else:
            await ctx.send(content="**Choose roles to be removed on ticket open**", components=dropdown)

        cog: cog_class = self.bot.get_cog(name="SetupCog")
        res: disnake.MessageInteraction = await cog.interaction_handler(ctx=ctx, function=None)
        ticket_roles = res.values

        type = "roles_to_add" if mode == "Add Roles" else "roles_to_remove"

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.{type}": ticket_roles}})
        await res.edit_original_message(content=f"**{button} Button {mode} Saved!**", components=[])


    @ticket.sub_command(name="account-apply", description="Set settings regarding")
    async def ticket_account_apply(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str):
        pass


    #COMMANDS
    @ticket.sub_command(name="transcript")
    async def ticket_transcript(self, ctx: disnake.ApplicationCommandInteraction):
        #TO-DO check if this is a ticket channel
        await ctx.response.defer()
        transcript = await chat_exporter.export(ctx.channel, limit=20)
        transcript_file = disnake.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{ctx.channel.name}.html",
        )
        await ctx.send(file=transcript_file)
        message = await ctx.original_response()
        link = await chat_exporter.link(message)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label=f"Online View", emoji="🌐", url=link))

        await ctx.edit_original_message(components=[buttons])




    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if disnake.utils.get(ctx.user.roles, id=1034134693869797416) is None and disnake.utils.get(ctx.user.roles, id=1065325454560591882) is None:
            return await ctx.send(content="Not for you yet :)", ephemeral=True)

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": ctx.data.custom_id.split("_")[0]}]})
        if result is not None:
            button_settings = result.get(f"{ctx.data.custom_id}_settings")

            actions = ["questions", "account_apply", "apply_clans", "open_ticket", "message", "roles_to_add", "roles_to_remove", "private_thread", "player_info", "question_answers"]

            channel = None
            thread = None
            player_tag = None
            message = None
            applyclan = None
            answers = []
            questions = []

            for action in actions:
                if action != "questions":
                    if not ctx.response.is_done():
                        await ctx.response.defer(ephemeral=True)
                if action == "open_ticket":
                    channel = await self.open_ticket(ctx=ctx)
                    if message is None:
                        await ctx.send(content=f"{channel.mention} ticket opened!", ephemeral=True)
                    else:
                        await message.edit(content=f"{channel.mention} ticket opened!")


                elif action == "account_apply":
                    if not button_settings.get("account_apply"):
                        continue
                    linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
                    if not linked_accounts:
                        return await ctx.send(content="No accounts linked to you. Use `/link` to get started.",ephemeral=True)
                    accounts = await self.bot.get_players(tags=linked_accounts)
                    accounts.sort(key=lambda x: x.town_hall, reverse=True)
                    options = []
                    for account in accounts[:25]:
                        account: coc.Player
                        options.append(disnake.SelectOption(label=account.name, emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji, value=f"{account.tag}"))

                    if not options:
                        continue
                        #TO_DO TEST
                    options = options[:25]
                    select = disnake.ui.Select(
                        options=options,
                        placeholder="Select Account",
                        # the placeholder text to show when no options have been chosen
                        min_values=1,  # the minimum number of options a user must select
                        max_values=1,  # the maximum number of options a user can select
                    )
                    dropdown = [disnake.ui.ActionRow(select)]
                    if message is None:
                        message = await ctx.followup.send(content="Select Account to Apply With", components=dropdown, ephemeral=True)
                    else:
                        await message.edit(content="Select Account to Apply With", components=dropdown)

                    def check(res: disnake.MessageInteraction):
                        return res.message.id == message.id

                    valid_value = None
                    while valid_value is None:
                        try:
                            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
                        except:
                            raise Exception

                        if res.author.id != ctx.author.id:
                            await res.send(content="You must run the command to interact with components.", ephemeral=True)
                            continue

                        valid_value = res.values

                    player_tag = valid_value[0]
                    await res.response.defer()
                    await message.edit(content="Done!", components=[])

                elif action == "apply_clans":
                    if not button_settings.get("apply_clans"):
                        continue
                    clans = await self.bot.get_clans(tags=button_settings.get("apply_clans"))
                    (applyclan, message) = await self.apply_clans(clans=clans, ctx=ctx, message=message)

                elif action == "questions":
                    if not button_settings.get("questions"):
                        continue
                    questions = button_settings.get("questions")
                    (message, answers) = await self.ask_questions(ctx=ctx, message=message, questions=questions)

                elif action == "message":
                    message = button_settings.get("message")
                    await self.send_message(channel=channel, embed_data=message, user=ctx.user)

                elif action == "roles_to_add":
                    roles_to_add = button_settings.get("roles_to_add")
                    if not roles_to_add:
                        continue
                    await self.add_roles(member=ctx.user, roles=roles_to_add)

                elif action == "roles_to_remove":
                    roles_to_remove = button_settings.get("roles_to_remove")
                    if not roles_to_remove:
                        continue
                    await self.remove_roles(member=ctx.user, roles=roles_to_remove)


                elif action == "private_thread":
                    if not button_settings.get("private_thread"):
                        continue
                    thread = await self.create_private_thread(channel=channel)


                elif action == "player_info":
                    if player_tag is not None:
                        await self.send_player_info(player_tag=player_tag, channel=thread if thread is not None else channel, ctx=ctx)

                elif action == "question_answers":
                    if not answers and applyclan is None:
                        continue
                    await self.send_answers(questions=questions, answers=answers, apply_clan=applyclan, channel=channel, thread=thread)


    async def send_answers(self, questions: List[str], answers: List[str], apply_clan: coc.Clan, channel: disnake.TextChannel, thread: disnake.Thread):
        description = ""
        if answers:
            for count, answer in enumerate(answers, 1):
                description += f"**{count}. {questions[count]}**\n> {answer}\n"

        if apply_clan is not None:
            emoji = await self.bot.create_new_badge_emoji(url=apply_clan.badge.url)
            description += f"\n**Clan I would like to apply for: {emoji}{apply_clan.name}**"
        embed = disnake.Embed(title="**Questionnaire Panel**", description=description, color=disnake.Color.green())
        await channel.send(embed=embed)
        if thread is not None:
            await thread.send(embed=embed)

    async def ask_questions(self, ctx: disnake.MessageInteraction, message: disnake.Message, questions: List[str]):
        components = [
            disnake.ui.TextInput(
                label=f"{question}",
                placeholder="answer here",
                custom_id=f"{count}",
                required=True,
                style=disnake.TextInputStyle.single_line,
                max_length=150,
            )
            for count, question in enumerate(questions) if question != ""
        ]
        # await ctx.send(content="Modal Opened", ephemeral=True)

        await ctx.response.send_modal(
            title="Questionnaire ",
            custom_id = f"Answers-{ctx.user.id}",
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
        await modal_inter.response.defer(ephemeral=True)
        message = await modal_inter.followup.send(content="Answers Submitted!")
        answers = [modal_inter.text_values[f"{x}"] for x in range(0, len(components))]
        return (message, answers)

    async def send_message(self, channel: disnake.TextChannel, embed_data: dict, user: disnake.Member, content:str = None):
        if embed_data is not None:
            embed = disnake.Embed.from_dict(data=embed_data)
        else:
            embed = disnake.Embed(description="This ticket will be handled shortly!\nPlease be patient")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label=f"Close Ticket", style=disnake.ButtonStyle.red))
        buttons.append_item(disnake.ui.Button(label=f"Create Transcript", style=disnake.ButtonStyle.grey))
        if content is None:
            content = f"{user.mention}"
        else:
            content = content.replace("{user.mention}", user.mention)
        await channel.send(content=f"{content}", embed=embed, components=[buttons])


    async def open_ticket(self, ctx: disnake.MessageInteraction):
        overwrite = disnake.PermissionOverwrite()
        overwrite.view_channel = False

        category: disnake.CategoryChannel = ctx.channel.category
        channel = await ctx.guild.create_text_channel(name="ticket", reason="ticket",
                                                      overwrites={ctx.guild.default_role: overwrite}, category=category)
        return channel

    async def create_private_thread(self, channel: disnake.TextChannel):
        thread = await channel.create_thread(name="Testing thread creation", type=disnake.ChannelType.public_thread)
        return thread

    async def send_player_info(self, player_tag, channel: disnake.TextChannel, ctx):
        player = await self.bot.getPlayer(player_tag=player_tag, custom=True)
        embed = await create_profile_stats(bot=self.bot, ctx=ctx, player=player)
        embed2 = await create_profile_troops(bot=self.bot, result=player)
        embed3 = await history(bot=self.bot, ctx=ctx, result=player)
        await channel.send(embeds=[embed, embed2])
        await channel.send(embed=embed3)

    async def apply_clans(self, clans: List[coc.Clan], ctx: disnake.MessageInteraction, message: disnake.Message):
        select_menu_options = []
        for count, clan in enumerate(clans):
            emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)

            if count < 25:
                select_menu_options.append(
                    disnake.SelectOption(label=clan.name, emoji=self.bot.partial_emoji_gen(emoji_string=emoji), value=clan.tag))

        select = disnake.ui.Select(
            options=select_menu_options,
            # the placeholder text to show when no options have been chosen
            placeholder="Select Clan",
            min_values=1,  # the minimum number of options a user must select
            # the maximum number of options a user can select
            max_values=1,
        )

        dropdown = [disnake.ui.ActionRow(select)]

        if message is None:
            message = await ctx.followup.send(content=f"**Select Clan to Apply To**", components=dropdown, ephemeral=True)
        else:
            await message.edit(content=f"**Select Clan to Apply To**", components=dropdown)

        def check(res: disnake.MessageInteraction):
            return res.message.id == message.id

        valid_value = None
        while valid_value is None:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                raise Exception

            if res.author.id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", ephemeral=True)
                continue

            valid_value = res.values

        clan_tag = valid_value[0]
        await message.edit(content="Done!", components=[])
        return (coc.utils.get(clans, tag=clan_tag), message)


    async def add_roles(self, member: disnake.Member, roles: List[str]):
        try:
            await member.add_roles(*[disnake.utils.get(member.guild.roles, id=int(role)) for role in roles])
        except:
            pass

    async def remove_roles(self, member: disnake.Member, roles: List[str]):
        try:
            await member.remove_roles(*[disnake.utils.get(member.guild.roles, id=int(role)) for role in roles])
        except:
            pass


    @ticket_button_add.autocomplete("panel_name")
    @ticket_button_remove.autocomplete("panel_name")
    @ticket_panel_post.autocomplete("panel_name")
    @ticket_questionaire.autocomplete("panel_name")
    @ticket_apply_clans.autocomplete("panel_name")
    @ticket_message.autocomplete("panel_name")
    @ticket_roles.autocomplete("panel_name")
    async def autocomp_tickets(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        aliases = await self.bot.tickets.distinct("name", filter={"server_id": ctx.guild.id})
        alias_list = []
        for alias in aliases:
            if query.lower() in alias.lower():
                alias_list.append(f"{alias}")
        return alias_list[:25]

    @ticket_questionaire.autocomplete("button")
    @ticket_apply_clans.autocomplete("button")
    @ticket_message.autocomplete("button")
    @ticket_roles.autocomplete("button")
    @ticket_button_remove.autocomplete("button")
    async def autocomp_tickets(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        panel_name = ctx.filled_options["panel_name"]
        if panel_name == "":
            return []
        aliases = await self.bot.tickets.distinct("components.label", filter={"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        alias_list = []
        for alias in aliases:
            if query.lower() in alias.lower():
                alias_list.append(f"{alias}")
        return alias_list[:25]


    async def create_setting_if_none(self, server_id):
        results = await self.bot.ticket_settings.find_one({
            "server_id": server_id
        })
        if results is None:
            await self.bot.ticket_settings.insert_one({
                "server_id": server_id,
                "messages": {},
                "clan-weights": {},
                "questions" : {},
            })



    '''    @commands.Cog.listener()
    async def on_message(self, sent_message: disnake.Message):
        if "<@808566437199216691>" in sent_message.content or (sent_message.reference is not None and sent_message.reference.resolved.author.id == self.bot.user.id):
            message = sent_message.content.replace("<@808566437199216691>", "")
            parameters = {
                "botkey": "d2a98e27651751da35edc2ed6584f997fd62508eaffeaff1ef7cb57667178bee",
                "input": message,
                "client_id" : sent_message.author.id
            }
            response = requests.post("https://devman.kuki.ai/talk", params=parameters)
            await sent_message.reply(content="\n".join(response.json().get("responses")))
    '''


    '''async def cog_slash_command_error(self, inter: disnake.ApplicationCommandInteraction, error: Exception):
        print(error)'''
