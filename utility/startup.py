import asyncio
import base64
import os
from io import BytesIO
from os import getenv
from typing import TYPE_CHECKING
import imagehash
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

        TOTAL_SHARDS = config.total_clusters * 2

        shard_distribution = calculate_shard_distribution(TOTAL_SHARDS, config.total_clusters)

        # Determine the start and end of shards for the current cluster
        start_shard = sum(shard_distribution[: CURRENT_CLUSTER - 1])
        end_shard = start_shard + shard_distribution[CURRENT_CLUSTER - 1]

        # Generate shard_ids for the current cluster
        shard_ids = list(range(start_shard, end_shard))

        cluster_kwargs = {
            'shard_ids': shard_ids,
            'shard_count': TOTAL_SHARDS,
        }

    return cluster_kwargs


def create_config() -> 'Config':
    BOT_TOKEN = getenv('BOT_TOKEN')
    bot_config_url = 'https://api.clashk.ing/bot/config'
    bot_config = requests.get(bot_config_url, timeout=5, headers={'bot-token': BOT_TOKEN}).json()
    config = Config(remote_settings=bot_config)
    config.bot_token = BOT_TOKEN
    return config


def compute_image_hash(image_data: bytes) -> str:
    """
    Computes a perceptual hash (pHash) for the given image data.
    """
    with Image.open(BytesIO(image_data)) as img:
        return str(imagehash.phash(img))

