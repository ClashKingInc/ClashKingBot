
from discord.ext import commands, tasks
from HelperMethods.clashClient import client, link_client, coc_client, pingToMember
import coc
from discord_slash.utils.manage_components import wait_for_component, create_select, create_select_option, create_actionrow
import discord
import datetime as dt
from main import check_commands
from datetime import timezone

usafam = client.usafam
clans = usafam.clans
server = usafam.server
war_db = usafam.war

in_main = False

class war_pings(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.war_ping_check.start()

    def cog_unload(self):
        self.war_ping_check.cancel()


    @commands.group(name="warping", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def warping(self, ctx):
        pass

    @warping.group(name="status", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def warping_set(self, ctx, on_off, *, aliases=None):
        on_off = on_off.lower()
        if on_off != "on" and on_off != "off":
            return await ctx.send("Warping status must be either `on` or `off`.")

        select = create_select(
            options=[  # the options in your dropdown
                create_select_option("1 Hour", value="1"),
                create_select_option("2 Hours", value="2"),
                create_select_option("4 Hours", value="4"),
                create_select_option("8 Hours", value="8")
            ],
            placeholder="Choose a page",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=4,  # the maximum number of options a user can select
        )
        dropdown = [create_actionrow(select)]

        embed = discord.Embed(
            description=f"Choose the hour reminders you would like for this clan(s).",
            color=discord.Color.green())

        msg = await ctx.send(embed=embed, components=dropdown)

        values = None
        while values is None:

            try:
                res = await wait_for_component(self.bot, components=dropdown,
                                               messages=msg, timeout=600)
            except:
                return await msg.edit(components=[])

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()
            values = res.selected_options


        if aliases == None:
            tracked = clans.find({"server": ctx.guild.id})
            limit = await clans.count_documents(filter={"server": ctx.guild.id})
            if limit == 0:
                return await ctx.send("This server has no linked clans.")
            for tClan in await tracked.to_list(length=limit):
                tag = tClan.get("tag")
                one_hour = "1" in values
                if one_hour:
                    if on_off == "on":
                        await clans.update_one({"$and": [
                            {"tag": tag},
                            {"server": ctx.guild.id}]},
                            {'$set': {'one_hour': True}})
                    else:
                        await clans.update_one({"$and": [
                            {"tag": tag},
                            {"server": ctx.guild.id}]},
                            {'$set': {'one_hour': False}})

                two_hour = "2" in values
                if two_hour:
                    if on_off == "on":
                        await clans.update_one({"$and": [
                            {"tag": tag},
                            {"server": ctx.guild.id}]},
                            {'$set': {'two_hour': True}})
                    else:
                        await clans.update_one({"$and": [
                            {"tag": tag},
                            {"server": ctx.guild.id}]},
                            {'$set': {'two_hour': False}})

                four_hour = "4" in values
                if four_hour:
                    if on_off == "on":
                        await clans.update_one({"$and": [
                            {"tag": tag},
                            {"server": ctx.guild.id}]},
                            {'$set': {'four_hour': True}})
                    else:
                        await clans.update_one({"$and": [
                            {"tag": tag},
                            {"server": ctx.guild.id}]},
                            {'$set': {'four_hour': False}})

                eight_hour = "8" in values
                if eight_hour:
                    if on_off == "on":
                        await clans.update_one({"$and": [
                            {"tag": tag},
                            {"server": ctx.guild.id}]},
                            {'$set': {'eight_hour': True}})
                    else:
                        await clans.update_one({"$and": [
                            {"tag": tag},
                            {"server": ctx.guild.id}]},
                            {'$set': {'eight_hour': False}})

            type = ""
            if on_off == "on":
                type = "created for"
            else:
                type = "removed from"
            values = ", ".join(values)
            embed = discord.Embed(
                description=f"Warpings for {values} hours {type} {limit} clans",
                color=discord.Color.green())

            return await msg.edit(embed=embed, components=[])

        else:
            aliases = aliases.split()
            for alias in aliases:
                results = await clans.find_one({"$and": [
                    {"alias": alias},
                    {"server": ctx.guild.id}
                ]})
                if results is None:
                    return await ctx.send(f"Invalid alias {alias} found.\n**Note:** This command only supports single word aliases when given multiple.")

            for alias in aliases:
                one_hour = "1" in values
                if one_hour:
                    if on_off == "on":
                        await clans.update_one({"$and": [
                            {"alias": alias},
                            {"server": ctx.guild.id}]},
                            {'$set': {'one_hour': True}})
                    else:
                        await clans.update_one({"$and": [
                            {"alias": alias},
                            {"server": ctx.guild.id}]},
                            {'$set': {'one_hour': False}})

                two_hour = "2" in values
                if two_hour:
                    if on_off == "on":
                        await clans.update_one({"$and": [
                            {"alias": alias},
                            {"server": ctx.guild.id}]},
                            {'$set': {'two_hour': True}})
                    else:
                        await clans.update_one({"$and": [
                            {"alias": alias},
                            {"server": ctx.guild.id}]},
                            {'$set': {'two_hour': False}})

                four_hour = "4" in values
                if four_hour:
                    if on_off == "on":
                        await clans.update_one({"$and": [
                            {"alias": alias},
                            {"server": ctx.guild.id}]},
                            {'$set': {'four_hour': True}})
                    else:
                        await clans.update_one({"$and": [
                            {"alias": alias},
                            {"server": ctx.guild.id}]},
                            {'$set': {'four_hour': False}})

                eight_hour = "8" in values
                if eight_hour:
                    if on_off == "on":
                        await clans.update_one({"$and": [
                            {"alias": alias},
                            {"server": ctx.guild.id}]},
                            {'$set': {'eight_hour': True}})
                    else:
                        await clans.update_one({"$and": [
                            {"alias": alias},
                            {"server": ctx.guild.id}]},
                            {'$set': {'eight_hour': False}})

            type = ""
            if on_off == "on":
                type = "created for"
            else:
                type = "removed from"
            values = ", ".join(values)
            embed = discord.Embed(
                description=f"Warpings for {values} hours {type} {len(aliases)} clans",
                color=discord.Color.green())

            return await msg.edit(embed=embed, components=[])

    @warping.group(name="list", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def warping_list(self, ctx):
        text = ""
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("This server has no active warpings.")
        for document in await tracked.to_list(length=limit):
            t = ""
            name = document.get("name")
            one_hour = document.get("one_hour")
            if one_hour:
                t+= "1, "
            two_hour = document.get("two_hour")
            if two_hour:
                t+= "2, "
            four_hour = document.get("four_hour")
            if four_hour:
                t+= "4, "
            eight_hour = document.get("eight_hour")
            if eight_hour:
                t+= "8"

            if t != "":
                text += f"{name}: {t} hour warpings\n"

        if text == "":
            text= "No active warpings."

        embed = discord.Embed(title=f"{ctx.guild.name} warpings\n",
            description=text,
            color=discord.Color.green())
        await ctx.send(embed=embed)


    @coc.ClientEvents.maintenance_start()
    async def maintenance_start(self):
        global in_main
        in_main = True

    @coc.ClientEvents.maintenance_completion()
    async def maintenance_end(self, start_datetime):
        now = dt.datetime.utcnow()
        time_left = start_datetime - now
        secs = time_left.total_seconds()

        war_ping_results = war_db.find(results={})
        war_ping_limit = await war_db.count_documents(filter={})
        for document in await war_ping_results.to_list(length=war_ping_limit):
            tag = document.get("tag")
            time = document.get("time")
            await war_db.update_one({"tag": tag}, {"$set": {"time": time+secs}})

        global in_main
        in_main= False


    @tasks.loop(seconds=60)
    async def war_ping_check(self):

        if in_main == True:
            return

        #current time, split into day, hour, minute for db search
        dtt = dt.datetime.now(timezone.utc)
        utc_time = dtt.replace(tzinfo=timezone.utc)
        utc_timestamp = utc_time.timestamp()

        #loop thru any results matching the time = war ping
        war_ping_results = war_db.find({"time" : {"$lte" : utc_timestamp + 60}})
        war_ping_limit = await war_db.count_documents(filter={"time" : {"$lte" : utc_timestamp + 60}})
        for document in await war_ping_results.to_list(length=war_ping_limit):
            clan_tag = document.get("tag")

            #get all matching clans (find all - could be in multiple servers)
            clan_results = clans.find(results={"tag": clan_tag})
            clan_result_limit = await clans.count_documents(filter={"tag": clan_tag})
            for clan_result in await clan_results.to_list(length=clan_result_limit):
                war_channel = clan_result.get("warChannel")
                if war_channel == None:
                    continue

                try:
                    war_channel = self.bot.get_channel(war_channel)
                except:
                    continue

                server_id = clan_result.get("server")
                guild = self.bot.get_guild(server_id)

                war = None
                try:
                    war = await coc_client.get_clan_war(clan_tag)
                except coc.errors.PrivateWarLog:
                    continue

                attacks_given = war.attacks_per_member

                missing_attacks = ""
                for member in war.members:
                    attacks_done = len(member.attacks)
                    if attacks_done < attacks_given:
                        num_attacks_missing = attacks_given - attacks_done
                        player_tag = member.tag
                        discord_id = await link_client.get_link(player_tag)
                        who_missed = None
                        try:
                            who_missed = await guild.fetch_member(discord_id)
                            who_missed = who_missed.mention
                        except:
                            who_missed = member.name

                        missing_attacks += f"{who_missed} - {num_attacks_missing} attacks missing.\n"

                try:
                    await war_channel.send(missing_attacks)
                except:
                    continue


    @war_ping_check.before_loop
    async def before_printer(self):
        print('waiting...')
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(war_pings(bot))