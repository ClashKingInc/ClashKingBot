async def raid_map(self, ctx: disnake.ApplicationCommandInteraction, clan: str):
    await ctx.response.defer()
    clan = await self.bot.getClan(clan_tag=clan)
    weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
    weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot, limit=1)
    current_clan = weekend_raid_entry.attack_log[-1]

    background = Image.open('ImageGen/RaidMap.png')
    draw = ImageDraw.Draw(background)

    capital_names = ImageFont.truetype('ImageGen/SCmagic.ttf', 27)
    league_name_font = ImageFont.truetype('ImageGen/SCmagic.ttf', 35)

    paste_spot = {
        'Capital Peak': (1025, 225),
        'Barbarian Camp': (1360, 500),
        'Wizard Valley': (1025, 675),
        'Balloon Lagoon': (750, 920),
        "Builder's Workshop": (1250, 970),
    }
    text_spot = {'Wizard Valley': (1128, 655), 'Balloon Lagoon': (845, 900), "Builder's Workshop": (1300, 920)}
    for spot, district in enumerate(current_clan.districts):
        name = 'District_Hall'
        if district.id == 70000000:
            name = 'Capital_Hall'
        if district.id not in [70000000, 70000001]:
            draw.text(
                text_spot.get(district.name, (100, 100)),
                district.name,
                anchor='mm',
                fill=(255, 255, 255),
                stroke_width=3,
                stroke_fill=(0, 0, 0),
                font=capital_names,
            )

        name = f'{name}{district.hall_level}'
        district_image = Image.open(f'ImageGen/CapitalDistricts/{name}.png')
        size = 212, 200
        district_image = district_image.resize(size, Image.ANTIALIAS)
        area = paste_spot.get(district.name, (100, 106))
        background.paste(district_image, area, district_image.convert('RGBA'))

    def save_im(background):
        # background.show()
        temp = io.BytesIO()
        # background = background.resize((725, 471))
        # background = background.resize((1036, 673))
        background.save(temp, format='png', compress_level=1)
        temp.seek(0)
        file = disnake.File(fp=temp, filename='filename.png')
        temp.close()
        return file

    loop = asyncio.get_event_loop()
    file = await loop.run_in_executor(None, save_im, background)

    await ctx.send(file=file)


