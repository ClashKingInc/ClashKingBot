import asyncio
import base64
import os
from io import BytesIO
from os import getenv
from typing import TYPE_CHECKING

import docker
import requests
from PIL import Image

from classes.config import Config

if TYPE_CHECKING:
    from classes.bot import CustomClient


def get_portainer_token(config: 'Config'):
    url = 'https://hosting.clashk.ing/api/auth'
    payload = {
        'Username': config.portainer_user,
        'Password': config.portainer_pw,
    }
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to authenticate with Portainer: {response.text}")

    # Extract the JWT token from the response
    token = response.json().get('jwt')
    if not token:
        raise Exception("Failed to retrieve Portainer token")

    return token

def get_cluster_breakdown(config: 'Config'):
    cluster_kwargs = {'shard_count': None}
    if config.is_main:
        portainer_token = get_portainer_token(config)
        headers = {
            'Authorization': f'Bearer {portainer_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(f"https://hosting.clashk.ing/api/endpoints/2/docker/containers/json", headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch containers: {response.text}")
        all_containers = response.json()

        with open('/proc/self/mountinfo') as file:
            line = file.readline().strip()
            while line:
                if '/docker/containers/' in line:
                    containerID = line.split('/docker/containers/')[-1]  # Take only text to the right
                    HOSTNAME = containerID.split('/')[0]  # Take only text to the left
                    break
                line = file.readline().strip()

        our_container = [c for c in all_containers if c['Id'][:12] == HOSTNAME[:12]][0]
        container_name = our_container['Names'][0].strip('/')
        config.cluster_id = CURRENT_CLUSTER = int(container_name.split('_')[-1])

        def calculate_shard_distribution(total_shards, total_clusters):
            base_shard_count = total_shards // total_clusters
            extra_shards = total_shards % total_clusters

            shard_distribution = [base_shard_count] * total_clusters

            # Distribute the extra shards to the first few clusters
            for i in range(extra_shards):
                shard_distribution[i] += 1

            return shard_distribution

        TOTAL_SHARDS = config.total_clusters

        shard_distribution = calculate_shard_distribution(TOTAL_SHARDS, config.total_clusters)

        # Determine the start and end of shards for the current cluster
        start_shard = sum(shard_distribution[: CURRENT_CLUSTER - 1])
        end_shard = start_shard + shard_distribution[CURRENT_CLUSTER - 1]

        # Generate shard_ids for the current cluster
        shard_ids = list(range(start_shard, end_shard))

        cluster_kwargs = {
            'shard_ids': shard_ids,
            'shard_count': len(shard_ids),
        }

    return cluster_kwargs


def create_config() -> 'Config':
    BOT_TOKEN = getenv('BOT_TOKEN')
    bot_config_url = 'https://api.clashking.xyz/bot/config'
    bot_config = requests.get(bot_config_url, timeout=5, headers={'bot-token': BOT_TOKEN}).json()
    config = Config(remote_settings=bot_config)
    config.bot_token = BOT_TOKEN
    return config


async def fetch_emoji_dict(bot: 'CustomClient'):
    config = bot._config

    if config.is_main and config.cluster_id != 1:
        await asyncio.sleep(30)
    response = requests.get(config.emoji_url).json()

    assets_url = response.pop('assets_url')

    full_emoji_dict = {}
    for emoji_type, emoji_dict in response.items():
        full_emoji_dict = full_emoji_dict | emoji_dict

    current_emoji = discord_get(f'https://discord.com/api/v10/applications/{bot.application_id}/emojis', bot_token=config.bot_token).get('items', [])
    current_emoji_names = [emoji['name'].replace('____', '').replace('xx', ' ').replace('__', '.') for emoji in current_emoji]

    emoji_to_be_deleted = [
        emoji for emoji in current_emoji if emoji['name'].replace('____', '').replace('xx', ' ').replace('__', '.') not in full_emoji_dict.keys()
    ]

    for emoji in emoji_to_be_deleted:
        try:
            delete_response = discord_delete(
                f"https://discord.com/api/v10/applications/{bot.application_id}/emojis/{emoji['id']}", bot_token=config.bot_token
            )
            print(f"Deleted emoji: {emoji['name']}")
        except requests.exceptions.RequestException as e:
            # Handle rate-limiting or other errors
            print(f"Failed to delete emoji {emoji['name']}: {e}")

    emoji_to_be_added = [name for name in full_emoji_dict.keys() if name not in current_emoji_names]

    for name in emoji_to_be_added:   # type: str
        image_path = full_emoji_dict[name]
        if name.isnumeric():
            name = f'{name}____'
        name = name.replace(' ', 'xx')
        name = name.replace('.', '__')
        image_url = f'{assets_url}{image_path}'
        try:
            # Fetch the image
            image_response = requests.get(image_url)
            image_response.raise_for_status()

            # Resize and compress the image
            resized_image_data = resize_and_compress_image(image_response.content)

            # Encode the image in base64
            image_base64 = base64.b64encode(resized_image_data).decode('utf-8')
            image_base64 = f'data:image/png;base64,{image_base64}'

            # Print base64 string length (for debugging)
            print(f'Base64 length: {len(image_base64)}')

            # Post the new emoji to Discord
            post_response = discord_post(
                f'https://discord.com/api/v10/applications/{bot.application_id}/emojis',
                json_data={'name': name, 'image': image_base64},
                bot_token=config.bot_token,
            )
            print(f'Added emoji: {name}')

        except requests.exceptions.RequestException as e:
            # Handle issues like fetching the image or posting to Discord
            print(f'Failed to add emoji {name}: {e}')
            print(f'Response content: {e.response.content.decode()}')

    current_emoji = discord_get(f'https://discord.com/api/v10/applications/{bot.application_id}/emojis', bot_token=config.bot_token).get('items', [])
    combined_emojis = {}
    for emoji in current_emoji:
        is_animated = emoji.get('animated')
        start = '<:' if not is_animated else '<a:'
        name = emoji.get('name')
        # ____ for int, __ for ., ___ for space
        name = name.replace('____', '').replace('xx', ' ').replace('__', '.')
        name = int(name) if name.isnumeric() else name
        id = emoji.get('id')
        combined_emojis[name] = f'{start}{emoji.get("name")}:{id}>'
    return combined_emojis


def discord_get(url, bot_token):
    headers = {'Authorization': f'Bot {bot_token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def discord_delete(url, bot_token):
    headers = {'Authorization': f'Bot {bot_token}'}
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response


def discord_post(url, json_data, bot_token):
    headers = {'Authorization': f'Bot {bot_token}', 'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response


# Function to resize and compress the image
def resize_and_compress_image(image_content, max_size=(128, 128), max_kb=256):
    image = Image.open(BytesIO(image_content))

    # Resize image
    image.thumbnail(max_size)

    # Save to a bytes buffer
    buffer = BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    buffer_size = buffer.tell() / 1024  # Size in KB

    print(f'Image size after resize/compression: {buffer_size} KB')  # Debug: Print image size

    # If the image is still too large, compress it further
    if buffer_size > max_kb:
        buffer = BytesIO()
        image.save(buffer, format='PNG', optimize=True, quality=85)  # Adjust quality as needed
        buffer_size = buffer.tell() / 1024
        print(f'Image size after additional compression: {buffer_size} KB')  # Debug: Print image size

    return buffer.getvalue()


def load_cogs(disallowed: set):
    file_list = []
    for root, _, files in os.walk('commands'):
        for filename in files:
            if filename.endswith('.py') and filename.split('.')[0] in [
                'commands',
                'buttons',
            ]:
                path = os.path.join(root, filename)[len('commands/') :][:-3].replace(os.path.sep, '.')
                if path.split('.')[0] in disallowed:
                    continue
                file_list.append(f'commands.{path}')
    return file_list


def sentry_filter(event, hint):
    try:
        if (
            'unclosed client session' in str(event['logentry']['message']).lower()
            or 'unclosed connector' in str(event['logentry']['message']).lower()
        ):
            return None
    except:
        pass
    return event
