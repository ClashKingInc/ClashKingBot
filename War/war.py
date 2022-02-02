
from discord.ext import commands, tasks
from HelperMethods.clashClient import client, link_client, coc_client, pingToMember
import coc
from discord_slash.utils.manage_components import wait_for_component, create_select, create_select_option, create_actionrow
import discord
import datetime as dt



usafam = client.usafam
clans = usafam.clans
server = usafam.server


class autoB(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.war_ping_check.start()

    def cog_unload(self):
        self.war_ping_check.cancel()

    @tasks.loop(seconds=60)
    async def war_ping_check(self):

        #current time, split into day, hour, minute for db search
        now = dt.datetime.utcnow()
        day = now.day
        hour = now.hour
        minute = now.minute

        #loop thru any results matching the time = war ping
        war_ping_results = server.find(results = {"$and": [{"day": day},{"hour": hour}, {"minute": minute}]})
        war_ping_limit = await server.count_documents(filter={"$and": [{"day": day},{"hour": hour},{"minute": minute}]})
        for document in await war_ping_results.to_list(length=war_ping_limit):
            clan_tag = document.get("tag")

            #get all matching clans (find all - could be in multiple servers)
            clan_results = clans.find(results={"tag": clan_tag})
            clan_result_limit = await clans.count_documents(filter={"tag": clan_tag})
            for clan_result in await clan_results.to_list(length=clan_result_limit):
                war_channel = clan_result.get("warChannel")
                war_channel = self.bot.get_channel(war_channel)

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
    bot.add_cog(autoB(bot))