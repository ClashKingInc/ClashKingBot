import discord
from discord.ext import commands
from HelperMethods.clashClient import client, getPlayer, getClan, getTags, coc_client
import asyncio

from Dictionaries.emojiDictionary import emojiDictionary

from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component, create_select_option, create_select
from discord_slash.model import ButtonStyle

usafam = client.usafam
clans = usafam.clans
rosters = usafam.rosters


class Roster_Commands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="roster", pass_context=True, invoke_without_command=True)
    async def roster_co(self, ctx, *, alias=None):
        if alias==None:
            await ctx.send(f"Alias is a required argument. `{ctx.prefix}roster [alias]")
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
            "members": member_list[0],
            "clan" : member_list[1],
            "alias": alias
        })

        embed = discord.Embed(title=f"Roster ({alias}) successfully added.",
                              description=f"Alias: {alias}\n"
                                          f"Linked Clan: {member_list[1]}",
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())
        await roster.msg.edit(embed=embed)


    @roster_co.group(name="edit", pass_context=True, invoke_without_command=True)
    async def roster_edit(self, ctx, *, alias=None):
        if alias==None:
            await ctx.send(f"Alias is a required argument. `{ctx.prefix}roster edit [alias]")
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
        clan = await roster.linked_clan(alias, ctx.guild.id)

        embed = discord.Embed(title=f"{clan.name} Roster",
            description=text,
            color=discord.Color.green())

        stat_buttons = [
            create_button(label="Add", emoji="➕", custom_id="Add", style=ButtonStyle.green),
            create_button(label="Remove", emoji="➖", custom_id="Remove", style=ButtonStyle.red),
            create_button(label="Save", emoji="💾", custom_id="Save", style=ButtonStyle.grey)]
        buttons = create_actionrow(*stat_buttons)
        embed.set_footer(text=f"Currently in {mode} mode.")
        msg = await ctx.send(content="Use the buttons to switch between add or remove modes.\n"
                                     "**ADD** - Send PlayerTag or Mention player in chat to add to roster\n"
                                     "**REMOVE** - Send number on roster (i.e 15)\n"
                                     "**SAVE** - Save roster & get log of changes.\n"
                                     "**NOTE:** If its an invalid option for add or remove, the list will stay unchanged.",embed=embed, components=[buttons])



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
                        embed = discord.Embed(title=f"{clan.name} Roster",
                                              description=text,
                                              color=discord.Color.green())

                        embed.set_footer(text=f"Currently in {mode} mode.")
                        await msg.edit(embed=embed, components=[buttons])
                        continue
                    except:
                        pass

                    try:
                        ping = text_res.content
                        tags = await getTags(ctx, ping)
                        if tags == []:
                            continue
                        options = []
                        async for player in coc_client.get_players(tags):
                            emoji = emojiDictionary(player.town_hall)
                            emoji = emoji.split(":", 2)
                            emoji = emoji[2]
                            emoji = emoji[0:len(emoji) - 1]
                            emoji = self.bot.get_emoji(int(emoji))
                            emoji = discord.PartialEmoji(name=emoji.name, id=emoji.id)
                            options.append(create_select_option(f"{player.name}", value=f"{player.tag}", emoji=emoji))

                        select1 = create_select(
                            options=options,
                            placeholder="Choose player to add to roster.",
                            min_values=1,  # the minimum number of options a user must select
                            max_values=1  # the maximum number of options a user can select
                        )
                        action_row = create_actionrow(select1)

                        msg2 = await ctx.reply(content="Choose player to add to roster.", components=[action_row],
                                              mention_author=False)

                        value = None
                        while value == None:
                            try:
                                res = await wait_for_component(self.bot, components=action_row,
                                                               messages=msg2, timeout=600)
                            except:
                                await msg.edit(components=[])
                                break

                            if res.author_id != ctx.author.id:
                                await res.send(content="You must run the command to interact with components.",
                                               hidden=True)
                                continue

                            await res.edit_origin()
                            value = res.values[0]

                        await msg2.delete()
                        await roster.add_member(alias, ctx.guild.id, value)
                        player = await getPlayer(value)
                        added += f"[{player.name}]({player.share_link}) | {player.tag}\n"
                        text = await roster.create_member_list(alias, ctx.guild.id)
                        embed = discord.Embed(title=f"{clan.name} Roster",
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
                        embed = discord.Embed(title=f"{clan.name} Roster",
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
                embed = discord.Embed(title=f"{clan.name} Roster",
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
        embed = discord.Embed(title=f"**{ctx.guild} CWL Rosters List:**",
                              description=text,
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())
        await ctx.send(embed=embed)

    @roster_co.group(name="remove", pass_context=True, invoke_without_command=True)
    async def roster_remove(self, ctx, *, alias=None):
        if alias==None:
            await ctx.send(f"Alias is a required argument. `{ctx.prefix}roster remove [alias]")
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

    @roster_co.group(name="compare", pass_context=True, invoke_without_command=True)
    async def roster_remove(self, ctx, clan=None, *, alias=None):
        if clan==None or alias==None:
            await ctx.send(f"Alias and Clan are required arguments. `{ctx.prefix}roster compare [clan] [alias]")

        clan = clan.lower()
        results = await clans.find_one({"$and": [
            {"alias": clan},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(clan)

        if clan is None:
            return await ctx.reply("Not a valid clan tag.",
                                   mention_author=False)

        roster = self.bot.get_cog("Roster")
        valid_alias = await roster.is_valid_alias(alias, ctx.guild.id)
        if not valid_alias:
            embed = discord.Embed(
                description=f"A roster with that alias/name does not exist.\nUse `{ctx.prefix}roster list` to see server rosters & aliases.",
                color=discord.Color.red())
            return await ctx.send(embed=embed)

        members = await roster.fetch_members(alias, ctx.guild.id)

        clan_members = []
        for m in clan.members:
            clan_members.append(m.tag)

        not_present = ""
        for member in members:
            if member not in clan_members:
                member = await getPlayer(member)
                not_present += f"{member.name}\n"
        if not_present == "":
            not_present = "None"
        embed = discord.Embed(title=f"{clan.name} Roster/Clan Comparison",
            description=f"Missing Members:\n{not_present}",
            color=discord.Color.green())
        return await ctx.send(embed=embed)



def setup(bot: commands.Bot):
    bot.add_cog(Roster_Commands(bot))