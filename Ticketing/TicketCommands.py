from disnake.ext.commands.cog import _cog_special_method
from typing import List, Union
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

from Utility.profile_embeds import create_profile_stats, create_profile_troops, history, upgrade_embed
from main import check_commands
from CustomClasses.CustomPlayer import MyCustomPlayer

class TicketCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="ticket")
    async def ticket(self, ctx: disnake.ApplicationCommandInteraction):
        pass


    #PANELS
    @ticket.sub_command(name="panel-create", description="Get started here! Create your first ticket panel")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
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
                embed = await self.bot.parse_to_embed(custom_json=custom_embed, guild=ctx.guild)
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
                "player_info" : False,
                "ping_staff" : True
            }
        })

        await ctx.edit_original_message(content="This is what your panel will look like. (You can change it later with `/ticket panel-edit`)", embed=embed, components=None)

    @ticket.sub_command(name="panel-post", description="Post your created ticket panels anywhere!")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
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


        action_buttons = [[], [], [], [], []]
        row = 0
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
            action_buttons[row].append(disnake.ui.Button(label=component.get("label"), emoji=emoji, style=style[component.get("style")], custom_id=component.get("custom_id")))
            if len(action_buttons[row]) == 5:
                row += 1

        all_buttons = []
        for button_row in action_buttons:
            if not button_row:
                continue
            buttons = disnake.ui.ActionRow()
            for button in button_row:
                buttons.append_item(button)
            all_buttons.append(buttons)

        await ctx.channel.send(embed=embed, components=all_buttons)
        await ctx.edit_original_response(content="Panel Posted!")


    @ticket.sub_command(name="panel-edit", description="Edit the embed portion of your existing panels")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
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
            embed = await self.bot.parse_to_embed(custom_json=custom_embed, guild=ctx.guild)
        except:
            raise FaultyJson

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$set" : {"embed" : embed.to_dict()}})
        await ctx.edit_original_message(
            content="This is what your panel will look like. (You can change it later with `/ticket panel-edit`)",
            embed=embed, components=None)


    #BUTTONS
    @ticket.sub_command(name="button-add", description="Add a button to a ticket panel")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
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
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
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
    @ticket.sub_command(name="questions", description="Create a set of questions (up to 5) that will be asked when a ticket is opened")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_questionaire(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str, remove=commands.Param(default="False", choices=["True"])):
        """
            Parameters
            ----------
            panel_name: name of panel
            button: name of button
            remove: (optional) remove questions from this button
        """

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


    @ticket.sub_command(name="private-thread",
                        description="Turn private thread use - on/off")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_thread(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str, option=commands.Param(choices=["On", "Off"])):
        await ctx.response.defer()

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.private_thread": (option == "On")}})
        return await ctx.send(
            embed=disnake.Embed(description=f"Private Thread Settings Updated!",color=disnake.Color.green()))

    @ticket.sub_command(name="message", description="Customize the message that is sent when a ticket is opened")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_message(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str,  custom_embed: str = None, ping_staff = commands.Param(default=None, choices=["True", "False"])):
        if ping_staff is None and custom_embed is None:
            return await ctx.send("Must use the `custom_embed` or `ping_staff` field.")

        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        if ping_staff is not None:
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {
                                                  f"{button_id.get('custom_id')}_settings.ping_staff": (ping_staff == "True")}})
            return await ctx.send(content=f"**Ping Staff Setting changed to {ping_staff == 'True'}**")

        try:
            embed = await self.bot.parse_to_embed(custom_json=custom_embed, guild=ctx.guild)
        except:
            raise FaultyJson
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.message": embed.to_dict()}})

        await ctx.edit_original_message(content=f"**Custom Message to be Sent added to `{button}` button on `{panel_name}` panel**", embed=embed)


    @ticket.sub_command(name="staff", description="Set staff roles, that get added to tickets created with this button")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_mods(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str, remove=commands.Param(default="False", choices=["True"])):
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        if remove == "True":
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {f"{button_id.get('custom_id')}_settings.mod_role": None}})
            return await ctx.send(embed=disnake.Embed(description=f"Staff Roles removed for {button} button on {panel_name} panel", color=disnake.Color.green()))


        role_select = disnake.ui.RoleSelect(placeholder="Choose Roles (max 10)", max_values=10)
        dropdown = [disnake.ui.ActionRow(role_select)]

        await ctx.send(content="**Choose Staff Roles to be Added to Tickets created using this button**", components=dropdown)

        cog: cog_class = self.bot.get_cog(name="SetupCog")
        res: disnake.MessageInteraction = await cog.interaction_handler(ctx=ctx, function=None)
        ticket_roles = res.values

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.mod_role": ticket_roles}})
        await res.edit_original_message(content=f"**{button} Staff Roles Saved!**", components=[])


    @ticket.sub_command(name="apply-clans", description="Set clans that user can choose to apply to")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_apply_clans(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str, remove= commands.Param(default="False", choices=["True"])):
        await ctx.response.defer()

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        if remove == "True":
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {
                                                  f"{button_id.get('custom_id')}_settings.apply_clans": []}})
            return await ctx.send(embed=disnake.Embed(description=f"Apply Clans removed for {button} button on {panel_name} panel", color=disnake.Color.green()))


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

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.apply_clans": apply_clans}})
        await res.edit_original_message(content="**Application Clans Saved!**", components=[])


    @ticket.sub_command(name="roles", description="Set roles to be removed/added when ticket is opened")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_roles(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str,
                           mode=commands.Param(choices=["Add Roles", "Remove Roles"]), remove= commands.Param(default="False", choices=["True"])):
        await ctx.response.defer()

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        type = "roles_to_add" if mode == "Add Roles" else "roles_to_remove"

        if remove == "True":
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {
                                                  f"{button_id.get('custom_id')}_settings.{type}": []}})
            return await ctx.send(
                embed=disnake.Embed(description=f"{mode} removed for {button} button on {panel_name} panel",
                                    color=disnake.Color.green()))

        role_select = disnake.ui.RoleSelect(placeholder="Choose Roles (max 10)", max_values=10)
        dropdown = [disnake.ui.ActionRow(role_select)]
        if mode == "Add Roles":
            await ctx.send(content="**Choose roles to be added on ticket open**", components=dropdown)
        else:
            await ctx.send(content="**Choose roles to be removed on ticket open**", components=dropdown)

        cog: cog_class = self.bot.get_cog(name="SetupCog")
        res: disnake.MessageInteraction = await cog.interaction_handler(ctx=ctx, function=None)
        ticket_roles = res.values

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.{type}": ticket_roles}})
        await res.edit_original_message(content=f"**{button} Button {mode} Saved!**", components=[])


    @ticket.sub_command(name="account-apply", description="Set settings regarding")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_account_apply(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, button: str, option = commands.Param(default=None, choices=["On", "Off"]), number_of_accounts: int = None, send_player_info = commands.Param(default = None, choices=["True", "False"]),
                                   townhall_minimum: int = commands.Param(default=None, name="townhall_minimum")):
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        if option is not None:
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {f"{button_id.get('custom_id')}_settings.account_apply": (option == "On")}})

        if number_of_accounts is not None:
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {f"{button_id.get('custom_id')}_settings.num_apply": number_of_accounts}})

        if townhall_minimum is not None:
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {f"{button_id.get('custom_id')}_settings.th_min": int(townhall_minimum)}})

        if send_player_info is not None:
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {f"{button_id.get('custom_id')}_settings.player_info": (send_player_info == "True")}})
        return await ctx.send(
            embed=disnake.Embed(description=f"Account Apply Settings Updated!",
                                color=disnake.Color.green()))


    #COMMANDS
    @ticket.sub_command(name="transcript", description="Create a transcript of a channel")
    async def ticket_transcript(self, ctx: disnake.ApplicationCommandInteraction):
        #TO-DO check if this is a ticket channel
        await ctx.response.defer()
        open_result = await self.bot.open_tickets.find_one({
            "channel": ctx.channel.id
        })
        if open_result is None:
            return await ctx.send("Not a ticket channel")

        panel = open_result.get("panel")
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel}]})
        log_channel = result.get("log-channel")
        try:
            channel = await self.bot.getch_channel(log_channel)
        except:
            channel = None
        if channel is None:
            return await ctx.send(content="**Must have log-channel set up. `/ticket log-channel`")

        thread_channel = open_result.get("thread")
        if thread_channel is not None:
            try:
                thread_channel = await self.bot.getch_channel(channel_id=thread_channel)
            except:
                thread_channel = None
            if thread_channel is not None:
                transcript = await chat_exporter.export(thread_channel)
                transcript_file = disnake.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"transcript-{thread_channel.name}.html",
                )
                message = await channel.send(file=transcript_file)
                link = await chat_exporter.link(message)

                buttons = disnake.ui.ActionRow()
                buttons.append_item(disnake.ui.Button(label=f"Online View", emoji="🌐", url=link))
                await message.edit(components=[buttons])

        transcript = await chat_exporter.export(ctx.channel)
        transcript_file = disnake.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{ctx.channel.name}.html",
        )
        message = await channel.send(file=transcript_file)
        link = await chat_exporter.link(message)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label=f"Online View", emoji="🌐", url=link))
        await message.edit(components=[buttons])
        await ctx.send(f"Transcript sent to {channel.mention}")



    @ticket.sub_command(name="naming", description="Creating a naming convention for channels")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_name(self, ctx: disnake.ApplicationCommandInteraction, panel_name : str, button: str, naming_convention: str):
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.naming": naming_convention[0:100]}})

        await ctx.send(content=f"Naming Convention Saved : `{naming_convention}`")



    @ticket.sub_command(name="category", description="Category where you want different types of tickets")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_categories(self, ctx: disnake.ApplicationCommandInteraction, panel_name:str, status = commands.Param(choices=["all", "open", "sleep", "closed"]), category: disnake.CategoryChannel = commands.Param(name="category")):
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound

        if status == "all":
            status_types = ["open", "sleep", "closed"]
        else:
            status_types = [status]
        text = ""
        for status in status_types:
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {f"{status}-category" : category.id}})
            text += f"{status} tickets will now go to {category.mention}\n"

        await ctx.send(content=text)


    @ticket.sub_command(name="log-channel", description="Log Channel for ticket actions")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_logging(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str, channel: disnake.TextChannel):
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"log-channel": channel.id}})
        await ctx.send(content=f"Logging channel for {panel_name} panel set to {channel.mention}")

    @ticket.sub_command(name="status", description="Change status of ticket")
    @commands.check_any(commands.has_permissions(manage_channels=True), check_commands())
    async def ticket_status(self, ctx: disnake.ApplicationCommandInteraction, status = commands.Param(choices=["open", "sleep", "close", "delete"])):
        await ctx.response.defer(ephemeral=True)

        if status == "close":
            status = "closed"

        result = await self.bot.open_tickets.find_one({"channel": ctx.channel.id})
        if result is None:
            return await ctx.send("Not a ticket channel")
        if result.get("status") == status:
            return await ctx.send(content=f"Ticket already {status}")

        panel_settings = await self.bot.tickets.find_one(
            {"$and": [{"server_id": ctx.guild.id}, {"name": result.get("panel")}]})

        await self.bot.open_tickets.update_one({
            "channel": ctx.channel.id
        }, {"$set": {"status": status}})

        if status == "delete":
            ticketresult = await self.bot.open_tickets.find_one({
                "channel": ctx.channel.id
            })
            if ticketresult is None:
                return await ctx.send("Not a ticket channel")

            await self.ticket_log(result=panel_settings, open_result=result, channel=ctx.channel)
            await ctx.send(content="Deleting channel...")
            return await ctx.channel.delete()

        member = await ctx.guild.getch_member(result.get("user"))
        if status == "closed" or status == "open":
            user_overwrite = disnake.PermissionOverwrite()
            user_overwrite.view_channel = (status == "open")
            channel: disnake.TextChannel = ctx.channel
            await channel.set_permissions(member, overwrite=user_overwrite)

        if result.get("apply_account") is not None:
            account = await self.bot.getPlayer(player_tag=result.get("apply_account"))
        else:
            account = None
        if "status" in result.get("naming"):
            name = await self.rename_channel(user= member, ctx=ctx, apply_account=account, naming_convention=result.get("naming"), channel=ctx.channel, number=result.get("number"), status=status)

        category = None
        if panel_settings.get(f"{status}-category") is not None:
            try:
                category = await self.bot.getch_channel(panel_settings.get(f"{status}-category"))
            except:
                pass
        if category is None:
            category: disnake.CategoryChannel = ctx.channel.category

        if "status" in result.get("naming"):
            await ctx.channel.edit(name=name, category = category)
        else:
            await ctx.channel.edit(category=category)


        await ctx.send(content=f"Ticket status switched to {status}")


    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if ctx.channel.id == 1066526556874346587:
            return

        if ctx.data.custom_id == "close_ticket":
            result = await self.bot.open_tickets.find_one({
                "channel": ctx.channel.id
            })
            if result.get("status") == "closed":
                return await ctx.send(content="Ticket already closed", ephemeral=True)

            await ctx.response.defer()
            await self.bot.open_tickets.update_one({
                "channel": ctx.channel.id
            }, {"$set": {"status": "closed"}})
            result = await self.bot.open_tickets.find_one({
                "channel": ctx.channel.id
            })

            if result.get("apply_account") is not None:
                account = await self.bot.getPlayer(player_tag=result.get("apply_account"))
            else:
                account = None
            name = await self.rename_channel(user=ctx.user, ctx=ctx, apply_account=account, naming_convention=result.get("naming"), channel=ctx.channel, number=result.get("number"), status=result.get("status"))
            category = None

            panel_settings = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": result.get("panel")}]})
            if panel_settings.get(f"closed-category") is not None:
                try:
                    category = await self.bot.getch_channel(panel_settings.get("closed-category"))
                except:
                    pass
            if category is None:
                category: disnake.CategoryChannel = ctx.channel.category

            await ctx.channel.edit(name=name, category=category)
            user_overwrite = disnake.PermissionOverwrite()
            user_overwrite.view_channel = False
            member = await ctx.guild.getch_member(ctx.user.id)
            channel: disnake.TextChannel = ctx.channel
            await channel.set_permissions(member, overwrite=user_overwrite)
            await ctx.send(content="Ticket closed", ephemeral=True)

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": ctx.data.custom_id.split("_")[0]}]})
        if result is not None:

            button_settings = result.get(f"{ctx.data.custom_id}_settings")
            if button_settings is None:
                return await ctx.send("Button No Longer Exists", ephemeral=True)

            actions = ["questions", "account_apply", "apply_clans", "open_ticket", "message", "roles_to_add", "roles_to_remove", "private_thread", "player_info", "question_answers"]

            channel = None
            thread = None
            players = None
            message = None
            applyclan = None
            answers = []
            questions = []
            for action in actions:
                if action != "questions":
                    if not ctx.response.is_done():
                        await ctx.response.defer(ephemeral=True)
                if action == "open_ticket":
                    channel = await self.open_ticket(panel_settings=result, ctx=ctx, mod_roles=button_settings.get("mod_role") if button_settings.get("mod_role") is not None else [])
                    if message is None:
                        await ctx.send(content=f"{channel.mention} ticket opened!", ephemeral=True)
                    else:
                        await message.edit(content=f"{channel.mention} ticket opened!")


                elif action == "account_apply":
                    if not button_settings.get("account_apply"):
                        continue

                    th_min = button_settings.get("th_min", 0)
                    linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
                    stat_buttons = [
                        disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.green,
                                          custom_id="Start Link"),
                        disnake.ui.Button(label="Help", emoji="❓", style=disnake.ButtonStyle.grey,
                                          custom_id="Link Help")]
                    buttons = disnake.ui.ActionRow()
                    for button in stat_buttons:
                        buttons.append_item(button)
                    if not linked_accounts:
                        if message is None:
                            return await ctx.send(content="No accounts linked to you. Click the button below to link. **Once you are done, please open a ticket again.**",
                                           components=buttons, ephemeral=True)
                        else:
                            return await message.edit(content="No accounts linked to you. Click the button below to link. **Once you are done, please open a ticket again.**",
                                           components=buttons)

                    accounts = await self.bot.get_players(tags=linked_accounts, custom=True)
                    accounts.sort(key=lambda x: x.town_hall, reverse=True)
                    options = []
                    options.append(disnake.SelectOption(label="Link a different account", emoji=self.bot.emoji.up_green_arrow.partial_emoji, value=f"LinkDiff"))
                    for account in accounts:
                        if account.town_hall >= th_min:
                            account: coc.Player
                            options.append(disnake.SelectOption(label=account.name, emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji, value=f"{account.tag}"))

                    if not options:
                        return await ctx.send(
                            content=f"Sorry, you must have a townhall of {th_min} or higher to apply here. If you do, but need to link the account, use the button below & apply again.",
                            components=buttons, ephemeral=True)
                    options = options[:25]
                    select = disnake.ui.Select(
                        options=options,
                        placeholder="Select Account",
                        # the placeholder text to show when no options have been chosen
                        min_values=1,  # the minimum number of options a user must select
                        max_values=min(button_settings.get("num_apply", 1), len(options))  # the maximum number of options a user can select
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

                    if "LinkDiff" in valid_value:
                        await res.response.defer()
                        return await message.edit(
                            content="Click the button below to link. **Once you are done, please open a ticket again.**",
                            components=buttons)

                    players = [coc.utils.get(accounts, tag=tag) for tag in valid_value]
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
                    await self.send_message(channel=channel, embed_data=message, user=ctx.user, ctx=ctx, mod_roles=button_settings.get("mod_role") if button_settings.get("mod_role") is not None else [],
                                            ping_staff=button_settings.get("ping_staff", True))

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
                    thread = await self.create_private_thread(ctx= ctx, channel=channel, mod_roles=button_settings.get("mod_role") if button_settings.get("mod_role") is not None else [])


                elif action == "player_info":
                    if players is not None:
                        await self.send_player_info(players=players, channel=thread if thread is not None else channel, ctx=ctx)

                elif action == "question_answers":
                    if not answers and applyclan is None:
                        continue
                    await self.send_answers(questions=questions, answers=answers, apply_clan=applyclan, channel=channel, thread=thread, apply_accounts=players)

            all_ticket_nums = await self.bot.open_tickets.distinct("number", filter={"server" : ctx.guild.id})
            if not all_ticket_nums:
                all_ticket_nums = [0]
            await self.bot.open_tickets.insert_one({
                "user" :  ctx.user.id,
                "channel" : channel.id,
                "thread" : thread.id if thread is not None else thread,
                "status" : "open",
                "number" : max(all_ticket_nums) + 1,
                "apply_account" : players[0].name if players is not None else None,
                "naming" : button_settings.get("naming", '{ticket_count}-{user}'),
                "panel" : ctx.data.custom_id.split("_")[0],
                "server" : ctx.guild.id
            })
            name = await self.rename_channel(user=ctx.user, naming_convention=button_settings.get("naming", '{ticket_count}-{user}'), apply_account=players[0] if players is not None else None,
                                      ctx=ctx, channel=channel, number= max(all_ticket_nums) + 1, status="open")
            await channel.edit(name=name)
            if thread is not None:
                await thread.edit(name=f"private-{name}")


    async def ticket_log(self, open_result, result, channel: disnake.TextChannel):
        log_channel = result.get("log-channel")
        try:
            l_channel = await self.bot.getch_channel(log_channel)
        except:
            l_channel = None
        if l_channel is None:
            return

        user = open_result.get("user")
        user = await self.bot.getch_user(user)
        thread_channel = open_result.get("thread")
        now = int(datetime.now().timestamp())
        if thread_channel is not None:
            try:
                thread_channel = await self.bot.getch_channel(channel_id=thread_channel)
            except:
                thread_channel = None
            if thread_channel is not None:
                transcript = await chat_exporter.export(thread_channel)
                transcript_file = disnake.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"transcript-{thread_channel.name}.html",
                )
                message = await l_channel.send(file=transcript_file)
                link = await chat_exporter.link(message)

                buttons = disnake.ui.ActionRow()
                buttons.append_item(disnake.ui.Button(label=f"Online View", emoji="🌐", url=link))
                await message.edit(embed=disnake.Embed(description=f"{user.mention}, Private Thread for Ticket #{open_result.get('number')}\n"
                                                                   f"Ticket Deleted: <t:{now}:R>" ),components=[buttons])

        transcript = await chat_exporter.export(channel)
        transcript_file = disnake.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{channel.name}.html",
        )
        message = await l_channel.send(file=transcript_file)
        link = await chat_exporter.link(message)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label=f"Online View", emoji="🌐", url=link))
        await message.edit(embed=disnake.Embed(description=f"{user.mention}, Main Ticket #{open_result.get('number')}\n"
                                                                   f"Ticket Deleted: <t:{now}:R>" ), components=[buttons])


    async def change_status(self, ctx: disnake.MessageInteraction, channel: disnake.TextChannel, status : str):
        await self.bot.open_tickets.update_one({
            "channel": channel.id
        }, {"$set" : {"status" : status}})

    async def rename_channel(self, user:disnake.User, ctx: disnake.MessageInteraction, apply_account: coc.Player, naming_convention: str, channel: disnake.TextChannel, number = None, status = None):
        if number is None:
            all_ticket_nums = await self.bot.open_tickets.distinct("number")
            if not all_ticket_nums:
                all_ticket_nums = [0]
            number = max(all_ticket_nums) + 1
        if status is None:
            result = await self.bot.open_tickets.find_one({
                    "channel": channel.id
             })
            status = result.get("status")

        status_emoji = {"open" : "✅", "sleep" : "🌙", "closed" : "❌"}
        types = {"{ticket_count}": number, "{user}" : user. name, "{account_name}" : apply_account.name if apply_account is not None else "", "{account_th}" : apply_account.town_hall if apply_account is not None else "",
                 "{ticket_status}" : status, "{emoji_status}" : status_emoji[status]}

        for type, replace in types.items():
            naming_convention = naming_convention.replace(type, str(replace))
        return naming_convention

    async def send_answers(self, questions: List[str], answers: List[str], apply_accounts: List[MyCustomPlayer], apply_clan: coc.Clan, channel: disnake.TextChannel, thread: disnake.Thread):
        description = ""
        if answers:
            for count, answer in enumerate(answers, 1):
                description += f"**{count}. {questions[count - 1]}**\n> {answer}\n"

        if apply_clan is not None:
            emoji = await self.bot.create_new_badge_emoji(url=apply_clan.badge.url)
            description += f"\n**Clan I would like to apply for: {emoji}{apply_clan.name}**"

        if apply_accounts is not None:
            description += f"\n**Accounts I would like to apply with:**\n"
            for account in apply_accounts:
                description += f"{self.bot.fetch_emoji(name=account.town_hall)} {account.name}\n"

        embed = disnake.Embed(title="**Questionnaire Panel**", description=description, color=disnake.Color.green())
        await channel.send(embed=embed)
        if thread is not None:
            await thread.send(embed=embed)

    async def ask_questions(self, ctx: disnake.MessageInteraction, message: disnake.Message, questions: List[str]):
        components = [
            disnake.ui.TextInput(
                label=f"Question #{count+1}:",
                placeholder=f"{question}",
                custom_id=f"{count}",
                required=True,
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
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

    async def send_message(self, ctx, channel: disnake.TextChannel, embed_data: dict, user: disnake.Member, ping_staff: bool, mod_roles: List[int]):
        if embed_data is not None:
            embed = disnake.Embed.from_dict(data=embed_data)
        else:
            embed = disnake.Embed(description="This ticket will be handled shortly!\nPlease be patient")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label=f"Close Ticket", emoji="✖", style=disnake.ButtonStyle.red, custom_id="close_ticket"))

        if not ping_staff:
            content = f"{user.mention}"
        else:
            mod_roles = [disnake.utils.get(ctx.guild.roles, id=int(role)) for role in mod_roles]
            text = " ".join([role.mention for role in mod_roles if not role.is_bot_managed()])
            content = f"{user.mention} {text}"
        await channel.send(content=f"{content}", embed=embed, components=[buttons])

    async def open_ticket(self, panel_settings, ctx: disnake.MessageInteraction, mod_roles: List[int]):
        overwrite = disnake.PermissionOverwrite()
        overwrite.view_channel = False
        overwrite_dict = {}
        overwrite_dict.update({ctx.guild.default_role : overwrite})

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

        user_overwrite = disnake.PermissionOverwrite()
        user_overwrite.view_channel = True
        user_overwrite.external_emojis = True
        user_overwrite.add_reactions = True
        user_overwrite.read_message_history = True
        user_overwrite.send_messages = True
        user_overwrite.attach_files = True

        for role in mod_roles:
            role = disnake.utils.get(ctx.guild.roles, id=int(role))
            if role is not None:
                overwrite_dict.update({role : mod_overwrite})
        member = await ctx.guild.getch_member(ctx.user.id)
        overwrite_dict.update({member: user_overwrite})

        category = None
        if panel_settings.get("open-category") is not None:
            try:
                category = await self.bot.getch_channel(panel_settings.get("open-category"))
            except:
                pass
        if category is None:
            category: disnake.CategoryChannel = ctx.channel.category
        channel = await ctx.guild.create_text_channel(name="ticket", reason="ticket", overwrites=overwrite_dict, category=category)
        return channel

    async def create_private_thread(self, ctx: disnake.MessageInteraction, channel: disnake.TextChannel, mod_roles: List[int]):
        thread = await channel.create_thread(name="Private Thread", type=disnake.ChannelType.private_thread)
        if not mod_roles:
            mod_roles = [role for role in ctx.guild.roles if role.permissions.administrator and not role.is_bot_managed()]
        else:
            mod_roles = [disnake.utils.get(ctx.guild.roles, id=int(role)) for role in mod_roles]

        text = " ".join([role.mention for role in mod_roles])
        await thread.send(content=text)
        return thread

    async def send_player_info(self, players: List[coc.Player], channel: disnake.TextChannel, ctx):
        for player in players:
            embed = await create_profile_stats(bot=self.bot, ctx=ctx, player=player)
            embed2 = await create_profile_troops(bot=self.bot, result=player)
            embed3 = upgrade_embed(bot=self.bot, player=player)
            try:
                embed4 = await history(bot=self.bot, ctx=ctx, result=player)
            except:
                embed4 = disnake.Embed(description="This player has made their clash of stats history private.",
                                      color=disnake.Color.green())
            message = await channel.send(embeds=[embed, embed2])
            message1 = await channel.send(embeds=embed3)
            message2 = await channel.send(embed=embed4)
            await message.pin()

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
        for role in roles:
            try:
                await member.remove_roles(*[disnake.utils.get(member.guild.roles, id=int(role))])
            except:
                pass


    @ticket_button_add.autocomplete("panel_name")
    @ticket_button_remove.autocomplete("panel_name")
    @ticket_panel_post.autocomplete("panel_name")
    @ticket_questionaire.autocomplete("panel_name")
    @ticket_apply_clans.autocomplete("panel_name")
    @ticket_message.autocomplete("panel_name")
    @ticket_roles.autocomplete("panel_name")
    @ticket_account_apply.autocomplete("panel_name")
    @ticket_mods.autocomplete("panel_name")
    @ticket_roles.autocomplete("panel_name")
    @ticket_name.autocomplete("panel_name")
    @ticket_categories.autocomplete("panel_name")
    @ticket_logging.autocomplete("panel_name")
    @ticket_panel_edit.autocomplete("panel_name")
    @ticket_thread.autocomplete("panel_name")
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
    @ticket_account_apply.autocomplete("button")
    @ticket_mods.autocomplete("button")
    @ticket_roles.autocomplete("button")
    @ticket_name.autocomplete("button")
    @ticket_thread.autocomplete("button")
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
