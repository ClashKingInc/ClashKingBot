import json
import disnake
from collections import deque

#EVAL CONSTANTS
DEFAULT_EVAL_ROLE_TYPES = ["family", "only_family", "not_family", "clan", "leadership", "townhall", "builderhall", "category", "league", "builder_league", "nicknames"]

ROLE_TREATMENT_TYPES = ["Add", "Remove"]

BOARD_TYPES = ["Overview Board", "Simple Board", "Summary", "Donation", "Received", "Dono Ratio", "Discord Links", "War Preference", "Super Troops", "Clan Games", "Activity", "Last Online", "War Log", "CWL History"]
TOWNHALL_LEVELS = [x for x in range(1, 17)]
TOP_TOWNHALL = TOWNHALL_LEVELS[-1]

MAX_ARMY_CAMP = 320
MAX_NUM_SPELLS = 11


MAX_NUM_SUPERS = 2
SHORT_PLAYER_LINK = "https://api.clashking.xyz/p/"
SHORT_CLAN_LINK = "https://api.clashking.xyz/c/"

item_to_name = {"Player Tag" : "tag", "Role" : "role",
                "Versus Trophies" : "versus_trophies", "Trophies" : "trophies",
                "Clan Capital Contributions" : "clan_capital_contributions", "Clan Capital Raided" : "ach_Aggressive Capitalism",
                "XP Level" : "exp_level", "Combined Heroes" : "heroes", "Obstacles Removed" : "ach_Nice and Tidy", "War Stars" : "war_stars",
                "DE Looted" : "ach_Heroic Heist", "CWL Stars" : "ach_War League Legend", "Attacks Won (all time)" : "ach_Conqueror",
                "Attacks Won (season)" : "attack_wins", "Defenses Won (season)" : "defense_wins", "Defenses Won (all time)" : "ach_Unbreakable", "Total Donated" : "ach_Friend in Need",
                "Versus Trophy Record" : "ach_Champion Builder", "Trophy Record" : "ach_Sweet Victory!",
                "Clan Games Points" : "ach_Games Champion", "Versus Battles Won" : "versus_attack_wins", "Best Season Rank" : "legendStatistics.bestSeason.rank", "Townhall Level" : "town_hall"}

HOME_VILLAGE_HEROES = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
EMBED_COLOR = 2829617
EMBED_COLOR_CLASS = disnake.Color(EMBED_COLOR)

HERO_EQUIPMENT = {
        "Barbarian Puppet" : "Barbarian King",
        "Rage Vial" : "Barbarian King",
        "Archer Puppet" :  "Archer Queen",
        "Invisibility Vial" :  "Archer Queen",
        "Eternal Tome" : "Grand Warden",
        "Life Gem" : "Grand Warden",
        "Seeking Shield" : "Royal Champion",
        "Royal Gem" : "Royal Champion",
        "Earthquake Boots" : "Barbarian King",
        "Vampstache" : "Barbarian King",
        "Giant Arrow" :  "Archer Queen",
        "Healer Puppet" :  "Archer Queen",
        "Rage Gem" : "Grand Warden",
        "Healing Tome" : "Grand Warden",
        "Giant Gauntlet" : "Barbarian King"
    }

POSTER_LIST = {"Edrag" : "edrag",
               "Hogrider" : "hogrider",
               "Clash Forest" : "clashforest",
               "Clan War" : "clanwar",
               "Loons" : "loons",
               "Witch" : "witch",
               "Archers" : "archers",
               "Bowler" : "bowler",
               "Barbs" : "barbs",
               "Barb & Archer" : "barbandarcher",
               "Big Boy Skelly" : "bigboy",
               "Wiz Tower" : "wiztower",
               "Spells" : "spells",
               "Barb Sunset" : "barbsunset",
               "Wood Board" : "woodboard",
               "Clash Sky" : "clashsky",
               "Super Wizard" : "swiz",
               "Village Battle" : "villagebattle",
               "Hero Pets" : "heropets"}

