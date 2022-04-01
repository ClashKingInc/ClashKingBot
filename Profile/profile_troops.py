from disnake.ext import commands
import disnake
from HelperMethods.troop_methods import heros, heroPets, troops, deTroops, siegeMachines, spells
from utils.clashClient import getPlayer



class profileTroops(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_profile_troops(self, result):
        player = await getPlayer(result)
        hero = heros(player)
        pets = heroPets(player)
        troop = troops(player)
        deTroop = deTroops(player)
        siege = siegeMachines(player)
        spell = spells(player)

        embed = disnake.Embed(title="You are looking at " + player.name,
                               description="Troop, hero, & spell levels for this account.",
                               color=disnake.Color.green())
        embed.add_field(name=f'__**{player.name}** (Th{player.town_hall})__ {player.trophies}', value="Profile: " + f'[{player.tag}]({player.share_link})',
                         inline=False)

        if (hero != None):
            embed.add_field(name="**Heroes:** ", value=hero, inline=False)

        if (pets != None):
            embed.add_field(name="**Pets:** ", value=pets, inline=False)

        if (troop != None):
            embed.add_field(name="**Elixir Troops:** ", value=troop, inline=False)

        if (deTroop != None):
            embed.add_field(name="**Dark Elixir Troops:** ", value=deTroop, inline=False)

        if (siege != None):
            embed.add_field(name="**Siege Machines:** ", value=siege, inline=False)

        if (spell != None):
            embed.add_field(name="**Spells:** ", value=spell, inline=False)

        return embed


def setup(bot: commands.Bot):
    bot.add_cog(profileTroops(bot))