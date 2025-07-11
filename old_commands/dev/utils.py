import asyncio
import base64
from io import BytesIO
from typing import TYPE_CHECKING

import aiohttp
import disnake
import imagehash
import pendulum as pend
import requests
from PIL import Image

if TYPE_CHECKING:
    from classes.bot import CustomClient

GITHUB_API_BASE = 'https://api.github.com'
from utility.constants import EMBED_COLOR_CLASS
from utility.discord_utils import register_button


async def fetch_github_milestones(bot: 'CustomClient', repo_name: str):
    """Fetch milestones from the GitHub repository."""
    url = f'{GITHUB_API_BASE}/repos/{repo_name}/milestones'
    headers = {'Authorization': f'token {bot._config.github_token}'}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(f'Failed to fetch milestones: {response.status}')
            return await response.json()


async def fetch_issues_for_milestone(bot: 'CustomClient', repo_name: str, milestone_number: int):
    """Fetch issues for a specific milestone."""
    url = f'{GITHUB_API_BASE}/repos/{repo_name}/issues?milestone={milestone_number}&state=open'
    headers = {'Authorization': f'token {bot._config.github_token}'}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(f'Failed to fetch issues: {response.status}')
            return await response.json()


@register_button('githubtimeline', parser='_:repo')
async def milestone_embed(bot: 'CustomClient', repo: str):
    milestones: list[dict] = await fetch_github_milestones(bot=bot, repo_name=repo)
    if not milestones:
        return disnake.Embed(
            title=f"{repo.split('/')[-1]} Timeline",
            description='No open milestones found.',
            color=disnake.Color.red(),
        )

    embed = disnake.Embed(
        title=f"{repo.split('/')[-1]} Timeline",
        color=EMBED_COLOR_CLASS,
    )
    milestones.sort(key=lambda x: x.get('due_on') or '2099-09-09')
    for milestone in milestones:
        total_issues = milestone['open_issues'] + milestone['closed_issues']
        completion_percentage = (milestone['closed_issues'] / total_issues) * 100 if total_issues > 0 else 0

        issues = await fetch_issues_for_milestone(bot=bot, repo_name=repo, milestone_number=milestone['number'])
        issues_list = '\n'.join([f"- {issue['title']}" for issue in issues[:5]])
        if len(issues) > 10:
            issues_list += '\n- ... and more'

        due_date = 'No due date'
        if milestone['due_on']:
            due_date = bot.timestamp(pend.parse(milestone['due_on']).int_timestamp).cal_date
        embed.add_field(
            name=f"{milestone['title']} ({completion_percentage:.0f}% complete)",
            value=(
                f'**Due Date:** {due_date}\n'
                f"**Last Updated:** {bot.timestamp(pend.parse(milestone['updated_at']).int_timestamp).relative}\n"
                f"**Issues:** {milestone['closed_issues']}/{milestone['open_issues']} complete\n"
                f'{issues_list}'
            ),
            inline=False,
        )

    return embed


def compute_image_hash(image_data: bytes) -> str:
    """
    Computes a perceptual hash (pHash) for the given image data.
    """
    with Image.open(BytesIO(image_data)) as img:
        return str(imagehash.phash(img))


