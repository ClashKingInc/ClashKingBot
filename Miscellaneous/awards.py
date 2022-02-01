import discord
from discord.ext import commands
from HelperMethods.clashClient import client, getClan, pingToRole, link_client, pingToMember

from discord_slash.utils.manage_components import create_button, wait_for_component, create_actionrow
from discord_slash.model import ButtonStyle

import emoji

from main import check_commands

usafam = client.usafam
clans = usafam.clans
server = usafam.server

class awards(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.group(name="award", pass_context=True, invoke_without_command=True)
    async def award(self, ctx):
        prefix = ctx.prefix
        embed = discord.Embed(
            description=f"**{prefix}award list Emoji**\n"
                        "Lists users with a specific emoji in their nickname\n"
                        f"**{prefix}award give #CLANTAG Emoji <@GrantDiscordRole>**\n"
                        "Add an emoji in front of the users in a given clan.\n"
                        f"**{prefix}award remove Emoji <@RemoveDiscordRole>**\n"
                        "Remove an emoji in front of the users in a given role.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @award.group(name="give", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def award_give(self, ctx, clan_tag=None, emoji_given=None, disc_role=None):

        prefix = ctx.prefix
        if clan_tag == None:
            return await ctx.reply(f"Please provide a clan_tag.\n`{prefix}award give #CLANTAG Emoji <@GrantDiscordRole>`")
        elif emoji_given== None:
            return await ctx.reply(f"Please provide an emoji.\n`{prefix}award give #CLANTAG Emoji <@GrantDiscordRole>`")
        elif disc_role == None:
            return await ctx.reply(f"Please provide a role.\n`{prefix}award give #CLANTAG Emoji <@GrantDiscordRole>`")

        clan = await getClan(clan_tag)
        if clan == None:
            return await ctx.reply(f"{clan_tag} is not a valid clan_tag.")

        if not emoji.is_emoji(emoji_given):
            return await ctx.reply(f"{emoji_given} is not a valid emoji (must be a default emoji, not discord/server emoji).")

        role = await pingToRole(ctx,disc_role)
        if role == None:
            return await ctx.reply(f"{disc_role} is not a valid role.")

        could_not = ""
        num = 0
        members_added = []
        text = ""
        embeds = []
        for player in clan.members:
            link = await link_client.get_link(player.tag)
            print(link)
            if link != None:
                if link not in members_added:
                    member = await pingToMember(ctx, link)
                    if member == None:
                        continue
                    try:
                        await member.edit(nick=f"{emoji_given}{member.display_name}")
                        await member.add_roles(role)
                        members_added.append(member.id)
                        text += f"{member.mention}\n"
                        num += 1
                        if num == 25:
                            embed = discord.Embed(title=f"Award add for {emoji_given} complete.",
                                                  description=text,
                                                  color=discord.Color.green())
                            embeds.append(embed)
                            text = ""
                            num = 0
                    except:
                       could_not+= f"{member.mention}\n"

        if text != "":
            embed = discord.Embed(title=f"Award add for {emoji_given} complete.",
                                  description=text,
                                  color=discord.Color.green())
            embeds.append(embed)

        if embeds == []:
            text = "No awards to add."
            embed = discord.Embed(title=f"Award add for {emoji_given} complete.",
                                  description=text,
                                  color=discord.Color.green())
            embeds.append(embed)



        if could_not != "":
            embed = discord.Embed(title=f"Unable to update these members:",
                                  description=could_not,
                                  color=discord.Color.green())
            embeds.insert(0, embed)

        current_page = 0
        limit = len(embeds)
        msg = await ctx.send(embed=embeds[0], components=self.create_components(current_page, limit),
                       mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=self.create_components(current_page, limit),
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()

            # print(res.custom_id)
            if res.custom_id == "Previous":
                current_page -= 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

    @award.group(name="remove", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def award_remove(self, ctx, emoji_given=None, disc_role=None):

        prefix = ctx.prefix
        if emoji_given == None:
            return await ctx.reply(f"Please provide an emoji.\n`{prefix}award remove Emoji <@RemoveDiscordRole>`")
        elif disc_role == None:
            return await ctx.reply(f"Please provide a role.\n`{prefix}award remove Emoji <@RemoveDiscordRole>`")

        if not emoji.is_emoji(emoji_given):
            return await ctx.reply(
                f"{emoji_given} is not a valid emoji (must be a default emoji, not discord/server emoji).")

        role = await pingToRole(ctx, disc_role)
        if role == None:
            return await ctx.reply(f"{disc_role} is not a valid role.")

        could_not = ""
        num = 0
        members_added = []
        members = ctx.guild.members
        embeds = []
        text = ""
        for member in members:
            if (emoji_given in member.display_name) and (member.id not in members_added):
                try:
                    curr_name = member.display_name
                    new_name = curr_name.replace(f"{emoji_given}", "")
                    await member.edit(nick=f"{new_name}")
                    await member.remove_roles(role)
                    members_added.append(member.id)
                    num += 1
                    text += f"{member.mention}\n"
                    num += 1
                    if num == 25:
                        embed = discord.Embed(title=f"Award add for {emoji_given} complete.",
                                              description=text,
                                              color=discord.Color.green())
                        embeds.append(embed)
                        text = ""
                        num = 0
                except:
                    could_not += f"{member.mention}\n"

        if text != "":
            embed = discord.Embed(title=f"Award remove for {emoji_given} complete.",
                                  description=text,
                                  color=discord.Color.green())
            embeds.append(embed)

        if embeds == []:
            text = "No awards to remove."
            embed = discord.Embed(title=f"Award remove for {emoji_given} complete.",
                                  description=text,
                                  color=discord.Color.green())
            embeds.append(embed)

        if could_not != "":
            embed = discord.Embed(title=f"Unable to update these members:",
                                  description=could_not,
                                  color=discord.Color.green())
            embeds.insert(0, embed)

        current_page = 0
        limit = len(embeds)
        msg = await ctx.send(embed=embeds[0], components=self.create_components(current_page, limit),
                             mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=self.create_components(current_page, limit),
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()

            # print(res.custom_id)
            if res.custom_id == "Previous":
                current_page -= 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))




    @award.group(name="list", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def award_list(self, ctx, emoji_given=None):

        prefix = ctx.prefix
        if emoji_given == None:
            return await ctx.reply(f"Please provide an emoji.\n`{prefix}award list Emoji`")

        if not emoji.is_emoji(emoji_given):
            return await ctx.reply(
                f"{emoji_given} is not a valid emoji (must be a default emoji, not discord/server emoji).")

        members = ctx.guild.members
        embeds = []
        text = ""
        num = 0
        for member in members:
            if emoji_given in member.display_name:
                text += f"{member.display_name} | {member.mention}\n"
                num += 1
                if num == 25:
                    embed = discord.Embed(title=f"{emoji_given} Award List:",
                                          description=text,
                                          color=discord.Color.green())
                    embeds.append(embed)
                    text = ""
                    num = 0

        if text != "":
            embed = discord.Embed(title=f"{emoji_given} Award List:",
                                  description=text,
                                  color=discord.Color.green())
            embeds.append(embed)

        if embeds == []:
            text = "No ward found."
            embed = discord.Embed(title=f"{emoji_given} Award List:",
                                  description=text,
                                  color=discord.Color.green())
            embeds.append(embed)

        current_page = 0
        limit = len(embeds)
        msg = await ctx.send(embed=embeds[0], components=self.create_components(current_page, limit),
                             mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=self.create_components(current_page, limit),
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()

            # print(res.custom_id)
            if res.custom_id == "Previous":
                current_page -= 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))


    def create_components(self, current_page, limit):
        length = limit
        if length == 1:
            return []

        page_buttons = [create_button(label="", emoji="◀️", style=ButtonStyle.blue, disabled=(current_page == 0),
                                      custom_id="Previous"),
                        create_button(label=f"Page {current_page + 1}/{length}", style=ButtonStyle.grey,
                                      disabled=True),
                        create_button(label="", emoji="▶️", style=ButtonStyle.blue,
                                      disabled=(current_page == length - 1), custom_id="Next")]
        page_buttons = create_actionrow(*page_buttons)

        return [page_buttons]



def setup(bot: commands.Bot):
    bot.add_cog(awards(bot))