async def fetch_emoji_dict(bot: 'CustomClient'):
    config = bot._config
    if config.is_main:
        shard_data = await bot.bot_sync.find_one({"$and" : [{"bot_id": bot.user.id}, {"cluster_id" : 1}]})
    else:
        shard_data = await bot.bot_sync.find_one({"bot_id": bot.user.id})

    already_updated = shard_data.get("emoji_asset_version") == config.emoji_asset_version

    if config.cluster_id >= 2:
        while not already_updated:
            shard_data = await bot.bot_sync.find_one({"$and": [{"bot_id": bot.user.id}, {"cluster_id": 1}]})
            already_updated = shard_data.get("emoji_asset_version") == config.emoji_asset_version
            await asyncio.sleep(5)

    # Fetch the desired emoji definitions
    response = requests.get(config.emoji_url).json()
    assets_url = "https://assets.clashk.ing"

    original_name_map = {}
    full_emoji_dict = {}

    # Convert keys to a normalized form, just like your original code
    for emoji_type, emoji_dict in response.items():
        hold_dict = emoji_dict.copy()
        for key, value in emoji_dict.items():
            prev_value = hold_dict.pop(key)
            prev_key = key.replace(".", "").replace(" ", "").lower()
            if prev_key.isnumeric():
                prev_key = f"{prev_key}xx"
            original_name_map[prev_key] = key
            hold_dict[prev_key] = prev_value
        full_emoji_dict = full_emoji_dict | hold_dict

    if config.cluster_id <= 1 and not already_updated:

        # Fetch current emojis from Discord
        current_emoji = discord_get(
            f'https://discord.com/api/v10/applications/{bot.application_id}/emojis',
            bot_token=config.bot_token
        ).get('items', [])

        current_emoji_names = [emoji['name'] for emoji in current_emoji if emoji["name"]]

        # --------------------------------------------------------------------------------
        # 1) Build a map of existing emojis {emoji_name -> (id, hash)} to detect changes
        # --------------------------------------------------------------------------------
        existing_emoji_map = {}
        for emoji in current_emoji:
            # Attempt to fetch the current image from Discord's CDN and hash it
            emoji_name = emoji['name']
            emoji_id = emoji['id']
            # Discord CDN URL for the emoji image (PNG format)
            cdn_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png?size=128&quality=lossless"

            try:
                cdn_resp = requests.get(cdn_url)
                cdn_resp.raise_for_status()
                existing_hash = compute_image_hash(cdn_resp.content)
                existing_emoji_map[emoji_name] = {'id': emoji_id, 'hash': existing_hash}
            except requests.exceptions.RequestException:
                # If fetching fails, store None; we can decide how to handle it below
                existing_emoji_map[emoji_name] = {'id': emoji_id, 'hash': None}
        print("created hashmap")
        # --------------------------------------------------------------------------------
        # 2) Determine which emojis need to be deleted (unused in the new config)
        # --------------------------------------------------------------------------------

        emoji_to_be_deleted = [
            emoji for emoji in current_emoji
            if emoji['name'] not in full_emoji_dict.keys()
        ]

        for emoji in emoji_to_be_deleted:
            try:
                delete_response = discord_delete(
                    f"https://discord.com/api/v10/applications/{bot.application_id}/emojis/{emoji['id']}",
                    bot_token=config.bot_token
                )
                print(f"Deleted emoji: {emoji['name']}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to delete emoji {emoji['name']}: {e}")
        print("deleted emojis, no longer existing")

        # --------------------------------------------------------------------------------
        # 3) Identify new emojis that need to be added
        # --------------------------------------------------------------------------------
        emoji_to_be_added = [
            name for name in full_emoji_dict.keys()
            if name not in current_emoji_names
        ]

        # Add new emojis
        for name in emoji_to_be_added:
            image_path = full_emoji_dict[name]
            image_url = f'{assets_url}{image_path}'
            try:
                image_response = requests.get(image_url)
                image_response.raise_for_status()

                resized_image_data = resize_and_compress_image(image_response.content)
                # Compute hash (not stored, but we could store it if needed for debugging)
                _ = compute_image_hash(resized_image_data)

                image_base64 = base64.b64encode(resized_image_data).decode('utf-8')
                image_base64 = f'data:image/png;base64,{image_base64}'

                # Print length for debugging
                print(f'Base64 length: {len(image_base64)}')

                # Post the new emoji
                post_response = discord_post(
                    f'https://discord.com/api/v10/applications/{bot.application_id}/emojis',
                    json_data={'name': name, 'image': image_base64},
                    bot_token=config.bot_token,
                )
                print(f'Added emoji: {name}')
            except requests.exceptions.RequestException as e:
                print(f'Failed to add emoji {name}: {e}')
                if hasattr(e, 'response') and e.response is not None:
                    print(f'Response content: {e.response.content.decode()}')

        print("identified new emojis")
        # --------------------------------------------------------------------------------
        # 4) Check existing emojis for updates (hash changes)
        # --------------------------------------------------------------------------------
        emoji_to_be_checked = [
            name for name in full_emoji_dict.keys()
            if name in current_emoji_names
        ]

        for name in emoji_to_be_checked:
            try:
                # Desired image
                image_path = full_emoji_dict[name]
                image_url = f'{assets_url}{image_path}'
                image_resp = requests.get(image_url)
                image_resp.raise_for_status()

                desired_resized_data = resize_and_compress_image(image_resp.content)
                desired_hash = compute_image_hash(desired_resized_data)

                # Compare with existing hash
                existing_info = existing_emoji_map.get(name)
                if not existing_info:
                    # If somehow not present, skip or add it
                    continue

                current_hash = existing_info['hash']
                emoji_id = existing_info['id']

                # If hash is different (and we have a valid existing hash), update the emoji
                if current_hash and desired_hash and current_hash != desired_hash:
                    print(f"Hash mismatch for emoji '{name}' -> Updating...")

                    # Delete the existing emoji
                    try:
                        discord_delete(
                            f"https://discord.com/api/v10/applications/{bot.application_id}/emojis/{emoji_id}",
                            bot_token=config.bot_token
                        )
                        print(f"Deleted emoji for update: {name}")
                    except requests.exceptions.RequestException as e:
                        print(f"Failed to delete emoji {name} for update: {e}")
                        continue  # Skip re-adding if we failed to delete

                    # Re-add the updated emoji
                    new_base64 = base64.b64encode(desired_resized_data).decode('utf-8')
                    new_base64 = f'data:image/png;base64,{new_base64}'

                    try:
                        discord_post(
                            f'https://discord.com/api/v10/applications/{bot.application_id}/emojis',
                            json_data={'name': name, 'image': new_base64},
                            bot_token=config.bot_token
                        )
                        print(f'Updated emoji: {name}')
                    except requests.exceptions.RequestException as e:
                        print(f"Failed to add updated emoji {name}: {e}")
                else:
                    # Either hashes match or we couldn't fetch one of them
                    print(f"Emoji '{name}' is up-to-date or unable to compare. No action needed.")

            except requests.exceptions.RequestException as e:
                print(f'Failed to check/update emoji {name}: {e}')
                if hasattr(e, 'response') and e.response is not None:
                    print(f'Response content: {e.response.content.decode()}')

        print("compared hashes")

    # --------------------------------------------------------------------------------
    # 5) Re-fetch current emojis and build the final combined dictionary
    # --------------------------------------------------------------------------------
    current_emoji = discord_get(
        f'https://discord.com/api/v10/applications/{bot.application_id}/emojis',
        bot_token=config.bot_token
    ).get('items', [])

    combined_emojis = {}
    for emoji in current_emoji:
        is_animated = emoji.get('animated')
        start = '<:' if not is_animated else '<a:'
        # Map back to original name if available
        real_name = original_name_map.get(emoji['name'], emoji['name'])

        # Convert numeric name to int if needed
        if isinstance(real_name, str) and real_name.isnumeric():
            real_name = int(real_name)

        combined_emojis[real_name] = f'{start}{emoji["name"]}:{emoji["id"]}>'

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
