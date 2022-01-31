import discord
from discord.ext import commands
from HelperMethods.clashClient import client, getPlayer
import asyncio

from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

usafam = client.usafam
clans = usafam.clans
rosters = usafam.rosters


class Roster_Commands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="roster", pass_context=True, invoke_without_command=True)
    async def roster_co(self, ctx, *, alias):
        roster = self.bot.get_cog("Roster")
        valid_alias = await roster.is_valid_alias(alias, ctx.guild.id)
        if not valid_alias:
            embed = discord.Embed(description=f"A roster with that alias/name does not exist.\nUse `{ctx.prefix}roster list` to see server rosters & aliases.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        embeds = await roster.create_roster_embeds(alias, ctx.guild.id)
        for embed in embeds:
            await ctx.send(embed=embed)


    @roster_co.group(name="create", pass_context=True, invoke_without_command=True)
    async def roster_create(self, ctx):

        roster = self.bot.get_cog("Roster")
        member_list = await roster.get_members(ctx)
        if member_list == None:
            return
        alias = await roster.get_alias(ctx)
        if alias == None:
            return

        await rosters.insert_one({
            "server": ctx.guild.id,
            "members": member_list,
            "alias": alias
        })

        clans = roster.clans
        clans = ", ".join(clans)
        embed = discord.Embed(title=f"Roster ({alias}) successfully added.",
                              description=f"Alias: {alias}\n"
                                          f"Clans: {clans}",
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())
        await roster.msg.edit(embed=embed)


    @roster_co.group(name="edit", pass_context=True, invoke_without_command=True)
    async def roster_edit(self, ctx, *, alias):

        added = ""
        removed = ""
        mode = "Add"
        roster = self.bot.get_cog("Roster")
        valid_alias = await roster.is_valid_alias(alias, ctx.guild.id)
        if not valid_alias:
            embed = discord.Embed(
                description=f"A roster with that alias/name does not exist.\nUse `{ctx.prefix}roster list` to see server rosters & aliases.",
                color=discord.Color.red())
            return await ctx.send(embed=embed)

        text = await roster.create_member_list(alias, ctx.guild.id)

        embed = discord.Embed(title=f"{alias} Roster",
            description=text,
            color=discord.Color.green())

        stat_buttons = [
            create_button(label="Add", emoji="➕", custom_id="Add", style=ButtonStyle.green),
            create_button(label="Remove", emoji="➖", custom_id="Remove", style=ButtonStyle.red),
            create_button(label="Save", emoji="💾", custom_id="Save", style=ButtonStyle.grey)]
        buttons = create_actionrow(*stat_buttons)
        embed.set_footer(text=f"Currently in {mode} mode.")
        msg = await ctx.send(content="Use the buttons to switch between add or remove modes.\n"
                                     "**ADD** - Send PlayerTag in chat to add to roster\n"
                                     "**REMOVE** - Send PlayerTag **or** number on roster (i.e 15)\n"
                                     "**SAVE** - Save roster & get log of changes.",embed=embed, components=[buttons])



        while True:
            def check(res):
                return res.author_id == ctx.message.author.id

            def check2(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == ctx.message.author and message.channel == ctx.message.channel

            try:
                button = wait_for_component(self.bot, components=[buttons],messages=msg, timeout=600, check=check)
                text_res = self.bot.wait_for('message', check=check2, timeout=300)
            except:
                return await msg.edit(components=[])


            button = asyncio.create_task(button)
            text_res = asyncio.create_task(text_res)

            tasks = [button, text_res]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            if text_res in done:
                text_res = await text_res
                await text_res.delete()
                if mode == "Add":
                    try:
                        tag = text_res.content
                        player = await getPlayer(tag)
                        tag = player.tag
                        await roster.add_member(alias, ctx.guild.id, tag)
                        added += f"[{player.name}]({player.share_link}) | {player.tag}\n"
                        text = await roster.create_member_list(alias, ctx.guild.id)
                        embed = discord.Embed(title=f"{alias} Roster",
                                              description=text,
                                              color=discord.Color.green())

                        embed.set_footer(text=f"Currently in {mode} mode.")
                        await msg.edit(embed=embed, components=[buttons])
                        continue
                    except:
                        pass


                elif mode == "Remove":
                    try:
                        num = int(text_res.content)
                        member_list = await roster.fetch_members(alias, ctx.guild.id)
                        tag = member_list[num-1]
                        await roster.remove_member(alias,ctx.guild.id, tag)
                        player = await getPlayer(tag)
                        removed+= f"[{player.name}]({player.share_link}) | {player.tag}\n"
                        text = await roster.create_member_list(alias, ctx.guild.id)
                        embed = discord.Embed(title=f"{alias} Roster",
                                              description=text,
                                              color=discord.Color.green())

                        embed.set_footer(text=f"Currently in {mode} mode.")
                        await msg.edit(embed=embed, components=[buttons])
                        continue
                    except:
                        pass

                    try:
                        tag = text_res.content
                        player = await getPlayer(tag)
                        tag = player.tag
                        await roster.remove_member(alias, ctx.guild.id, tag)
                        removed+=f"[{player.name}]({player.share_link}) | {player.tag}\n"
                        text = await roster.create_member_list(alias, ctx.guild.id)
                        embed = discord.Embed(title=f"{alias} Roster",
                                              description=text,
                                              color=discord.Color.green())

                        embed.set_footer(text=f"Currently in {mode} mode.")
                        await msg.edit(embed=embed, components=[buttons])
                        continue
                    except:
                        pass

            elif button in done:
                button = await button
                #print("here2")
                await button.edit_origin()
                mode = button.custom_id
                text = await roster.create_member_list(alias, ctx.guild.id)
                embed = discord.Embed(title=f"{alias} Roster",
                                      description=text,
                                      color=discord.Color.green())

                embed.set_footer(text=f"Currently in {mode} mode.")
                await msg.edit(embed=embed, components=[buttons])
                if mode == "Save":
                    embed.set_footer(text="Roster Saved")
                    if added == "":
                        added = "None"
                    if removed == "":
                        removed = "None"
                    embed2 = discord.Embed(title="Changes Made:",
                        description=f"Players added:\n{added}\nPlayers Removed:\n{removed}",
                        color=discord.Color.green())
                    await ctx.reply(embed=embed2, mention_author=False)
                    return await msg.edit(embed =embed,components=[])


    @roster_co.group(name="list", pass_context=True, invoke_without_command=True)
    async def roster_list(self, ctx):
        roster = self.bot.get_cog("Roster")
        text = await roster.create_alias_list(ctx.guild.id)
        embed = discord.Embed(title=f"**{ctx.guild} Roster List:**",
                              description=text,
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())
        await ctx.send(embed=embed)

    @roster_co.group(name="remove", pass_context=True, invoke_without_command=True)
    async def roster_remove(self, ctx, *, alias):
        roster = self.bot.get_cog("Roster")
        valid_alias = await roster.is_valid_alias(alias, ctx.guild.id)
        if not valid_alias:
            embed = discord.Embed(
                description=f"A roster with that alias/name does not exist.\nUse `{ctx.prefix}roster list` to see server rosters & aliases.",
                color=discord.Color.red())
            return await ctx.send(embed=embed)

        await rosters.find_one_and_delete({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]})

        embed = discord.Embed(description=f"{alias} Roster Removed",
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())
        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Roster_Commands(bot))