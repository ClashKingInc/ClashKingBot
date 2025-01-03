from datetime import datetime

import aiohttp
import disnake

from classes.config import Config


async def upload_to_cdn(config: Config, picture: disnake.Attachment, reason: str):
    headers = {
        'content-type': 'application/octet-stream',
        'AccessKey': config.bunny_api_token,
    }
    payload = await picture.read()
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url=f'https://storage.bunnycdn.com/clashking-files/{reason}/{picture.id}/{picture.filename}',
            headers=headers,
            data=payload,
        ) as response:
            await session.close()
    return f'https://cdn.clashking.xyz/{reason}/{picture.id}/{picture.filename}'


async def general_upload_to_cdn(config: Config, bytes_, id):
    headers = {
        'content-type': 'application/octet-stream',
        'AccessKey': config.bunny_api_token,
    }
    payload = bytes_
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url=f'https://storage.bunnycdn.com/clashking-files/{id}.png',
            headers=headers,
            data=payload,
        ) as response:
            await session.close()
    return f'https://cdn.clashking.xyz/{id}.png?{int(datetime.now().timestamp())}'


async def upload_html_to_cdn(config: Config, bytes_, id):
    headers = {
        'content-type': 'application/octet-stream',
        'AccessKey': config.bunny_api_token,
    }

    payload = bytes_
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url=f'https://storage.bunnycdn.com/clashking-files/{id}.html',
            headers=headers,
            data=payload,
        ) as response:
            await session.close()
    return f'https://cdn.clashking.xyz/{id}.html'