locations = ["global", 32000007, 32000008, 32000009, 32000010, 32000011, 32000012, 32000013, 32000014, 32000015, 32000016,
             32000017,
             32000018, 32000019, 32000020, 32000021, 32000022, 32000023, 32000024, 32000025, 32000026, 32000027,
             32000028,
             32000029, 32000030, 32000031, 32000032, 32000033, 32000034, 32000035, 32000036, 32000037, 32000038,
             32000039,
             32000040, 32000041, 32000042, 32000043, 32000044, 32000045, 32000046, 32000047, 32000048, 32000049,
             32000050,
             32000051, 32000052, 32000053, 32000054, 32000055, 32000056, 32000057, 32000058, 32000059, 32000060,
             32000061,
             32000062, 32000063, 32000064, 32000065, 32000066, 32000067, 32000068, 32000069, 32000070, 32000071,
             32000072,
             32000073, 32000074, 32000075, 32000076, 32000077, 32000078, 32000079, 32000080, 32000081, 32000082,
             32000083,
             32000084, 32000085, 32000086, 32000087, 32000088, 32000089, 32000090, 32000091, 32000092, 32000093,
             32000094,
             32000095, 32000096, 32000097, 32000098, 32000099, 32000100, 32000101, 32000102, 32000103, 32000104,
             32000105,
             32000106, 32000107, 32000108, 32000109, 32000110, 32000111, 32000112, 32000113, 32000114, 32000115,
             32000116,
             32000117, 32000118, 32000119, 32000120, 32000121, 32000122, 32000123, 32000124, 32000125, 32000126,
             32000127,
             32000128, 32000129, 32000130, 32000131, 32000132, 32000133, 32000134, 32000135, 32000136, 32000137,
             32000138,
             32000139, 32000140, 32000141, 32000142, 32000143, 32000144, 32000145, 32000146, 32000147, 32000148,
             32000149,
             32000150, 32000151, 32000152, 32000153, 32000154, 32000155, 32000156, 32000157, 32000158, 32000159,
             32000160,
             32000161, 32000162, 32000163, 32000164, 32000165, 32000166, 32000167, 32000168, 32000169, 32000170,
             32000171,
             32000172, 32000173, 32000174, 32000175, 32000176, 32000177, 32000178, 32000179, 32000180, 32000181,
             32000182,
             32000183, 32000184, 32000185, 32000186, 32000187, 32000188, 32000189, 32000190, 32000191, 32000192,
             32000193,
             32000194, 32000195, 32000196, 32000197, 32000198, 32000199, 32000200, 32000201, 32000202, 32000203,
             32000204,
             32000205, 32000206, 32000207, 32000208, 32000209, 32000210, 32000211, 32000212, 32000213, 32000214,
             32000215,
             32000216, 32000217, 32000218, 32000219, 32000220, 32000221, 32000222, 32000223, 32000224, 32000225,
             32000226,
             32000227, 32000228, 32000229, 32000230, 32000231, 32000232, 32000233, 32000234, 32000235, 32000236,
             32000237,
             32000238, 32000239, 32000240, 32000241, 32000242, 32000243, 32000244, 32000245, 32000246, 32000247,
             32000248,
             32000249, 32000250, 32000251, 32000252, 32000253, 32000254, 32000255, 32000256, 32000257, 32000258,
             32000259, 32000260]

BADGE_GUILDS = deque([1029631304817451078, 1029631182196977766, 1029631107240562689, 1029631144641183774, 1029629452403097651,
                             1029629694854828082, 1029629763087777862, 1029629811221610516, 1029629853017841754, 1029629905903833139,
                             1029629953907634286, 1029629992830783549, 1029630376911581255, 1029630455202455563, 1029630702125318144,
                             1029630796966932520, 1029630873588469760, 1029630918106824754, 1029630974025277470, 1029631012084396102])

SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]

DARK_ELIXIR = ["Minion", "Hog Rider", "Valkyrie", "Golem", "Witch", "Lava Hound", "Bowler", "Ice Golem", "Headhunter"]
SUPER_TROOPS = ["Super Barbarian", "Super Archer", "Super Giant", "Sneaky Goblin", "Super Wall Breaker", "Rocket Balloon", "Super Wizard", "Inferno Dragon",
                "Super Minion", "Super Valkyrie", "Super Witch", "Ice Hound", "Super Bowler", "Super Dragon", "Super Miner"]

