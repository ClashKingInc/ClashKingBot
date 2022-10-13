import disnake
from disnake.ext import commands
from coc import utils
import coc
from Dictionaries.emojiDictionary import emojiDictionary
from CustomClasses.CustomBot import CustomClient
from collections import defaultdict

class Family(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="family")
    async def family(self, ctx):
        pass

    @family.sub_command(name="clans", description="List of family clans")
    async def family_clan(self, ctx: disnake.ApplicationCommandInteraction):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")
        categoryTypesList = []
        categoryTypesList.append("All Clans")

        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if category not in categoryTypesList:
                categoryTypesList.append(category)

        embeds = []
        master_embed = disnake.Embed(description=f"__**{ctx.guild.name} Clans**__",
                                     color=disnake.Color.green())
        if ctx.guild.icon is not None:
            master_embed.set_thumbnail(url=ctx.guild.icon.url)
        for category in categoryTypesList:
            if category == "All Clans":
                continue
            text = ""
            other_text = ""

            results = self.bot.clan_db.find({"$and": [
                {"category": category},
                {"server": ctx.guild.id}
            ]}).sort("name", 1)

            limit = await self.bot.clan_db.count_documents(filter={"$and": [
                {"category": category},
                {"server": ctx.guild.id}
            ]})
            for result in await results.to_list(length=limit):
                tag = result.get("tag")
                clan = await self.bot.getClan(tag)
                try:
                    leader = utils.get(clan.members, role=coc.Role.leader)
                except:
                    continue
                if clan is None:
                    continue
                if clan.member_count == 0:
                    continue
                text += f"[{clan.name}]({clan.share_link}) | ({clan.member_count}/50)\n" \
                        f"**Leader:** {leader.name}\n\n"
                other_text += f"{clan.name} | ({clan.member_count}/50)\n"

            embed = disnake.Embed(title=f"__**{category} Clans**__",
                                  description=text,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            master_embed.add_field(name=f"__**{category} Clans**__", value=other_text, inline=False)
            embeds.append(embed)

        embeds.append(master_embed)


        options = []
        for category in categoryTypesList:
            options.append(disnake.SelectOption(label=f"{category}", value=f"{category}"))

        select1 = disnake.ui.Select(
            options=options,
            placeholder="Choose clan category",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = disnake.ui.ActionRow()
        action_row.append_item(select1)

        await ctx.send(embed=embeds[len(embeds)-1], components=[action_row])

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

            if res.author.id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", ephemeral=True)
                continue

            value = res.values[0]

            current_page = categoryTypesList.index(value)-1

            await res.response.edit_message(embed=embeds[current_page])

    @family.sub_command(name='compo', description="Compo of an individual clan or all server clans if left blank")
    async def thcomp(self, ctx: disnake.ApplicationCommandInteraction, clan:str=None):
        """
            Parameters
            ----------
            clan: clan to calculate th composition of [alias or tag], if blank does all server clans
        """

        clan_list = []
        is_all = False
        await ctx.response.defer()

        if clan is None:
            embed = disnake.Embed(
                description=f"<a:loading:884400064313819146> Calculating TH Composition for {ctx.guild.name}.",
                color=disnake.Color.green())
            await ctx.edit_original_message(embed=embed)
            is_all = True
            tracked = self.bot.clan_db.find({"server": ctx.guild.id})
            limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
            if limit == 0:
                return await ctx.edit_original_message(content="Provide a clan tag please.", embed=None)
            for tClan in await tracked.to_list(length=limit):
                tag = tClan.get("tag")
                clan = await self.bot.getClan(tag)
                clan_list.append(clan)
        else:
            clan = clan.lower()
            results = await self.bot.clan_db.find_one({"$and": [
                {"alias": clan},
                {"server": ctx.guild.id}
            ]})

            if results is not None:
                tag = results.get("tag")
                clan = await self.bot.getClan(tag)
            else:
                clan = await self.bot.getClan(clan)

            if clan is None:
                return await ctx.send("Not a valid clan tag.")
            clan_list.append(clan)


        thcount = defaultdict(int)
        total = 0
        sumth = 0


        clan_members = []
        for clan in clan_list:
            clan = await self.bot.getClan(clan.tag)
            clan_members += [member.tag for member in clan.members]
        list_members = await self.bot.get_players(tags=clan_members, custom=False)
        for player in list_members:
            th = player.town_hall
            sumth += th
            total += 1
            thcount[th] += 1

        stats = ""
        for th_level, th_count in thcount.items():
            if (th_level) <= 9:
                th_emoji = emojiDictionary(th_level)
                stats += f"{th_emoji} `TH{th_level} ` : {th_count}\n"
            else:
                th_emoji = emojiDictionary(th_level)
                stats += f"{th_emoji} `TH{th_level}` : {th_count}\n"

        average = round((sumth/total),2)
        if is_all:
            embed = disnake.Embed(title=f"{ctx.guild.name} Townhall Composition", description=stats, color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
            await ctx.edit_original_message(embed=embed)
        else:
            embed = disnake.Embed(title=f"{clan.name} Townhall Composition", description=stats, color=disnake.Color.green())
            embed.set_thumbnail(url=clan.badge.large)
            embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
            await ctx.edit_original_message(embed=embed)

def setup(bot: CustomClient):
    bot.add_cog(Family(bot))