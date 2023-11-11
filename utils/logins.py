import asyncio
import coc
import os
from dotenv import load_dotenv
from utils.keys import get_keys

load_dotenv()
from coc import Client
from typing import AsyncGenerator
EMAILS = ["apiclashofclans+test30@gmail.com",
          "apiclashofclans+test39@gmail.com",
          "apiclashofclans+test41@gmail.com",
          "apiclashofclans+test42@gmail.com",
          "apiclashofclans+test43@gmail.com"]
PASSWORDS = [os.getenv("COC_PASSWORD") for x in range(len(EMAILS))]

class AbstractClient:
    """Class holding the async generator used to get the client and login on demand"""

    def __init__(self):
        # Pass credentials here or use a venv etc. to avoid hard coding them
        self.__async_gen = self.__yield_client()  # create the async generator

    async def __yield_client(self) -> AsyncGenerator[coc.Client, None]:
        """Get the async generator which always yields the client"""

        async with coc.Client(loop=asyncio.get_event_loop_policy().get_event_loop(), key_count=10, key_names="DiscordBot", throttle_limit=500, cache_max_size=1000,
                        load_game_data=coc.LoadGameData(always=False), raw_attribute=True, stats_max_size=10000) as client:
            if os.getenv("IS_BETA") != "yes":
                tokens = await get_keys(emails=EMAILS[:1], passwords=PASSWORDS[:1], key_names="test", key_count=10)
                await client.login_with_tokens(*tokens)
            else:
                await client.login(os.getenv("COC_EMAIL"), os.getenv("COC_PASSWORD"))  # be aware that hard coding credentials is bad practice!
            while True:
                try:
                    yield client
                except GeneratorExit:
                    break

    async def get_client(self) -> Client:
        """Get the actual logged in client"""
        if not hasattr(self, '__async_gen') and not hasattr(self, '_AbstractClient__async_gen'):
            self.__async_gen = self.__yield_client()  # create async generator if needed
        coc_client = await self.__async_gen.__anext__()
        return coc_client

    @property
    async def client(self) -> Client:
        """Get the actual logged in client"""
        if not hasattr(self, '__async_gen') and not hasattr(self, '_AbstractClient__async_gen'):
            self.__async_gen = self.__yield_client()  # create async generator if needed
        coc_client = await self.__async_gen.__anext__()
        return coc_client

    async def shutdown(self):
        """Log out and close the ClientSession"""
        await self.__async_gen.aclose()

abstractClient = AbstractClient()



coc_client = asyncio.get_event_loop().run_until_complete(abstractClient.get_client())
