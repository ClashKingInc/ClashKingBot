
from CustomClasses.CustomBot import CustomClient
import disnake
import coc
from typing import Union, List
from CustomClasses.CustomPlayer import MyCustomPlayer


async def params_to_tags(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, player: Union[List[MyCustomPlayer], None], user: Union[disnake.User, None],
                         clan: Union[coc.Clan, None], guild: Union[disnake.Guild, None]):
    tags = []
    if player:
        tags = [player.tag for player in player]
    elif user:
        tags = await bot.get_tags(user.id)
    elif clan:
        tags = [member.tag for member in clan.members]
    else:
        guild = ctx.guild if guild is None
        tags = await bot.get_family_member_tags(guild_id=guild.id)