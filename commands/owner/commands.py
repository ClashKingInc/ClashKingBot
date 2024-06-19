import coc
import disnake
from classes.bot import CustomClient
from disnake.ext import commands
from datetime import datetime
import textwrap
from contextlib import redirect_stdout
import io
import re
import asyncio
import aiohttp
from discord.options import convert, autocomplete
from assets.emojis import *
import json
from classes.DatabaseClient.Classes.settings import DatabaseClan
from utility.discord_utils import get_webhook_for_channel
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.general import calculate_time
from classes.DatabaseClient.Classes.settings import DatabaseServer
from utility.constants import DEFAULT_EVAL_ROLE_TYPES, EMBED_COLOR_CLASS
from ..eval.utils import logic


class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.count = 0
        self.model = None

    @commands.slash_command(name="exec")
    @commands.is_owner()
    async def exec(self, ctx: disnake.ApplicationCommandInteraction):

        def cleanup_code(content: str) -> str:
            """Automatically removes code blocks from the code and reformats linebreaks"""

            # remove ```py\n```
            if content.startswith("```") and content.endswith("```"):
                return "\n".join(content.split("\n")[1:-1])

            return "\n".join(content.split(";"))

        def e_(msg: str) -> str:
            """unescape discord markdown characters
            Parameters
            ----------
                msg: string
                    the text to remove escape characters from
            Returns
            -------
                the message excluding escape characters
            """

            return re.sub(r"\\(\*|~|_|\||`)", r"\1", msg)

        components = [
            disnake.ui.TextInput(
                label=f"Code",
                custom_id=f"code",
                required=False,
                style=disnake.TextInputStyle.paragraph,
                max_length=750,
            )
        ]
        t_ = int(datetime.now().timestamp())
        await ctx.response.send_modal(
            title="Code", custom_id=f"basicembed-{t_}", components=components
        )

        def check(res: disnake.ModalInteraction):
            return (
                ctx.author.id == res.author.id and res.custom_id == f"basicembed-{t_}"
            )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            return None, None

        code = modal_inter.text_values.get("code")

        embed = disnake.Embed(title="Query", description=f"```py\n{code}```")
        await modal_inter.send(embed=embed)

        stmts = cleanup_code(e_(code))
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(stmts, "  ")}'

        env = {"self": self, "ctx": ctx}
        env.update(globals())

        exec(to_compile, env)

        func = env["func"]

        with redirect_stdout(stdout):
            ret = await func()

        value = stdout.getvalue()
        values = value.split("\n")
        buf = f"{len(values)} lines output\n"
        buffer = []
        for v in values:
            if len(v) < 4000:
                if len(buf) + len(v) < 500:
                    buf += v + "\n"
                else:
                    buffer.append(buf)
                    buf = v + "\n"
            else:
                for x in range(0, len(v), 4000):
                    if x + 4000 < len(v):
                        buffer.append(v[x : x + 4000])
                    else:
                        buffer.append(v[x:])
        buffer.append(buf)
        for i, b in enumerate(buffer):
            await ctx.followup.send(embed=disnake.Embed(description=f"```py\n{b}```"))
        if ret is not None:
            ret = ret.split("\n")
            buf = f"{len(ret)} lines output\n"
            buffer = []
            for v in ret:
                if len(buf) + len(v) < 500:
                    buf += v + "\n"
                else:
                    buffer.append(buf)
                    buf = v + "\n"
            buffer.append(buf)
            for i, b in enumerate(buffer):
                await ctx.followup.send(
                    embed=disnake.Embed(description=f"```py\n{b}```")
                )

    @commands.slash_command(name="test", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def test(self, ctx: disnake.ApplicationCommandInteraction):
        event = {
            "trigger": "townHallLevel",
            "old_player": {
                "tag": "#8PPUCGPYV",
                "name": "SUSMITCR7",
                "townHallLevel": 10,
                "expLevel": 102,
                "trophies": 2278,
                "bestTrophies": 2345,
                "warStars": 310,
                "attackWins": 58,
                "defenseWins": 2,
                "builderHallLevel": 5,
                "builderBaseTrophies": 1741,
                "bestBuilderBaseTrophies": 1814,
                "role": "member",
                "warPreference": "in",
                "donations": 0,
                "donationsReceived": 0,
                "clanCapitalContributions": 0,
                "clan": {
                    "tag": "#2QJGQLVJ9",
                    "name": "BØRN FØR WAŘ",
                    "clanLevel": 22,
                    "badgeUrls": {
                        "small": "https://api-assets.clashofclans.com/badges/70/c9uHJQHQ4P7-ZcVAauv6janOXV-8vhnF29GhQMN7hQ8.png",
                        "large": "https://api-assets.clashofclans.com/badges/512/c9uHJQHQ4P7-ZcVAauv6janOXV-8vhnF29GhQMN7hQ8.png",
                        "medium": "https://api-assets.clashofclans.com/badges/200/c9uHJQHQ4P7-ZcVAauv6janOXV-8vhnF29GhQMN7hQ8.png",
                    },
                },
                "league": {
                    "id": 29000011,
                    "name": "Crystal League II",
                    "iconUrls": {
                        "small": "https://api-assets.clashofclans.com/leagues/72/jhP36EhAA9n1ADafdQtCP-ztEAQjoRpY7cT8sU7SW8A.png",
                        "tiny": "https://api-assets.clashofclans.com/leagues/36/jhP36EhAA9n1ADafdQtCP-ztEAQjoRpY7cT8sU7SW8A.png",
                        "medium": "https://api-assets.clashofclans.com/leagues/288/jhP36EhAA9n1ADafdQtCP-ztEAQjoRpY7cT8sU7SW8A.png",
                    },
                },
                "builderBaseLeague": {"id": 44000017, "name": "Copper League III"},
                "achievements": [
                    {
                        "name": "Bigger Coffers",
                        "stars": 3,
                        "value": 11,
                        "target": 10,
                        "info": "Upgrade a Gold Storage to level 10",
                        "completionInfo": "Highest Gold Storage level: 11",
                        "village": "home",
                    },
                    {
                        "name": "Get even more Goblins!",
                        "stars": 1,
                        "value": 45,
                        "target": 255,
                        "info": "Win 255 Stars on the Campaign Map",
                        "completionInfo": "Stars in Campaign Map: 45",
                        "village": "home",
                    },
                    {
                        "name": "Bigger & Better",
                        "stars": 3,
                        "value": 10,
                        "target": 8,
                        "info": "Upgrade Town Hall to level 8",
                        "completionInfo": "Current Town Hall level: 10",
                        "village": "home",
                    },
                    {
                        "name": "Nice and Tidy",
                        "stars": 3,
                        "value": 1295,
                        "target": 500,
                        "info": "Remove 500 obstacles (trees, rocks, bushes)",
                        "completionInfo": "Total obstacles removed: 1295",
                        "village": "home",
                    },
                    {
                        "name": "Discover New Troops",
                        "stars": 3,
                        "value": 1,
                        "target": 1,
                        "info": "Unlock Dragon in the Barracks",
                        "completionInfo": None,
                        "village": "home",
                    },
                    {
                        "name": "Gold Grab",
                        "stars": 3,
                        "value": 252359776,
                        "target": 100000000,
                        "info": "Steal 100000000 Gold",
                        "completionInfo": "Total Gold looted: 252359776",
                        "village": "home",
                    },
                    {
                        "name": "Elixir Escapade",
                        "stars": 3,
                        "value": 269042088,
                        "target": 100000000,
                        "info": "Steal 100000000 elixir",
                        "completionInfo": "Total Elixir looted: 269042088",
                        "village": "home",
                    },
                    {
                        "name": "Sweet Victory!",
                        "stars": 3,
                        "value": 2345,
                        "target": 1250,
                        "info": "Achieve a total of 1250 trophies in Multiplayer battles",
                        "completionInfo": "Trophy record: 2345",
                        "village": "home",
                    },
                    {
                        "name": "Empire Builder",
                        "stars": 3,
                        "value": 6,
                        "target": 4,
                        "info": "Upgrade Clan Castle to level 4",
                        "completionInfo": "Current Clan Castle level: 6",
                        "village": "home",
                    },
                    {
                        "name": "Wall Buster",
                        "stars": 3,
                        "value": 9252,
                        "target": 2000,
                        "info": "Destroy 2000 Walls in Multiplayer battles",
                        "completionInfo": "Total Walls destroyed: 9252",
                        "village": "home",
                    },
                    {
                        "name": "Humiliator",
                        "stars": 2,
                        "value": 785,
                        "target": 2000,
                        "info": "Destroy 2000 Town Halls in Multiplayer battles",
                        "completionInfo": "Total Town Halls destroyed: 785",
                        "village": "home",
                    },
                    {
                        "name": "Union Buster",
                        "stars": 3,
                        "value": 2665,
                        "target": 2500,
                        "info": "Destroy 2500 Builder's Huts in Multiplayer battles",
                        "completionInfo": "Total Builder's Huts destroyed: 2665",
                        "village": "home",
                    },
                    {
                        "name": "Conqueror",
                        "stars": 2,
                        "value": 952,
                        "target": 5000,
                        "info": "Win 5000 Multiplayer battles",
                        "completionInfo": "Total multiplayer battles won: 952",
                        "village": "home",
                    },
                    {
                        "name": "Unbreakable",
                        "stars": 1,
                        "value": 206,
                        "target": 250,
                        "info": "Successfully defend against 250 attacks",
                        "completionInfo": "Total defenses won: 206",
                        "village": "home",
                    },
                    {
                        "name": "Friend in Need",
                        "stars": 1,
                        "value": 3432,
                        "target": 5000,
                        "info": "Donate 5000 capacity worth of reinforcements to Clanmates",
                        "completionInfo": "Total capacity donated: 3432",
                        "village": "home",
                    },
                    {
                        "name": "Mortar Mauler",
                        "stars": 2,
                        "value": 2743,
                        "target": 5000,
                        "info": "Destroy 5000 Mortars in Multiplayer battles",
                        "completionInfo": "Total Mortars destroyed: 2743",
                        "village": "home",
                    },
                    {
                        "name": "Heroic Heist",
                        "stars": 3,
                        "value": 1235374,
                        "target": 1000000,
                        "info": "Steal 1000000 Dark Elixir",
                        "completionInfo": "Total Dark Elixir looted: 1235374",
                        "village": "home",
                    },
                    {
                        "name": "League All-Star",
                        "stars": 1,
                        "value": 11,
                        "target": 1,
                        "info": "Reach the Masters League",
                        "completionInfo": None,
                        "village": "home",
                    },
                    {
                        "name": "X-Bow Exterminator",
                        "stars": 2,
                        "value": 337,
                        "target": 2500,
                        "info": "Destroy 2500 X-Bows in Multiplayer battles",
                        "completionInfo": "Total X-Bows destroyed: 337",
                        "village": "home",
                    },
                    {
                        "name": "Firefighter",
                        "stars": 1,
                        "value": 84,
                        "target": 250,
                        "info": "Destroy 250 Inferno Towers in Multiplayer battles",
                        "completionInfo": "Total Inferno Towers destroyed: 84",
                        "village": "home",
                    },
                    {
                        "name": "War Hero",
                        "stars": 2,
                        "value": 310,
                        "target": 1000,
                        "info": "Score 1000 Stars for your clan in Clan War battles",
                        "completionInfo": "Total Stars scored for clan in Clan War battles: 310",
                        "village": "home",
                    },
                    {
                        "name": "Clan War Wealth",
                        "stars": 2,
                        "value": 67937634,
                        "target": 100000000,
                        "info": "Collect 100000000 Gold from the Clan Castle",
                        "completionInfo": "Total Gold collected in Clan War bonuses: 67937634",
                        "village": "home",
                    },
                    {
                        "name": "Anti-Artillery",
                        "stars": 0,
                        "value": 1,
                        "target": 20,
                        "info": "Destroy 20 Eagle Artilleries in Multiplayer battles",
                        "completionInfo": "Total Eagle Artilleries destroyed: 1",
                        "village": "home",
                    },
                    {
                        "name": "Sharing is caring",
                        "stars": 0,
                        "value": 46,
                        "target": 100,
                        "info": "Donate 100 Spell storage capacity worth of Spells",
                        "completionInfo": "Total Spell capacity donated: 46",
                        "village": "home",
                    },
                    {
                        "name": "Keep Your Account Safe!",
                        "stars": 0,
                        "value": 0,
                        "target": 1,
                        "info": "Protect your Village by connecting to a social network",
                        "completionInfo": "Completed!",
                        "village": "home",
                    },
                    {
                        "name": "Master Engineering",
                        "stars": 2,
                        "value": 5,
                        "target": 8,
                        "info": "Upgrade Builder Hall to level 8",
                        "completionInfo": "Current Builder Hall level: 5",
                        "village": "builderBase",
                    },
                    {
                        "name": "Next Generation Model",
                        "stars": 1,
                        "value": 1,
                        "target": 1,
                        "info": "Unlock Sneaky Archer in the Builder Barracks",
                        "completionInfo": None,
                        "village": "builderBase",
                    },
                    {
                        "name": "Un-Build It",
                        "stars": 2,
                        "value": 264,
                        "target": 2000,
                        "info": "Destroy 2000 Builder Halls in Builder Battles",
                        "completionInfo": "Total Builder Halls destroyed: 264",
                        "village": "builderBase",
                    },
                    {
                        "name": "Champion Builder",
                        "stars": 2,
                        "value": 1814,
                        "target": 3000,
                        "info": "Achieve a total of 3000 trophies in Builder Battles",
                        "completionInfo": "Builder Trophy record: 1814",
                        "village": "builderBase",
                    },
                    {
                        "name": "High Gear",
                        "stars": 1,
                        "value": 1,
                        "target": 2,
                        "info": "Gear Up 2 buildings using the Master Builder",
                        "completionInfo": "Total buildings geared up: 1",
                        "village": "builderBase",
                    },
                    {
                        "name": "Hidden Treasures",
                        "stars": 3,
                        "value": 1,
                        "target": 1,
                        "info": "Rebuild Battle Machine",
                        "completionInfo": None,
                        "village": "builderBase",
                    },
                    {
                        "name": "Games Champion",
                        "stars": 0,
                        "value": 1600,
                        "target": 10000,
                        "info": "Earn 10000 points in Clan Games",
                        "completionInfo": "Total Clan Games points: 1600",
                        "village": "home",
                    },
                    {
                        "name": "Dragon Slayer",
                        "stars": 0,
                        "value": 0,
                        "target": 1,
                        "info": "Slay the Giant Dragon on the Campaign Map",
                        "completionInfo": None,
                        "village": "home",
                    },
                    {
                        "name": "War League Legend",
                        "stars": 0,
                        "value": 0,
                        "target": 20,
                        "info": "Score 20 Stars for your clan in War League battles",
                        "completionInfo": "Total Stars scored for clan in War League battles: 0",
                        "village": "home",
                    },
                    {
                        "name": "Keep Your Account Safe!",
                        "stars": 0,
                        "value": 0,
                        "target": 1,
                        "info": "Connect your account to Supercell ID for safe keeping.",
                        "completionInfo": "Completed!",
                        "village": "home",
                    },
                    {
                        "name": "Well Seasoned",
                        "stars": 1,
                        "value": 7280,
                        "target": 15000,
                        "info": "Earn 15000 points in Season Challenges",
                        "completionInfo": "Total Season Challenges points: 7280",
                        "village": "home",
                    },
                    {
                        "name": "Shattered and Scattered",
                        "stars": 0,
                        "value": 0,
                        "target": 40,
                        "info": "Destroy 40 Scattershots in Multiplayer battles",
                        "completionInfo": "Total Scattershots destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Not So Easy This Time",
                        "stars": 0,
                        "value": 0,
                        "target": 10,
                        "info": "Destroy 10 weaponized Town Halls in Multiplayer battles",
                        "completionInfo": "Weaponized Town Halls destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Bust This!",
                        "stars": 0,
                        "value": 0,
                        "target": 25,
                        "info": "Destroy 25 weaponized Builder's Huts in Multiplayer battles",
                        "completionInfo": "Total weaponized Builder's Huts destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Superb Work",
                        "stars": 0,
                        "value": 0,
                        "target": 20,
                        "info": "Boost a Super Troop 20 times",
                        "completionInfo": "Total times Super Troops boosted: 0",
                        "village": "home",
                    },
                    {
                        "name": "Siege Sharer",
                        "stars": 0,
                        "value": 0,
                        "target": 50,
                        "info": "Donate 50 Siege Machines",
                        "completionInfo": "Total Siege Machines donated: 0",
                        "village": "home",
                    },
                    {
                        "name": "Aggressive Capitalism",
                        "stars": 1,
                        "value": 78500,
                        "target": 250000,
                        "info": "Loot 250000 Capital Gold during Raid attacks",
                        "completionInfo": "Total Capital Gold looted: 78500",
                        "village": "clanCapital",
                    },
                    {
                        "name": "Most Valuable Clanmate",
                        "stars": 0,
                        "value": 0,
                        "target": 40000,
                        "info": "Contribute 40000 Capital Gold to upgrades in the Clan Capital",
                        "completionInfo": "Total Capital Gold contributed: 0",
                        "village": "clanCapital",
                    },
                    {
                        "name": "Counterspell",
                        "stars": 0,
                        "value": 0,
                        "target": 40,
                        "info": "Destroy 40 Spell Towers in Multiplayer Battles",
                        "completionInfo": "Total Spell Towers Destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Monolith Masher",
                        "stars": 0,
                        "value": 0,
                        "target": 20,
                        "info": "Destroy 20 Monoliths in Multiplayer Battles",
                        "completionInfo": "Total Monoliths Destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Ungrateful Child",
                        "stars": 0,
                        "value": 0,
                        "target": 1,
                        "info": "Defeat M.O.M.M.A on the Campaign Map",
                        "completionInfo": None,
                        "village": "home",
                    },
                ],
                "labels": [],
                "troops": [
                    {
                        "name": "Barbarian",
                        "level": 6,
                        "maxLevel": 12,
                        "village": "home",
                    },
                    {"name": "Archer", "level": 6, "maxLevel": 12, "village": "home"},
                    {"name": "Goblin", "level": 6, "maxLevel": 9, "village": "home"},
                    {"name": "Giant", "level": 6, "maxLevel": 12, "village": "home"},
                    {
                        "name": "Wall Breaker",
                        "level": 5,
                        "maxLevel": 12,
                        "village": "home",
                    },
                    {"name": "Balloon", "level": 6, "maxLevel": 11, "village": "home"},
                    {"name": "Wizard", "level": 6, "maxLevel": 12, "village": "home"},
                    {"name": "Healer", "level": 4, "maxLevel": 9, "village": "home"},
                    {"name": "Dragon", "level": 4, "maxLevel": 11, "village": "home"},
                    {
                        "name": "P.E.K.K.A",
                        "level": 4,
                        "maxLevel": 11,
                        "village": "home",
                    },
                    {"name": "Minion", "level": 5, "maxLevel": 12, "village": "home"},
                    {
                        "name": "Hog Rider",
                        "level": 5,
                        "maxLevel": 13,
                        "village": "home",
                    },
                    {"name": "Valkyrie", "level": 4, "maxLevel": 11, "village": "home"},
                    {"name": "Golem", "level": 4, "maxLevel": 13, "village": "home"},
                    {"name": "Witch", "level": 3, "maxLevel": 7, "village": "home"},
                    {
                        "name": "Lava Hound",
                        "level": 2,
                        "maxLevel": 6,
                        "village": "home",
                    },
                    {"name": "Bowler", "level": 2, "maxLevel": 8, "village": "home"},
                    {
                        "name": "Baby Dragon",
                        "level": 2,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {"name": "Miner", "level": 1, "maxLevel": 10, "village": "home"},
                    {
                        "name": "Super Barbarian",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Archer",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Wall Breaker",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Giant",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Raged Barbarian",
                        "level": 8,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Sneaky Archer",
                        "level": 8,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Beta Minion",
                        "level": 8,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Boxer Giant",
                        "level": 10,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Bomber",
                        "level": 8,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Baby Dragon",
                        "level": 10,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Sneaky Goblin",
                        "level": 1,
                        "maxLevel": 5,
                        "village": "home",
                    },
                    {
                        "name": "Super Miner",
                        "level": 1,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {
                        "name": "Rocket Balloon",
                        "level": 1,
                        "maxLevel": 7,
                        "village": "home",
                    },
                    {
                        "name": "Inferno Dragon",
                        "level": 1,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {
                        "name": "Super Valkyrie",
                        "level": 1,
                        "maxLevel": 11,
                        "village": "home",
                    },
                    {
                        "name": "Super Witch",
                        "level": 1,
                        "maxLevel": 7,
                        "village": "home",
                    },
                    {"name": "Ice Hound", "level": 1, "maxLevel": 6, "village": "home"},
                    {
                        "name": "Super Bowler",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Dragon",
                        "level": 1,
                        "maxLevel": 9,
                        "village": "home",
                    },
                    {
                        "name": "Super Wizard",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Minion",
                        "level": 1,
                        "maxLevel": 9,
                        "village": "home",
                    },
                    {
                        "name": "Super Hog Rider",
                        "level": 1,
                        "maxLevel": 10,
                        "village": "home",
                    },
                ],
                "heroes": [
                    {
                        "name": "Barbarian King",
                        "level": 30,
                        "maxLevel": 95,
                        "equipment": [
                            {
                                "name": "Earthquake Boots",
                                "level": 8,
                                "maxLevel": 18,
                                "village": "home",
                            },
                            {
                                "name": "Rage Vial",
                                "level": 8,
                                "maxLevel": 18,
                                "village": "home",
                            },
                        ],
                        "village": "home",
                    },
                    {
                        "name": "Archer Queen",
                        "level": 29,
                        "maxLevel": 95,
                        "equipment": [
                            {
                                "name": "Giant Arrow",
                                "level": 9,
                                "maxLevel": 18,
                                "village": "home",
                            },
                            {
                                "name": "Invisibility Vial",
                                "level": 9,
                                "maxLevel": 18,
                                "village": "home",
                            },
                        ],
                        "village": "home",
                    },
                    {
                        "name": "Battle Machine",
                        "level": 3,
                        "maxLevel": 35,
                        "village": "builderBase",
                    },
                ],
                "heroEquipment": [
                    {
                        "name": "Barbarian Puppet",
                        "level": 2,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Rage Vial",
                        "level": 8,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Archer Puppet",
                        "level": 2,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Invisibility Vial",
                        "level": 9,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Earthquake Boots",
                        "level": 8,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Giant Arrow",
                        "level": 9,
                        "maxLevel": 18,
                        "village": "home",
                    },
                ],
                "spells": [
                    {
                        "name": "Lightning Spell",
                        "level": 6,
                        "maxLevel": 11,
                        "village": "home",
                    },
                    {
                        "name": "Healing Spell",
                        "level": 6,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {
                        "name": "Rage Spell",
                        "level": 5,
                        "maxLevel": 6,
                        "village": "home",
                    },
                    {
                        "name": "Jump Spell",
                        "level": 2,
                        "maxLevel": 5,
                        "village": "home",
                    },
                    {
                        "name": "Freeze Spell",
                        "level": 2,
                        "maxLevel": 7,
                        "village": "home",
                    },
                    {
                        "name": "Poison Spell",
                        "level": 3,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {
                        "name": "Earthquake Spell",
                        "level": 3,
                        "maxLevel": 5,
                        "village": "home",
                    },
                    {
                        "name": "Haste Spell",
                        "level": 2,
                        "maxLevel": 5,
                        "village": "home",
                    },
                    {
                        "name": "Clone Spell",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Skeleton Spell",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                ],
            },
            "new_player": {
                "tag": "#8PPUCGPYV",
                "name": "SUSMITCR7",
                "townHallLevel": 10,
                "expLevel": 102,
                "trophies": 2278,
                "bestTrophies": 2345,
                "warStars": 310,
                "attackWins": 58,
                "defenseWins": 2,
                "builderHallLevel": 5,
                "builderBaseTrophies": 1741,
                "bestBuilderBaseTrophies": 1814,
                "role": "member",
                "warPreference": "in",
                "donations": 0,
                "donationsReceived": 0,
                "clanCapitalContributions": 0,
                "clan": {
                    "tag": "#2QJGQLVJ9",
                    "name": "BØRN FØR WAŘ",
                    "clanLevel": 22,
                    "badgeUrls": {
                        "small": "https://api-assets.clashofclans.com/badges/70/c9uHJQHQ4P7-ZcVAauv6janOXV-8vhnF29GhQMN7hQ8.png",
                        "large": "https://api-assets.clashofclans.com/badges/512/c9uHJQHQ4P7-ZcVAauv6janOXV-8vhnF29GhQMN7hQ8.png",
                        "medium": "https://api-assets.clashofclans.com/badges/200/c9uHJQHQ4P7-ZcVAauv6janOXV-8vhnF29GhQMN7hQ8.png",
                    },
                },
                "league": {
                    "id": 29000011,
                    "name": "Crystal League II",
                    "iconUrls": {
                        "small": "https://api-assets.clashofclans.com/leagues/72/jhP36EhAA9n1ADafdQtCP-ztEAQjoRpY7cT8sU7SW8A.png",
                        "tiny": "https://api-assets.clashofclans.com/leagues/36/jhP36EhAA9n1ADafdQtCP-ztEAQjoRpY7cT8sU7SW8A.png",
                        "medium": "https://api-assets.clashofclans.com/leagues/288/jhP36EhAA9n1ADafdQtCP-ztEAQjoRpY7cT8sU7SW8A.png",
                    },
                },
                "builderBaseLeague": {"id": 44000017, "name": "Copper League III"},
                "achievements": [
                    {
                        "name": "Bigger Coffers",
                        "stars": 3,
                        "value": 11,
                        "target": 10,
                        "info": "Upgrade a Gold Storage to level 10",
                        "completionInfo": "Highest Gold Storage level: 11",
                        "village": "home",
                    },
                    {
                        "name": "Get even more Goblins!",
                        "stars": 1,
                        "value": 45,
                        "target": 255,
                        "info": "Win 255 Stars on the Campaign Map",
                        "completionInfo": "Stars in Campaign Map: 45",
                        "village": "home",
                    },
                    {
                        "name": "Bigger & Better",
                        "stars": 3,
                        "value": 10,
                        "target": 8,
                        "info": "Upgrade Town Hall to level 8",
                        "completionInfo": "Current Town Hall level: 10",
                        "village": "home",
                    },
                    {
                        "name": "Nice and Tidy",
                        "stars": 3,
                        "value": 1295,
                        "target": 500,
                        "info": "Remove 500 obstacles (trees, rocks, bushes)",
                        "completionInfo": "Total obstacles removed: 1295",
                        "village": "home",
                    },
                    {
                        "name": "Discover New Troops",
                        "stars": 3,
                        "value": 1,
                        "target": 1,
                        "info": "Unlock Dragon in the Barracks",
                        "completionInfo": None,
                        "village": "home",
                    },
                    {
                        "name": "Gold Grab",
                        "stars": 3,
                        "value": 252359776,
                        "target": 100000000,
                        "info": "Steal 100000000 Gold",
                        "completionInfo": "Total Gold looted: 252359776",
                        "village": "home",
                    },
                    {
                        "name": "Elixir Escapade",
                        "stars": 3,
                        "value": 269042088,
                        "target": 100000000,
                        "info": "Steal 100000000 elixir",
                        "completionInfo": "Total Elixir looted: 269042088",
                        "village": "home",
                    },
                    {
                        "name": "Sweet Victory!",
                        "stars": 3,
                        "value": 2345,
                        "target": 1250,
                        "info": "Achieve a total of 1250 trophies in Multiplayer battles",
                        "completionInfo": "Trophy record: 2345",
                        "village": "home",
                    },
                    {
                        "name": "Empire Builder",
                        "stars": 3,
                        "value": 6,
                        "target": 4,
                        "info": "Upgrade Clan Castle to level 4",
                        "completionInfo": "Current Clan Castle level: 6",
                        "village": "home",
                    },
                    {
                        "name": "Wall Buster",
                        "stars": 3,
                        "value": 9252,
                        "target": 2000,
                        "info": "Destroy 2000 Walls in Multiplayer battles",
                        "completionInfo": "Total Walls destroyed: 9252",
                        "village": "home",
                    },
                    {
                        "name": "Humiliator",
                        "stars": 2,
                        "value": 785,
                        "target": 2000,
                        "info": "Destroy 2000 Town Halls in Multiplayer battles",
                        "completionInfo": "Total Town Halls destroyed: 785",
                        "village": "home",
                    },
                    {
                        "name": "Union Buster",
                        "stars": 3,
                        "value": 2665,
                        "target": 2500,
                        "info": "Destroy 2500 Builder's Huts in Multiplayer battles",
                        "completionInfo": "Total Builder's Huts destroyed: 2665",
                        "village": "home",
                    },
                    {
                        "name": "Conqueror",
                        "stars": 2,
                        "value": 952,
                        "target": 5000,
                        "info": "Win 5000 Multiplayer battles",
                        "completionInfo": "Total multiplayer battles won: 952",
                        "village": "home",
                    },
                    {
                        "name": "Unbreakable",
                        "stars": 1,
                        "value": 206,
                        "target": 250,
                        "info": "Successfully defend against 250 attacks",
                        "completionInfo": "Total defenses won: 206",
                        "village": "home",
                    },
                    {
                        "name": "Friend in Need",
                        "stars": 1,
                        "value": 3432,
                        "target": 5000,
                        "info": "Donate 5000 capacity worth of reinforcements to Clanmates",
                        "completionInfo": "Total capacity donated: 3432",
                        "village": "home",
                    },
                    {
                        "name": "Mortar Mauler",
                        "stars": 2,
                        "value": 2743,
                        "target": 5000,
                        "info": "Destroy 5000 Mortars in Multiplayer battles",
                        "completionInfo": "Total Mortars destroyed: 2743",
                        "village": "home",
                    },
                    {
                        "name": "Heroic Heist",
                        "stars": 3,
                        "value": 1235374,
                        "target": 1000000,
                        "info": "Steal 1000000 Dark Elixir",
                        "completionInfo": "Total Dark Elixir looted: 1235374",
                        "village": "home",
                    },
                    {
                        "name": "League All-Star",
                        "stars": 1,
                        "value": 11,
                        "target": 1,
                        "info": "Reach the Masters League",
                        "completionInfo": None,
                        "village": "home",
                    },
                    {
                        "name": "X-Bow Exterminator",
                        "stars": 2,
                        "value": 337,
                        "target": 2500,
                        "info": "Destroy 2500 X-Bows in Multiplayer battles",
                        "completionInfo": "Total X-Bows destroyed: 337",
                        "village": "home",
                    },
                    {
                        "name": "Firefighter",
                        "stars": 1,
                        "value": 84,
                        "target": 250,
                        "info": "Destroy 250 Inferno Towers in Multiplayer battles",
                        "completionInfo": "Total Inferno Towers destroyed: 84",
                        "village": "home",
                    },
                    {
                        "name": "War Hero",
                        "stars": 2,
                        "value": 310,
                        "target": 1000,
                        "info": "Score 1000 Stars for your clan in Clan War battles",
                        "completionInfo": "Total Stars scored for clan in Clan War battles: 310",
                        "village": "home",
                    },
                    {
                        "name": "Clan War Wealth",
                        "stars": 2,
                        "value": 67937634,
                        "target": 100000000,
                        "info": "Collect 100000000 Gold from the Clan Castle",
                        "completionInfo": "Total Gold collected in Clan War bonuses: 67937634",
                        "village": "home",
                    },
                    {
                        "name": "Anti-Artillery",
                        "stars": 0,
                        "value": 1,
                        "target": 20,
                        "info": "Destroy 20 Eagle Artilleries in Multiplayer battles",
                        "completionInfo": "Total Eagle Artilleries destroyed: 1",
                        "village": "home",
                    },
                    {
                        "name": "Sharing is caring",
                        "stars": 0,
                        "value": 46,
                        "target": 100,
                        "info": "Donate 100 Spell storage capacity worth of Spells",
                        "completionInfo": "Total Spell capacity donated: 46",
                        "village": "home",
                    },
                    {
                        "name": "Keep Your Account Safe!",
                        "stars": 0,
                        "value": 0,
                        "target": 1,
                        "info": "Protect your Village by connecting to a social network",
                        "completionInfo": "Completed!",
                        "village": "home",
                    },
                    {
                        "name": "Master Engineering",
                        "stars": 2,
                        "value": 5,
                        "target": 8,
                        "info": "Upgrade Builder Hall to level 8",
                        "completionInfo": "Current Builder Hall level: 5",
                        "village": "builderBase",
                    },
                    {
                        "name": "Next Generation Model",
                        "stars": 2,
                        "value": 1,
                        "target": 1,
                        "info": "Unlock Cannon Cart in the Builder Barracks",
                        "completionInfo": None,
                        "village": "builderBase",
                    },
                    {
                        "name": "Un-Build It",
                        "stars": 2,
                        "value": 264,
                        "target": 2000,
                        "info": "Destroy 2000 Builder Halls in Builder Battles",
                        "completionInfo": "Total Builder Halls destroyed: 264",
                        "village": "builderBase",
                    },
                    {
                        "name": "Champion Builder",
                        "stars": 2,
                        "value": 1814,
                        "target": 3000,
                        "info": "Achieve a total of 3000 trophies in Builder Battles",
                        "completionInfo": "Builder Trophy record: 1814",
                        "village": "builderBase",
                    },
                    {
                        "name": "High Gear",
                        "stars": 1,
                        "value": 1,
                        "target": 2,
                        "info": "Gear Up 2 buildings using the Master Builder",
                        "completionInfo": "Total buildings geared up: 1",
                        "village": "builderBase",
                    },
                    {
                        "name": "Hidden Treasures",
                        "stars": 3,
                        "value": 1,
                        "target": 1,
                        "info": "Rebuild Battle Machine",
                        "completionInfo": None,
                        "village": "builderBase",
                    },
                    {
                        "name": "Games Champion",
                        "stars": 0,
                        "value": 1600,
                        "target": 10000,
                        "info": "Earn 10000 points in Clan Games",
                        "completionInfo": "Total Clan Games points: 1600",
                        "village": "home",
                    },
                    {
                        "name": "Dragon Slayer",
                        "stars": 0,
                        "value": 0,
                        "target": 1,
                        "info": "Slay the Giant Dragon on the Campaign Map",
                        "completionInfo": None,
                        "village": "home",
                    },
                    {
                        "name": "War League Legend",
                        "stars": 0,
                        "value": 0,
                        "target": 20,
                        "info": "Score 20 Stars for your clan in War League battles",
                        "completionInfo": "Total Stars scored for clan in War League battles: 0",
                        "village": "home",
                    },
                    {
                        "name": "Keep Your Account Safe!",
                        "stars": 0,
                        "value": 0,
                        "target": 1,
                        "info": "Connect your account to Supercell ID for safe keeping.",
                        "completionInfo": "Completed!",
                        "village": "home",
                    },
                    {
                        "name": "Well Seasoned",
                        "stars": 1,
                        "value": 7280,
                        "target": 15000,
                        "info": "Earn 15000 points in Season Challenges",
                        "completionInfo": "Total Season Challenges points: 7280",
                        "village": "home",
                    },
                    {
                        "name": "Shattered and Scattered",
                        "stars": 0,
                        "value": 0,
                        "target": 40,
                        "info": "Destroy 40 Scattershots in Multiplayer battles",
                        "completionInfo": "Total Scattershots destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Not So Easy This Time",
                        "stars": 0,
                        "value": 0,
                        "target": 10,
                        "info": "Destroy 10 weaponized Town Halls in Multiplayer battles",
                        "completionInfo": "Weaponized Town Halls destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Bust This!",
                        "stars": 0,
                        "value": 0,
                        "target": 25,
                        "info": "Destroy 25 weaponized Builder's Huts in Multiplayer battles",
                        "completionInfo": "Total weaponized Builder's Huts destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Superb Work",
                        "stars": 0,
                        "value": 0,
                        "target": 20,
                        "info": "Boost a Super Troop 20 times",
                        "completionInfo": "Total times Super Troops boosted: 0",
                        "village": "home",
                    },
                    {
                        "name": "Siege Sharer",
                        "stars": 0,
                        "value": 0,
                        "target": 50,
                        "info": "Donate 50 Siege Machines",
                        "completionInfo": "Total Siege Machines donated: 0",
                        "village": "home",
                    },
                    {
                        "name": "Aggressive Capitalism",
                        "stars": 1,
                        "value": 78500,
                        "target": 250000,
                        "info": "Loot 250000 Capital Gold during Raid attacks",
                        "completionInfo": "Total Capital Gold looted: 78500",
                        "village": "clanCapital",
                    },
                    {
                        "name": "Most Valuable Clanmate",
                        "stars": 0,
                        "value": 0,
                        "target": 40000,
                        "info": "Contribute 40000 Capital Gold to upgrades in the Clan Capital",
                        "completionInfo": "Total Capital Gold contributed: 0",
                        "village": "clanCapital",
                    },
                    {
                        "name": "Counterspell",
                        "stars": 0,
                        "value": 0,
                        "target": 40,
                        "info": "Destroy 40 Spell Towers in Multiplayer Battles",
                        "completionInfo": "Total Spell Towers Destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Monolith Masher",
                        "stars": 0,
                        "value": 0,
                        "target": 20,
                        "info": "Destroy 20 Monoliths in Multiplayer Battles",
                        "completionInfo": "Total Monoliths Destroyed: 0",
                        "village": "home",
                    },
                    {
                        "name": "Ungrateful Child",
                        "stars": 0,
                        "value": 0,
                        "target": 1,
                        "info": "Defeat M.O.M.M.A on the Campaign Map",
                        "completionInfo": None,
                        "village": "home",
                    },
                ],
                "labels": [],
                "troops": [
                    {
                        "name": "Barbarian",
                        "level": 6,
                        "maxLevel": 12,
                        "village": "home",
                    },
                    {"name": "Archer", "level": 6, "maxLevel": 12, "village": "home"},
                    {"name": "Goblin", "level": 6, "maxLevel": 9, "village": "home"},
                    {"name": "Giant", "level": 6, "maxLevel": 12, "village": "home"},
                    {
                        "name": "Wall Breaker",
                        "level": 5,
                        "maxLevel": 12,
                        "village": "home",
                    },
                    {"name": "Balloon", "level": 6, "maxLevel": 11, "village": "home"},
                    {"name": "Wizard", "level": 6, "maxLevel": 12, "village": "home"},
                    {"name": "Healer", "level": 4, "maxLevel": 9, "village": "home"},
                    {"name": "Dragon", "level": 4, "maxLevel": 11, "village": "home"},
                    {
                        "name": "P.E.K.K.A",
                        "level": 4,
                        "maxLevel": 11,
                        "village": "home",
                    },
                    {"name": "Minion", "level": 5, "maxLevel": 12, "village": "home"},
                    {
                        "name": "Hog Rider",
                        "level": 5,
                        "maxLevel": 13,
                        "village": "home",
                    },
                    {"name": "Valkyrie", "level": 4, "maxLevel": 11, "village": "home"},
                    {"name": "Golem", "level": 4, "maxLevel": 13, "village": "home"},
                    {"name": "Witch", "level": 3, "maxLevel": 7, "village": "home"},
                    {
                        "name": "Lava Hound",
                        "level": 2,
                        "maxLevel": 6,
                        "village": "home",
                    },
                    {"name": "Bowler", "level": 2, "maxLevel": 8, "village": "home"},
                    {
                        "name": "Baby Dragon",
                        "level": 2,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {"name": "Miner", "level": 1, "maxLevel": 10, "village": "home"},
                    {
                        "name": "Super Barbarian",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Archer",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Wall Breaker",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Giant",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Raged Barbarian",
                        "level": 8,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Sneaky Archer",
                        "level": 8,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Beta Minion",
                        "level": 8,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Boxer Giant",
                        "level": 10,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Bomber",
                        "level": 8,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Cannon Cart",
                        "level": 1,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Baby Dragon",
                        "level": 10,
                        "maxLevel": 20,
                        "village": "builderBase",
                    },
                    {
                        "name": "Sneaky Goblin",
                        "level": 1,
                        "maxLevel": 5,
                        "village": "home",
                    },
                    {
                        "name": "Super Miner",
                        "level": 1,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {
                        "name": "Rocket Balloon",
                        "level": 1,
                        "maxLevel": 7,
                        "village": "home",
                    },
                    {
                        "name": "Inferno Dragon",
                        "level": 1,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {
                        "name": "Super Valkyrie",
                        "level": 1,
                        "maxLevel": 11,
                        "village": "home",
                    },
                    {
                        "name": "Super Witch",
                        "level": 1,
                        "maxLevel": 7,
                        "village": "home",
                    },
                    {"name": "Ice Hound", "level": 1, "maxLevel": 6, "village": "home"},
                    {
                        "name": "Super Bowler",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Dragon",
                        "level": 1,
                        "maxLevel": 9,
                        "village": "home",
                    },
                    {
                        "name": "Super Wizard",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Super Minion",
                        "level": 1,
                        "maxLevel": 9,
                        "village": "home",
                    },
                    {
                        "name": "Super Hog Rider",
                        "level": 1,
                        "maxLevel": 10,
                        "village": "home",
                    },
                ],
                "heroes": [
                    {
                        "name": "Barbarian King",
                        "level": 30,
                        "maxLevel": 95,
                        "equipment": [
                            {
                                "name": "Earthquake Boots",
                                "level": 8,
                                "maxLevel": 18,
                                "village": "home",
                            },
                            {
                                "name": "Rage Vial",
                                "level": 8,
                                "maxLevel": 18,
                                "village": "home",
                            },
                        ],
                        "village": "home",
                    },
                    {
                        "name": "Archer Queen",
                        "level": 29,
                        "maxLevel": 95,
                        "equipment": [
                            {
                                "name": "Giant Arrow",
                                "level": 9,
                                "maxLevel": 18,
                                "village": "home",
                            },
                            {
                                "name": "Invisibility Vial",
                                "level": 9,
                                "maxLevel": 18,
                                "village": "home",
                            },
                        ],
                        "village": "home",
                    },
                    {
                        "name": "Battle Machine",
                        "level": 3,
                        "maxLevel": 35,
                        "village": "builderBase",
                    },
                ],
                "heroEquipment": [
                    {
                        "name": "Barbarian Puppet",
                        "level": 2,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Rage Vial",
                        "level": 8,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Archer Puppet",
                        "level": 2,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Invisibility Vial",
                        "level": 9,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Earthquake Boots",
                        "level": 8,
                        "maxLevel": 18,
                        "village": "home",
                    },
                    {
                        "name": "Giant Arrow",
                        "level": 9,
                        "maxLevel": 18,
                        "village": "home",
                    },
                ],
                "spells": [
                    {
                        "name": "Lightning Spell",
                        "level": 6,
                        "maxLevel": 11,
                        "village": "home",
                    },
                    {
                        "name": "Healing Spell",
                        "level": 6,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {
                        "name": "Rage Spell",
                        "level": 5,
                        "maxLevel": 6,
                        "village": "home",
                    },
                    {
                        "name": "Jump Spell",
                        "level": 2,
                        "maxLevel": 5,
                        "village": "home",
                    },
                    {
                        "name": "Freeze Spell",
                        "level": 2,
                        "maxLevel": 7,
                        "village": "home",
                    },
                    {
                        "name": "Poison Spell",
                        "level": 3,
                        "maxLevel": 10,
                        "village": "home",
                    },
                    {
                        "name": "Earthquake Spell",
                        "level": 3,
                        "maxLevel": 5,
                        "village": "home",
                    },
                    {
                        "name": "Haste Spell",
                        "level": 2,
                        "maxLevel": 5,
                        "village": "home",
                    },
                    {
                        "name": "Clone Spell",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                    {
                        "name": "Skeleton Spell",
                        "level": 1,
                        "maxLevel": 8,
                        "village": "home",
                    },
                ],
            },
            "timestamp": 1718164947,
        }

        if (clan_data := event.get("clan")) is not None:
            clan_tag = clan_data.get("tag")
            clan_name = clan_data.get("name")
            player_tag = event.get("member").get("tag")
            player_name = event.get("member").get("name")
        else:
            player_tag = event.get("new_player").get("tag")
            clan_tag = event.get("new_player").get("clan", {}).get("tag", "")
            clan_name = event.get("new_player").get("clan", {}).get("name", "No Clan")
            player_name = event.get("new_player").get("name")

        server_ids = await self.bot.clan_db.distinct(
            "server", filter={"tag": "#2QJGQLVJ9"}
        )
        for server_id in server_ids:
            db_server = await self.bot.ck_client.get_server_settings(
                server_id=server_id
            )

            if db_server.server_id not in self.bot.OUR_GUILDS:
                continue

            convert_trigger = {
                "townHallLevel": "townhall_change",
                "role": "role_change",
                "league": "league_change",
            }
            if (
                trigger_name := convert_trigger.get(
                    event.get("trigger"), event.get("trigger")
                )
            ) not in db_server.autoeval_triggers:
                continue

            link = await self.bot.link_client.get_link("#2J8V28GV0")
            if link is not None:
                server = await self.bot.getch_guild(server_id)
                if server is None:
                    continue
                discord_member = await server.getch_member(link)
                if discord_member is None:
                    continue

                for role in discord_member.roles:
                    if role.id in db_server.blacklisted_roles:
                        return

                embeds = await logic(
                    bot=self.bot,
                    guild=server,
                    db_server=db_server,
                    members=[discord_member],
                    role_or_user=discord_member,
                    eval_types=DEFAULT_EVAL_ROLE_TYPES,
                    role_treatment=db_server.role_treatment,
                )
                # if db_server.auto_eval_log is not None:
                try:
                    channel = await self.bot.getch_channel(1197924424863731792)
                    await channel.send(
                        content=f"Trigger by {trigger_name}", embeds=embeds
                    )
                except (disnake.NotFound, disnake.Forbidden):
                    # await self.bot.server_db.update_one({"server": data.get("server")}, {'$set': {"autoeval_log": None}})
                    pass

    @commands.slash_command(name="anniversary", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def anniversary(self, ctx: disnake.ApplicationCommandInteraction):
        guild = ctx.guild
        await ctx.send(content="Starting")
        msg = await ctx.channel.send("Editing 0 Members")
        x = 0
        eighteen_month = disnake.utils.get(ctx.guild.roles, id=1183978690019864679)
        twelve_month = disnake.utils.get(ctx.guild.roles, id=1029249316981833748)
        nine_month = disnake.utils.get(ctx.guild.roles, id=1029249365858062366)
        six_month = disnake.utils.get(ctx.guild.roles, id=1029249360178987018)
        three_month = disnake.utils.get(ctx.guild.roles, id=1029249480261906463)
        for member in guild.members:
            if member.bot:
                continue
            if x % 25 == 0:
                await msg.edit(f"Editing {x} Members")
            year = member.joined_at.year
            month = member.joined_at.month
            n_year = datetime.now().year
            n_month = datetime.now().month
            num_months = (n_year - year) * 12 + (n_month - month)
            if num_months >= 18:
                if eighteen_month not in member.roles:
                    await member.add_roles(*[eighteen_month])
                if (
                    twelve_month in member.roles
                    or nine_month in member.roles
                    or six_month in member.roles
                    or three_month in member.roles
                ):
                    await member.remove_roles(
                        *[twelve_month, nine_month, six_month, three_month]
                    )
            elif num_months >= 12:
                if twelve_month not in member.roles:
                    await member.add_roles(*[twelve_month])
                if (
                    nine_month in member.roles
                    or six_month in member.roles
                    or three_month in member.roles
                ):
                    await member.remove_roles(*[nine_month, six_month, three_month])
            elif num_months >= 9:
                if nine_month not in member.roles:
                    await member.add_roles(*[nine_month])
                if (
                    twelve_month in member.roles
                    or six_month in member.roles
                    or three_month in member.roles
                ):
                    await member.remove_roles(*[twelve_month, six_month, three_month])
            elif num_months >= 6:
                if six_month not in member.roles:
                    await member.add_roles(*[six_month])
                if (
                    twelve_month in member.roles
                    or nine_month in member.roles
                    or three_month in member.roles
                ):
                    await member.remove_roles(*[twelve_month, nine_month, three_month])
            elif num_months >= 3:
                if three_month not in member.roles:
                    await member.add_roles(*[three_month])
                if (
                    twelve_month in member.roles
                    or nine_month in member.roles
                    or six_month in member.roles
                ):
                    await member.remove_roles(*[twelve_month, nine_month, six_month])
            x += 1
        await msg.edit(content="Done")

    """
    @commands.slash_command(name="raid-map", description="See the live raid map", guild_ids=[923764211845312533])
    async def raid_map(self, ctx: disnake.ApplicationCommandInteraction, clan: str):
        await ctx.response.defer()
        clan = await self.bot.getClan(clan_tag=clan)
        weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot, limit=1)
        current_clan = weekend_raid_entry.attack_log[-1]

        background = Image.open("ImageGen/RaidMap.png")
        draw = ImageDraw.Draw(background)

        capital_names = ImageFont.truetype("ImageGen/SCmagic.ttf", 27)
        league_name_font = ImageFont.truetype("ImageGen/SCmagic.ttf", 35)

        paste_spot = {"Capital Peak" : (1025, 225), "Barbarian Camp" : (1360, 500), "Wizard Valley" : (1025, 675),
                      "Balloon Lagoon" : (750, 920), "Builder's Workshop" : (1250, 970)}
        text_spot = {"Wizard Valley" : (1128, 655), "Balloon Lagoon" : (845, 900), "Builder's Workshop" : (1300, 920)}
        for spot, district in enumerate(current_clan.districts):
            name = "District_Hall"
            if district.id == 70000000:
                name = "Capital_Hall"
            if district.id not in [70000000, 70000001]:
                draw.text(text_spot.get(district.name, (100, 100)), district.name, anchor="mm", fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0), font=capital_names)

            name = f"{name}{district.hall_level}"
            district_image = Image.open(f"ImageGen/CapitalDistricts/{name}.png")
            size = 212, 200
            district_image = district_image.resize(size, Image.ANTIALIAS)
            area = paste_spot.get(district.name, (100, 106))
            background.paste(district_image, area, district_image.convert("RGBA"))

        def save_im(background):
            # background.show()
            temp = io.BytesIO()
            #background = background.resize((725, 471))
            # background = background.resize((1036, 673))
            background.save(temp, format="png", compress_level=1)
            temp.seek(0)
            file = disnake.File(fp=temp, filename="filename.png")
            temp.close()
            return file

        loop = asyncio.get_event_loop()
        file = await loop.run_in_executor(None, save_im, background)

        await ctx.send(file=file)

    @commands.slash_command(name="cwl-image", description="Image showing cwl rankings & th comps",
                            guild_ids=[923764211845312533])
    async def testthis(self, ctx: disnake.ApplicationCommandInteraction, clan: str):
        await ctx.response.defer()
        tag = clan
        try:
            base_clan = await self.bot.getClan(clan_tag=tag)
            cwl: coc.ClanWarLeagueGroup = await self.bot.coc_client.get_league_group(clan_tag=base_clan.tag)
        except:
            return await ctx.send(content="Clan not in cwl")

        background = Image.open("ImageGen/cwlbk.png")
        clan_name = ImageFont.truetype("ImageGen/SCmagic.ttf", 30)
        league_name_font = ImageFont.truetype("ImageGen/SCmagic.ttf", 35)
        numbers = ImageFont.truetype("ImageGen/SCmagic.ttf", 35)
        small_numbers = ImageFont.truetype("ImageGen/SCmagic.ttf", 15)
        stat_numbers = ImageFont.truetype("ImageGen/SCmagic.ttf", 25)
        perc_numbers = ImageFont.truetype("ImageGen/SCmagic.ttf", 20)

        draw = ImageDraw.Draw(background)
        stroke = 4
        star_dict = defaultdict(int)
        dest_dict = defaultdict(int)
        tag_to_obj = defaultdict(str)

        for round in cwl.rounds:
            for war_tag in round:
                war = await self.bot.coc_client.get_league_war(war_tag)
                war: coc.ClanWar
                if str(war.status) == "won":
                    star_dict[war.clan.tag] += 10
                elif str(war.status) == "lost":
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
                background.paste(badge, (200, 645 + (105 * count)), badge.convert("RGBA"))
            if clan.tag == base_clan.tag:
                color = (136, 193, 229)
            else:
                color = (255, 255, 255)
            draw.text((315, 690 + (106 * count)), f"{clan.name[:17]}", anchor="lm", fill=color, stroke_width=stroke,
                      stroke_fill=(0, 0, 0), font=clan_name)
            promo = [x["promo"] for x in war_leagues["items"] if x["name"] == base_clan.war_league.name][0]
            demo = [x["demote"] for x in war_leagues["items"] if x["name"] == base_clan.war_league.name][0]
            extra = 0
            if count + 1 <= promo:
                placement_img = Image.open("ImageGen/league_badges/2168_0.png")
                color = (166, 217, 112)
            elif count + 1 >= demo:
                placement_img = Image.open("ImageGen/league_badges/2170_0.png")
                color = (232, 16, 17)
            else:
                placement_img = Image.open("ImageGen/league_badges/2169_0.png")
                extra = 15
                color = (255, 255, 255)

            draw.text((100, 690 + (106 * count)), f"{count + 1}.", anchor="lm", fill=color, stroke_width=stroke,
                      stroke_fill=(0, 0, 0), font=numbers)
            size = 100, 100
            placement_img.thumbnail(size, Image.ANTIALIAS)
            background.paste(placement_img, (30, 663 + (107 * count) + extra), placement_img.convert("RGBA"))

            thcount = defaultdict(int)

            for player in clan.members:
                thcount[player.town_hall] += 1
            spot = 0
            for th_level, th_count in sorted(thcount.items(), reverse=True):
                e_ = ""
                if th_level >= 13:
                    e_ = "-2"
                th_img = Image.open(f"Assets/th_pics/town-hall-{th_level}{e_}.png")
                size = 60, 60
                th_img.thumbnail(size, Image.ANTIALIAS)
                spot += 1
                background.paste(th_img, (635 + (80 * spot), 662 + (106 * count)), th_img.convert("RGBA"))
                draw.text((635 + (80 * spot), 662 + (106 * count)), f"{th_count}", anchor="mm", fill=(255, 255, 255),
                          stroke_width=stroke, stroke_fill=(0, 0, 0), font=small_numbers)
                if spot >= 7:
                    break

            star_img = Image.open(f"ImageGen/league_badges/679_0.png")
            size = 45, 45
            star_img.thumbnail(size, Image.ANTIALIAS)
            # if 2 <=count < 7:

            background.paste(star_img, (1440, 665 + (106 * count)), star_img.convert("RGBA"))
            draw.text((1400, 685 + (107 * count)), f"{stars}", anchor="mm", fill=(255, 255, 255), stroke_width=stroke,
                      stroke_fill=(0, 0, 0), font=stat_numbers)
            draw.text((1647, 685 + (107 * count)), f"{int(destruction)}%", anchor="mm", fill=(255, 255, 255),
                      stroke_width=stroke, stroke_fill=(0, 0, 0), font=perc_numbers)

        league_name = f"War{base_clan.war_league.name.replace('League', '').replace(' ', '')}.png"
        league_img = Image.open(f"ImageGen/league_badges/{league_name}")
        size = 400, 400
        league_img = league_img.resize(size, Image.ANTIALIAS)
        background.paste(league_img, (785, 80), league_img.convert("RGBA"))

        draw.text((975, 520), f"{base_clan.war_league}", anchor="mm", fill=(255, 255, 255), stroke_width=stroke,
                  stroke_fill=(0, 0, 0), font=league_name_font)
        draw.text((515, 135), f"{len(cwl.rounds)}/{len(cwl.clans) - 1}", anchor="mm", fill=(255, 255, 255),
                  stroke_width=stroke, stroke_fill=(0, 0, 0), font=league_name_font)

        start = coc.utils.get_season_start().replace(tzinfo=pytz.utc).date()
        month = start.month
        if month == 12:
            month = 0
        month = calendar.month_name[month + 1]
        date_font = ImageFont.truetype("ImageGen/SCmagic.ttf", 24)
        draw.text((387, 75), f"{month} {start.year}", anchor="mm", fill=(237, 191, 33), stroke_width=3,
                  stroke_fill=(0, 0, 0), font=date_font)

        def save_im(background):
            # background.show()
            temp = io.BytesIO()
            # background = background.resize((725, 471))
            # background = background.resize((1036, 673))
            background.save(temp, format="png", compress_level=1)
            temp.seek(0)
            file = disnake.File(fp=temp, filename="filename.png")
            temp.close()
            return file

        loop = asyncio.get_event_loop()
        file = await loop.run_in_executor(None, save_im, background)

        await ctx.send(file=file)


    @commands.slash_command(name="create_war_ids", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def create_war_ids(self, ctx: disnake.ApplicationCommandInteraction):
        things = []
        for war in await self.bot.clan_wars.find({}).to_list(length=100000):
            war_id = war.get("war_id")
            if war.get("custom_id") is not None:
                continue
            source = string.ascii_letters
            custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()

            is_used = await self.bot.clan_wars.find_one({"custom_id": custom_id})
            while is_used is not None:
                custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()
                is_used = await self.bot.clan_wars.find_one({"custom_id": custom_id})

            things.append(UpdateOne({"war_id": war_id}, {"$set" : {"custom_id": custom_id}}))

        await self.bot.clan_wars.bulk_write(things)
        print("done")"""

    """@testthis.autocomplete("clan")
    @raid_map.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=5)
                for clan in results:
                    league = str(clan.war_league).replace("League ", "")
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]"""


def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))
