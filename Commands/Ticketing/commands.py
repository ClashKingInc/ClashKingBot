import asyncio
import disnake

from operator import attrgetter
from Exceptions.CustomExceptions import *
from typing import  Union
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from datetime import datetime
from Utils.cdn import upload_to_cdn
from main import check_commands
from Utils.discord_utils import interaction_handler
from CustomClasses.Ticketing import TicketPanel, OpenTicket, LOG_TYPE
from Discord.autocomplete import Autocomplete as autocomplete
from disnake import ButtonStyle
from Utils.constants import TOWNHALL_LEVELS
from .buttons import TicketClick


class TicketCommands(TicketClick, commands.Cog, name="Ticket Commands"):

    def __init__(self, bot: CustomClient):
        super().__init__(bot)
        self.bot = bot


    @commands.slash_command(name="ticket")
    async def ticket(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    #PANELS
    @ticket.sub_command(name="panel-create", description="Get started here! Create your first ticket panel")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_panel_create(self, ctx: disnake.ApplicationCommandInteraction,
                                  panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel), embed_link:str = None):
        """
            Parameters
            ----------
            panel_name: name for panel
            embed_link: message link to an existing embed to copy
        """

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is not None:
            raise PanelAlreadyExists

        if embed_link is None:
            modal_inter, embed = await self.basic_embed_modal(ctx=ctx)
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
    async def ticket_panel_post(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel)):
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
    async def ticket_panel_edit(self, ctx: disnake.ApplicationCommandInteraction,
                                panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel), embed_link: str = None):
        """
            Parameters
            ----------
            panel_name: name of panel
            embed_link: message link to an existing embed to copy
        """
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound

        if embed_link is None:
            modal_inter, embed = await self.basic_embed_modal(ctx=ctx, previous_embed=disnake.Embed.from_dict(data=result.get("embed")))
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

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$set" : {"embed" : embed.to_dict()}})
        await ctx.edit_original_message(content="This is what your panel will look like.", embed=embed, components=None)


    @ticket.sub_command(name="panel-delete", description="Delete a panel (and everything attached to it)")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_panel_delete(self, ctx: disnake.ApplicationCommandInteraction, panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel)):
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        await self.bot.tickets.delete_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        await ctx.send(content=f"**{panel_name} Panel Deleted**")


    #BUTTONS
    @ticket.sub_command(name="button-add", description="Add a button to a ticket panel")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_button_add(self, ctx: disnake.ApplicationCommandInteraction,
                                panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                                button_text: str = commands.Param(),
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
        await ctx.response.defer()
        panel_settings = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if panel_settings is None:
            raise PanelNotFound
        panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)
        await panel.create_button(label=button_text, color=button_color, emoji=button_emoji)
        await ctx.edit_original_message(content="**Button Created!**", components=[])



    @ticket.sub_command(name="button-edit", description="Edit a button on a ticket panel")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_button_edit(self, ctx: disnake.ApplicationCommandInteraction,
                                panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                                button: str = commands.Param(),
                                new_text: str = commands.Param(),
                                new_color=commands.Param(choices=["Blue", "Green", "Grey", "Red"]), new_emoji: str = None):
        """
            Parameters
            ----------
            panel_name: name of panel
            button: button to edit
            new_text: Text that shows up on button
            new_color: Color for button
            new_emoji: (optional) default discord emoji or one from *your* server
        """
        await ctx.response.defer()
        panel_settings = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if panel_settings is None:
            raise PanelNotFound
        panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)
        await panel.edit_button(button=button, new_text=new_text, new_color=new_color, new_emoji=new_emoji)
        await ctx.edit_original_message(content="**Button Edited!**", components=[])


    @ticket.sub_command(name="button-remove", description="Remove a button from a ticket panel")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_button_remove(self, ctx: disnake.ApplicationCommandInteraction,
                                   panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                                   button: str = commands.Param()):
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
    @ticket.sub_command(name="settings", description="Turn/set questions & private thread usage")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_settings(self, ctx: disnake.ApplicationCommandInteraction,
                                  panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                                  button: str = commands.Param(),
                                  choice: str = commands.Param(choices=["Questions", "Private Thread"]),
                                  option=commands.Param(default="On", choices=["Off"])):
        """
            Parameters
            ----------
            panel_name: name of panel
            button: name of button
            choice: thing you are setting
            remove: (optional) remove questions from this button
        """

        if choice == "Questions":
            if option == "Off":
                await ctx.response.defer()
            result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
            if result is None:
                raise PanelNotFound
            button_id = next((x for x in result.get("components") if x.get("label") == button), None)
            if button_id is None:
                raise ButtonNotFound

            if option == "Off":
                await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$set": {f"{button_id.get('custom_id')}_settings.questions": []}})
                return await ctx.send(embed=disnake.Embed(description=f"Questionnaire removed for {button} button on {panel_name} panel", color=disnake.Color.green()))

            components = [
                disnake.ui.TextInput(
                    label=f"Question {x}",
                    placeholder="Question (under 100 characters)",
                    custom_id=f"question_{x}",
                    required=(x == 1),
                    style=disnake.TextInputStyle.single_line,
                    max_length=99,
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

        elif choice == "Private Thread":
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
                embed=disnake.Embed(description=f"Private Thread Settings Updated!", color=disnake.Color.green()))



    @ticket.sub_command(name="message", description="Customize the message that is sent when a ticket is opened")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_message(self, ctx: disnake.ApplicationCommandInteraction,
                             panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                             button: str = commands.Param(),
                             embed_link: str = None,
                             ping_staff = commands.Param(default=None, choices=["True", "False"])):
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound

        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        if button_id is None:
            raise ButtonNotFound

        if ping_staff is not None:
            await ctx.response.defer()
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                              {"$set": {
                                                  f"{button_id.get('custom_id')}_settings.ping_staff": (ping_staff == "True")}})
            return await ctx.edit_original_message(content=f"**Ping Staff Setting changed to {ping_staff == 'True'}**")

        if embed_link is None:
            modal_inter, embed = await self.basic_embed_modal(ctx=ctx)
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
                return await ctx.edit_original_message(content=f"Something went wrong :/ An error occured with the message link.")


        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.message": embed.to_dict()}})

        await ctx.edit_original_message(content=f"**Custom Message to be Sent added to `{button}` button on `{panel_name}` panel**", embed=embed)


    @ticket.sub_command(name="staff", description="Set staff roles, that get added to tickets created with this button")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_mods(self, ctx: disnake.ApplicationCommandInteraction,
                          panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                          button: str = commands.Param(),
                          remove=commands.Param(default="False", choices=["True"])):
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

        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx, function=None, bot=self.bot)
        ticket_roles = res.values

        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.mod_role": ticket_roles}})
        await res.edit_original_message(content=f"**{button} Staff Roles Saved!**", components=[])


    @ticket.sub_command(name="roles", description="Manage Roles around Tickets being opened")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_roles(self, ctx: disnake.ApplicationCommandInteraction,
                           panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                           button: str = commands.Param(),
                           mode=commands.Param(choices=["Add to", "Remove Roles"]),
                           remove= commands.Param(default="False", choices=["True"])):

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

        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx, function=None, bot=self.bot)
        ticket_roles = res.values

        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        button_id = next((x for x in result.get("components") if x.get("label") == button), None)
        await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]},
                                          {"$set": {f"{button_id.get('custom_id')}_settings.{type}": ticket_roles}})
        await res.edit_original_message(content=f"**{button} Button {mode} Saved!**", components=[])



    @ticket.sub_command(name="apply", description="Set settings regarding accounts applying")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_account_apply(self, ctx: disnake.ApplicationCommandInteraction,
                                   panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                                   button: str = commands.Param()):
        await ctx.response.defer()

        panel_settings = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if panel_settings is None:
            raise PanelNotFound
        panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)
        button = panel.get_button(label=button)

        number_allowed_to_apply = button.number_allowed_to_apply
        account_apply = button.account_apply
        send_player_info = button.send_player_info
        townhall_minimum = button.townhall_minimum

        def create_components(account_apply: bool, send_player_info: bool, townhall_minimum: int, number_allowed_to_apply: int):
            account_select = disnake.ui.Select(
                options=[disnake.SelectOption(label=f"{x} Accounts", value=f"numaccounts_{x}",
                                              emoji=self.bot.emoji.green_tick.partial_emoji if x == number_allowed_to_apply else None)
                                              for x in range(1, 26)],
                placeholder=f"# of Accounts Allowed to Apply",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )

            townhall_min = disnake.ui.Select(
                options=[disnake.SelectOption(label=f"Townhall {x}", value=f"townhall_{x}",
                                                emoji=self.bot.fetch_emoji(x).partial_emoji if x != townhall_minimum else self.bot.emoji.green_tick.partial_emoji)
                                                for x in reversed(TOWNHALL_LEVELS)],
                placeholder=f"Minimum Townhall Allowed",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )

            dropdowns = [disnake.ui.ActionRow(account_select), disnake.ui.ActionRow(townhall_min)]
            buttons = disnake.ui.ActionRow()
            for b in [
                disnake.ui.Button(label="On/Off", style=ButtonStyle.green if account_apply else ButtonStyle.red, custom_id="account_apply"),
                disnake.ui.Button(label=f"Send Player Info", style=ButtonStyle.green if send_player_info else ButtonStyle.red, custom_id="send_player_info"),
            ]:
                buttons.append_item(b)
            dropdowns.append(buttons)
            return dropdowns

        await ctx.edit_original_message(content="**Edit Account Apply Settings**\n(Settings Saved As You Go)",
                                        components=create_components(account_apply, send_player_info, townhall_minimum, number_allowed_to_apply))

        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, no_defer=True)
            if res.data.component_type.value == 2:
                if "send_player_info" in res.data.custom_id:
                    send_player_info = not send_player_info
                    await button.set_player_info(state=send_player_info)

                elif "account_apply" in res.data.custom_id:
                    account_apply = not account_apply
                    await button.set_account_apply(state=account_apply)
            else:
                select_value = res.values[0]
                if "townhall_" in select_value:
                    townhall_minimum = int(select_value.split("_")[-1])
                    await button.set_townhall_minimum(level=townhall_minimum)

                elif "numaccounts_" in select_value:
                    number_allowed_to_apply = int(select_value.split("_")[-1])
                    await button.set_number_allowed_to_apply(num=number_allowed_to_apply)



            await res.response.edit_message(components=create_components(account_apply, send_player_info, townhall_minimum, number_allowed_to_apply))


    @ticket.sub_command(name="apply-rules", description="Set hero restrictions & more on accounts applying")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_apply_rules(self, ctx: disnake.ApplicationCommandInteraction,
                                 panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                                 button: str = commands.Param(),
                                 show_my_current_rules: str = commands.Param(default="False",choices=["True"])
                                 ):
        if show_my_current_rules == "True":
            return await ctx.send("*Coming Soon*", ephemeral=True)
        await ctx.response.defer()

        panel_settings = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if panel_settings is None:
            raise PanelNotFound
        panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)
        button = panel.get_button(label=button)

        buttons = [disnake.ui.ActionRow(disnake.ui.Button(label=f"Upload Requirements", style=ButtonStyle.grey, custom_id="upload_requirements"))]

        example_text = '```TH, BK, AQ, GW, RC, WARST,\n ' \
                       '9, 10, 15,  0,  0,   250,\n' \
                       '10, 25, 25,  0,  0,   300,\n' \
                       '11, 35, 35, 15,  0,   350,\n' \
                       '12, 40, 40, 25,  0,   400,\n' \
                       '13, 55, 55, 35, 10,   450,\n' \
                       '14, 65, 65, 45, 20,   500,\n' \
                       '15, 75, 75, 55, 30,   600,```'

        embed = disnake.Embed(description=f"**Copy the text above**\n"
                               f"- Make Any Edits (may be easier on desktop)\n"
                               f"- You can add/remove TH's on the example text, as long as same format\n"
                               f"- Click Button and Upload to Modal & Submit",
                              color=disnake.Color(2829617))

        await ctx.send(embed=embed, content=example_text, components=buttons)

        res: disnake.ApplicationCommandInteraction = await interaction_handler(bot=self.bot, ctx=ctx, no_defer=True)
        await res.response.send_modal(
            title="Townhall Requirements Upload",
            custom_id=f"threq-{int(datetime.now().timestamp())}",
            components=[
                disnake.ui.TextInput(
                    label="Requirements Here",
                    placeholder="Requirements Must be in the correct format",
                    custom_id=f"th_req",
                    required=True,
                    style=disnake.TextInputStyle.paragraph,
                    max_length=1000,
                )
            ])

        def check(r):
            return res.author.id == r.author.id

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except Exception:
            raise ExpiredComponents
        try:
            await modal_inter.response.defer(ephemeral=True)
        except Exception:
            pass

        requirements: str = modal_inter.text_values["th_req"]
        try:
            requirements = requirements.replace("```", "")
            split_req = requirements.split(",")
            headers = split_req[:6]
            rest = split_req[6:]
            index = 0
            key = 0
            new_data = {}
            for r in rest:
                r = r.replace("\n","").replace(" ", "")
                if r == "":
                    continue
                if r.isdigit():
                    r = int(r)
                if index == 0:
                    new_data[str(r)] = {}
                    key = str(r)
                new_data[key][headers[index].replace(" ", "")] = r
                index += 1
                if index == 6:
                    index = 0
        except Exception:
            return await modal_inter.send(content="Invalid Format, Please Run Command & Try Again")

        await button.set_townhall_requirements(requirements=new_data)
        await modal_inter.send(content=f"Requirements Stored\n```{requirements}```")
        buttons = [disnake.ui.ActionRow(disnake.ui.Button(label=f"Upload Requirements", style=ButtonStyle.grey, custom_id="upload_requirements", disabled=True))]
        await ctx.edit_original_message(components=buttons)


    @ticket.sub_command(name="apply-messages", description="Set up to 25 approve/deny messages")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_messages(self, ctx: disnake.ApplicationCommandInteraction,
                                 panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                                 name: str = commands.Param(),
                                 ):
        result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
        if result is None:
            raise PanelNotFound
        ticket = TicketPanel(bot=self.bot, panel_settings=result)


        await ctx.response.send_modal(
            title="Approve/Deny Messages",
            custom_id=f"approvemsg-{int(datetime.utcnow().timestamp())}",
            components=[
            disnake.ui.TextInput(
                label=f"Message",
                placeholder="",
                custom_id=f"approve_msg",
                required=True,
                style=disnake.TextInputStyle.paragraph,
                max_length=1000,
            )
        ])

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
        await ticket.add_edit_approve_messages(name=name, message=modal_inter.text_values["approve_msg"])
        await modal_inter.send(content="Message Added/Edited/Updated")



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
    async def ticket_categories(self, ctx: disnake.ApplicationCommandInteraction, panel_name:str,
                                status = commands.Param(choices=["all", "open", "sleep", "closed"]),
                                category: disnake.CategoryChannel = commands.Param(name="category")):

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


    #TO-DO add all panels as an option
    @ticket.sub_command(name="logging", description="Loggin Channels for ticket actions")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_logging(self, ctx: disnake.ApplicationCommandInteraction,
                             panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
                             types: str = commands.Param(choices=["All", "Ticket Button Click", "Ticket Close", "Status Change"]),
                             channel: Union[disnake.TextChannel, disnake.Thread]=None):
        """
            Parameters
            ----------
            panel_name: name of panel
            types: types of logging
            channel: Channel to set up logging in
        """
        await ctx.response.defer()
        if channel is None:
            channel = ctx.channel

        if panel_name != "All Panels":
            result = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]})
            if result is None:
                raise PanelNotFound

        types = types.lower().replace(" ", "_") + "_log"
        updater_list = {
            "ticket_button_click_log" : channel.id,
            "ticket_close_log" : channel.id,
            "status_change_log" : channel.id
        }
        if types != "all_log":
            updater_list = {types: updater_list.get(types)}

        if panel_name != "All Panels":
            await self.bot.tickets.update_one({"$and": [{"server_id": ctx.guild.id}, {"name": panel_name}]}, {"$set": updater_list})
        else:
            await self.bot.tickets.update_many({"server_id": ctx.guild.id}, {"$set": updater_list})
        await ctx.send(content=f"Logging channel for {panel_name} panel set to {channel.mention}")



    @ticket.sub_command(name="status", description="Change status of ticket")
    @commands.check_any(commands.has_permissions(manage_channels=True), check_commands())
    async def ticket_status(self, ctx: disnake.ApplicationCommandInteraction, status = commands.Param(choices=["open", "sleep", "close", "delete"])):
        await ctx.response.defer(ephemeral=True)

        if status == "close":
            status = "closed"

        ticket_data = await self.bot.open_tickets.find_one({"channel": ctx.channel.id})
        if ticket_data is None:
            return await ctx.send("Not a ticket channel")

        ticket = OpenTicket(bot=self.bot, open_ticket=ticket_data)
        if ticket.status == status:
            return await ctx.send(content=f"Ticket already {status}")

        await ticket.set_ticket_status(status=status)
        panel_settings = await self.bot.tickets.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": ticket.panel_name}]})
        panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)

        await panel.send_log(log_type=LOG_TYPE.STATUS_CHANGE, user=ctx.user, ticket_channel=ctx.channel, ticket=ticket)

        if status == "delete":
            await panel.send_log(log_type=LOG_TYPE.TICKET_CLOSE, user=ctx.user, ticket_channel=ctx.channel, ticket=ticket)
            await ctx.send(content="Deleting channel in 15 seconds")
            await asyncio.sleep(15)
            return await ctx.channel.delete()

        member = await ctx.guild.getch_member(ticket.user)
        if status == "closed" or status == "open":
            user_overwrite = disnake.PermissionOverwrite()
            user_overwrite.view_channel = (status == "open")
            channel: disnake.TextChannel = ctx.channel
            await channel.set_permissions(member, overwrite=user_overwrite)

        if "status" in ticket.naming_convention:
            await ticket.rename_ticket()

        category = None
        if panel_settings.get(f"{status}-category") is not None:
            category = await self.bot.getch_channel(panel_settings.get(f"{status}-category"))

        if category is None:
            category: disnake.CategoryChannel = ctx.channel.category
        await ctx.channel.edit(category=category)

        await ctx.send(content=f"Ticket status switched to {status}")


    @ticket.sub_command(name="add", description="Add a member to a ticket")
    @commands.check_any(commands.has_permissions(manage_channels=True), check_commands())
    async def ticket_add(self, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member):
        await ctx.response.defer()
        result = await self.bot.open_tickets.find_one({"channel": ctx.channel.id})
        if result is None:
            return await ctx.send("Not a ticket channel")
        user_overwrite = disnake.PermissionOverwrite()
        user_overwrite.view_channel = True
        user_overwrite.external_emojis = True
        user_overwrite.add_reactions = True
        user_overwrite.read_message_history = True
        user_overwrite.send_messages = True
        user_overwrite.attach_files = True
        await ctx.channel.set_permissions(member, overwrite=user_overwrite)
        await ctx.send(f"**{member.mention} added to this ticket by {ctx.user.mention}**")


    @ticket.sub_command(name="opt", description="Opt in/out of a ticket")
    @commands.check_any(commands.has_permissions(manage_channels=True), check_commands())
    async def ticket_opt(self, ctx: disnake.ApplicationCommandInteraction, opt= commands.Param(choices=["In", "Out"])):
        await ctx.response.defer(ephemeral=True)
        result = await self.bot.open_tickets.find_one({"channel": ctx.channel.id})
        if result is None:
            return await ctx.send("Not a ticket channel")
        if opt == "In":
             await self.bot.open_tickets.update_one({"channel": ctx.channel.id}, {"$push" : {"opted_in":ctx.user.id}})
        else:
            await self.bot.open_tickets.update_one({"channel": ctx.channel.id}, {"$pull": {"opted_in": ctx.user.id}})
        await ctx.send(content=f"Opted {opt} now!")




    @ticket_message.autocomplete("button")
    @ticket_roles.autocomplete("button")
    @ticket_button_remove.autocomplete("button")
    @ticket_account_apply.autocomplete("button")
    @ticket_mods.autocomplete("button")
    @ticket_roles.autocomplete("button")
    @ticket_name.autocomplete("button")
    @ticket_button_edit.autocomplete("button")
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

    async def basic_embed_modal(self, ctx: disnake.ApplicationCommandInteraction, previous_embed=None):
        components = [
            disnake.ui.TextInput(
                label=f"Embed Title",
                custom_id=f"title",
                required=False,
                style=disnake.TextInputStyle.single_line,
                max_length=75,
            ),
            disnake.ui.TextInput(
                label=f"Embed Description",
                custom_id=f"desc",
                required=False,
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
            ),
            disnake.ui.TextInput(
                label=f"Embed Thumbnail",
                custom_id=f"thumbnail",
                placeholder="Must be a valid url",
                required=False,
                style=disnake.TextInputStyle.single_line,
                max_length=200,
            ),
            disnake.ui.TextInput(
                label=f"Embed Image",
                custom_id=f"image",
                placeholder="Must be a valid url",
                required=False,
                style=disnake.TextInputStyle.single_line,
                max_length=200,
            ),
            disnake.ui.TextInput(
                label=f"Embed Color (Hex Color)",
                custom_id=f"color",
                required=False,
                style=disnake.TextInputStyle.short,
                max_length=10,
            )
        ]
        t_ = int(datetime.now().timestamp())
        await ctx.response.send_modal(
            title="Basic Embed Creator ",
            custom_id=f"basicembed-{t_}",
            components=components)

        def check(res: disnake.ModalInteraction):

            return ctx.author.id == res.author.id and res.custom_id == f"basicembed-{t_}"

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            return None

        color = disnake.Color.dark_grey()
        if modal_inter.text_values.get("color") != "":
            try:
                r, g, b = tuple(
                    int(modal_inter.text_values.get("color").replace("#", "")[i:i + 2], 16) for i in (0, 2, 4))
                color = disnake.Color.from_rgb(r=r, g=g, b=b)
            except:
                raise InvalidHexCode

        our_embed = {"title": modal_inter.text_values.get("title"), "description": modal_inter.text_values.get("desc"),
                     "image.url": modal_inter.text_values.get("image"),
                     "thumbnail.url": modal_inter.text_values.get("thumbnail"), "color": color}

        embed = await self.generate_embed(our_embed=our_embed, embed=previous_embed)
        await modal_inter.response.defer()

        return (modal_inter, embed)

    async def generate_embed(self, our_embed: dict, embed=None):
        if embed is None:
            embed = disnake.Embed()
        for attribute, embed_field in our_embed.items():
            if embed_field is None or embed_field == "":
                continue
            attribute: str
            if "field" in attribute:
                if embed_field["name"] is None or embed_field == "":
                    continue
                embed.insert_field_at(index=int(attribute.split("_")[1]) - 1, name=embed_field["name"],
                                      value=embed_field["value"], inline=embed_field["inline"])
            elif "image" in attribute:
                if embed_field != "" and embed_field != "None":
                    embed_field = await upload_to_cdn( embed_field)
                if embed_field == "None":
                    embed._image = None
                else:
                    embed.set_image(url=embed_field)
            elif "thumbnail" in attribute:
                if embed_field != "" and embed_field != "None":
                    embed_field = await upload_to_cdn(embed_field)
                if embed_field == "None":
                    embed._thumbnail = None
                else:
                    embed.set_thumbnail(url=embed_field)
            elif "footer" in attribute:
                if embed_field["text"] is None:
                    continue
                embed.set_footer(icon_url=embed_field["icon"], text=embed_field["text"])
            elif "author" in attribute:
                if embed_field["text"] is None:
                    continue
                embed.set_author(icon_url=embed_field["icon"], name=embed_field["text"])
            else:
                if len(attribute.split(".")) == 2:
                    obj = attrgetter(attribute.split(".")[0])(embed)
                    setattr(obj, attribute.split(".")[1], embed_field)
                else:
                    setattr(embed, attribute, embed_field)

        return embed


def setup(bot):
    bot.add_cog(TicketCommands(bot))



