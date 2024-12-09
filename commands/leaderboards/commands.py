import coc
import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from discord.options import autocomplete
from utility.components import create_components
from utility.discord_utils import interaction_handler
from .utils import bb_clan_leaderboard, bb_player_leaderboard, clan_capital_leaderboard, hv_clan_leaderboard, hv_player_leaderboard


class Leaderboards(commands.Cog, name='Leaderboards'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='leaderboard')
    async def leaderboard(self, ctx):
        await ctx.response.defer()

    @leaderboard.sub_command(name='location', description='Top 200 Leaderboard for a location as seen in-game')
    async def leaderboard_location(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        type: str = commands.Param(choices=['HV Players', 'HV Clans', 'Clan Capital', 'BB Players', 'BB Clans']),
        country: str = commands.Param(autocomplete=autocomplete.country_names),
    ):

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)

        type_map: dict[str, callable] = {
            'HV Players': self.bot.coc_client.get_location_players,
            'HV Clans': self.bot.coc_client.get_location_clans,
            'Clan Capital': self.bot.coc_client.get_location_clans_capital,
            'BB Players': self.bot.coc_client.get_location_players_builder_base,
            'BB Clans': self.bot.coc_client.get_location_clans_builder_base,
        }

        if country == 'Global':
            country_id = 'global'
            location_emoji = self.bot.emoji.earth.emoji_string
        else:
            locations: list[coc.Location] = await self.bot.get_country_names()
            country_obj = coc.utils.get(locations, name=country, is_country=country != 'International')
            if country == 'International':
                location_emoji = self.bot.emoji.earth.emoji_string
            else:
                location_emoji = f':flag_{country_obj.country_code.lower()}:'
            country_id = country_obj.id

        rankings = await type_map.get(type)(location_id=country_id)

        family_clan_tags = await self.bot.clan_db.distinct('tag', filter={'server': ctx.guild_id})

        if type == 'HV Players':
            embeds = await hv_player_leaderboard(
                bot=self.bot,
                country_name=country.capitalize(),
                rankings=rankings,
                location_emoji=location_emoji,
                embed_color=embed_color
            )
        elif type == 'HV Clans':
            embeds = await hv_clan_leaderboard(
                bot=self.bot,
                country_name=country.capitalize(),
                rankings=rankings,
                location_emoji=location_emoji,
                family_clan_tags=family_clan_tags,
                embed_color=embed_color,
            )
        elif type == 'Clan Capital':
            embeds = await clan_capital_leaderboard(
                bot=self.bot,
                country_name=country.capitalize(),
                rankings=rankings,
                location_emoji=location_emoji,
                family_clan_tags=family_clan_tags,
                embed_color=embed_color,
            )
        elif type == 'BB Players':
            embeds = await bb_player_leaderboard(
                bot=self.bot,
                country_name=country.capitalize(),
                rankings=rankings,
                location_emoji=location_emoji,
                family_clan_tags=family_clan_tags,
                embed_color=embed_color,
            )
        elif type == 'BB Clans':
            embeds = await bb_clan_leaderboard(
                bot=self.bot,
                country_name=country.capitalize(),
                rankings=rankings,
                location_emoji=location_emoji,
                family_clan_tags=family_clan_tags,
                embed_color=embed_color,
            )

        current_page = 0
        await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))

        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

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
                await ctx.delete_original_message()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(Leaderboards(bot))
