import math

import disnake
from disnake.ext import commands

from assets.thPicDictionary import thDictionary
from classes.bot import CustomClient
from classes.player.stats import LegendRanking
from exceptions.CustomExceptions import ExpiredComponents, NoLinkedAccounts
from utility.components import create_components
from utility.general import create_superscript
from utility.search import search_results


class FamilyStats(commands.Cog, name='Family Trophy Stats'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='ranked')
    async def ranked(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

    @commands.slash_command(name='rank', description='Ranks for player')
    async def player_rank(self, ctx: disnake.ApplicationCommandInteraction, user: disnake.User):
        """
        Parameters
        ----------
        tag_or_user: Player tag or discord user to search for
        """
        await ctx.response.defer()
        tags = await self.bot.get_tags(user.id)
        players = await self.bot.get_players(tags=tags, custom=False)
        if not players:
            raise NoLinkedAccounts
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)

        rr = {}
        clan_tags = await self.bot.clan_db.distinct('tag', filter={'server': ctx.guild.id})
        clans = await self.bot.get_clans(tags=clan_tags)
        for clan in clans:
            for player in clan.members:
                rr[player.tag] = player.trophies

        rr = {key: rank for rank, key in enumerate(sorted(rr, key=rr.get, reverse=True), 1)}

        leaderboard_rankings = await self.bot.leaderboard_db.find({'tag': {'$in': tags}}).to_list(length=None)
        leaderboard_rankings = {r.get('tag'): r for r in leaderboard_rankings}

        players.sort(key=lambda x: rr.get(x.tag, 10000))
        embeds = []
        for player in players:
            ranking = LegendRanking(leaderboard_rankings.get(player.tag))

            server_ranking = rr.get(player.tag, f'<:status_offline:910938138984206347>')

            clan = player.clan.name if player.clan else 'None'

            embed = disnake.Embed(
                description=f'Name: {player.name}\n' + f'Tag: {player.tag}\n' + f'Clan: {clan}\n' + f'Trophies: {player.trophies}\n'
                f'{ctx.guild.name} : {server_ranking}\n'
                f'Rank: <a:earth:861321402909327370> {ranking.global_ranking} | {ranking.flag} {ranking.local_ranking}\n'
                + f'Country: {ranking.country}',
                color=embed_color,
            )
            embed.set_footer(text=f'Ranks for {user.display_name}', icon_url=user.display_avatar.url)
            embed.set_thumbnail(url=thDictionary(player.town_hall))
            embeds.append(embed)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds))

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
            except Exception:
                raise ExpiredComponents

            if res.data.custom_id == 'Previous':
                current_page -= 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds),
                )

            elif res.data.custom_id == 'Next':
                current_page += 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds),
                )

    @ranked.sub_command(
        name='best',
        description='Arranges players to create best 5 clans if eos was now',
    )
    async def ranked_best(self, ctx: disnake.ApplicationCommandInteraction):
        rankings = []
        tracked = self.bot.clan_db.find({'server': ctx.guild.id})
        l = await self.bot.clan_db.count_documents(filter={'server': ctx.guild.id})
        for clan in await tracked.to_list(length=l):
            tag = clan.get('tag')
            clan = await self.bot.getClan(tag)
            if clan is None:
                continue
            for player in clan.members:
                try:
                    playerStats = []
                    playerStats.append(player.name)
                    playerStats.append(player.trophies)
                    playerStats.append(player.clan.name)
                    playerStats.append(player.tag)
                    rankings.append(playerStats)
                except:
                    continue

        if l == 0:
            return await ctx.send(content=f'No clans linked to server.')

        ranking = sorted(rankings, key=lambda l: l[1], reverse=True)

        max_clans = math.floor(len(ranking) / 50)
        if max_clans > 5:
            max_clans = 5
        text = ''
        clan_num = 0
        for y in range(clan_num, max_clans):
            cum_score = 0
            z = 1
            tt = ranking[(50 * y) : ((50 * y) + 50)]
            for r in tt:
                if z >= 1 and z <= 10:
                    cum_score += (r[1]) * 0.50
                elif z >= 11 and z <= 20:
                    cum_score += (r[1]) * 0.25
                elif z >= 21 and z <= 30:
                    cum_score += (r[1]) * 0.12
                elif z >= 31 and z <= 40:
                    cum_score += (r[1]) * 0.10
                elif z >= 41 and z <= 50:
                    cum_score += (r[1]) * 0.03
                z += 1

            cum_score = int(cum_score)
            cum_score = '{:,}'.format(cum_score)
            text += f'Clan #{y + 1}: 🏆{cum_score}\n'

        embed = disnake.Embed(
            title=f'Best Possible EOS for {ctx.guild.name}',
            description=text,
            color=disnake.Color.green(),
        )
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text='All Clans have 50 Members')
        await ctx.edit_original_message(embed=embed)

    @ranked.sub_command(name='players', description='Region rankings for players on server')
    async def ranked_players(self, ctx: disnake.ApplicationCommandInteraction):
        server_players = {}
        names = {}
        trophies = {}
        tracked = self.bot.clan_db.find({'server': ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={'server': ctx.guild.id})
        tags = []
        for clan in await tracked.to_list(length=limit):
            tag = clan.get('tag')
            tags.append(tag)

        async for clan in self.bot.coc_client.get_clans(tags):
            for player in clan.members:
                try:
                    server_players[player.tag] = player.trophies
                    trophies[player.tag] = player.trophies
                    names[player.tag] = player.name
                except:
                    continue

        sorted(server_players, key=server_players.get, reverse=True)
        server_players = {key: rank for rank, key in enumerate(sorted(server_players, key=server_players.get, reverse=True), 1)}
        server_players_list = list(server_players.keys())

        embeds = []
        num = 0
        text = ''
        # [loc, rank, country, clantag, clanname, trophies, playername]
        for tag in server_players_list:
            result_ranking = await self.bot.leaderboard_db.find_one({'tag': tag})
            ranking = LegendRanking(result_ranking)
            if ranking.global_ranking != '<:status_offline:910938138984206347>':
                num += 1
                text += f'<:trophy:956417881778815016>`{trophies[tag]}` | <a:earth:861321402909327370> `{ranking.global_ranking}` | {names[tag]}\n'

            if ranking.local_ranking != '<:status_offline:910938138984206347>':
                num += 1
                text += f'<:trophy:956417881778815016>`{trophies[tag]}` | {ranking.flag} {ranking.country} | {names[tag]}\n'

            if num == 25:
                embed = disnake.Embed(
                    title=f'**{ctx.guild.name} Player Country LB Rankings**',
                    description=text,
                )
                embeds.append(embed)
                num = 0
                text = ''

        if text != '':
            embed = disnake.Embed(
                title=f'**{ctx.guild.name} Player Country LB Rankings**',
                description=text,
            )
            embeds.append(embed)

        if embeds == []:
            return await ctx.edit_original_message(content='No ranked players on this server.')
        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
            except:
                await msg.edit(components=[])
                break

            await res.response.defer()
            if res.data.custom_id == 'Previous':
                current_page -= 1
                await res.edit_original_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == 'Next':
                current_page += 1
                await res.edit_original_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == 'Print':
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)

    @ranked.sub_command(name='clans', description='Region rankings for clans on server')
    async def ranked_clans(self, ctx: disnake.ApplicationCommandInteraction):
        server_clans = []
        tracked = self.bot.clan_db.find({'server': ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={'server': ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get('tag')
            server_clans.append(tag)

        num = 0
        text = ''
        for tag in server_clans:
            result_ranking = await self.bot.clan_leaderboard_db.find_one({'tag': tag})
            ranking = LegendRanking(result_ranking)

            clan = None
            if ranking.global_ranking != '<:status_offline:910938138984206347>':
                num += 1
                clan = await self.bot.getClan(tag)
                text += f'<a:earth:861321402909327370> `{ranking.global_ranking}` | {clan.name}\n'

            if ranking.local_ranking != '<:status_offline:910938138984206347>':
                num += 1
                if clan is None:
                    clan = await self.bot.getClan(tag)
                text += f'{ranking.flag} `{ranking.local_ranking}` | {ranking.country} | {clan.name}\n'

        if text == '':
            text = 'No ranked clans'
        embed = disnake.Embed(
            title=f'**{ctx.guild.name} Clan Country Rankings (Top 200)**',
            description=text,
            color=disnake.Color.green(),
        )
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        await ctx.edit_original_message(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(FamilyStats(bot))
