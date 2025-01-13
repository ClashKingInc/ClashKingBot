import coc

coc_client: coc.Client = coc.Client(
    base_url='https://proxy.clashk.ing/v1',
    key_count=10,
    key_names='test',
    throttle_limit=500,
    cache_max_size=10_000,
    load_game_data=coc.LoadGameData(default=True),
    raw_attribute=True,
    stats_max_size=10_000,
)


async def coc_login():
    await coc_client.login_with_tokens(*['who needs this lol'])
    return coc_client
