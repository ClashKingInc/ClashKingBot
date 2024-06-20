from typing import TYPE_CHECKING, TYPE_CHECKINGfrom, import, typing

import disnake
import emoji as emoji_package
from disnake.ext import commands

from classes.bot import CustomClient
from utility.components import create_components


class Awards(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="award")
    async def award(self, ctx):
        pass

    @award.sub_command(name="give", description="Add a role and/or emoji to users in a given clan")
    async def award_give(self, ctx: disnake.ApplicationCommandInteraction, clan_tag, role:disnake.Role, emoji=None):
        """
            Parameters
            ----------
            clan_tag: clan_tag as found in-game
            role: role to give to people in clan
            emoji: (optional) emoji to award to people in clan
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan = await self.bot.getClan(clan_tag)
        if clan is None:
            return await ctx.send(f"{clan_tag} is not a valid clan_tag.")

        if emoji is not None:
            if not emoji_package.is_emoji(emoji):
                return await ctx.send(f"{emoji} is not a valid emoji (must be a default emoji, not discord/server emoji).")

        await ctx.response.defer()
        could_not = ""
        num = 0
        members_added = []
        text = ""
        embeds = []
        for player in clan.members:
            link = await self.bot.link_client.get_link(player.tag)
            if link is not None:
                if link not in members_added:
                    member = await self.bot.pingToMember(ctx, link)
                    if member is None:
                        continue
                    try:
                        if emoji is not None:
                            await member.edit(nick=f"{emoji}{member.display_name}")
                        await member.add_roles(role)
                        members_added.append(member.id)
                        text += f"{member.mention}\n"
                        num += 1
                        if num == 25:
                            if emoji is None:
                                embed = disnake.Embed(title=f"Award add for {role.mention} complete.",
                                                      description=text,
                                                      color=disnake.Color.green())
                            else:
                                embed = disnake.Embed(title=f"Award add for {emoji} complete.",
                                                      description=text,
                                                      color=disnake.Color.green())
                            embeds.append(embed)
                            text = ""
                            num = 0
                    except:
                       could_not+= f"{member.mention}\n"

        if text != "":
            if emoji is None:
                embed = disnake.Embed(title=f"Award add for {role.mention} complete.",
                                      description=text,
                                      color=disnake.Color.green())
            else:
                embed = disnake.Embed(title=f"Award add for {emoji} complete.",
                                      description=text,
                                      color=disnake.Color.green())
            embeds.append(embed)

        if embeds == []:
            text = "No awards to add."
            if emoji is None:
                embed = disnake.Embed(title=f"Award add for {role.mention} complete.",
                                      description=text,
                                      color=disnake.Color.green())
            else:
                embed = disnake.Embed(title=f"Award add for {emoji} complete.",
                                      description=text,
                                      color=disnake.Color.green())
            embeds.append(embed)



        if could_not != "":
            embed = disnake.Embed(title=f"Unable to update these members:",
                                  description=could_not,
                                  color=disnake.Color.green())
            embeds.insert(0, embed)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await ctx.edit_original_message(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)

    @award.sub_command(name="remove", description="Remove a role and/or emoji from users")
    async def award_remove(self, ctx: disnake.ApplicationCommandInteraction, role:disnake.Role, emoji: str=None, remove_role = commands.Param(default="True", choices=["True" , "False"])):
        """
            Parameters
            ----------
            role: role to clear the members of
            emoji: (optional) emoji to remove from members in this role
            remove_role: default is True
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        remove_role = (remove_role == "True")
        if emoji is not None:
            if not emoji_package.is_emoji(emoji):
                return await ctx.send(
                    f"{emoji} is not a valid emoji (must be a default emoji, not discord/server emoji).")

        await ctx.response.defer()
        could_not = ""
        num = 0
        members = role.members
        embeds = []
        text = ""
        for member in members:
            try:
                curr_name = member.display_name
                if emoji is not None:
                    remove_emoji = emoji_package.demojize(emoji)
                    curr_name = emoji_package.demojize(curr_name)
                    new_name = curr_name.replace(f"{remove_emoji}", "")
                    new_name = emoji_package.emojize(new_name)
                    await member.edit(nick=f"{new_name}")
                if remove_role:
                    await member.remove_roles(role)
                num += 1
                text += f"{member.mention}\n"
                num += 1
                if num == 25:
                    if emoji is None:
                        embed = disnake.Embed(title=f"Award removal for {role.mention} complete.",
                                              description=text,
                                              color=disnake.Color.green())
                    else:
                        embed = disnake.Embed(title=f"Award removal for {emoji} complete.",
                                              description=text,
                                              color=disnake.Color.green())
                    embeds.append(embed)
                    text = ""
                    num = 0
            except:
                could_not += f"{member.mention}\n"

        if text != "":
            if emoji is None:
                embed = disnake.Embed(title=f"Award removal for {role.mention} complete.",
                                      description=text,
                                      color=disnake.Color.green())
            else:
                embed = disnake.Embed(title=f"Award removal for {emoji} complete.",
                                      description=text,
                                      color=disnake.Color.green())
            embeds.append(embed)

        if embeds == []:
            text = "No awards to remove."
            if emoji is None:
                embed = disnake.Embed(title=f"Award removal for {role.mention} complete.",
                                      description=text,
                                      color=disnake.Color.green())
            else:
                embed = disnake.Embed(title=f"Award removal for {emoji} complete.",
                                      description=text,
                                      color=disnake.Color.green())
            embeds.append(embed)

        if could_not != "":
            embed = disnake.Embed(title=f"Unable to update these members:",
                                  description=could_not,
                                  color=disnake.Color.green())
            embeds.insert(0, embed)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)



    @award.sub_command(name="list", description="List users with a specific emoji in their nickname")
    async def award_list(self, ctx: disnake.ApplicationCommandInteraction, emoji):
        """
            Parameters
            ----------
            emoji: emoji to search for in nicknames (must be a valid default emoji)
        """

        emoji = emoji_package.emojize(emoji)
        if not emoji_package.is_emoji(emoji):
            return await ctx.send(
                f"{emoji} is not a valid emoji (must be a default emoji, not discord/server emoji).")

        await ctx.response.defer()
        members = ctx.guild.members
        embeds = []
        text = ""
        num = 0
        for member in members:
            if emoji in member.display_name:
                text += f"{member.display_name} | {member.mention}\n"
                num += 1
                if num == 25:
                    embed = disnake.Embed(title=f"{emoji} Award List:",
                                          description=text,
                                          color=disnake.Color.green())
                    embeds.append(embed)
                    text = ""
                    num = 0

        if text != "":
            embed = disnake.Embed(title=f"{emoji} Award List:",
                                  description=text,
                                  color=disnake.Color.green())
            embeds.append(embed)

        if embeds == []:
            text = "No emoji found in any nicknames"
            embed = disnake.Embed(title=f"{emoji} Award List:",
                                  description=text,
                                  color=disnake.Color.green())
            embeds.append(embed)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)



def setup(bot: CustomClient):
    bot.add_cog(Awards(bot))