import os
from os import getenv

import requests

from classes.config import Config


def create_config() -> 'Config':
    BOT_TOKEN = getenv('BOT_TOKEN')
    CLUSTER_ID = getenv('CLUSTER_ID', '0')
    bot_config_url = 'https://api.clashk.ing/bot/config'
    bot_config = requests.get(bot_config_url, timeout=5, headers={'bot-token': BOT_TOKEN}).json()
    config = Config(remote_settings=bot_config)
    config.bot_token = BOT_TOKEN
    config.cluster_id = int(CLUSTER_ID)
    return config


def load_cogs(disallowed: set) -> list[str]:
    file_list = []

    for root, _, files in os.walk('commands'):
        if '__init__.py' not in files:
            continue  # Skip folders that aren't Python packages (i.e., not cogs)

        module_path = root.replace('/', '.').replace('\\', '.')

        # Get the last part of the path (folder name) and skip if disallowed
        cog_name = os.path.basename(root)
        if cog_name in disallowed:
            continue

        file_list.append(module_path)

    return file_list
