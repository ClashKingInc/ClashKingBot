import asyncio
from itertools import islice

import coc

from classes.config import Config


config = Config()


async def coc_login(bot):
    emails = [config.coc_email.format(x=x) for x in range(config.min_coc_email, config.max_coc_email + 1)]
    passwords = [config.coc_password] * (config.max_coc_email + 1 - config.min_coc_email)
    tokens = []
    coc_client: coc.Client = coc.Client(
        base_url="https://api.clashking.xyz/v1",
        key_count=10,
        key_names='test',
        throttle_limit=500,
        cache_max_size=1000,
        load_game_data=coc.LoadGameData(always=False),
        raw_attribute=True,
        stats_max_size=10_000,
    )
    tokens = await bot.new_looper.get_collection('api_tokens').distinct('token')

    '''if config.min_coc_email == 1:
        tokens = await bot.new_looper.get_collection('api_tokens').distinct('token')
    else:
        for email, password in zip(emails, passwords):
            await coc_client.login(email=email, password=password)
            tokens.extend(list(islice(coc_client.http._keys, 10)))
            await coc_client.close()'''
    await coc_client.login_with_tokens(*tokens)
    return coc_client