leagues = ["Legend League", "Titan League I" , "Titan League II" , "Titan League III" ,"Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]

ROLES = ["Member", "Elder", "Co-Leader", "Leader"]

war_leagues = json.load(open(f"assets/war_leagues.json"))

USE_CODE_TEXT = [
    "Hey :) Consider supporting me in-game with code [ClashKing](<https://link.clashofclans.com/en?action=SupportCreator&id=clashking>)!",
    "Code [ClashKing](<https://link.clashofclans.com/en?action=SupportCreator&id=clashking>)?",
    "Roses are red, Violets are Blue, if you use Code [ClashKing](<https://link.clashofclans.com/en?action=SupportCreator&id=clashking>), I will love you :)",
    "Nothing is certain except for death, taxes, and Code [ClashKing](<https://link.clashofclans.com/en?action=SupportCreator&id=clashking>) - Not Benjamin Franklin",
    "We may encounter many ~~defeats~~ [creator codes](<https://link.clashofclans.com/en?action=SupportCreator&id=clashking>) but we must not be defeated. - Unknown",
    "Using Code [ClashKing](<https://link.clashofclans.com/en?action=SupportCreator&id=clashking>) is Elementary, my dear Watson ;)",
    "[Go ahead, make my day.](<https://link.clashofclans.com/en?action=SupportCreator&id=clashking>)",
]

TH_FILTER = ['1v2', '1v3', '1v4', '1v5', '1v6', '1v7', '1v8', '1v9', '1v10', '1v11', '1v12', '1v13', '1v14', '1v15', '1v16',
             '2v1', '2v3', '2v4', '2v5', '2v6', '2v7', '2v8', '2v9', '2v10', '2v11', '2v12', '2v13', '2v14', '2v15', '2v16',
             '3v1', '3v2', '3v4', '3v5', '3v6', '3v7', '3v8', '3v9', '3v10', '3v11', '3v12', '3v13', '3v14', '3v15', '3v16',
             '4v1', '4v2', '4v3', '4v5', '4v6', '4v7', '4v8', '4v9', '4v10', '4v11', '4v12', '4v13', '4v14', '4v15', '4v16',
             '5v1', '5v2', '5v3', '5v4', '5v6', '5v7', '5v8', '5v9', '5v10', '5v11', '5v12', '5v13', '5v14', '5v15', '5v16',
             '6v1', '6v2', '6v3', '6v4', '6v5', '6v7', '6v8', '6v9', '6v10', '6v11', '6v12', '6v13', '6v14', '6v15', '6v16',
             '7v1', '7v2', '7v3', '7v4', '7v5', '7v6', '7v8', '7v9', '7v10', '7v11', '7v12', '7v13', '7v14', '7v15', '7v16',
             '8v1', '8v2', '8v3', '8v4', '8v5', '8v6', '8v7', '8v9', '8v10', '8v11', '8v12', '8v13', '8v14', '8v15', '8v16',
             '9v1', '9v2', '9v3', '9v4', '9v5', '9v6', '9v7', '9v8', '9v10', '9v11', '9v12', '9v13', '9v14', '9v15', '9v16',
             '10v1', '10v2', '10v3', '10v4', '10v5', '10v6', '10v7', '10v8', '10v9', '10v11', '10v12', '10v13', '10v14', '10v15', '10v16',
             '11v1', '11v2', '11v3', '11v4', '11v5', '11v6', '11v7', '11v8', '11v9', '11v10', '11v12', '11v13', '11v14', '11v15', '11v16',
             '12v1', '12v2', '12v3', '12v4', '12v5', '12v6', '12v7', '12v8', '12v9', '12v10', '12v11', '12v13', '12v14', '12v15', '12v16',
             '13v1', '13v2', '13v3', '13v4', '13v5', '13v6', '13v7', '13v8', '13v9', '13v10', '13v11', '13v12', '13v14', '13v15', '13v16',
             '14v1', '14v2', '14v3', '14v4', '14v5', '14v6', '14v7', '14v8', '14v9', '14v10', '14v11', '14v12', '14v13', '14v15', '14v16',
             '15v1', '15v2', '15v3', '15v4', '15v5', '15v6', '15v7', '15v8', '15v9', '15v10', '15v11', '15v12', '15v13', '15v14', '15v16',
             '16v1', '16v2', '16v3', '16v4', '16v5', '16v6', '16v7', '16v8', '16v9', '16v10', '16v11', '16v12', '16v13', '16v14', '16v15'] + \
             ["{}v{}".format(x, x) for x in TOWNHALL_LEVELS]

TH_FILTER_OPTIONS = sorted(TH_FILTER, reverse=True)

WHITELIST_OPTIONS = [
    "ticket"
]