async def fetch_emoji_dict(bot: 'CustomClient'):
    await asyncio.sleep(1)
    config = bot._config

    # Fetch the desired emoji definitions
    response = requests.get(config.emoji_url).json()
    assets_url = 'https://assets.clashk.ing'

    bot_config = await bot.db_client.bot.settings.find_one({'type': 'bot'}, {'_id': 0})
    tokens = [bot_config.get('prod_token')] + bot_config.get('beta_tokens', [])
    for bot_token in tokens:
        application_id = discord_get(
            'https://discord.com/api/v10/oauth2/applications/@me',
            bot_token=bot_token,
        ).get('id')
        original_name_map = {}
        full_emoji_dict = {}

        # Convert keys to a normalized form, just like your original code
        for emoji_type, emoji_dict in response.items():
            hold_dict = emoji_dict.copy()
            for key, value in emoji_dict.items():
                prev_value = hold_dict.pop(key)
                prev_key = key.replace('.', '').replace(' ', '').lower()
                if prev_key.isnumeric():
                    prev_key = f'{prev_key}xx'
                original_name_map[prev_key] = key
                hold_dict[prev_key] = prev_value
            full_emoji_dict = full_emoji_dict | hold_dict

        # Fetch current emojis from Discord
        current_emoji = discord_get(
            f'https://discord.com/api/v10/applications/{application_id}/emojis',
            bot_token=bot_token,
        ).get('items', [])

        current_emoji_names = [emoji['name'] for emoji in current_emoji if emoji['name']]

        # --------------------------------------------------------------------------------
        # 1) Build a map of existing emojis {emoji_name -> (id, hash)} to detect changes
        # --------------------------------------------------------------------------------
        existing_emoji_map = {}
        for emoji in current_emoji:
            # Attempt to fetch the current image from Discord's CDN and hash it
            emoji_name = emoji['name']
            emoji_id = emoji['id']
            # Discord CDN URL for the emoji image (PNG format)
            cdn_url = f'https://cdn.discordapp.com/emojis/{emoji_id}.png?size=128&quality=lossless'

            try:
                cdn_resp = requests.get(cdn_url)
                cdn_resp.raise_for_status()
                existing_hash = compute_image_hash(cdn_resp.content)
                existing_emoji_map[emoji_name] = {'id': emoji_id, 'hash': existing_hash}
            except requests.exceptions.RequestException:
                # If fetching fails, store None; we can decide how to handle it below
                existing_emoji_map[emoji_name] = {'id': emoji_id, 'hash': None}
        print('created hashmap')
        # --------------------------------------------------------------------------------
        # 2) Determine which emojis need to be deleted (unused in the new config)
        # --------------------------------------------------------------------------------

        emoji_to_be_deleted = [emoji for emoji in current_emoji if emoji['name'] not in full_emoji_dict.keys()]

        for emoji in emoji_to_be_deleted:
            try:
                delete_response = discord_delete(
                    f"https://discord.com/api/v10/applications/{application_id}/emojis/{emoji['id']}",
                    bot_token=bot_token,
                )
                print(f"Deleted emoji: {emoji['name']}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to delete emoji {emoji['name']}: {e}")
        print('deleted emojis, no longer existing')

        # --------------------------------------------------------------------------------
        # 3) Identify new emojis that need to be added
        # --------------------------------------------------------------------------------
        emoji_to_be_added = [name for name in full_emoji_dict.keys() if name not in current_emoji_names]

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
                    f'https://discord.com/api/v10/applications/{application_id}/emojis',
                    json_data={'name': name, 'image': image_base64},
                    bot_token=bot_token,
                )
                print(f'Added emoji: {name}')
            except requests.exceptions.RequestException as e:
                print(f'Failed to add emoji {name}: {e}')
                if hasattr(e, 'response') and e.response is not None:
                    print(f'Response content: {e.response.content.decode()}')

        print('identified new emojis')
        # --------------------------------------------------------------------------------
        # 4) Check existing emojis for updates (hash changes)
        # --------------------------------------------------------------------------------
        emoji_to_be_checked = [name for name in full_emoji_dict.keys() if name in current_emoji_names]

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
                            f'https://discord.com/api/v10/applications/{application_id}/emojis/{emoji_id}',
                            bot_token=bot_token,
                        )
                        print(f'Deleted emoji for update: {name}')
                    except requests.exceptions.RequestException as e:
                        print(f'Failed to delete emoji {name} for update: {e}')
                        continue  # Skip re-adding if we failed to delete

                    # Re-add the updated emoji
                    new_base64 = base64.b64encode(desired_resized_data).decode('utf-8')
                    new_base64 = f'data:image/png;base64,{new_base64}'

                    try:
                        discord_post(
                            f'https://discord.com/api/v10/applications/{application_id}/emojis',
                            json_data={'name': name, 'image': new_base64},
                            bot_token=bot_token,
                        )
                        print(f'Updated emoji: {name}')
                    except requests.exceptions.RequestException as e:
                        print(f'Failed to add updated emoji {name}: {e}')
                else:
                    # Either hashes match or we couldn't fetch one of them
                    print(f"Emoji '{name}' is up-to-date or unable to compare. No action needed.")

            except requests.exceptions.RequestException as e:
                print(f'Failed to check/update emoji {name}: {e}')
                if hasattr(e, 'response') and e.response is not None:
                    print(f'Response content: {e.response.content.decode()}')

        print('compared hashes')


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
