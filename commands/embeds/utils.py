import base64
import json
import aiohttp
from urllib.parse import quote, unquote


def encoded_data(data: dict):
    encoded_data = quote(json.dumps(data, separators=(',', ':'), sort_keys=True), safe="!~*'()")
    base64_encoded = base64.b64encode(encoded_data.encode('utf-8')).decode('utf-8').rstrip('=')
    base64_encoded = base64_encoded.replace("%3D", "=").replace("+", "%2B")
    return base64_encoded

def reverse_encoding(base64_encoded: str):
    # Step 1: Replace `%2B` with `+`. The replacement of `=` with `%3D` might not be necessary here, as the decoding step will handle URL-encoded values.
    base64_encoded = base64_encoded.replace("%2B", "+")

    # Step 2: Add back the removed `=` padding. The length of base64 string should be a multiple of 4.
    padding_needed = len(base64_encoded) % 4
    if padding_needed:  # If padding is needed, add the necessary amount of '=' characters.
        base64_encoded += '=' * (4 - padding_needed)

    # Step 3: Decode the base64-encoded string.
    decoded_data = base64.b64decode(base64_encoded)

    # Step 4: URL-decode this string.
    json_string = unquote(decoded_data.decode('utf-8'))

    # Step 5: Parse the JSON string back into a Python dictionary.
    embed_dict = json.loads(json_string)

    return dict(embed_dict)



async def shorten_link(url: str):
    api_url = "https://api.clashking.xyz/shortner"
    params = {'url': url}
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("url")
            else:
                return None