import io

import coc
import disnake
import pytz
from PIL import Image, ImageDraw, ImageFont

utc = pytz.utc
import asyncio
import concurrent.futures
from io import BytesIO

import aiohttp

th_to_xp = {
    1: 1,
    2: 1,
    3: 1,
    4: 2,
    5: 2,
    6: 2,
    7: 3,
    8: 4,
    9: 5,
    10: 7,
    11: 7,
    12: 10,
    13: 11,
    14: 11,
    15: 12,
    16: 13,
    17: 14,
}


async def generate_war_result_image(war: coc.ClanWar):
    possible_xp = 85
    won_xp = 0

    win_xp = 0
    if war.status == 'won':
        won_xp += 50
        win_xp = 50
        result_text = 'Victory'
    elif war.status == 'tie':
        result_text = 'Draw'
    else:
        result_text = 'Defeat'

    possible_war_xp = 0
    actual_war_xp = 0
    for player in war.opponent.members:
        possible_xp += th_to_xp[player.town_hall]
        possible_war_xp += th_to_xp[player.town_hall]
        best_attack = player.best_opponent_attack
        if best_attack is None:
            continue
        if best_attack.stars >= 1:
            won_xp += th_to_xp[player.town_hall]
            actual_war_xp += th_to_xp[player.town_hall]

    forty_percent = int(0.4 * (war.clan.max_stars))
    sixty_percent = int(0.6 * (war.clan.max_stars))

    forty_xp = 0
    sixty_xp = 0
    if war.clan.stars >= forty_percent:
        forty_xp = 10
        won_xp += 10
    if war.clan.stars >= sixty_percent:
        sixty_xp = 25
        won_xp += 25

    background = Image.open('utility/imagegen/warbkpng.png')
    clan_name = ImageFont.truetype('utility/imagegen/SCmagic.ttf', 45)
    result_font = ImageFont.truetype('utility/imagegen/SCmagic.ttf', 65)
    score_font = ImageFont.truetype('utility/imagegen/SCmagic.ttf', 70)
    total_xp_font = ImageFont.truetype('utility/imagegen/SCmagic.ttf', 35)
    box_xp_font = ImageFont.truetype('utility/imagegen/SCmagic.ttf', 25)
    destruction_font = ImageFont.truetype('utility/imagegen/SCmagic.ttf', 25)

    draw = ImageDraw.Draw(background)

    async def fetch(url, session):
        async with session.get(url) as response:
            image_data = BytesIO(await response.read())
            return image_data

    tasks = []
    async with aiohttp.ClientSession() as session:
        tasks.append(fetch(war.clan.badge.medium, session))
        tasks.append(fetch(war.opponent.badge.medium, session))
        responses = await asyncio.gather(*tasks)
        await session.close()

    for count, image_data in enumerate(responses):
        badge = Image.open(image_data)
        if count == 0:
            background.paste(badge, (850, 50), badge.convert('RGBA'))
        else:
            background.paste(badge, (1050, 50), badge.convert('RGBA'))

    stroke = 4
    draw.text(
        (800, 130),
        f'{war.clan.name}',
        anchor='rm',
        fill=(255, 255, 204),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=clan_name,
    )
    draw.text(
        (1250, 130),
        f'{war.opponent.name}',
        anchor='lm',
        fill=(255, 255, 204),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=clan_name,
    )

    draw.text(
        (1040, 290),
        f'{result_text}',
        anchor='mm',
        fill=(255, 248, 113),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=result_font,
    )
    draw.text(
        (1040, 380),
        f'{war.clan.stars} - {war.opponent.stars}',
        anchor='mm',
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        fill=(255, 255, 204),
        font=score_font,
    )

    draw.text(
        (1600, 585),
        f'+{actual_war_xp} / {possible_war_xp}',
        anchor='rm',
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        fill=(255, 255, 255),
        font=box_xp_font,
    )
    draw.text(
        (1600, 640),
        f'+{forty_xp} / 10',
        anchor='rm',
        fill=(255, 255, 255),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=box_xp_font,
    )
    draw.text(
        (1600, 705),
        f'+{sixty_xp} / 25',
        anchor='rm',
        fill=(255, 255, 255),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=box_xp_font,
    )
    draw.text(
        (1600, 762),
        f'+{win_xp} / 50',
        anchor='rm',
        fill=(255, 255, 255),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=box_xp_font,
    )

    draw.text(
        (775, 642),
        f'{forty_percent}',
        anchor='mm',
        fill=(255, 255, 255),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=box_xp_font,
    )
    draw.text(
        (775, 705),
        f'{sixty_percent}',
        anchor='mm',
        fill=(255, 255, 255),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=box_xp_font,
    )

    draw.text(
        (850, 452),
        f"{format(round(war.clan.destruction, 2), '.2f')}%",
        anchor='rm',
        fill=(255, 255, 204),
        stroke_width=3,
        stroke_fill=(0, 0, 0),
        font=destruction_font,
    )
    draw.text(
        (1250, 452),
        f"{format(round(war.opponent.destruction, 2), '.2f')}%",
        anchor='lm',
        fill=(255, 255, 204),
        stroke_width=3,
        stroke_fill=(0, 0, 0),
        font=destruction_font,
    )

    draw.text(
        (490, 775),
        f'{won_xp} / {possible_xp}',
        anchor='mm',
        fill=(255, 255, 255),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=total_xp_font,
    )

    def save_im(background):
        # background.show()
        temp = io.BytesIO()
        background = background.resize((725, 471))
        # background = background.resize((1036, 673))
        background.save(temp, format='png', compress_level=1)
        temp.seek(0)
        file = disnake.File(fp=temp, filename='filename.png')
        temp.close()
        return file

    with concurrent.futures.ThreadPoolExecutor() as pool:
        loop = asyncio.get_event_loop()
        file = await loop.run_in_executor(pool, save_im, background)

    return file
