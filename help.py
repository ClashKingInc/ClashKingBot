
from disnake.ext import commands
import disnake
from utils.components import create_components
from collections import defaultdict

family = ["Bans", "Clan Commands", "Family"]
war = ["War", "CWL"]
trophies = ["Legends", "Family Trophy Stats", "Leaderboards", "DM Feed & Reports"]
utility = ["Army", "Awards", "Super Troops", "Profile"]
link = ["Eval", "Linking"]
setups = ["Clan Setup", "Board Setup", "Eval Setup", "Statbar Setup", "Welcome Setup"]
settings = ["Settings"]
other = ["Other"]

pages = [family, trophies, war, utility, link, setups, settings, other]
page_names = ["Family_and_Clans", "Legends & Trophies", "War & CWL", "Utility", "Link & Eval", "Setups", "Settings", "Other"]

class help(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name='help', description="List of commands & descriptions for ClashKing")
    async def help(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        cog_dict = defaultdict(list)
        command_description = {}
        command_mentions = {}
        for command in self.bot.slash_commands:
            cog_name = command.cog_name
            base_command = command.name
            children = command.children
            if children != {}:
                for child in children:
                    command = children[child]
                    full_name = f"{base_command} {command.name}"
                    #for option in command.body.options:
                        #full_name += f" [{option.name}]"
                    cog_dict[cog_name].append(full_name)
                    desc = command.body.description
                    command_description[full_name] = desc
            else:
                desc = command.description
                #for option in command.body.options:
                    #base_command += f" [{option.name}]"
                command_description[base_command] = desc
                cog_dict[cog_name].append(base_command)

        embeds = []
        x = 0
        select_options = []
        for page in pages:
            select_options.append(disnake.SelectOption(label=page_names[x], emoji="⚙️", value=page_names[x]))
            embed = disnake.Embed(title=page_names[x],
                                  color=disnake.Color.green())
            embed.set_footer(text=f"{len(command_description)} commands")
            for cog in page:
                text = ""
                commands = cog_dict[cog]
                for command in commands:

                    description = command_description[command]
                    name = command.split(" ")[0]
                    command_ = self.bot.get_global_command_named(name=name)
                    if command_ is None:
                        continue
                    if len(text) + len(f"</{command}:{command_.id}>\n{description}\n") >= 1020:
                        embed.add_field(name=cog, value=text, inline=False)
                        text = ""
                    text+= f"</{command}:{command_.id}>\n{description}\n"
                embed.add_field(name=cog, value=text, inline=False)
            embeds.append(embed)
            x+=1

        select_options.append(disnake.SelectOption(label="Print", emoji="🖨️", value="Print"))
        select = disnake.ui.Select(
            options=select_options,
            placeholder="Help Modules",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.edit_original_message(embed=embeds[0], components=dropdown)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if res.values[0] == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)
            else:
                await res.response.edit_message(embed=embeds[page_names.index(res.values[0])])





def setup(bot: commands.Bot):
    bot.add_cog(help(bot))