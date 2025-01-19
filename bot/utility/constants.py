import json
import disnake

CLASH_ISO_FORMAT = "YYYYMMDDTHHmmss.000[Z]"

# EVAL CONSTANTS
DEFAULT_EVAL_ROLE_TYPES = [
    'family',
    'only_family',
    'not_family',
    'clan',
    'leadership',
    'townhall',
    'builderhall',
    'category',
    'league',
    'builder_league',
    'nicknames',
]

ROLE_TREATMENT_TYPES = ['Add', 'Remove']

TOWNHALL_LEVELS = sorted([x for x in range(1, 18)], reverse=True)

MAX_ARMY_CAMP = 320
MAX_NUM_SPELLS = 11
MAX_NUM_SUPERS = 2


SHORT_PLAYER_LINK = 'https://p.clashk.ing/'
SHORT_CLAN_LINK = 'https://c.clashk.ing/'

item_to_name = {
    'Player Tag': 'tag',
    'Role': 'role',
    'Versus Trophies': 'versus_trophies',
    'Trophies': 'trophies',
    'Clan Capital Contributions': 'clan_capital_contributions',
    'Clan Capital Raided': 'ach_Aggressive Capitalism',
    'XP Level': 'exp_level',
    'Combined Heroes': 'heroes',
    'Obstacles Removed': 'ach_Nice and Tidy',
    'War Stars': 'war_stars',
    'DE Looted': 'ach_Heroic Heist',
    'CWL Stars': 'ach_War League Legend',
    'Attacks Won (all time)': 'ach_Conqueror',
    'Attacks Won (season)': 'attack_wins',
    'Defenses Won (season)': 'defense_wins',
    'Defenses Won (all time)': 'ach_Unbreakable',
    'Total Donated': 'ach_Friend in Need',
    'Versus Trophy Record': 'ach_Champion Builder',
    'Trophy Record': 'ach_Sweet Victory!',
    'Clan Games Points': 'ach_Games Champion',
    'Versus Battles Won': 'versus_attack_wins',
    'Best Season Rank': 'legendStatistics.bestSeason.rank',
    'Townhall Level': 'town_hall',
}


EMBED_COLOR = 2829617
EMBED_COLOR_CLASS = disnake.Color(EMBED_COLOR)


POSTER_LIST = {
    'Edrag': 'edrag',
    'Hogrider': 'hogrider',
    'Clash Forest': 'clashforest',
    'Clan War': 'clanwar',
    'Loons': 'loons',
    'Witch': 'witch',
    'Archers': 'archers',
    'Bowler': 'bowler',
    'Barbs': 'barbs',
    'Barb & Archer': 'barbandarcher',
    'Big Boy Skelly': 'bigboy',
    'Wiz Tower': 'wiztower',
    'Spells': 'spells',
    'Barb Sunset': 'barbsunset',
    'Wood Board': 'woodboard',
    'Clash Sky': 'clashsky',
    'Super Wizard': 'swiz',
    'Village Battle': 'villagebattle',
    'Hero Pets': 'heropets',
}


SUPER_SCRIPTS = ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹']


LEAGUES = [
    'Legend League',
    'Titan League I',
    'Titan League II',
    'Titan League III',
    'Champion League I',
    'Champion League II',
    'Champion League III',
    'Master League I',
    'Master League II',
    'Master League III',
    'Crystal League I',
    'Crystal League II',
    'Crystal League III',
    'Gold League I',
    'Gold League II',
    'Gold League III',
    'Silver League I',
    'Silver League II',
    'Silver League III',
    'Bronze League I',
    'Bronze League II',
    'Bronze League III',
    'Unranked',
]

ROLES = ['Member', 'Elder', 'Co-Leader', 'Leader']

WAR_LEAGUES = json.load(open(f'assets/war_leagues.json'))


TH_FILTER = [f"{th1}v{th2}" for th1 in TOWNHALL_LEVELS for th2 in TOWNHALL_LEVELS if th1 != th2]
TH_FILTER += [f"{x}v{x}" for x in TOWNHALL_LEVELS]
TH_FILTER = sorted(TH_FILTER, reverse=True)


ICON_PLACEHOLDERS = [
    'https://clashking.b-cdn.net/placeholders/DRC_pose03_groundShadows_5k.png',
    'https://clashking.b-cdn.net/placeholders/Electrofire%20Wizard.png',
    'https://clashking.b-cdn.net/placeholders/Frosty.png',
    'https://clashking.b-cdn.net/placeholders/Goblin%20Champion%20July%202023.png',
    'https://clashking.b-cdn.net/placeholders/PainterKing_Marketing_Shadow_B.png',
    'https://clashking.b-cdn.net/placeholders/Royal%20Ghost.png',
    'https://clashking.b-cdn.net/placeholders/LeagueRC_Pose04_NoShadow.png',
    'https://clashking.b-cdn.net/placeholders/League%20Queen.png',
    'https://clashking.b-cdn.net/placeholders/LeagueBK_Pose06_NoShadow.png',
]


AUTOREFRESH_TRIGGERS = [
    'Member Join',
    'Member Leave',
    'Townhall Change',
    'League Change',
    'Role Change',
]
