
from expiring_dict import ExpiringDict
import aiohttp
import io
IMAGE_CACHE = ExpiringDict()

async def download_image(url: str):
    cached = IMAGE_CACHE.get(url)
    if cached is None:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                image_data = await response.read()
            await session.close()
        image_bytes: bytes = image_data
        IMAGE_CACHE.ttl(url, image_bytes, 3600 * 4)
    else:
        image_bytes = cached
    return io.BytesIO(image_bytes)