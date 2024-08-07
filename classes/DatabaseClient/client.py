from typing import TYPE_CHECKING

import disnake


if TYPE_CHECKING:
    from classes.bot import CustomClient
else:
    from disnake import AutoShardedClient as CustomClient

from utility.constants import EMBED_COLOR

from .Classes.settings import DatabaseServer


class BaseClient:
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def get_server_settings(self, server_id: int):
        pipeline = [
            {'$match': {'server': server_id}},
            {
                '$lookup': {
                    'from': 'legendleagueroles',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'eval.league_roles',
                }
            },
            {
                '$lookup': {
                    'from': 'evalignore',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'eval.ignored_roles',
                }
            },
            {
                '$lookup': {
                    'from': 'generalrole',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'eval.family_roles',
                }
            },
            {
                '$lookup': {
                    'from': 'linkrole',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'eval.not_family_roles',
                }
            },
            {
                '$lookup': {
                    'from': 'familyexclusiveroles',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'eval.only_family_roles',
                }
            },
            {
                '$lookup': {
                    'from': 'townhallroles',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'eval.townhall_roles',
                }
            },
            {
                '$lookup': {
                    'from': 'builderhallroles',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'eval.builderhall_roles',
                }
            },
            {
                '$lookup': {
                    'from': 'builderleagueroles',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'eval.builder_league_roles',
                }
            },
            {
                '$lookup': {
                    'from': 'clans',
                    'localField': 'server',
                    'foreignField': 'server',
                    'as': 'clans',
                }
            },
        ]
        data = await self.bot.server_db.aggregate(pipeline).to_list(length=1)
        if not data:
            await self.bot.server_db.insert_one(
                {
                    'server': server_id,
                    'banlist': None,
                    'greeting': None,
                    'cwlcount': None,
                    'topboardchannel': None,
                    'tophour': None,
                    'lbboardChannel': None,
                    'lbhour': None,
                }
            )
            pipeline = [
                {'$match': {'server': server_id}},
                {
                    '$lookup': {
                        'from': 'legendleagueroles',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.league_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'evalignore',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.ignored_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'generalrole',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.family_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'family_roles',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.family_position_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'linkrole',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.not_family_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'familyexclusiveroles',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.only_family_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'townhallroles',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.townhall_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'builderhallroles',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.builderhall_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'builderleagueroles',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'eval.builder_league_roles',
                    }
                },
                {
                    '$lookup': {
                        'from': 'clans',
                        'localField': 'server',
                        'foreignField': 'server',
                        'as': 'clans',
                    }
                },
            ]
            data = await self.bot.server_db.aggregate(pipeline).to_list(length=1)
        return DatabaseServer(bot=self.bot, data=data[0])

    async def get_server_embed_color(self, server_id: int) -> disnake.Color:
        server_data = await self.bot.server_db.find_one({'server': server_id}, {'server': 1, 'embed_color': 1})
        if server_data is None:
            await self.bot.server_db.insert_one(
                {
                    'server': server_id,
                    'banlist': None,
                    'greeting': None,
                    'cwlcount': None,
                    'topboardchannel': None,
                    'tophour': None,
                    'lbboardChannel': None,
                    'lbhour': None,
                }
            )
            server_data = await self.bot.server_db.find_one({'server': server_id}, {'server': 1, 'embed_color': 1})
        return disnake.Color(server_data.get('embed_color', EMBED_COLOR))
