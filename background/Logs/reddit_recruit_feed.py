from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from Utils.player_pagination import button_pagination
from datetime import datetime

import asyncpraw
import os
import disnake
import re
import coc

subreddit = "ClashOfClansRecruit"
secret = os.getenv("SECRET")
RPW = os.getenv("RPW")
reddit = asyncpraw.Reddit(
    client_id="-dOCgLIHqUJK7g",
    client_secret= secret,
    username="Powerful-Flight2605",
    password=RPW,
    user_agent="Reply Recruit"
)

class reddit_feed(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.loop.create_task(self.reddit_task())

    async def other_reddit_task(self):
        print("feed")
        while True:
            try:
                sub = await reddit.subreddit(subreddit)
                async for comment in sub.stream.comments(skip_existing=True):
                    try:
                        comment: asyncpraw.reddit.Comment
                        if str(comment.author) == "Powerful-Flight2605":
                            continue
                        if str(comment.submission.id) != "16n8g76":
                            continue
                        text = comment.body
                        print(text)
                        tags = re.findall('[#][PYLQGRJCUVOpylqgrjcuvo0289]{5,11}', text)
                        tags = [coc.utils.correct_tag(tag) for tag in tags]
                        print(tags)
                        player = None
                        for tag in tags:
                            player = await self.bot.getPlayer(player_tag=tag, custom=True)
                            if player is not None:
                                break

                        if player is None:
                            continue

                        full_text = f"##{player.name} | Townhall {player.town_hall}\n"
                        start_date = 0
                        end_date = int(coc.utils.get_season_end().timestamp())

                        time_range = f"{datetime.fromtimestamp(start_date).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_date).strftime('%m/%d/%y')}"
                        hitrate = await player.hit_rate(start_timestamp=start_date, end_timestamp=end_date)
                        hr_text = ""
                        for hr in hitrate:
                            hr_type = f"{hr.type}".ljust(5)
                            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
                            hr_text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
                        if hr_text == "":
                            hr_text = "No war hits tracked.\n"

                        full_text += f"###**Triple Hit Rate**\n{hr_text}\n"

                        defrate = await player.defense_rate(start_timestamp=start_date, end_timestamp=end_date)
                        def_text = ""
                        for hr in defrate:
                            hr_type = f"{hr.type}".ljust(5)
                            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
                            def_text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
                        if def_text == "":
                            def_text = "No war defenses tracked.\n"
                        full_text += f"###**Triple Defense Rate**\n{def_text}\n"

                        text = ""
                        hr = hitrate[0]
                        footer_text = f"Avg. Off Stars: `{round(hr.average_stars, 2)}`"
                        if hr.total_zeros != 0:
                            hr_nums = f"{hr.total_zeros}/{hr.num_attacks}".center(5)
                            text += f"`Off 0 Stars` | `{hr_nums}` | {round(hr.average_zeros * 100, 1)}%\n"
                        if hr.total_ones != 0:
                            hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
                            text += f"`Off 1 Stars` | `{hr_nums}` | {round(hr.average_ones * 100, 1)}%\n"
                        if hr.total_twos != 0:
                            hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
                            text += f"`Off 2 Stars` | `{hr_nums}` | {round(hr.average_twos * 100, 1)}%\n"
                        if hr.total_triples != 0:
                            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
                            text += f"`Off 3 Stars` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"

                        hr = defrate[0]
                        footer_text += f"\nAvg. Def Stars: `{round(hr.average_stars, 2)}`"
                        if hr.total_zeros != 0:
                            hr_nums = f"{hr.total_zeros}/{hr.num_attacks}".center(5)
                            text += f"`Def 0 Stars` | `{hr_nums}` | {round(100 - (hr.average_zeros * 100), 1)}%\n"
                        if hr.total_ones != 0:
                            hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
                            text += f"`Def 1 Stars` | `{hr_nums}` | {round(100 - (hr.average_ones * 100), 1)}%\n"
                        if hr.total_twos != 0:
                            hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
                            text += f"`Def 2 Stars` | `{hr_nums}` | {round(100 - (hr.average_twos * 100), 1)}%\n"
                        if hr.total_triples != 0:
                            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
                            text += f"`Def 3 Stars` | `{hr_nums}` | {round(100 - (hr.average_triples * 100), 1)}%\n"

                        if text == "":
                            text = "No attacks/defenses yet.\n"

                        full_text += f"###**Star Count %'s**\n{text}\n"

                        fresh_hr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
                        nonfresh_hr = await player.hit_rate(fresh_type=[False], start_timestamp=start_date, end_timestamp=end_date)
                        fresh_dr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
                        nonfresh_dr = await player.defense_rate(fresh_type=[False], start_timestamp=start_date,
                                                                end_timestamp=end_date)
                        hitrates = [fresh_hr, nonfresh_hr, fresh_dr, nonfresh_dr]
                        names = ["Fresh HR", "Non-Fresh HR", "Fresh DR", "Non-Fresh DR"]
                        text = ""
                        for count, hr in enumerate(hitrates):
                            hr = hr[0]
                            if hr.num_attacks == 0:
                                continue
                            hr_type = f"{names[count]}".ljust(12)
                            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
                            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
                        if text == "":
                            text = "No attacks/defenses yet.\n"

                        full_text += f"###**Fresh/Not Fresh**\n{text}\n"

                        random = await player.hit_rate(war_types=["random"], start_timestamp=start_date, end_timestamp=end_date)
                        cwl = await player.hit_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
                        friendly = await player.hit_rate(war_types=["friendly"], start_timestamp=start_date, end_timestamp=end_date)
                        random_dr = await player.defense_rate(war_types=["random"], start_timestamp=start_date,
                                                              end_timestamp=end_date)
                        cwl_dr = await player.defense_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
                        friendly_dr = await player.defense_rate(war_types=["friendly"], start_timestamp=start_date,
                                                                end_timestamp=end_date)
                        hitrates = [random, cwl, friendly, random_dr, cwl_dr, friendly_dr]
                        names = ["War HR", "CWL HR", "Friendly HR", "War DR", "CWL DR", "Friendly DR"]
                        text = ""
                        for count, hr in enumerate(hitrates):
                            hr = hr[0]
                            if hr.num_attacks == 0:
                                continue
                            hr_type = f"{names[count]}".ljust(11)
                            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
                            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
                        if text == "":
                            text = "No attacks/defenses yet.\n"

                        full_text += f"###**War Type**\n{text}\n"

                        war_sizes = list(range(5, 55, 5))
                        hitrates = []
                        for size in war_sizes:
                            hr = await player.hit_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
                            hitrates.append(hr)
                        for size in war_sizes:
                            hr = await player.defense_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
                            hitrates.append(hr)

                        text = ""
                        names = [f"{size}v{size} HR" for size in war_sizes] + [f"{size}v{size} DR" for size in war_sizes]
                        for count, hr in enumerate(hitrates):
                            hr = hr[0]
                            if hr.num_attacks == 0:
                                continue
                            hr_type = f"{names[count]}".ljust(8)
                            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
                            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
                        if text == "":
                            text = "No attacks/defenses yet.\n"

                        full_text += f"###**War Size**\n{text}\n"
                        footer_text += f"\nHR: HitRate, DR: DefenseRate, Stats are what I have collected, not necessarily perfect, but hopefully can give *some* insight"
                        full_text += footer_text
                        full_text = full_text.replace("\n", "  \r")
                        await comment.reply(body=full_text)
                    except:
                        pass
            except:
                continue


    async def reddit_task(self):
        print("feed")
        while True:
            try:
                count = 0
                sub = await reddit.subreddit(subreddit)
                async for submission in sub.stream.submissions():
                    if count < 100:  # This removes the 100 historical submissions that SubredditStream pulls.
                        count += 1
                        continue
                    if submission.link_flair_text == 'Searching':
                        text = f"{submission.selftext} {submission.title}"
                        tags = re.findall('[#PYLQGRJCUVOpylqgrjcuvo0289]{5,11}', text)
                        player = None
                        for tag in tags:
                            player = await self.bot.getPlayer(player_tag=tag)
                            if player is not None:
                                break

                        results = await self.bot.server_db.find({"reddit_feed": {"$ne": None}}).to_list(length=None)
                        for r in results:
                            try:
                                channel = await self.bot.getch_channel(r.get("reddit_feed"), raise_exception=True)
                                role = r.get("reddit_role")
                                embed = disnake.Embed(title=f'{submission.title}',
                                                      description=submission.selftext
                                                                  + f'\n{submission.score} points | [Link]({submission.url}) | [Comments](https://www.reddit.com/r/{subreddit}/comments/{submission.id})',
                                                      color=disnake.Color.green())
                                buttons = disnake.ui.ActionRow()
                                buttons.append_item(disnake.ui.Button(label="Post Link", emoji=self.bot.emoji.reddit_icon.partial_emoji, url=submission.url))
                                if tags and player is not None:
                                    buttons.append_item(disnake.ui.Button(label="Player Profile", emoji=self.bot.emoji.troop.partial_emoji, style=disnake.ButtonStyle.green, custom_id=f"redditplayer_{player.tag}"))

                                if role is not None:
                                    await channel.send(content=f"<@&{role}>",
                                                   embed=embed, components=buttons)
                                else:
                                    await channel.send(embed=embed, components=buttons)

                            except (disnake.NotFound, disnake.Forbidden):
                                serv = r.get("server")
                                #await self.bot.server_db.update_one({"server": serv}, {"$set": {"reddit_feed": None, "reddit_role" : None}})

            except Exception as e:
                print(e)
                continue

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "redditplayer_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True, with_message=True)
            tag = (str(ctx.data.custom_id).split("_"))[-1]
            msg = await ctx.original_message()
            player = await self.bot.getPlayer(player_tag=tag, custom=True)
            if player is None:
                return await ctx.edit_original_response(content="No player found.")
            await button_pagination(self.bot, ctx, msg, [player])


def setup(bot: CustomClient):
    bot.add_cog(reddit_feed(bot))