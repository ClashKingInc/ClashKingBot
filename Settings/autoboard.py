from disnake.ext import commands
import disnake

from CustomClasses.CustomBot import CustomClient

class autoB(commands.Cog, name="Board Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="autoboard")
    async def autoboard(self, ctx):
        pass


    @autoboard.sub_command(name="create", description="Create server autoposting leaderboards")
    async def setupboard(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, autoboard_type: str = commands.Param(choices=["Player Leaderboard", "Clan Leaderboard"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await ctx.response.defer()
        msg = await ctx.original_message()

        country = None
        if autoboard_type == "Clan Leaderboard":
            rr = []
            tracked = self.bot.clan_db.find({"server": ctx.guild.id})
            limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})

            for clan in await tracked.to_list(length=limit):
                tag = clan.get("tag")
                c = await self.bot.getClan(tag)
                location = str(c.location)
                if location not in rr:
                    rr.append(str(location))

            options = []
            for country in rr:
                options.append(disnake.SelectOption(label=f"{country}", value=f"{country}"))

            select1 = disnake.ui.Select(
                options=options,
                placeholder="Page Navigation",
                min_values=1,  # the minimum number of options a user must select
                max_values=1  # the maximum number of options a user can select
            )
            action_row = disnake.ui.ActionRow()
            action_row.append_item(select1)

            embed = disnake.Embed(title="**For what country would you like the leaderboard autoboard?**",
                                  color=disnake.Color.green())

            await ctx.edit_original_message(embed=embed, components=[action_row])

            def check(res: disnake.MessageInteraction):
                return res.message.id == msg.id

            country = False
            while country is False:
                try:
                    res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                              timeout=600)
                except:
                    await msg.edit(components=[])
                    break

                if res.author.id != ctx.author.id:
                    await res.send(content="You must run the command to interact with components.", ephemeral=True)
                    continue
                await res.response.defer()
                country = str(res.values[0])
                await res.edit_original_message(components=[])


        tex = ""
        if autoboard_type == "Player Leaderboard":
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"topboardchannel": channel.id}})
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"tophour": 5}})
        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"lbboardChannel": channel.id}})
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"country": country}})
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"lbhour": 5}})
            tex = f"\nCountry: {country}"

        time = f"<t:{1643263200}:t>"
        embed = disnake.Embed(title="**Autoboard Successfully Setup**",
                              description=f"Channel: {channel.mention}\n"
                                          f"Time: {time}\n"
                                          f"Type: {autoboard_type}{tex}",
                              color=disnake.Color.green())
        await msg.edit(embed=embed)


    @autoboard.sub_command(name="remove", description="Remove a server autoboard")
    async def removeboard(self, ctx: disnake.ApplicationCommandInteraction, autoboard_type: str = commands.Param(choices=["Player Leaderboard", "Clan Leaderboard"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if autoboard_type == "Player Leaderboard":
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"topboardchannel": None}})
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"tophour": None}})
        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"lbboardChannel": None}})
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"country": None}})
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"lbhour": None}})

        embed = disnake.Embed(description=f"{autoboard_type} autoboard has been removed.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed, components=[])


    @autoboard.sub_command(name="list", description="View server autoboards")
    async def boardlist(self, ctx):
        tbc = None
        th = None
        lbc = None
        lbh = None
        country = None

        results = await self.bot.server_db.find_one({"server": ctx.guild.id})

        real_times = []
        start_time = 1643263200
        for x in range(0, 24):
            t = start_time + (x * 3600)
            real_times.append(t)

        try:
            tbc =  results.get("topboardchannel")
            tbc = await self.bot.pingToChannel(ctx, tbc)
            tbc = tbc.mention
        except:
            pass


        try:
            th = results.get("tophour")
            th = real_times[th - 5]
            th = f"<t:1643263200:t>"
        except:
            pass

        try:
            lbc = results.get("lbboardChannel")
            lbc = await self.bot.pingToChannel(ctx, lbc)
            lbc = lbc.mention
        except:
            pass

        try:
            lbh = results.get("lbhour")
            lbh = real_times[lbh - 5]
            lbh = f"<t:1643263200:t>"
        except:
            pass

        try:
            country = results.get("country")
        except:
            pass

        embed = disnake.Embed(title="**Autoboard List**",
                              description=f"Player leaderboard Channel: {tbc}\n"
                                    f"Player leaderboard Post Time: {th}\n"
                                    f"Clan leaderboard Channel: {lbc}\n"
                                    f"Clan leaderboard Post Time: {lbh}\n"
                                    f"Clan leaderboard Country: {country}\n",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

def setup(bot: CustomClient):
    bot.add_cog(autoB(bot))