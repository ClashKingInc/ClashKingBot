import base64
import json
from urllib.parse import unquote

import aiohttp


# data = {'messages': [{'data': {'content': 'fuck', 'embeds': [{'title': "What's this about?", 'description': 'fuck fuck fuck', 'color': 5814783}], 'attachments': []}}]}


def encoded_data(data: dict):
    if data.get('embeds') == []:
        data['embeds'] = None
    data['attachments'] = []
    data = {'messages': [{'data': data}]}

    json_string = json.dumps(data, separators=(',', ':'), sort_keys=True)

    # Encode the JSON string to base64
    base64_encoded = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')

    # Remove any '=' padding characters
    base64_encoded = base64_encoded.rstrip('=')

    # Replace '+' with '%2B' for URL encoding
    base64_encoded = base64_encoded.replace('+', '%2B')

    # Since the decoding side expects '%3D' to replace '=', add '=' signs back for URL encoding.
    # But this is not typically how you would handle base64 in URL parameters.
    # Instead, let's ensure that '=' is handled correctly in URL encoding scenarios.
    # This depends on whether your decoding logic expects '%3D' or '=' directly.
    # Comment out the next line if your decoder does not convert '%3D' back to '='.
    base64_encoded = base64_encoded.replace('=', '%3D')

    return base64_encoded


def reverse_encoding(embed_dict: dict):
    """# Step 1: Replace `%2B` with `+` if necessary (though for URL-safe base64, `%2B` is not used)
    base64_encoded = base64_encoded.replace('%2B', '+')

    # Step 2: Handle padding for URL-safe base64
    base64_encoded += '=' * (4 - len(base64_encoded) % 4)

    # Step 3: Decode the base64-encoded string using urlsafe_b64decode
    try:
        decoded_data = base64.urlsafe_b64decode(base64_encoded)
    except Exception as e:
        return None

    # Step 4: URL-decode this string
    try:
        json_string = unquote(decoded_data.decode('utf-8'))
    except UnicodeDecodeError as e:
        return None

    # Step 5: Parse the JSON string back into a Python dictionary
    try:
        embed_dict = json.loads(json_string)
    except json.JSONDecodeError as e:
        return None"""

    data = embed_dict.get('data').get('messages')[0]
    data = data.get('data')
    data.pop('attachments', None)
    if data.get('embeds') is None:
        data['embeds'] = []

    return data


async def shorten_link(url: str):
    api_url = 'https://api.clashk.ing/shortner'
    params = {'url': url}
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('url')
            else:
                return None
