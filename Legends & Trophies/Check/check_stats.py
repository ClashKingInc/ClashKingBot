
from disnake.ext import commands
import disnake
from coc import utils
import pytz
utc = pytz.utc
from datetime import datetime
import calendar


from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient


class CheckStats(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def checkEmbed(self, player: MyCustomPlayer):

        if player.league_as_string != "Legend League":
            embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name}",
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

        embed.add_field(name="**Stats**",
                        value=f"- Rank: {self.bot.emoji.earth.emoji_string} {player.ranking().global_ranking} | {player.ranking().flag} {player.ranking().local_ranking}\n- Country: {player.ranking().country}"
                        , inline=False)


        embed.set_author(name=f"{player.name} | {player.clan_name()}", icon_url=f"{player.clan_badge_link()}")


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

        embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name}",
                              description=f"No previous stats for this season.",
                              color=disnake.Color.blue())
        return embed

        if player.league != "Legend League":
            embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name}",
                                  description=f"Player not currently in legends.",
                                  color=disnake.Color.blue())
            return embed

        start = utils.get_season_start().replace(tzinfo=utc).date()
        now = datetime.utcnow().replace(tzinfo=utc).date()
        now_ = datetime.utcnow().replace(tzinfo=utc)
        current_season_progress = now - start
        current_season_progress = current_season_progress.days

        if now_.hour < 5:
            current_season_progress -= 1
        first_record = 0
        last_record = current_season_progress
        real = last_record
        eod = result.get("end_of_day")

        len_y = len(eod)
        if last_record > len_y:
            last_record = len(eod)

        text = f""
        initial = f"**Attacks Won:** {player.num_season_hits} | **Def Won:** {player.num_season_defs}\n"
        text += initial
        day = (((last_record - real) * -1))
        hits = player.previous_hits[len(player.previous_hits) - last_record:len(player.previous_hits) - first_record]
        defs = player.previous_defs[len(player.previous_defs) - last_record:len(player.previous_defs) - first_record]

        spot = 0
        for hit in hits:
            day+=1
            numHits = len(hit)
            if numHits >= 9:
                numHits = 8
            def_spot = defs[spot]
            numDefs = len(def_spot)
            if numDefs >= 9:
                numHits = 8
            numHits = SUPER_SCRIPTS[numHits]
            numDefs = SUPER_SCRIPTS[numDefs]
            spot+=1

            day_text = f"Day {day}"
            day_text = day_text.ljust(6)
            text+=f"`{day_text}` <:sword:948471267604971530>{sum(hit)}{numHits} <:clash:877681427129458739> {sum(def_spot)}{numDefs}\n"

        if text == initial:
            text += "\n**No Previous Days Tracked**"
        embed = disnake.Embed(title=f"Season Legends Overview",
                              description=text,
                              color=disnake.Color.blue())

        if player.clan_name != "No Clan" and player.clan_badge_link != "No Clan":
            embed.set_author(name=f"{player.name} | {player.clan_name}", icon_url=f"{player.clan_badge_link}", url=player.link)
            if player.town_hall == 14:
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/886889518890885141/911184447628513280/1_14_5.png")
            elif player.town_hall == 13:
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/886889518890885141/911184958293430282/786299624725545010.png")
        else:
            embed.set_author(name=f"{player.name} | {player.clan_name}", icon_url="https://cdn.discordapp.com/attachments/880895199696531466/911187298513747998/601618883853680653.png")

        month = calendar.month_name[start.month + 1]
        embed.set_footer(text=f"{month} {start.year} Season")

        return embed

def setup(bot: CustomClient):
    bot.add_cog(CheckStats(bot))

