from disnake.ext import commands
import re
from Dictionaries.army_ids import troop_ids, spell_ids, size
from Dictionaries.emojiDictionary import emojiDictionary
import coc
from CustomClasses.CustomBot import CustomClient
import disnake

class ArmyLinks(commands.Cog, name="Army"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='army', description="Create a visual message representation of an army link")
    async def army(self, ctx: disnake.ApplicationCommandInteraction, link, name:str = "Results", clan_castle:str = "None"):
        try:
            embed = await self.armyEmbed(ctx, name, link, clan_castle)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label=f"Copy Army Link", emoji=self.bot.emoji.troop.partial_emoji,
                                  url=link))
            await ctx.send(embed=embed, components=buttons)
        except:
            pass


    async def armyEmbed(self, ctx, nick, link, clan_castle):
        valid = await self.is_link_valid(link)
        if not valid:
            return await ctx.send("Not a valid army link.")
        troops_patten = "u([\d+x-]+)"
        armycomp = re.split(troops_patten, link)

        sieges = "**Sieges:**\n"
        troop_string = ""
        troops_used = []
        eightTroops = ["Valkyrie", "Golem", "P.E.K.K.A"]
        isEight = False
        #generate troops

        troopSpace = 0
        troop_string += "**Troops:**\n"
        if len(armycomp) > 1 and armycomp[1] != '':
            troops = armycomp[1]
            troops_str = troops.split('-')
            for troop in troops_str:
                split_num_and_id = troop.split('x')
                num = split_num_and_id[0]
                id = split_num_and_id[1]
                troops_used.append(id)
                troop_name = troop_ids(int(id))
                if troop_name in eightTroops:
                    isEight = True
                troop_emoji = emojiDictionary(troop_name)
                if troop_name not in coc.SIEGE_MACHINE_ORDER:
                    troopSpace += (size(troop_name) * int(num))
                    #print(troop_name + " " + str(troopSpace))
                    troop_string += f"{troop_emoji}`x {str(num)}` {troop_name}\n"
                else:
                    sieges += f"{troop_emoji}`x {str(num)}` {troop_name}\n"
        else:
            troop_string += "None"

        spells_patten = "s([\d+x-]+)"
        armycomp = re.split(spells_patten, link)

        spell_string = "**Spells:**\n"
        spells_used = []
        spell_space = 0
        if len(armycomp) > 1 and armycomp[1] != '':
            spells = armycomp[1]
            spells_str = spells.split('-')
            for spell in spells_str:
                split_num_and_id = spell.split('x')
                num = split_num_and_id[0]
                id = split_num_and_id[1]
                spells_used.append(id)
                spell_name = spell_ids(int(id))
                spell_emoji = emojiDictionary(spell_name)
                spell_space += (size(spell_name) * int(num))
                spell_string += f"{spell_emoji}`x {str(num)}` {spell_name}\n"
        else:
            spell_string += "None"

        if sieges == "**Sieges:**\n":
            sieges += "None"

        army = ""
        townhall_lv = self.townhall_army(troopSpace, troops_used, spells_used)
        townhall_lv = townhall_lv[0]
        if townhall_lv == "TH7-8" and isEight:
            townhall_lv = "TH8"

        army += townhall_lv + f" Army Composition\n<:blanke:838574915095101470>"

        army += f"\n<:troop:861797310224400434> {troopSpace} <:spell:861797310282727484> {spell_space}\n<:blanke:838574915095101470>\n"

        army += troop_string + "<:blanke:838574915095101470>\n"
        army += spell_string + "<:blanke:838574915095101470>\n"
        army += sieges + "<:blanke:838574915095101470>\n"
        army += f"**Clan Castle:**\n{self.bot.emoji.clan_castle.emoji_string} {clan_castle}"


        embed = disnake.Embed(title=nick,description= army, color=disnake.Color.green())
        return embed

    def townhall_army(self, size, troops, spells):

        if size <= 20:
            return ["TH1", 1]
        elif size <= 30:
            return ["TH2", 2]
        elif size <= 70:
            return ["TH3", 3]
        elif size <= 80:
            return ["TH4", 4]
        elif size <= 135:
            return ["TH5", 5]
        elif size <= 150:
            return ["TH6", 6]
        elif size <= 200:
            return ["TH7-8", 7]
        elif size <= 220:
            return ["TH9", 9]
        elif size <= 240:
            return ["TH10", 10]
        elif size <= 260:
            return ["TH11", 11]
        elif size <= 280:
            return ["TH12", 12]
        elif size <= 300:
            return ["TH13-14", 13]
        elif size <= 320:
            return ["TH15", 15]

    async def is_link_valid(self, link: str):

        if 'https://link.clashofclans.com/' not in link:
            return False

        if "?action=CopyArmy&army=" not in link:
            return False

        spot = (link.find("=", link.find("=") + 1))
        link = link[spot+1:]

        if 'u' not in link and 's' not in link:
            return False

        letter_u_count = 0
        letter_s_count = 0
        for letter in link:
            if letter == "u":
                letter_u_count += 1
            if letter == "s":
                letter_s_count += 1

        if letter_u_count > 1:
            return False
        if letter_s_count > 1:
            return False

        for character in link:
            if character == 'u' or character == 'x' or character == '-' or character.isdigit() or character == 's':
                pass
            else:
                return False

        troops_patten = "u([\d+x-]+)"
        check_link_troops = re.split(troops_patten, link)
        print(check_link_troops)
        if len(check_link_troops) > 1 and check_link_troops[1] != '':
            troops_str = check_link_troops[1].split('-')
            for troop in troops_str:
                strings = troop.split('x')
                if int(strings[0]) > 320:  # check for a valid count of the unit
                    # print('wrong count')
                    return False
                if not troop_ids(int(strings[1])):  # check if it actually exists in dicts
                    # print('wrong id')
                    return False

        spells_patten = "s([\d+x-]+)"
        check_link_spells = re.split(spells_patten, link)
        print(check_link_spells)
        if len(check_link_spells) > 1 and check_link_spells[1] != '':
            spells_str = check_link_spells[1].split('-')
            for spell in spells_str:
                string = spell.split('x')
                if int(string[0]) > 11:  # check for a valid count of the unit
                    print('wrong count')
                    return False
                if not spell_ids(int(string[1])):  # check if it actually exists in dicts
                    print('wrong id')
                    return False

        return True

    '''
    async def clan_castle(self, ctx: disnake.ApplicationCommandInteraction, query:str):
        link = ctx.filled_options.get("army_link")
        if not self.is_link_valid(link):
            return []

        troops_patten = "u([\d+x-]+)"
        armycomp = re.split(troops_patten, link)

        troop_string = ""
        troops = armycomp[1]
        troopSpace = 0
        troop_string += "**Troops:**\n"
        if troops != '':
            troops_str = troops.split('-')
            for troop in troops_str:
                split_num_and_id = troop.split('x')
                num = split_num_and_id[0]
                id = split_num_and_id[1]
                troop_name = troop_ids(int(id))
                if troop_name not in coc.SIEGE_MACHINE_ORDER:
                    troopSpace += (size(troop_name) * int(num))

        if troopSpace == 0:
            return []

        valid_cc = [20, 30, 70, 80, 135, 150, 200, 220, 240, 260, 280, 300]
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
            57: "Rocket Balloon",
            58: "Ice Golem",
            59: "Electro Dragon",
            63: "Inferno Dragon",
            64: "Super Valkyrie",
            65: "Dragon Rider",
            66: "Super Witch",
            76: "Ice Hound",
            80: "Super Bowler",
            81: "Super Dragon",
            82: "Headhunter",
            83: "Super Wizard",
            84: "Super Minion",
        }
        import itertools
        from collections import defaultdict
        for max in valid_cc:
            ways = []
            troops = switcher.values()
            for troop in troops:
                num = size(troop)
                num_troop = max // num
                for x in range(1, num_troop):
                    ways.append(f"{x}-{troop}")

            for r in range(len(ways) + 1):
                for combination in itertools.combinations(ways, r):
                    combo = list(combination)
                    space = 0
                    troop_occurance = defaultdict(int)
                    new_combo = []
                    all_under = True
                    for troop in combo:
                        troop: str
                        items = troop.split("-")
                        num = items[0]
                        troop = items[1]
                        troop_occurance[troop] += 1
                        if troop_occurance[troop] >= 2:
                            all_under = False
                        space += size(troop) * int(num)
                        new_combo.append(f"{num} {troop}")
                    if space == max and all_under and len(new_combo) <= 5:
                        # print(new_combo)
                        await options.insert_one({"space": max, "combo": new_combo})
    '''

def setup(bot: CustomClient):
    bot.add_cog(ArmyLinks(bot))