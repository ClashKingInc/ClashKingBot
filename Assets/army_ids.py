
def troop_ids(troop_id):
    switcher = {
        0: "Barbarian",
        1: "Archer",
        2: "Goblin",
        3: "Giant",
        4: "Wall Breaker",
        5: "Balloon",
        6: "Wizard",
        7: "Healer",
        8: "Dragon",
        9: "P.E.K.K.A",
        10: "Minion",
        11: "Hog Rider",
        12: "Valkyrie",
        13: "Golem",
        15: "Witch",
        17: "Lava Hound",
        22: "Bowler",
        23: "Baby Dragon",
        24: "Miner",
        26: "Super Barbarian",
        27: "Super Archer",
        28: "Super Wall Breaker",
        29: "Super Giant",
        53: "Yeti",
        55: "Sneaky Goblin",
        56: "Super Miner",
        57: "Rocket Balloon",
        58: "Ice Golem",
        59: "Electro Dragon",
        63: "Inferno Dragon",
        64: "Super Valkyrie",
        65: "Dragon Rider",
        66: "Super Witch",
        76: "Ice Hound",
        80 : "Super Bowler",
        81 : "Super Dragon",
        82: "Headhunter",
        83: "Super Wizard",
        84: "Super Minion",
        95: "Electro Titan",


        51: "Wall Wrecker",
        52: "Battle Blimp",
        62: "Stone Slammer",
        75: "Siege Barracks",
        87: "Log Launcher",
        91 : "Flame Flinger",
        92 : "Battle Drill"

    }

    troop_name = switcher.get(troop_id, False)
    return troop_name

def spell_ids(spell_id):
    switcher = {
        0: "Lightning Spell",
        1: "Healing Spell",
        2: "Rage Spell",
        3: "Jump Spell",
        5: "Freeze Spell",
        9: "Poison Spell",
        10: "Earthquake Spell",
        11: "Haste Spell",
        16: "Clone Spell",
        17: "Skeleton Spell",
        28: "Bat Spell",
        35: "Invisibility Spell",
        53: "Recall Spell"
    }

    spell_name = switcher.get(spell_id, False)
    return spell_name

def size(troop_or_spell):
    switcher = {
        "Barbarian" : 1,
        "Archer" : 1,
        "Goblin" : 1,
        "Giant" : 5,
        "Wall Breaker" : 2,
        "Balloon" : 5,
        "Wizard" : 4,
        "Healer" : 14,
        "Dragon" : 20,
        "P.E.K.K.A" : 25,
        "Minion" : 2,
        "Hog Rider" : 5,
        "Valkyrie" : 8,
        "Golem" : 30,
        "Witch" : 12,
        "Lava Hound" : 30,
        "Bowler" : 6,
        "Baby Dragon" : 10,
        "Miner" : 6,
        "Super Barbarian" : 5,
        "Super Archer" :12,
        "Super Wall Breaker" : 8,
        "Super Giant" : 10,
        "Yeti" : 18,
        "Sneaky Goblin" : 3,
        "Rocket Balloon" : 8,
        "Ice Golem" : 15,
        "Electro Dragon" : 30,
        "Inferno Dragon" : 15,
        "Super Valkyrie" : 20,
        "Dragon Rider" : 25,
        "Super Witch" : 40,
        "Ice Hound" : 40,
        "Headhunter" : 6,
        "Super Wizard" : 10,
        "Super Minion" : 12,
        "Super Bowler" : 30,
        "Super Dragon" : 40,
        "Electro Titan" : 32,
        "Super Miner" : 24,

        "Lightning Spell" : 1,
        "Healing Spell" : 2,
        "Rage Spell" : 2,
        "Jump Spell" : 2,
        "Freeze Spell" : 1,
        "Poison Spell" : 1,
        "Earthquake Spell" : 1,
        "Haste Spell" : 1,
        "Clone Spell" : 3,
        "Skeleton Spell" : 1,
        "Bat Spell" : 1,
        "Invisibility Spell" : 1,
        "Recall Spell" : 2
    }

    size = switcher.get(troop_or_spell, 0)
    return size