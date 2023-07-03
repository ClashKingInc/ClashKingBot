import disnake
import coc
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import CustomServer, ServerClan
from main import check_commands
from typing import Union
from utils.general import calculate_time
from utils.discord_utils import interaction_handler


class Logs(commands.Cog, name="Logs"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @commands.slash_command(name="log")
    async def log(self, ctx):


    @log.sub_command(name="add", description="Set a variety of different clan logs for your server!")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_log_add(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                          channel: Union[disnake.TextChannel, disnake.Thread] = commands.Param(default=None,name="channel")):
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.", ephemeral=True)
        await ctx.response.defer()

        if channel is None:
            channel = ctx.channel

        type_dict = {"Clan Join": "join_log", "Clan Leave" : "leave_log",
                     "Townhall Upgrade", "Troop Upgrade", "Spell Upgrade", "Hero Upgrade", "Pet Upgrade",
                     "Legend Attacks", "Legend Defenses",
                     "Capital Donations", "Capital Attacks (offense)", "Capital Attacks (defense)", "Capital Summary (weekly)", "Capital Panel (offense)",
                     "Capital Opponent Summary (defense)", "Donation Log" : "donolog",
                     "Continuous War Log", "War Panel Log"}


        type_dict = {"Clan Capital Log": "clan_capital", "Join Log": "joinlog",
                     "War Log - Continuous": "war_log-Continuous Feed", "War Log - Panel": "war_log-Update Feed",
                     "Legend Log": "legend_log", "Donation Log": "donolog", "Clan Log": "upgrade_log"}
        swapped_type_dict = {v: k for k, v in type_dict.items()}
        options = []
        for log_type in log_types:
            options.append(disnake.SelectOption(label=log_type, emoji=self.bot.emoji.clock.partial_emoji,
                                                value=type_dict[log_type]))
        select = disnake.ui.Select(
            options=options,
            placeholder="Select logs!",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        embed = disnake.Embed(
            description=f"Choose the logs that you would like to add for {clan.name} in {channel.mention}\n"
                        f"Use </set log help:1033741922562494569> for more details", color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id and res.author.id == ctx.author.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await ctx.edit_original_message(components=[])
        await res.response.defer()

        if "war_log-Continuous Feed" in res.values and "war_log-Update Feed" in res.values:
            embed = disnake.Embed(description=f"Cannot choose both war log types!", color=disnake.Color.red())
            return await res.edit_original_message(embed=embed, components=[])

        if isinstance(channel, disnake.Thread):
            await channel.add_user(self.bot.user)

        text = ""
        for value in res.values:
            if "war_log" in value:
                log_type = value.split("-")[-1]
                print(log_type)
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan.tag},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"war_log": channel.id, "attack_feed": log_type}})
                text += f"{swapped_type_dict[value]}- {self.bot.emoji.yes}Success\n"
            elif value == "legend_log":
                success = await self.legend_log(ctx, clan, channel)
                if success:
                    text += f"{swapped_type_dict[value]}- {self.bot.emoji.yes}Success\n"
                else:
                    text += f"{swapped_type_dict[value]}- {self.bot.emoji.no}Error\n"
            else:
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan.tag},
                    {"server": ctx.guild.id}
                ]}, {'$set': {f"{value}": channel.id}})
                text += f"{swapped_type_dict[value]}- {self.bot.emoji.yes}Success\n"

        embed = disnake.Embed(title=f"Logs Created for {clan.name}", description=text,
                              color=disnake.Color.green())
        # embed.set_thumbnail(url=clan.badge.medium.url)
        await res.edit_original_message(embed=embed, components=[])





    async def legend_log(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan,
                         channel: Union[disnake.TextChannel, disnake.Thread]):
        # may activate if duplicates becomes an issue
        # clan_webhooks = await self.bot.clan_db.distinct("legend_log.webhook", filter={"server": ctx.guild.id})
        is_thread = False
        try:
            bot_av = self.bot.user.avatar.read().close()
            if isinstance(channel, disnake.Thread):
                webhooks = await channel.parent.webhooks()
            else:
                webhooks = await channel.webhooks()
            webhook = next((w for w in webhooks if w.user.id == self.bot.user.id), None)
            if webhook is None:
                if isinstance(channel, disnake.Thread):
                    webhook = await channel.parent.create_webhook(name="ClashKing", avatar=bot_av,
                                                                  reason="Legends Feed")
                else:
                    webhook = await channel.create_webhook(name="ClashKing", avatar=bot_av, reason="Legends Feed")
        except Exception as e:
            return False

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"legend_log.webhook": webhook.id}})
        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"legend_log.thread": None}})

        if isinstance(channel, disnake.Thread):
            await self.bot.clan_db.update_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]}, {'$set': {"legend_log.thread": ctx.channel.id}})
            await webhook.send("Legend Log Success", username='ClashKing',
                               avatar_url="https://cdn.discordapp.com/attachments/923767060977303552/1033385579091603497/2715c2864c10dc64a848f7d12d1640d0.png",
                               thread=channel)

        else:
            await webhook.send("Legend Log Success", username='ClashKing',
                               avatar_url="https://cdn.discordapp.com/attachments/923767060977303552/1033385579091603497/2715c2864c10dc64a848f7d12d1640d0.png")

        return True

    @log.sub_command(name="remove", description="Remove a log for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_log_remove(self, ctx: disnake.ApplicationCommandInteraction, clan: str, log_to_remove=commands.Param(
        choices=["Clan Capital Log", "Join Log", "War Log", "Legend Log", "Donation Log", "Clan Log"])):
        type_dict = {"Clan Capital Log": "clan_capital", "Join Log": "joinlog", "War Log": "war_log",
                     "Legend Log": "legend_log", "Donation Log": "donolog", "Clan Log": "upgrade_log"}
        log_type = type_dict[log_to_remove]

        clan = await self.bot.getClan(clan)

        if clan is None:
            return await ctx.edit_original_message("Not a valid clan tag")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        log_channel = results.get(log_type)
        if log_type == "legend_log" and log_channel is not None:
            log_channel = log_channel.get("webhook")

        if log_channel is None:
            embed = disnake.Embed(description=f"This clan does not have a {log_to_remove} set up on this server.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if log_type == "legend_log":
            await self.bot.clan_db.update_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]}, {'$set': {f"{log_type}.thread": None}})
            log_type += ".webhook"

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {f"{log_type}": None}})

        if log_to_remove != "Legend Log":
            channel = await self.bot.fetch_channel(log_channel)

            embed = disnake.Embed(description=f"{log_to_remove} in {channel.mention} removed for {clan.name}",
                                  color=disnake.Color.green())
        else:
            embed = disnake.Embed(description=f"{log_to_remove} removed for {clan.name}",
                                  color=disnake.Color.green())

        await ctx.edit_original_message(embed=embed)

    @log.sub_command(name="help", description="Overview of common questions & functionality of logs")
    async def set_log_help(self, ctx: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(title="ClashKing Clan Log Overview",
                              description="__Answer to Common Questions__\n"
                                          "- The logs pull updated info about every 4-5 minutes\n"
                                          "- The logs support channels, threads, & forums"
                                          "- Multiple logs can be set in one channel")
        embed.add_field(name="Clan Capital Log",
                        value="- Reports Clan Capital Donations\n"
                              "- Reports Clan Capital Contributions (slightly inaccurate due to the COC API, will be fixed in a future update)\n"
                              "- Will post a overview for the week when Raid Weekend ends\n"
                              "- **Cannot** show what buildings gold is contributed to")
        embed.add_field(name="Join Leave Log",
                        value="- Reports Clan Member Joins\n"
                              "- Reports Clan Member Leaves\n"
                              "- Will show what clan the member left to")
        embed.add_field(name="Legend Log",
                        value="- Reports Legend Attacks & Defenses\n"
                              "- Some inaccuracies, `/faq` covers in more detail")
        embed.add_field(name="War Log",
                        value="- 2 styles\n"
                              "- Panel will post an embed just when the war starts, then update the embed as the war continues\n"
                              "- Continuous will post embeds everytime something happens in war (attack, defense, war start/end)")
        embed.add_field(name="Donation Log",
                        value="- Reports amount of troops donated & received and by which clan members\n"
                              "- **Cannot** show which troops were donated")
        embed.add_field(name="Clan Log",
                        value="- Reports when upgrades are done (townhall, troop, hero, pets, sieges, or spells)\n"
                              "- Reports when a name change is made\n"
                              "- Reports when a super troop is boosted\n"
                              "- Reports when a players league changes\n"
                              "- **Cannot** get building upgrades or when an lab or hero upgrade is started")
        await ctx.edit_original_message(embed=embed)




    @log.sub_command(name="reddit-recruit-feed",
                     description="Feed of searching for a clan posts on the recruiting subreddit")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def reddit_recruit(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel,
                             role_to_ping: disnake.Role = None,
                             remove=commands.Param(default=None, choices=["Remove Feed"])):
        """
            Parameters
            ----------
            channel: channel to set the feed to
            role_to_ping: role to ping when a new recruit appears
            remove: option to remove this feed
        """
        if remove is None:
            role_id = None if role_to_ping is None else role_to_ping.id
            await self.bot.server_db.update_one({"server": ctx.guild.id},
                                                {"$set": {"reddit_feed": channel.id, "reddit_role": role_id}})

            embed = disnake.Embed(description=f"**Reddit Recruit feed set to {channel.mention}**",
                                  color=disnake.Color.green())

        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id},
                                                {"$set": {"reddit_feed": None, "reddit_role": None}})

            embed = disnake.Embed(description="**Reddit Recruit feed removed**", color=disnake.Color.green())

        return await ctx.edit_original_message(embed=embed)


    @set_log_remove.autocomplete("clan")
    @set_log_add.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[:25]



def setup(bot: CustomClient):
    bot.add_cog(Logs(bot))