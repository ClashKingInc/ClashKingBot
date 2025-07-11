import coc
import disnake
from disnake import ApplicationCommandInteraction, ButtonStyle, Color, Embed, MessageInteraction
from disnake.ui import ActionRow, Button

from classes.bot import CustomClient
from utility.discord_utils import interaction_handler


async def add_clan(bot: CustomClient, clan: coc.Clan, ctx: ApplicationCommandInteraction):
    embed = Embed(
        description=f"{clan.name} [{clan.tag}] isn't added to the server. Do you want to add it?",
        color=Color.red(),
    )
    embed.set_thumbnail(url=clan.badge.large)

    page_buttons = [
        Button(
            label='Yes',
            emoji='✅',
            style=ButtonStyle.green,
            custom_id='Yes',
        ),
        Button(label='No', emoji='❌', style=ButtonStyle.red, custom_id='No'),
    ]
    buttons = ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    await ctx.edit_original_message(embed=embed, components=[buttons])

    res: MessageInteraction = await interaction_handler(bot=bot, ctx=ctx)

    if res.data.custom_id == 'Yes':
        await bot.clan_db.insert_one(
            {
                'name': clan.name,
                'tag': clan.tag,
                'generalRole': None,
                'leaderRole': None,
                'category': 'General',
                'server': ctx.guild.id,
                'clanChannel': None,
            }
        )
        embed = disnake.Embed(
            title=f'{clan.name} successfully added.',
            description='Run `/setup clan` again to edit settings for this clan.',
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=clan.badge.large)
        return await ctx.edit_original_message(embed=embed, components=None)
    else:
        embed = disnake.Embed(
            description='Sorry to hear that. Canceling the command now.',
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=clan.badge.large)
        return await res.response.edit_message(embed=embed, components=None)


async def create_countdown_text(type, war: coc.ClanWar = None) -> str:
    text = ''
    now = datetime.utcnow().replace(tzinfo=utc)
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    if type == 'CWL':
        is_cwl = True
        if day == 1:
            first = datetime(year, month, 1, hour=8, tzinfo=utc)
        else:
            if month + 1 == 13:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
            first = datetime(next_year, next_month, 1, hour=8, tzinfo=utc)
        end = datetime(year, month, 11, hour=8, tzinfo=utc)
        if day >= 1 and day <= 10:
            if (day == 1 and hour < 8) or (day == 11 and hour >= 8):
                is_cwl = False
            else:
                is_cwl = True
        else:
            is_cwl = False

        if is_cwl:
            time_left = end - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'ends {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'ends in {int(mins)}M'
            else:
                text = f'ends {int(days)}D {int(hrs)}H'
        else:
            time_left = first - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'in {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'in {int(mins)}M'
            else:
                text = f'in {int(days)}D {int(hrs)}H'

    elif type == 'Clan Games':
        is_games = True
        first = datetime(year, month, 22, hour=8, tzinfo=utc)
        end = datetime(year, month, 28, hour=8, tzinfo=utc)
        if day >= 22 and day <= 28:
            if (day == 22 and hour < 8) or (day == 28 and hour >= 8):
                is_games = False
            else:
                is_games = True
        else:
            is_games = False

        if day == 28 and hour >= 8:
            if month + 1 == 13:
                next_month = 1
                year += 1
            else:
                next_month = month + 1
            first = datetime(year, next_month, 22, hour=8, tzinfo=utc)

        if day >= 29:
            if month + 1 == 13:
                next_month = 1
                year += 1
            else:
                next_month = month + 1
            first = datetime(year, next_month, 22, hour=8, tzinfo=utc)

        if is_games:
            time_left = end - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'ends {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'ends in {int(mins)}M'
            else:
                text = f'ends {int(days)}D {int(hrs)}H'
        else:
            time_left = first - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'in {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'in {int(mins)}M'
            else:
                text = f'in {int(days)}D {int(hrs)}H'

    elif type == 'Raid Weekend':

        now = datetime.utcnow().replace(tzinfo=utc)
        current_dayofweek = now.weekday()
        if (
            (current_dayofweek == 4 and now.hour >= 7)
            or (current_dayofweek == 5)
            or (current_dayofweek == 6)
            or (current_dayofweek == 0 and now.hour < 7)
        ):
            if current_dayofweek == 0:
                current_dayofweek = 7
            is_raids = True
        else:
            is_raids = False

        if is_raids:
            end = datetime(year, month, day, hour=7, tzinfo=utc) + dt.timedelta(days=(7 - current_dayofweek))
            time_left = end - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'end {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'end in {int(mins)}M'
            else:
                text = f'end {int(days)}D {int(hrs)}H'
        else:
            first = datetime(year, month, day, hour=7, tzinfo=utc) + dt.timedelta(days=(4 - current_dayofweek))
            time_left = first - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'in {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'in {int(mins)}M'
            else:
                text = f'in {int(days)}D {int(hrs)}H'

    elif type == 'EOS':
        end = utils.get_season_end().replace(tzinfo=utc)
        time_left = end - now
        secs = time_left.total_seconds()
        days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
        hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
        mins, secs = divmod(secs, secs_per_min := 60)

        if int(days) == 0:
            text = f'in {int(hrs)}H {int(mins)}M'
            if int(hrs) == 0:
                text = f'in {int(mins)}M'
        else:
            text = f'in {int(days)}D {int(hrs)}H '

    elif type == 'Season Day':
        start = utils.get_season_start().replace(tzinfo=utc)
        end = utils.get_season_end().replace(tzinfo=utc)

        start_pendulum = pend.instance(start)
        end_pendulum = pend.instance(end)
        now = pend.now('UTC')

        days_since_start = now.diff(start_pendulum).in_days()
        days_from_start_to_end = start_pendulum.diff(end_pendulum).in_days()

        text = f'{days_since_start}/{days_from_start_to_end}'

    elif type == 'War Score':
        if war is None:
            text = 'Not in War'
        elif str(war.state) == 'preparation':
            secs = war.start_time.seconds_until
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(hrs) == 0:
                text = f'in {mins}M'
            else:
                text = f'{hrs}H {mins}M'
        else:
            text = f'{war.clan.stars}⭐| {war.opponent.stars}⭐'

    elif type == 'War Timer':
        if war is None:
            text = 'Not in War'
        else:
            secs = war.end_time.seconds_until
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if days != 0:
                text = f'{days}D {hrs}H'
            elif int(hrs) == 0:
                text = f'in {mins}M'
            else:
                text = f'{hrs}H {mins}M'

    return text