async def testthis(self, ctx: disnake.ApplicationCommandInteraction, clan: str):
    await ctx.response.defer()
    tag = clan
    try:
        base_clan = await self.bot.getClan(clan_tag=tag)
        cwl: coc.ClanWarLeagueGroup = await self.bot.coc_client.get_league_group(clan_tag=base_clan.tag)
    except:
        return await ctx.send(content='Clan not in cwl')

    background = Image.open('ImageGen/cwlbk.png')
    clan_name = ImageFont.truetype('ImageGen/SCmagic.ttf', 30)
    league_name_font = ImageFont.truetype('ImageGen/SCmagic.ttf', 35)
    numbers = ImageFont.truetype('ImageGen/SCmagic.ttf', 35)
    small_numbers = ImageFont.truetype('ImageGen/SCmagic.ttf', 15)
    stat_numbers = ImageFont.truetype('ImageGen/SCmagic.ttf', 25)
    perc_numbers = ImageFont.truetype('ImageGen/SCmagic.ttf', 20)

    draw = ImageDraw.Draw(background)
    stroke = 4
    star_dict = defaultdict(int)
    dest_dict = defaultdict(int)
    tag_to_obj = defaultdict(str)

    for round in cwl.rounds:
        for war_tag in round:
            war = await self.bot.coc_client.get_league_war(war_tag)
            war: coc.ClanWar
            if str(war.status) == 'won':
                star_dict[war.clan.tag] += 10
            elif str(war.status) == 'lost':
                star_dict[war.opponent.tag] += 10
            tag_to_obj[war.clan.tag] = war.clan
            tag_to_obj[war.opponent.tag] = war.opponent
            star_dict[war.clan.tag] += war.clan.stars
            for attack in war.clan.attacks:
                dest_dict[war.clan.tag] += attack.destruction
            star_dict[war.opponent.tag] += war.opponent.stars
            for attack in war.opponent.attacks:
                dest_dict[war.opponent.tag] += attack.destruction

    star_list = []
    for tag, stars in star_dict.items():
        destruction = dest_dict[tag]
        clan_obj = tag_to_obj[tag]
        star_list.append([clan_obj, stars, destruction])

    sorted_clans = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)

    for count, _ in enumerate(sorted_clans):
        clan = _[0]
        stars = _[1]
        destruction = _[2]
        clan: coc.ClanWarLeagueClan

        async def fetch(url, session):
            async with session.get(url) as response:
                image_data = BytesIO(await response.read())
                return image_data

        tasks = []
        async with aiohttp.ClientSession() as session:
            tasks.append(fetch(clan.badge.medium, session))
            responses = await asyncio.gather(*tasks)
            await session.close()

        for image_data in responses:
            badge = Image.open(image_data)
            size = 100, 100
            badge.thumbnail(size, Image.ANTIALIAS)
            background.paste(badge, (200, 645 + (105 * count)), badge.convert('RGBA'))
        if clan.tag == base_clan.tag:
            color = (136, 193, 229)
        else:
            color = (255, 255, 255)
        draw.text(
            (315, 690 + (106 * count)), f'{clan.name[:17]}', anchor='lm', fill=color, stroke_width=stroke, stroke_fill=(0, 0, 0), font=clan_name
        )
        promo = [x['promo'] for x in war_leagues['items'] if x['name'] == base_clan.war_league.name][0]
        demo = [x['demote'] for x in war_leagues['items'] if x['name'] == base_clan.war_league.name][0]
        extra = 0
        if count + 1 <= promo:
            placement_img = Image.open('ImageGen/league_badges/2168_0.png')
            color = (166, 217, 112)
        elif count + 1 >= demo:
            placement_img = Image.open('ImageGen/league_badges/2170_0.png')
            color = (232, 16, 17)
        else:
            placement_img = Image.open('ImageGen/league_badges/2169_0.png')
            extra = 15
            color = (255, 255, 255)

        draw.text((100, 690 + (106 * count)), f'{count + 1}.', anchor='lm', fill=color, stroke_width=stroke, stroke_fill=(0, 0, 0), font=numbers)
        size = 100, 100
        placement_img.thumbnail(size, Image.ANTIALIAS)
        background.paste(placement_img, (30, 663 + (107 * count) + extra), placement_img.convert('RGBA'))

        thcount = defaultdict(int)

        for player in clan.members:
            thcount[player.town_hall] += 1
        spot = 0
        for th_level, th_count in sorted(thcount.items(), reverse=True):
            e_ = ''
            if th_level >= 13:
                e_ = '-2'
            th_img = Image.open(f'Assets/th_pics/town-hall-{th_level}{e_}.png')
            size = 60, 60
            th_img.thumbnail(size, Image.ANTIALIAS)
            spot += 1
            background.paste(th_img, (635 + (80 * spot), 662 + (106 * count)), th_img.convert('RGBA'))
            draw.text(
                (635 + (80 * spot), 662 + (106 * count)),
                f'{th_count}',
                anchor='mm',
                fill=(255, 255, 255),
                stroke_width=stroke,
                stroke_fill=(0, 0, 0),
                font=small_numbers,
            )
            if spot >= 7:
                break

        star_img = Image.open(f'ImageGen/league_badges/679_0.png')
        size = 45, 45
        star_img.thumbnail(size, Image.ANTIALIAS)
        # if 2 <=count < 7:

        background.paste(star_img, (1440, 665 + (106 * count)), star_img.convert('RGBA'))
        draw.text(
            (1400, 685 + (107 * count)), f'{stars}', anchor='mm', fill=(255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0), font=stat_numbers
        )
        draw.text(
            (1647, 685 + (107 * count)),
            f'{int(destruction)}%',
            anchor='mm',
            fill=(255, 255, 255),
            stroke_width=stroke,
            stroke_fill=(0, 0, 0),
            font=perc_numbers,
        )

    league_name = f"War{base_clan.war_league.name.replace('League', '').replace(' ', '')}.png"
    league_img = Image.open(f'ImageGen/league_badges/{league_name}')
    size = 400, 400
    league_img = league_img.resize(size, Image.ANTIALIAS)
    background.paste(league_img, (785, 80), league_img.convert('RGBA'))

    draw.text(
        (975, 520), f'{base_clan.war_league}', anchor='mm', fill=(255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0), font=league_name_font
    )
    draw.text(
        (515, 135),
        f'{len(cwl.rounds)}/{len(cwl.clans) - 1}',
        anchor='mm',
        fill=(255, 255, 255),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
        font=league_name_font,
    )

    start = coc.utils.get_season_start().replace(tzinfo=pytz.utc).date()
    month = start.month
    if month == 12:
        month = 0
    month = calendar.month_name[month + 1]
    date_font = ImageFont.truetype('ImageGen/SCmagic.ttf', 24)
    draw.text((387, 75), f'{month} {start.year}', anchor='mm', fill=(237, 191, 33), stroke_width=3, stroke_fill=(0, 0, 0), font=date_font)

    def save_im(background):
        # background.show()
        temp = io.BytesIO()
        # background = background.resize((725, 471))
        # background = background.resize((1036, 673))
        background.save(temp, format='png', compress_level=1)
        temp.seek(0)
        file = disnake.File(fp=temp, filename='filename.png')
        temp.close()
        return file

    loop = asyncio.get_event_loop()
    file = await loop.run_in_executor(None, save_im, background)

    await ctx.send(file=file)
