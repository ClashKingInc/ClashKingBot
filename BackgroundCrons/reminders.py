import coc
import disnake
import math

from disnake.ext import commands
from main import scheduler
from CustomClasses.CustomBot import CustomClient

class reminders(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        #ends at 7 am monday
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["1 hr"], day_of_week="mon", hour=6)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["12 hr"], day_of_week="sun", hour=19)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["24 hr"], day_of_week="sun", hour=7)

    @commands.slash_command(name="reminder")
    async def reminder(self, ctx):
        pass

    @reminder.sub_command(name="create", description="Set a reminder for clan games, raid weekend, wars, & more")
    async def reminder_create(self, ctx: disnake.ApplicationCommandInteraction, clan:str, type:str = commands.Param(choices=["Clan Capital"])):
        clan = await self.bot.getClan(clan_tag=clan)
        if clan is None:
            return await ctx.send("Not a valid clan tag")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")


    @reminder.sub_command(name="remove", description="Remove a reminder set up on the server")
    async def reminder_remove(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @reminder.sub_command(name="list", description="Get the list of reminders set up on the server")
    async def reminder_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass


    async def clan_capital_reminder(self, time):
        hour = 4
        results = self.bot.server_db.find({"topboardchannel": {"$ne" : None}})
        limit = await self.bot.server_db.count_documents(filter={"topboardchannel": {"$ne" : None}})
        tasks = []
        date = self.bot.gen_legend_date()
        for r in await results.to_list(length=limit):
            try:
                serv = r.get("server")
                channel = r.get("topboardchannel")
                channel = await self.bot.fetch_channel(channel)
                g = self.bot.get_guild(serv)
                limit = 250
                rankings = []
                tracked = self.bot.clan_db.find({"server": serv})
                l = await self.bot.clan_db.count_documents(filter={"server": serv})
                if l == 0:
                    continue

                tags = []
                for clan in await tracked.to_list(length=l):
                    tag = clan.get("tag")
                    tags.append(tag)

                async for clan in self.bot.coc_client.get_clans(tags):
                    for player in clan.members:
                        try:
                            playerStats = []
                            playerStats.append(player.name)
                            playerStats.append(player.trophies)
                            playerStats.append(clan.name)
                            playerStats.append(player.tag)
                            rankings.append(playerStats)
                        except:
                            continue

                if limit > len(rankings):
                    limit = len(rankings)
                ranking = sorted(rankings, key=lambda l: l[1], reverse=True)

                embeds = []
                length = math.ceil(limit / 50)
                texts = []
                for e in range(0, length):
                    rText = ''
                    max = limit
                    if (e + 1) * 50 < limit:
                        max = (e + 1) * 50
                    for x in range(e * 50, max):
                        place = str(x + 1) + "."
                        place = place.ljust(3)
                        rText += f"\u200e`{place}` \u200e<:trophy:956417881778815016> \u200e{ranking[x][1]} - \u200e{ranking[x][0]} | \u200e{ranking[x][2]}\n"

                    embed = disnake.Embed(title=f"**Top {limit} {g.name} players**",
                                          description=rText)
                    texts.append(rText)
                    if g.icon is not None:
                        embed.set_thumbnail(url=g.icon.url)
                    embeds.append(embed)
                identifier = f"auto_{serv}{date}"
                if limit > 50:
                    buttons = disnake.ui.ActionRow()
                    buttons.append_item(disnake.ui.Button(label="Full Results", emoji=self.bot.emoji.start.partial_emoji,style=disnake.ButtonStyle.grey,custom_id=f"{identifier}"))
                    await channel.send(embed=embeds[0], components=buttons)
                else:
                    await channel.send(embed=embeds[0])

                tasks.append(InsertOne({"identifier": identifier, "text": texts }))

            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.server_db.update_one({"server": r.get("server")}, {'$set': {"topboardchannel": None}})

        country_results = []
        results = self.bot.server_db.find({"lbhour": hour+1})
        limit = await self.bot.server_db.count_documents(filter={"lbhour": hour+1})
        for r in await results.to_list(length=limit):
            try:
                channel = r.get("lbboardChannel")
                channel =  self.bot.get_channel(channel)
                serv = r.get("server")
                g = self.bot.get_guild(serv)
                country = r.get("country")

                tags = []
                tracked = self.bot.clan_db.find({"server": g.id})
                limit = await self.bot.clan_db.count_documents(filter={"server": g.id})

                for clan in await tracked.to_list(length=limit):
                    tag = clan.get("tag")
                    tags.append(tag)

                text = ""
                locations = await self.bot.coc_client.search_locations(limit=None)
                is_country = (country != "International")
                country = coc.utils.get(locations, name=country, is_country=is_country)
                country_names = country.name
                # print(country.id)
                rankings = await self.bot.coc_client.get_location_clans(location_id=country.id)
                # print(rankings)

                x = 1
                for clan in rankings:
                    rank = str(x)
                    rank = rank.ljust(2)
                    star = ""
                    if clan.tag in tags:
                        star = "⭐"
                    text += f"`\u200e{rank}`🏆`\u200e{clan.points}` \u200e{clan.name}{star}\n"
                    x += 1
                    if x == 26:
                        break

                embed = disnake.Embed(title=f"{country_names} Top 25 Leaderboard",
                                      description=text,
                                      color=disnake.Color.green())
                if g.icon is not None:
                    embed.set_thumbnail(url=g.icon.url)
                try:
                    await channel.send(embed=embed)
                except:
                    continue
            except:
                pass

        results = await self.bot.autoboards.bulk_write(tasks)

        results = self.bot.server_db.find({"comp_channel": {"$ne" : None}})
        limit = await self.bot.server_db.count_documents(filter={"comp_channel": {"$ne" : None}})
        for r in await results.to_list(length=limit):
            try:
                channel = r.get("comp_channel")
                channel = self.bot.get_channel(channel)
                all_tags = self.bot.erikuh.distinct("player_tag")
                all_players = await self.bot.get_players(tags=all_tags)
                serv = r.get("server")
                guild = self.bot.get_guild(serv)
                ranking = []
                for player in all_players:
                    try:
                        legend_day = player.legend_day()
                        ranking.append([player.name, player.trophy_start(), legend_day.attack_sum,
                                        legend_day.num_attacks.superscript, legend_day.defense_sum,
                                        legend_day.num_defenses.superscript, player.trophies])
                    except:
                        pass
                ranking = sorted(ranking, key=lambda l: l[6], reverse=True)
                embeds = await self.create_player_embed(guild, ranking)
                await channel.send(embed=embeds[0])
            except:
                continue




def setup(bot: CustomClient):
    bot.add_cog(reminders(bot))