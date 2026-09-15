import coc

from exceptions.CustomExceptions import MessageException

from .Classes.player import LegendPlayer
from .client import BaseClient


class PlayerClient(BaseClient):
    def __init__(self, bot):
        super().__init__(bot)

    async def get_legend_player(self, player: coc.Player):
        data = await self.bot.player_stats.find_one({'tag': player.tag}, {'tag': 1, 'legends': 1})
        if data is None:
            await self.bot.player_stats.update_one(
                {'tag': player.tag},
                {
                    '$set': {
                        'paused': False,
                        'name': player.name,
                        'tag': player.tag,
                        'league': player.league.name,
                    }
                },
                upsert=True,
            )
            data = {'tag': player.tag, 'legends': {}}
        ranking_data = await self.bot.leaderboard_db.find_one({'tag': player.tag})
        default = {
            'country_code': None,
            'country_name': None,
            'local_rank': None,
            'global_rank': None,
        }
        if ranking_data is None:
            ranking_data = default
        if ranking_data.get('global_rank') is None:
            self_global_ranking = await self.bot.legend_rankings.find_one({'tag': player.tag})
            if self_global_ranking:
                ranking_data['global_rank'] = self_global_ranking.get('rank')
        return LegendPlayer(data=data, ranking_data=ranking_data, api_player=player)

    async def get_clan_legend_players(self, clan: coc.Clan):
        members = [member for member in clan.members if member.league.name == 'Legend League']
        if not members:
            raise MessageException(f'No Legend Players in {clan.name}')

        tag_map = {m.tag: m for m in members}
        tags = list(tag_map.keys())

        results = await self.bot.player_stats.find({'tag': {'$in': list(tags)}}, {'tag': 1, 'legends': 1}).to_list(length=None)
        results = {r.get('tag'): r for r in results}

        full_ranking_data = await self.bot.leaderboard_db.find({'tag': {'$in': list(tags)}}).to_list(length=None)
        full_ranking_data = {r.get('tag'): r for r in full_ranking_data}

        full_global_ranking = await self.bot.legend_rankings.find({'tag': {'$in': list(tags)}}).to_list(length=None)
        full_global_ranking = {r.get('tag'): r for r in full_global_ranking}

        player_list = []
        for tag, member in tag_map.items():
            data = results.get(tag)
            if data is None:
                await self.bot.player_stats.update_one(
                    {'tag': tag},
                    {
                        '$set': {
                            'paused': False,
                            'name': member.name,
                            'tag': member.tag,
                            'league': member.league.name,
                        }
                    },
                    upsert=True,
                )
                data = {'tag': member.tag, 'legends': {}}
            default = {
                'country_code': None,
                'country_name': None,
                'local_rank': None,
                'global_rank': None,
            }
            ranking_data = full_ranking_data.get(tag)
            if ranking_data is None:
                ranking_data = default
            if ranking_data.get('global_rank') is None:
                self_global_ranking = full_global_ranking.get(tag)
                if self_global_ranking is not None:
                    ranking_data['global_rank'] = self_global_ranking.get('rank')
            player_list.append(LegendPlayer(data=data, ranking_data=ranking_data, api_player=member))

        return player_list
