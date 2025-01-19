from datetime import datetime, timedelta

import coc
import disnake
from disnake.ext import commands
from pytz import utc

from classes.bot import CustomClient
from exceptions.CustomExceptions import MessageException
from utility.discord_utils import check_commands


class Trials(commands.Cog, name='Trials'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def player_converter(self, player: str):
        player = await self.bot.getPlayer(player_tag=player, raise_exceptions=True)
        return player

    @commands.slash_command(name='trial')
    async def trial(self, ctx):
        await ctx.response.defer()

    @trial.sub_command(name='create', description='Create a trial for a player')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def trial_create(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel,
        player: coc.Player = commands.Param(converter=player_converter),
        duration: int = commands.Param(le=35),
        trophies: int = None,
        attack_wins: int = None,
        combined_hero_level: int = None,
        hitrate: int = None,
        capital_gold_looted: int = None,
        capital_gold_donated: int = None,
        allowed_clan_hops: int = None,
        num_wars_participated: int = None,
    ):
        result = await self.bot.trials.find_one(
            {
                '$and': [
                    {'player_tag': player.tag},
                    {'server_id': ctx.guild_id},
                    {'active': True},
                ]
            }
        )
        if result is not None:
            raise MessageException(
                f'**An active trial for {player.name} already exists.** Trials can be ended with `/trial end`'
            )

        await self.bot.track_players(players=[player])
        beginning_store = {
            'trophies': player.trophies,
            'attack_wins': player.attack_wins,
            'combined_hero_level': [hero for hero in player.heroes if hero.is_home_base],
            'hitrate': 0,
            'capital_gold_looted': 0,
            'capital_gold_donated': 0,
            'clan_hops': 0,
            'wars_participated': 0,
        }

        requirement_store = {
            'trophies': trophies,
            'attack_wins': attack_wins,
            'combined_hero_level': combined_hero_level,
            'hitrate': hitrate,
            'capital_gold_looted': capital_gold_looted,
            'capital_gold_donated': capital_gold_donated,
            'allowed_clan_hops': allowed_clan_hops,
            'num_wars_participated': num_wars_participated,
        }

        now = datetime.utcnow().replace(tzinfo=utc)
        rollover_days = now + timedelta(duration)
        check_date = int(rollover_days.timestamp())

        await self.bot.trials.insert_one(
            {
                'player_tag': player.tag,
                'channel': channel.id,
                'server_id': ctx.guild_id,
                'active': True,
                'beginning': beginning_store,
                'requirements': requirement_store,
                'end': {},
                'check_date': check_date,
                'notes': [],
            }
        )

        text = ''
        items = [
            trophies,
            attack_wins,
            combined_hero_level,
            hitrate,
            capital_gold_looted,
            capital_gold_donated,
            allowed_clan_hops,
            num_wars_participated,
        ]
        item_text = [
            'Trophies',
            'Attack Wins',
            'Combined Hero Level',
            'Hitrate',
            'Capital Gold Looted',
            'Capital Gold Donated',
            'Allowed Clan Hops',
            '\# Wars Participated',
        ]
        for item, text in zip(items, item_text):
            if item is not None:
                text += f'- **{text}:** {item}\n'

        embed = disnake.Embed(
            title=f'{duration} day Trial for {player.name}',
            description=f'- **Channel:** {channel.mention}' f'{text}',
            color=disnake.Color.green(),
        )
        await ctx.edit_original_message(embed=embed)

    @trial.sub_command(name='notate', description='Notate a trial for a player')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def trial_notate(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = commands.Param(converter=player_converter),
    ):
        pass

    @trial.sub_command(name='edit', description='Edit a trial for a player')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def trial_edit(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = commands.Param(converter=player_converter),
    ):
        pass

    @trial.sub_command(name='end', description='End a trial for a player')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def trial_edit(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = commands.Param(converter=player_converter),
    ):
        pass


def setup(bot: CustomClient):
    bot.add_cog(Trials(bot))
