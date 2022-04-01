import discord
from discord.ext import commands
from utils.clashClient import client, getClan
from coc import utils
import coc
from Dictionaries.emojiDictionary import emojiDictionary
from discord.ext.commands import CommandNotFound

from discord_slash.utils.manage_components import wait_for_component, create_select, create_select_option, create_actionrow

usafam = client.usafam
clans = usafam.clans


class family(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="family")
    async def family(self, ctx):
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")
        categoryTypesList = []
        categoryTypesList.append("All Clans")

        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if category not in categoryTypesList:
                categoryTypesList.append(category)

        embeds = []
        master_embed = discord.Embed(description=f"__**{ctx.guild.name} Clans**__",
                                     color=discord.Color.green())
        master_embed.set_thumbnail(url=ctx.guild.icon_url_as())
        for category in categoryTypesList:
            if category == "All Clans":
                continue
            text = ""
            other_text = ""

            results = clans.find({"$and": [
                {"category": category},
                {"server": ctx.guild.id}
            ]}).sort("name", 1)

            limit = await clans.count_documents(filter={"$and": [
                {"category": category},
                {"server": ctx.guild.id}
            ]})
            for result in await results.to_list(length=limit):
                tag = result.get("tag")
                alias = result.get("alias")
                print(tag)
                clan = await getClan(tag)
                leader = utils.get(clan.members, role=coc.Role.leader)
                text += f"[{clan.name}]({clan.share_link}) | ({clan.member_count}/50)\n" \
                        f"**Leader:** {leader.name}\n**Alias:** `{alias}`\n\n"
                other_text += f"{clan.name} | ({clan.member_count}/50)\n"

            embed = discord.Embed(title=f"__**{category} Clans**__",
                                  description=text,
                                  color=discord.Color.green())
            embed.set_thumbnail(url=ctx.guild.icon_url_as())
            master_embed.add_field(name=f"__**{category} Clans**__", value=other_text, inline=False)
            embeds.append(embed)

        embeds.append(master_embed)


        options = []
        for category in categoryTypesList:
            options.append(create_select_option(f"{category}", value=f"{category}"))

        select1 = create_select(
            options=options,
            placeholder="Choose clan category",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = create_actionrow(select1)


        msg = await ctx.reply(embed=embeds[len(embeds)-1], components=[action_row],
                       mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=action_row,
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()
            value = res.values[0]

            current_page = categoryTypesList.index(value)-1

            await msg.edit(embed=embeds[current_page],
                           components=[action_row])

    @commands.command(name='compo')
    async def thcomp(self, ctx, *, clan=None):
        clan_list = []
        is_all = False
        msg = None
        if clan is None:
            embed = discord.Embed(
                description=f"<a:loading:884400064313819146> Calculating TH Composition for {ctx.guild.name}.",
                color=discord.Color.green())
            msg = await ctx.reply(embed=embed, mention_author=False)
            is_all = True
            tracked = clans.find({"server": ctx.guild.id})
            limit = await clans.count_documents(filter={"server": ctx.guild.id})
            if limit == 0:
                return await ctx.send("Provide a clan tag please.")
            for tClan in await tracked.to_list(length=limit):
                tag = tClan.get("tag")
                clan = await getClan(tag)
                clan_list.append(clan)
        else:
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
            clan_list.append(clan)


        thcount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        total = 0
        sumth = 0

        for clan in clan_list:
            async for player in clan.get_detailed_members():
                th = player.town_hall
                sumth += th
                total += 1
                count = thcount[th - 1]
                thcount[th - 1] = count + 1

        stats = ""
        for x in reversed(range(len(thcount))):
            count = thcount[x]
            if count != 0:
                if (x + 1) <= 9:
                    th_emoji = emojiDictionary(x + 1)
                    stats += f"{th_emoji} `TH{x + 1} ` : {count}\n"
                else:
                    th_emoji = emojiDictionary(x + 1)
                    stats += f"{th_emoji} `TH{x + 1}` : {count}\n"

        average = round((sumth/total),2)
        if is_all:
            embed = discord.Embed(title=f"{ctx.guild.name} Townhall Composition", description=stats, color=discord.Color.green())
            embed.set_thumbnail(url=ctx.guild.icon_url_as())
            embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
            await msg.edit(embed=embed)
        else:
            embed = discord.Embed(title=f"{clan.name} Townhall Composition", description=stats, color=discord.Color.green())
            embed.set_thumbnail(url=clan.badge.large)
            embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
            await ctx.send(embed=embed)

    '''
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error : discord.DiscordServerError):
        if isinstance(error, CommandNotFound):
            return
        embed = discord.Embed(title='Exception in command {}'.format(ctx.command), description=str(error), color=discord.Color.red())
        await ctx.send(embed=embed)
    '''


def setup(bot: commands.Bot):
    bot.add_cog(family(bot))