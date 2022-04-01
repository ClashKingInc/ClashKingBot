from disnake.ext import commands
import disnake
from utils.clashClient import getPlayer, link_client, pingToMember, getClan



class profileHistory(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def history(self, ctx, result):
        discordID = await link_client.get_link(result)
        member = await pingToMember(ctx, str(discordID))
        player = await getPlayer(result)
        join = None
        try:
            join = member.joined_at
            day = str(join.day)
            month = str(join.month)
            year = str(join.year)
        except:
            pass


        import requests
        result = result.strip("#")
        url = f'https://www.clashofstats.com/players/{result}/history/'
        response = requests.get(url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        clans = soup.find_all("a", class_="v-list-item v-list-item--link theme--dark")
        test = soup.find_all("div", class_="subsection-title")
        num_clans = test[1].text.strip()
        text = ""
        x = 0
        for clan in clans:
            try:
                #title_element = clan.find("div", class_="subsection-title")
                company_element = clan.find("span", class_="text--secondary caption")
                location_element = clan.find("div", class_="v-list-item__subtitle")
                #print(title_element.text.strip())
                #print(company_element.text.strip())
                t = company_element.text.strip()
                t = t.strip("-")
                c = await getClan(t)
                t = f"[{c.name}]({c.share_link}), - "
                lstay = None
                for d in location_element.find_all("br"):
                    lstay = "".join(d.previous_siblings)
                # print(location_element.text.strip())
                lstay = " ".join(lstay.split())
                lstay = lstay.strip("Total ")
                text += f"\u200e{t} \u200e{lstay}\n"
                x+=1
                if x == 5:
                    break
            except:
                pass

        embed = disnake.Embed(title=f"{player.name} History",
                              description=f"{num_clans}",
                              color=disnake.Color.green())
        embed.add_field(name="**Top 5 Clans Player has stayed the most:**",
                        value=text, inline=False)


        result = result.strip("#")
        url = f'https://www.clashofstats.com/players/{result}/history/log'
        response = requests.get(url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        clans = soup.find_all("a", class_="v-list-item v-list-item--link theme--dark")
        text = ""
        x = 0
        types = ["Member", "Elder", "Co-leader", "Leader"]
        for clan in clans:
            try:
                title_element = clan.find("div", class_="v-list-item__title")
                location_element = clan.find("div", class_="v-list-item__subtitle text--secondary")
                t = title_element.text.strip()
                t = " ".join(t.split())
                ttt = t.split("#",1)
                clan = await getClan(ttt[1])
                type = "No Role"
                for ty in types:
                    if ty in t:
                        type = ty

                t = f"\u200e[{clan.name}]({clan.share_link}), \u200e{type}"

                lstay = location_element.text.strip()
                lstay = " ".join(lstay.split())
                text += f"{t} \n{lstay}\n"
                x += 1
                if x == 5:
                    break
            except:
                pass

        embed.add_field(name="**Last 5 Clans Player has been seen at:**",
                        value=text, inline=False)



        if join is not None:
            embed.add_field(name="**Tenure:**",
                             value=member.display_name + " has been in this server since " + str(
                                 month + "/" + day + "/" + year), inline=False)
        if ctx.guild.id == 328997757048324101:
            msg = ""
            channel = self.bot.get_channel(669593198771044363)
            async for message in channel.history():
                if message.author == member:
                    msg = message.jump_url
            if (msg != ""):
                embed.add_field(name="**A bit about me:**", value=f"[View here]({msg})", inline=False)

        return embed


def setup(bot: commands.Bot):
    bot.add_cog(profileHistory(bot))