import datetime
import disnake

from Utils.discord_utils import permanent_image, interaction_handler
from disnake.ext import commands
from exceptions.CustomExceptions import *
from operator import attrgetter
from CustomClasses.CustomBot import CustomClient

class CustomBoards(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="board", description="")
    async def board(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @board.sub_command(name="create", description="Create a custom board")
    async def create(self, ctx: disnake.ApplicationCommandInteraction, alias: str = commands.Param(min_length=3, max_length=25), embed_link: str = None):
        if embed_link is None:
            modal_inter, embed = await self.basic_embed_modal(ctx=ctx)
            ctx = modal_inter
        else:
            try:
                if "discord.com" not in embed_link:
                    return await ctx.send(content=f"Not a valid message link", ephemeral=True)
                link_split = embed_link.split("/")
                message_id = link_split[-1]
                channel_id = link_split[-2]

                channel = await self.bot.getch_channel(channel_id=int(channel_id))
                if channel is None:
                    return await ctx.send(content=f"Cannot access the channel this embed is in", ephemeral=True)
                message = await channel.fetch_message(int(message_id))
                if not message.embeds:
                    return await ctx.send(content=f"Message has no embeds", ephemeral=True)
                embed = message.embeds[0].to_dict()
            except:
                return await ctx.send(content=f"Something went wrong :/ An error occured with the message link.", ephemeral=True)

        result = await self.bot.custom_boards.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": alias}]})
        if result is not None:
            return await ctx.send(content=f"Custom Board - `{alias}` already exists", ephemeral=True)

        await self.bot.custom_boards.insert_one({
            "server_id" : ctx.guild.id,
            "name" : alias,
            "embed" : embed.to_dict(),
            "buttons" : []
        })

        await ctx.edit_original_message(embed=embed, content=f"**__{alias}__ custom board created!**")

    @board.sub_command(name="buttons-add", description="Add buttons on a custom board")
    async def board_buttons(self, ctx:disnake.ApplicationCommandInteraction, alias: str):
        result = await self.bot.custom_boards.find_one({"$and": [{"server_id": ctx.guild.id}, {"name": alias}]})
        if result is None:
            return await ctx.send(content=f"Custom Board - `{alias}` does not exist", ephemeral=True)
        await ctx.response.defer()
        panel = disnake.Embed().from_dict(data=result.get("embed"))
        components = result.get("buttons")
        new_component_list = await self.button_wizard(ctx=ctx, panel=panel, components=components)



    async def button_wizard(self, ctx: disnake.ApplicationCommandInteraction, panel: disnake.Embed, components: list):
        if len(components) <= 24:
            button = disnake.ui.Button(emoji="➕", style=disnake.ButtonStyle.green, custom_id="add_button")
            components.append(button.to_component_dict())

        buttons = await self.generate_components(components=components, disable=True)
        await ctx.edit_original_message(content="**Use the buttons below to edit existing buttons or add new ones**", embed=panel, components=buttons)

        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            if str(res.data.custom_id) == "add_button":
                button_types = [  # the options in your dropdown
                    disnake.SelectOption(label="Clan Command", value="clan_command"),
                    disnake.SelectOption(label="Family Command",  value="family_command"),
                    disnake.SelectOption(label="Ticket Button", value="ticket_button"),
                    disnake.SelectOption(label="URL Button",  value="url_button"),
                    disnake.SelectOption(label="Refresh Button", value="refresh_button"),
                    disnake.SelectOption(label="Link Button", value="link_button"),
                    disnake.SelectOption(label="Player To-Do Button", value="todo_button"),
                ]
                button_select = disnake.ui.StringSelect(options=button_types, placeholder="Choose a button type", max_values=1)
                msg = await res.followup.send(content="Select Button Type", components=[disnake.ui.ActionRow(button_select)], ephemeral=True)
                res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=res, msg=msg)
                if str(res.data.custom_id) == "clan_command":
                    clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
                    clans = await self.bot.get_clans(tags=clan_tags)
                    select_menu_options = []
                    clans = sorted(clans, key=lambda x: x.member_count, reverse=True)
                    for count, clan in enumerate(clans):
                        emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)
                        if count < 25:
                            select_menu_options.append(disnake.SelectOption(label=clan.name,emoji=self.bot.partial_emoji_gen(emoji_string=emoji), value=clan.tag))

                    select = disnake.ui.Select(
                        options=select_menu_options,
                        # the placeholder text to show when no options have been chosen
                        placeholder="Select Clans",
                        min_values=1,  # the minimum number of options a user must select
                        max_values=1,
                    )
                    await msg.edit(components=[disnake.ui.ActionRow(select)], content="Select Clan")
                    res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=res, msg=msg)
                    clan_tag = res.values[0]
                    (text, emoji) = await self.button_modal(self, res)
                    button = disnake.ui.Button(emoji=emoji, text=text, style=disnake.ButtonStyle.grey, custom_id=f"act_ephemeral_{self.bot.gen_season_date()}_{clan_tag}")
                    components.append(button.to_component_dict())
                    buttons = await self.generate_components(components=components, disable=True)
                    await ctx.edit_original_message(
                        content="**Use the buttons below to edit existing buttons or add new ones**", embed=panel,
                        components=buttons)


    async def button_modal(self, res: disnake.MessageInteraction):
        components = [
            disnake.ui.TextInput(
                label=f"Button Text",
                custom_id=f"text",
                required=True,
                style=disnake.TextInputStyle.short,
                min_length=2,
                max_length=20,
            ),
            disnake.ui.TextInput(
                label=f"Button Emoji",
                custom_id=f"emoji",
                required=False,
                style=disnake.TextInputStyle.short,
                max_length=25,
            )
        ]
        t_ = int(datetime.datetime.now().timestamp())
        await res.response.send_modal(
            title="Button Creator ",
            custom_id=f"buttoncreator-{t_}",
            components=components)

        def check(x: disnake.ModalInteraction):
            return res.author.id == x.author.id and x.custom_id == f"buttoncreator-{t_}"
        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            return None

        await modal_inter.response.defer()

        return (modal_inter.text_values["text"], modal_inter.text_values["emoji"])

    async def generate_components(self, components: list, disable=False):
        action_buttons = [[], [], [], [], []]
        row = 0
        for component in components:
            emoji = component.get("emoji")
            if emoji is not None:
                if emoji.get("id") is not None:
                    emoji = self.bot.partial_emoji_gen(f"<:{emoji.get('name')}:{emoji.get('id')}>")
                else:
                    emoji = emoji.get('name')
            style = {1: disnake.ButtonStyle.primary,
                     2: disnake.ButtonStyle.secondary,
                     3: disnake.ButtonStyle.success,
                     4: disnake.ButtonStyle.danger}
            do_disable = False
            if disable and component.get("custom_id") != "add_button":
                do_disable = True
            action_buttons[row].append(
                disnake.ui.Button(label=component.get("label"), emoji=emoji, style=style[component.get("style")],
                                  disabled=do_disable,
                                  custom_id=component.get("custom_id")))
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
        return all_buttons






def setup(bot):
    bot.add_cog(CustomBoards(bot))