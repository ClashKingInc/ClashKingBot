import aiohttp

from main import config


async def upload_to_cdn(payload: bytes, folder: str, id: int | str, filetype: str):
    """
    Uploads a file to BunnyCDN storage.

    :param payload: The bytes of the image/html to store.
    :param folder: The directory where the file should be stored.
    :param id: The ID or name of the file.
    :param filetype: The file extension, e.g., "png", "jpeg", "html".
    :return: The public URL of the uploaded file.
    :raises: aiohttp.ClientResponseError if the request fails.
    """
    headers = {
        'content-type': 'application/octet-stream',
        'AccessKey': config.bunny_api_token,
    }
    url = f'https://storage.bunnycdn.com/clashking-files/{folder}/{id}.{filetype}'
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, data=payload) as response:
            if response.status == 200:
                return f'https://cdn.clashking.xyz/{folder}/{id}/{filetype}'
            else:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_text,
                )
