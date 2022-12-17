async def fetch(url, session):
    async with session.get(url) as response:
        return await response.json()
