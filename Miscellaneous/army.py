from disnake.ext import commands
import re
from Dictionaries.army_ids import troop_ids, spell_ids, size
from Dictionaries.emojiDictionary import emojiDictionary
import discord
import coc

class ArmyLinks(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='army')
    async def army(self, ctx, *, link):
        embed = await self.armyEmbed(ctx, "Results", link)
        await ctx.send(embed=embed)


    async def armyEmbed(self, ctx, nick, link):
        valid = await self.is_link_valid(link)
        if not valid:
            return await ctx.send("Not a valid army link.")
        troops_patten = "u([\d+x-]+)"
        armycomp = re.split(troops_patten, link)

        sieges = "**Sieges:**\n"
        troop_string = ""
        eightTroops = ["Valkyrie", "Golem", "P.E.K.K.A"]
        isEight = False
        #generate troops
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
        spells = armycomp[1]
        spell_string = "**Spells:**\n"
        spell_space = 0
        if spells != '':
            spells_str = spells.split('-')
            for spell in spells_str:
                split_num_and_id = spell.split('x')
                num = split_num_and_id[0]
                id = split_num_and_id[1]
                spell_name = spell_ids(int(id))
                spell_emoji = emojiDictionary(spell_name)
                spell_space += (size(spell_name) * int(num))
                spell_string += f"{spell_emoji}`x {str(num)}` {spell_name}\n"
        else:
            spell_string += "None"

        if sieges == "**Sieges:**\n":
            sieges += "None"

        army = ""
        townhall_lv = self.townhall_army(troopSpace)
        townhall_lv = townhall_lv[0]
        if townhall_lv == "TH7-8" and isEight:
            townhall_lv = "TH8"

        army += townhall_lv + f" Army Composition \n🔗 [Click to Copy Army]({link})\n<:blanke:838574915095101470>"

        army += f"\n<:troop:861797310224400434> {troopSpace} <:spell:861797310282727484> {spell_space}\n<:blanke:838574915095101470>\n"





        army += troop_string + "<:blanke:838574915095101470>\n"
        army += spell_string + "<:blanke:838574915095101470>\n"
        army += sieges


        embed = discord.Embed(title=nick,description= army, color=discord.Color.green())
        return embed


    def townhall_army(self, size):
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

    async def is_link_valid(self, link):
        if 'https://link.clashofclans.com/en?action=CopyArmy&army=' not in link:
            return False

        link = link.replace('https://link.clashofclans.com/en?action=CopyArmy&army=', '')

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

        if check_link_troops[1] != '':
            troops_str = check_link_troops[1].split('-')
            for troop in troops_str:
                strings = troop.split('x')
                if int(strings[0]) > 300:  # check for a valid count of the unit
                    # print('wrong count')
                    return False
                if not troop_ids(int(strings[1])):  # check if it actually exists in dicts
                    # print('wrong id')
                    return False

        spells_patten = "s([\d+x-]+)"
        check_link_spells = re.split(spells_patten, link)

        if check_link_spells[1] != '':
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

def setup(bot: commands.Bot):
    bot.add_cog(ArmyLinks(bot))