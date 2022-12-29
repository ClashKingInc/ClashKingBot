
from disnake.ext import commands
import disnake
from coc import utils
import pytz
utc = pytz.utc
from datetime import datetime
import calendar


from CustomClasses.CustomPlayer import MyCustomPlayer, LegendDay
from CustomClasses.CustomBot import CustomClient


class CheckStats(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def checkEmbed(self, player: MyCustomPlayer):

        if player.league_as_string != "Legend League":
            embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name()}",
                                  description=f"Player not currently in legends.",
                                  color=disnake.Color.blue())
            return embed

        legend_day = player.legend_day()
        embed = disnake.Embed(
            description=f"**Legends Overview** | [profile]({player.share_link})\n" +
                        f"Start: {self.bot.emoji.legends_shield.emoji_string} {player.trophy_start()} | Now: {self.bot.emoji.legends_shield.emoji_string} {player.trophies}\n" +
                        f"- {legend_day.num_attacks.integer} attacks for +{legend_day.attack_sum} trophies\n" +
                        f"- {legend_day.num_defenses.integer} defenses for -{legend_day.defense_sum} trophies\n"
                        f"- Net Trophies: {legend_day.net_gain} trophies\n- Current Streak: {player.streak}",
            color=disnake.Color.blue())

        ranking = await player.ranking()
        embed.add_field(name="**Stats**",
                        value=f"- Rank: {self.bot.emoji.earth.emoji_string} {ranking.global_ranking} | {ranking.flag} {ranking.local_ranking}\n- Country: {ranking.country}"
                        , inline=False)


        embed.set_author(name=f"{player.name} | {player.clan_name()}", icon_url=f"{player.clan_badge_link()}")
        embed.set_thumbnail(url=player.town_hall_cls.image_url)

        off = ""
        for hit in legend_day.attacks:
            off += f"{self.bot.emoji.sword.emoji_string} +{hit}\n"

        defi = ""
        for d in legend_day.defenses:
            defi += f"{self.bot.emoji.shield.emoji_string} -{d}\n"

        if off == "":
            off = "No Attacks Yet."
        if defi == "":
            defi = "No Defenses Yet."
        embed.add_field(name="**Offense**", value=off, inline=True)
        embed.add_field(name="**Defense**", value=defi, inline=True)
        embed.set_footer(text=player.tag)

        return embed


    async def checkYEmbed(self, player: MyCustomPlayer):

        season_stats = player.season_of_legends()

        '''
        embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name()}",
                              description=f"No previous stats for this season.",
                              color=disnake.Color.blue())
        return embed
        '''

        if player.league_as_string != "Legend League":
            embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name()}",
                                  description=f"Player not currently in legends.",
                                  color=disnake.Color.blue())
            return embed


        text = f""
        initial = f"**Attacks Won:** {player.attack_wins} | **Def Won:** {player.defense_wins}\n"
        text += initial

        start = utils.get_season_start().replace(tzinfo=utc).date()
        now = datetime.now(tz=utc).date()
        now_ = datetime.now(tz=utc)
        current_season_progress = now - start
        current_season_progress = current_season_progress.days

        if now_.hour < 5:
            current_season_progress -= 1
        day = 0
        for legend_day in season_stats.values():
            day+=1
            legend_day: LegendDay

            day_text = f"Day {day}"
            day_text = day_text.ljust(6)
            text+=f"`{day_text}` {self.bot.emoji.sword.emoji_string}{legend_day.attack_sum}{legend_day.num_attacks.superscript} " \
                  f"{self.bot.emoji.shield.emoji_string}{legend_day.defense_sum}{legend_day.num_defenses.superscript}\n"
            if day == current_season_progress:
                break

        if text == initial:
            text += "\n**No Previous Days Tracked**"
        embed = disnake.Embed(title=f"Season Legends Overview",
                              description=text,
                              color=disnake.Color.blue())


        embed.set_author(name=f"{player.name} | {player.clan_name()}", icon_url=f"{player.clan_badge_link()}", url=player.share_link)
        embed.set_thumbnail(url=player.town_hall_cls.image_url)

        month = start.month
        if month == 12:
            month = 0
        month = calendar.month_name[month + 1]
        embed.set_footer(text=f"{month} {start.year} Season")

        return embed


