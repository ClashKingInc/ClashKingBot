import coc


async def coc_login():
    coc_client: coc.Client = coc.Client(
        base_url='https://api.clashking.xyz/v1',
        key_count=10,
        key_names='test',
        throttle_limit=500,
        cache_max_size=10_000,
        load_game_data=coc.LoadGameData(always=False),
        raw_attribute=True,
        stats_max_size=10_000,
    )
    await coc_client.login_with_tokens(*['who needs this lol'])
    return coc_client
