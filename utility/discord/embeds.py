import disnake
from exceptions.CustomExceptions import MessageException
from classes.bot import CustomClient



async def embed_parser(lookup_data: dict, bot: CustomClient, guild: disnake.Guild = None, user: disnake.User | disnake.Member = None):
    if not isinstance(lookup_data, dict):
        raise MessageException("This embed no longer exists")

    embed_conventions = {
        "{server_name}": guild.name if guild is not None else "",
        "{server_owner_mention}" : guild.owner.mention if guild is not None else "",
        "{user_name}" : user.name if user is not None else "",
    }



