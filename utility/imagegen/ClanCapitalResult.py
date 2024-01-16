import coc
import disnake
from PIL import Image, ImageDraw, ImageFont
import io
import pytz
utc = pytz.utc
import aiohttp
from io import BytesIO
import asyncio
from coc.raid import RaidLogEntry
from utility.clash.capital import calc_raid_medals
import concurrent.futures

async def generate_raid_result_image(raid_entry: RaidLogEntry, clan: coc.Clan):

    background = Image.open("utility/imagegen/raidweek.png")
    clan_name = ImageFont.truetype("utility/imagegen/SCmagic.ttf", 30)
    total_medal_font = ImageFont.truetype("utility/imagegen/SCmagic.ttf", 60)
    boxes_font = ImageFont.truetype("utility/imagegen/SCmagic.ttf",30)

    split_medal_font = ImageFont.truetype("utility/imagegen/SCmagic.ttf", 25)


    draw = ImageDraw.Draw(background)

    async def fetch(url, session):
        async with session.get(url) as response:
            image_data = BytesIO(await response.read())
            return image_data

    tasks = []
    async with aiohttp.ClientSession() as session:
        tasks.append(fetch(clan.badge.medium, session))
        responses = await asyncio.gather(*tasks)
        await session.close()

    for count, image_data in enumerate(responses):
        badge = Image.open(image_data)
        background.paste(badge, (1125, 135), badge.convert("RGBA"))


    if raid_entry.offensive_reward == 0:
        off_medal_reward = calc_raid_medals(raid_entry.attack_log)
    else:
        off_medal_reward = raid_entry.offensive_reward * 6

    stroke = 2
    draw.text((1225, 117), f"{clan.name}", anchor="mm", fill=(255,255,255), stroke_width=stroke, stroke_fill=(0, 0, 0),font=clan_name)
    draw.text((750, 250), f"{off_medal_reward + raid_entry.defensive_reward}", anchor="mm", fill=(255,255,255), stroke_width=4, stroke_fill=(0, 0, 0),font=total_medal_font)

    draw.text((155, 585), f"{raid_entry.total_loot}", anchor="lm", fill=(255,255,255), stroke_width=stroke, stroke_fill=(0, 0, 0),font=boxes_font)
    draw.text((870, 585), f"{len([log for log in raid_entry.attack_log if log.destroyed_district_count == log.district_count])}", anchor="lm", fill=(255,255,255), stroke_width=stroke, stroke_fill=(0, 0, 0),font=boxes_font)

    draw.text((155, 817), f"{raid_entry.attack_count}", anchor="lm", fill=(255,255,255), stroke_width=stroke, stroke_fill=(0, 0, 0),font=boxes_font)
    draw.text((870, 817), f"{raid_entry.destroyed_district_count}", anchor="lm", fill=(255,255,255), stroke_width=stroke, stroke_fill=(0, 0, 0),font=boxes_font)

    draw.text((550, 370), f"{off_medal_reward}", anchor="lm", fill=(255, 255, 255), stroke_width=stroke,stroke_fill=(0, 0, 0), font=split_medal_font)
    draw.text((1245, 370), f"{raid_entry.defensive_reward}", anchor="lm", fill=(255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0), font=split_medal_font)

    draw.text((25, 35), f"{raid_entry.start_time.time.date()}", anchor="lm", fill=(255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0), font=clan_name)

    def save_im(background):
        # background.show()
        temp = io.BytesIO()
        # background = background.resize((869, 637))
        # background = background.resize((1036, 673))
        background.save(temp, format="png", compress_level=1)
        temp.seek(0)
        file = disnake.File(fp=temp, filename="filename.png")
        temp.close()
        return file

    with concurrent.futures.ThreadPoolExecutor() as pool:
        loop = asyncio.get_event_loop()
        file = await loop.run_in_executor(pool, save_im, background)

    return file

