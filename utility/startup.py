
import os
from os import getenv
import requests

from classes.config import Config




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

        CURRENT_CLUSTER = config.cluster_id + 1

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
    CLUSTER_ID = getenv('CLUSTER_ID', '0')
    bot_config_url = 'https://api.clashk.ing/bot/config'
    bot_config = requests.get(bot_config_url, timeout=5, headers={'bot-token': BOT_TOKEN}).json()
    config = Config(remote_settings=bot_config)
    config.bot_token = BOT_TOKEN
    config.cluster_id = int(CLUSTER_ID)
    return config


async def fetch_emoji_dict(bot: 'CustomClient'):
    config = bot._config

    # Fetch the desired emoji definitions
    response = requests.get(config.emoji_url).json()

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
