from datetime import datetime

import aiohttp
import disnake

from classes.config import Config


config = Config()


async def upload_to_cdn(picture: disnake.Attachment):
    headers = {
        'content-type': 'application/octet-stream',
        'AccessKey': config.bunny_api_token,
    }
    payload = await picture.read()
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url=f'https://ny.storage.bunnycdn.com/clashking/{picture.id}.png',
            headers=headers,
            data=payload,
        ) as response:
            r = await response.read()
            await session.close()


async def general_upload_to_cdn(bytes_, id):
    headers = {
        'content-type': 'application/octet-stream',
        'AccessKey': config.bunny_api_token,
    }
    payload = bytes_
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url=f'https://ny.storage.bunnycdn.com/clashking/{id}.png',
            headers=headers,
            data=payload,
        ) as response:
            await session.close()
    return f'https://cdn.clashking.xyz/{id}.png?{int(datetime.now().timestamp())}'


async def upload_html_to_cdn(bytes_, id):
    headers = {
        'content-type': 'application/octet-stream',
        'AccessKey': config.bunny_api_token,
    }
    payload = bytes_
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url=f'https://ny.storage.bunnycdn.com/clashking/{id}.html',
            headers=headers,
            data=payload,
        ) as response:
            await session.close()
    return f'https://cdn.clashking.xyz/{id}.html'
