import coc.utils
import contextlib
import disnake
from disnake.ext import commands
import emoji
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient
from Utils.components import create_components


class Check(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="check")
    async def check(self, ctx):
        pass

    @check.sub_command(name="search", description="Search a player's Legend Day by name or tag")
    async def check_search(self, ctx: disnake.ApplicationCommandInteraction, smart_search):
        """
            Parameters
            ----------
            smart_search: Type a search, pick an option, or don't to get multiple results back
        """
        await ctx.response.defer()

        tag = self.bot.parse_legend_search(smart_search)
        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Fetching Stats. | Searches of 10+ players may take a few seconds.",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)
        msg = await ctx.original_message()
        await self.legends(ctx=ctx, msg=msg, search_query=tag, ez_look=True)

    @check_search.autocomplete("smart_search")
    async def autocomp_names(self, ctx: disnake.ApplicationCommandInteraction, user_input: str):
        results = await self.bot.search_name_with_tag(user_input)
        return results

    @check.sub_command(name="user",
                       description="Check a discord user's Legend Day")
    async def check_user(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member = None):
        """
            Parameters
            ----------
            discord_user: Search by @discordUser
        """
        await ctx.response.defer()

        if discord_user is None:
            discord_user = str(ctx.author.id)
        else:
            discord_user = str(discord_user.id)

        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Fetching Stats. | Searches of 10+ players may take a few seconds.",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)
        msg = await ctx.original_message()
        await self.legends(ctx=ctx, msg=msg, search_query=discord_user, ez_look=True)



    async def legends(self, ctx, msg, search_query, ez_look):
        results = await self.bot.search_results(search_query)
        #track for them if not found
        if results == []:
            player: MyCustomPlayer = await self.bot.getPlayer(search_query, custom=True)
            if player is None:
                embed = disnake.Embed(
                    description="**No results found.**\nNot a valid player tag or name not found.",
                    color=disnake.Color.red())
                return await msg.edit(content=None, embed=embed)
            await player.track()
            embed = disnake.Embed(
                description=f"{player.name} now tracked. View stats with `/check search {player.tag}`.\n**Note:** Legends stats aren't given, so they have to be collected as they happen. Stats will appear from now & forward :)",
                color=disnake.Color.green())
            return await msg.edit(content=None, embed=embed)
        else:
            r = await self.bot.player_stats.find_one({"tag" : results[0]})
            if r is not None and r.get("paused") is True:
                await self.bot.player_stats.update_one({"tag": search_query}, {"$set": {"paused": False}})


        pagination = self.bot.get_cog("Legends")
        await pagination.button_pagination(msg, results, ez_look, ctx)

    @check.sub_command(name="clan", description="Check a clan's legend day results")
    async def check_clan(self, ctx: disnake.ApplicationCommandInteraction, smart_search: str):
        """
            Parameters
            ----------
            smart_search: Search for a clan by name or tag
        """

        await ctx.response.defer()
        clan = await self.bot.getClan(smart_search)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(
                description="Not a valid clan tag.",
                color=disnake.Color.red())
            return await ctx.edit_original_message(content=None, embed=embed)

        member_tags = [member.tag for member in clan.members]
        clan_members = await self.bot.get_players(tags=member_tags, custom=True)

        ranking = []
        for member in clan_members:
            member: MyCustomPlayer

            if not member.is_legends():
                continue

            if member.results is None:
                await member.track()

            name = emoji.get_emoji_regexp().sub('', member.name)
            legend_day = member.legend_day()
            ranking.append([name, member.trophy_start(), legend_day.attack_sum, legend_day.num_attacks.superscript, legend_day.defense_sum, legend_day.num_defenses.superscript, member.trophies])

        if not ranking:
            embed = disnake.Embed(
                description="No legend players in this clan",
                color=disnake.Color.red())
            return await ctx.edit_original_message(content=None, embed=embed)

        ranking = sorted(ranking, key=lambda l: l[6], reverse=True)
        embeds = await self.create_embed(ctx, ranking, clan)

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
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break
            await res.response.defer()
            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.edit_original_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.edit_original_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await res.edit_original_message(embeds=embeds, components=None)



    async def create_embed(self, ctx, ranking, results):
        text = ""
        embeds = []
        x = 0
        for player in ranking:
            name = player[0]
            hits = player[2]
            numHits = player[3]
            defs = player[4]
            numDefs = player[5]
            trophies = player[6]
            text += f"\u200e**<:trophyy:849144172698402817>{trophies} | \u200e{name}**\n➼ <:cw:948845649229647952> {hits}{numHits} <:sh:948845842809360424> {defs}{numDefs}\n"

            x += 1
            if x == 25:
                embed = disnake.Embed(title=f"__**{results.name}**__", description=text)
                embed.set_thumbnail(url=results.badge.large)
                x = 0
                embeds.append(embed)
                text = ""
        if text != "":
            embed = disnake.Embed(title=f"__**{results.name}**__", description=text)
            embed.set_thumbnail(url=results.badge.large)
            embeds.append(embed)
        if not embeds:
            embed = disnake.Embed(title=f"__**{results.name}**__", description="No players tracked in clan.")

            embed.set_thumbnail(url=results.badge.large)
            embeds.append(embed)
        return embeds

    @check_clan.autocomplete("smart_search")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if not clan_list and len(query) >= 3:
            if is_valid_tag := coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
                if clan is not None:
                    clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
            else:
                results = await self.bot.coc_client.search_clans(name=query, limit=5, min_members=5)
                for clan in results:
                    try:
                        location = clan.location
                    except Exception:
                        location = "No Location"
                    clan_list.append(f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {location} | {clan.tag}")

        return clan_list[:25]
