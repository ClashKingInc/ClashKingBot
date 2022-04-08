import coc
import disnake

from utils.clash import client, coc_client

usafam = client.usafam
server = usafam.server
clans = usafam.clans
donations = usafam.donations

from disnake.ext import commands

class Donations(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        coc_client.add_events(self.dona)
        coc_client.add_events(self.new_season)

    @commands.slash_command(name="donations", description="Leaderboard of top 50 donators in family")
    async def dono(self, ctx):
        aliases = None
        tags = []
        if aliases is None:
            tracked = clans.find({"server": ctx.guild.id})
            limit = await clans.count_documents(filter={"server": ctx.guild.id})
            if limit == 0:
                return await ctx.send("This server has no linked clans.")
            for tClan in await tracked.to_list(length=limit):
                tag = tClan.get("tag")
                tags.append(tag)
        else:
            aliases = aliases.split(" ")
            if len(aliases) > 5:
                return await ctx.send(
                    f"Command only supports up to 5 clans.")
            for alias in aliases:
                results = await clans.find_one({"$and": [
                    {"alias": alias},
                    {"server": ctx.guild.id}
                ]})
                if results is None:
                    return await ctx.send(
                        f"Invalid alias {alias} found.\n**Note:** This command only supports single word aliases when given multiple.")
                tag = results.get("tag")
                tags.append(tag)

        rankings = []
        members = []
        ptags = []
        async for clan in coc_client.get_clans(tags):
            for member in clan.members:
                members.append(member)
                ptags.append(member.tag)


        don = 0
        results = donations.find({"tag": {"$in" : ptags}})
        limit = await clans.count_documents(filter={"tag": {"$in" : ptags}})
        for document in await results.to_list(length=limit):
            don = document.get("donations")
            if don < 0:
                tag = document.get("tag")
                ind = ptags.index(tag)
                r = []
                r.append(members[ind].name)
                r.append(don)
                r.append(members[ind].clan.name)
                rankings.append(r)
                members.pop(ind)
                ptags.pop(ind)

        for member in members:
            r = []
            r.append(member.name)
            r.append(member.donations)
            r.append(member.clan.name)
            rankings.append(r)


        ranking = sorted(rankings, key=lambda l: l[1], reverse=True)
        ranking = ranking[0:50]

        text = ""
        x = 0
        for rr in ranking:
            place = str(x + 1) + "."
            place = place.ljust(3)
            do = "{:,}".format(rr[1])
            text += f"\u200e`{place}` \u200e<:troop:861797310224400434> \u200e{do} - \u200e{rr[0]} | \u200e{rr[2]}\n"
            x += 1

        embed = disnake.Embed(title=f"**Top 50 Donators**",
                              description=text)
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @coc.ClanEvents.member_donations()
    async def dona(self, old_member : coc.ClanMember, new_member : coc.ClanMember):
        donated = new_member.donations - old_member.donations
        if donated <= 0:
            return
        tag = new_member.tag
        results = await donations.find_one({"tag": tag})
        if results is None:
            await donations.insert_one({
                "tag": tag,
                "donations": donated
            })
        else:
            donos = results.get("donations")
            if donos < new_member.donations:
                await donations.update_one({"tag": tag}, {'$set': {
                    "donations": new_member.donations
                }})
            else:
                await donations.update_one({"tag": tag}, {'$inc': {
                    "donations": donated
                }})

    @coc.ClientEvents.new_season_start()
    async def new_season(self):
        await donations.update_many({'donations': {'$gt': -1000000}},
                               {'$set': {'donations': 0}})


def setup(bot: commands.Bot):
    bot.add_cog(Donations(bot))