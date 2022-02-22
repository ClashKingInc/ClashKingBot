
from discord.ext import commands
from HelperMethods.clashClient import getPlayer, client, pingToChannel
import discord

from datetime import datetime

from discord_slash.utils.manage_components import create_button, wait_for_component, create_actionrow
from discord_slash.model import ButtonStyle

from main import check_commands

usafam = client.usafam
banlist = usafam.banlist
server = usafam.server


class banlists(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name='banlist', pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def banlisted(self, ctx):

        embed = discord.Embed(
            description="<a:loading:884400064313819146> Fetching banned players.",
            color=discord.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)

        embeds = await self.create_embeds(ctx)
        if embeds == []:
            embed = discord.Embed(
                description="No banned players on this server.",
                color=discord.Color.green())
            return await msg.edit(embed=embed, mention_author=False)


        current_page = 0
        limit = len(embeds)
        await msg.edit(embed=embeds[0], components=self.create_components(current_page, limit),
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

            elif res.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)




    @banlisted.group(name= "add", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def banlist_add(self, ctx, tag, *, notes="None"):

        player = await getPlayer(tag)

        if player is None:
            embed = discord.Embed(description=f"{tag} is not a valid player tag.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        results = await banlist.find_one({"$and": [
            {"VillageTag": player.tag},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            embed = discord.Embed(description=f"{player.name} is already banned on this server.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        now = datetime.now()
        # dd/mm/YY H:M:S
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")


        await banlist.insert_one({
            "VillageTag": player.tag,
            "DateCreated": dt_string,
            "Notes": notes,
            "server": ctx.guild.id
        })
        embed2 = discord.Embed(description=f"[{player.name}]({player.share_link}) added to the banlist by {ctx.message.author.mention}.\n"
                                          f"Notes: {notes}",
                              color=discord.Color.green())
        await ctx.send(embed=embed2)

        results = await server.find_one({"server": ctx.guild.id})
        banChannel = results.get("banlist")
        channel = await pingToChannel(ctx,banChannel)

        if channel is not None:
            x = 0
            async for message in channel.history(limit=None):
                await message.delete()
                x += 1
                if x == 100:
                    break
            embeds = await self.create_embeds(ctx)
            for embed in embeds:
                await channel.send(embed=embed)
            await channel.send(embed=embed2)


    @banlisted.group(name="remove", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def banlist_remove(self, ctx, tag):
        player = await getPlayer(tag)

        if player is None:
            embed = discord.Embed(description=f"{tag} is not a valid player tag.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        results = await banlist.find_one({"$and": [
            {"VillageTag": player.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = discord.Embed(description=f"{player.name} is not banned on this server.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        await banlist.find_one_and_delete({"$and": [
            {"VillageTag": player.tag},
            {"server": ctx.guild.id}
        ]})

        embed2 = discord.Embed(description=f"[{player.name}]({player.share_link}) removed from the banlist by {ctx.message.author.mention}.",
                              color=discord.Color.green())
        await ctx.send(embed=embed2)

        results = await server.find_one({"server": ctx.guild.id})
        banChannel = results.get("banlist")
        channel = await pingToChannel(ctx, banChannel)
        if channel is not None:
            async for message in channel.history(limit=None):
                await message.delete()
            embeds = await self.create_embeds(ctx)
            for embed in embeds:
                await channel.send(embed=embed)
            await channel.send(embed=embed2)

    async def create_embeds(self, ctx):
        text = []
        hold = ""
        num = 0
        all = banlist.find({"server": ctx.guild.id}).sort("DateCreated", 1)
        limit = await banlist.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return []

        for ban in await all.to_list(length=limit):
            tag = ban.get("VillageTag")
            player = await getPlayer(tag)
            if player is None:
                continue
            name = player.name
            # name = name.replace('*', '')
            date = ban.get("DateCreated")
            date = date[0:10]
            notes = ban.get("Notes")
            if notes == "":
                notes = "No Notes"
            clan = ""
            try:
                clan = player.clan.name
                clan = f"{clan}, {str(player.role)}"
            except:
                clan = "No Clan"
            hold += f"[{name}]({player.share_link}) | {player.tag}\n" \
                    f"{clan}\n" \
                    f"Added on: {date}\n" \
                    f"*{notes}*\n\n"
            num += 1
            if num == 10:
                text.append(hold)
                hold = ""
                num = 0

        if num != 0:
            text.append(hold)

        embeds = []
        for t in text:
            embed = discord.Embed(title=f"{ctx.guild.name} Ban List",
                                  description=t,
                                  color=discord.Color.green())
            embed.set_thumbnail(url=ctx.guild.icon_url_as())
            embeds.append(embed)

        return embeds

    def create_components(self, current_page, length):
        if length == 1:
            return []

        page_buttons = [create_button(label="", emoji="◀️", style=ButtonStyle.blue, disabled=(current_page == 0),
                                      custom_id="Previous"),
                        create_button(label=f"Page {current_page + 1}/{length}", style=ButtonStyle.grey,
                                      disabled=True),
                        create_button(label="", emoji="▶️", style=ButtonStyle.blue,
                                      disabled=(current_page == length - 1), custom_id="Next"),
                        create_button(label="", emoji="🖨️", style=ButtonStyle.grey,
                                       custom_id="Print")
                        ]
        page_buttons = create_actionrow(*page_buttons)

        return [page_buttons]



def setup(bot: commands.Bot):
    bot.add_cog(banlists(bot))