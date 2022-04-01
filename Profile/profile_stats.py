from disnake.ext import commands
import discord
from Dictionaries.emojiDictionary import emojiDictionary
from Dictionaries.thPicDictionary import thDictionary
from HelperMethods.troop_methods import profileSuperTroops, leagueAndTrophies
from utils.clashClient import getPlayer, link_client, pingToMember, client

usafam = client.usafam
server = usafam.server
banlist = usafam.banlist

class profileStats(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    async def create_profile_stats(self, ctx, result):

        embed=[]

        discordID = await link_client.get_link(result)
        player = await getPlayer(result)
        member = await pingToMember(ctx, str(discordID))



        name = player.name
        link = player.share_link
        donos = player.donations
        received = player.received
        ratio = str(round((donos / (received + 1)), 2))
        bestTrophies = emojiDictionary("trophy") + str(player.best_trophies)
        friendInNeed = str(player.get_achievement("Friend in Need").value)


        clan = ""
        try:
            clan = player.clan.name
            clan = f"{clan},"
        except:
            clan = "None"

        stroops = profileSuperTroops(player)
        # print(stroops)
        if (len(stroops) > 0):
            stroops = "\n**Super Troops:**\n" + stroops + "\n"
        else:
            stroops = ""

        troph = leagueAndTrophies(player)

        th = str(player.town_hall)
        role = str(player.role)
        if role == "None":
            role = ""
        emoji = emojiDictionary(player.town_hall)

        results = await server.find_one({"server": ctx.guild.id})
        prefix = results.get("prefix")

        tag = player.tag
        tag = tag.strip("#")
        if member is not None:
            embed = discord.Embed(title=f'{emoji} **{name}** ',
                                  description="Linked to " + member.mention +
                                  f"\nTh Level: {player.town_hall}\nTrophies: {troph}\n" +
                                    "Tag: " + f'[{player.tag}]({link})' "\n"
                                    f"Clan: {clan} {role}\n"
                                    f"[Clash Of Stats Profile](https://www.clashofstats.com/players/{tag})",
                                  color=discord.Color.green())
            embed.set_thumbnail(url=member.avatar_url)
        elif (member is None) and (discordID is not None):
            embed = discord.Embed(title=f'{emoji} **{name}** ',
                                  description=f"*Linked, but not on this server.*"+
                                              f"\nTh Level: {player.town_hall}\nTrophies: {troph}\n" +
                                              "Tag: " + f'[{player.tag}]({link})' "\n"
                                                        f"Clan: {clan} {role}\n"
                                                        f"[Clash Of Stats Profile](https://www.clashofstats.com/players/{tag})"
                                  , color=discord.Color.green())
            if player.town_hall >= 4:
                embed.set_thumbnail(url=thDictionary(player.town_hall))
        else:
            embed = discord.Embed(title=f'{emoji} **{name}** ',
                                  description=f"Not linked. Owner? Use `{prefix}link`" +
                                              f"\nTh Level: {player.town_hall}\nTrophies: {troph}\n" +
                                              "Tag: " + f'[{player.tag}]({link})' "\n"
                                                        f"Clan: {clan} {role}\n"
                                                        f"[Clash Of Stats Profile](https://www.clashofstats.com/players/{tag})"
                                  , color=discord.Color.green())
            if player.town_hall >= 4:
                embed.set_thumbnail(url=thDictionary(player.town_hall))




        embed.add_field(name="**Info:**",
                        value=f"<:warwon:932212939899949176>Donated: {donos} troops\n"
                              f"<:warlost:932212154164183081>Received: {received} troops\n"
                              f"<:winrate:932212939908337705>Donation Ratio: {ratio}\n"
                              f"<:sword:825589136026501160>Attack Wins: {player.attack_wins}\n"
                              f"<:clash:877681427129458739>Defense Wins: {player.defense_wins}\n"
                              f"{stroops}"
                              f"**Stats:**\n"
                              f"Best Trophies: {bestTrophies}\n"
                              f"War Stars: ⭐ {player.war_stars}\n"
                              f"All Time Donos: {friendInNeed}", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}",
                         icon_url=ctx.author.avatar_url)

        ban = await banlist.find_one({"$and": [
            {"VillageTag": f"{player.tag}"},
            {"server": ctx.guild.id}
        ]})

        if ban != None:
            date = ban.get("DateCreated")
            date = date[0:10]
            notes = ban.get("Notes")
            if notes == "":
                notes = "No Reason Given"
            embed.add_field(name="__**Banned Player**__",
                            value=f"Date: {date}\nReason: {notes}")
        return embed


def setup(bot: commands.Bot):
    bot.add_cog(profileStats(bot))