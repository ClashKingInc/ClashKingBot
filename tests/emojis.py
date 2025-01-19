import os
from dotenv import load_dotenv
load_dotenv()
import requests

def discord_get(url, bot_token):
    headers = {'Authorization': f'Bot {bot_token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

async def fetch_emoji_dict():

    # Fetch the desired emoji definitions
    response = requests.get("https://assets.clashk.ing/bot/emojis.json").json()

    original_name_map = {}
    full_emoji_dict = {}

    # Convert keys to a normalized form, just like your original code
    types_for_class = ["icon_emojis"]
    for emoji_type, emoji_dict in response.items():
        if emoji_type not in types_for_class:
            continue
        hold_dict = emoji_dict.copy()
        for key, value in emoji_dict.items():
            prev_value = hold_dict.pop(key)
            prev_key = key.replace('.', '').replace(' ', '').lower()
            if prev_key.isnumeric():
                prev_key = f'{prev_key}xx'
            original_name_map[prev_key] = key
            hold_dict[prev_key] = prev_value
        full_emoji_dict = full_emoji_dict | hold_dict

    current_emoji = discord_get(
        f'https://discord.com/api/v10/applications/808566437199216691/emojis', bot_token=os.getenv('BOT_TOKEN')
    ).get('items', [])

    combined_emojis = {}
    for emoji in current_emoji:
        is_animated = emoji.get('animated')
        start = '<:' if not is_animated else '<a:'
        # Map back to original name if available
        real_name = original_name_map.get(emoji['name'], None)
        if not real_name:
            continue

        # Convert numeric name to int if needed
        if isinstance(real_name, str) and real_name.isnumeric():
            real_name = int(real_name)

        combined_emojis[real_name] = f'{start}{emoji["name"]}:{emoji["id"]}>'

    class_code = f"class Emojis:\n"
    class_code += "    def __init__(self, bot: 'CustomClient'):\n"

    # Add each field dynamically
    for key in combined_emojis.keys():
        class_code += f"        self.{key} = EmojiType(bot.loaded_emojis.get('{key}'))\n"

    print(class_code)

import asyncio
asyncio.run(fetch_emoji_dict())