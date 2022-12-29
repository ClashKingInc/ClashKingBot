from main import check_commands
from disnake.ext import commands
from typing import Union
from .ReminderUtils import *

class ReminderCreation(commands.Cog, name="Reminders"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan


    @commands.slash_command(name="reminders")
    async def reminder(self, ctx):
        pass

    @reminder.sub_command_group(name="war")
    async def war_reminder(self, ctx):
        pass

    @reminder.sub_command_group(name="clan-capital")
    async def clan_capital_reminder(self, ctx):
        pass

    @reminder.sub_command_group(name="clan-games")
    async def clan_games_reminder(self, ctx):
        pass

    @reminder.sub_command_group(name="inactivity")
    async def inactivity_reminder(self, ctx):
        pass

    @war_reminder.sub_command(name="create", description="Setup reminders for clan wars & cwl")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def war_reminder_create(self, ctx: disnake.ApplicationCommandInteraction,
                              clan: coc.Clan = commands.Param(converter=clan_converter),
                              channel: Union[disnake.TextChannel, disnake.Thread] = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the reminder to
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        if channel is None:
            channel = ctx.channel
        await create_war_reminder(ctx=ctx, channel=channel, clan=clan, bot=self.bot)


    @war_reminder.sub_command(name="remove", description="Remove war reminder(s) for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def war_reminder_remove(self, ctx: disnake.ApplicationCommandInteraction,
                              clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        await remove_war_reminder(ctx=ctx, clan=clan, bot=self.bot)

    @war_reminder.sub_command(name="queue", description="Reminders in queue to be sent")
    async def war_reminder_queue(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        all_reminders_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        all_jobs = scheduler.get_jobs()
        job_list = ""
        clans = {}
        for job in all_jobs:
            if job.name in all_reminders_tags:
                time = str(job.id).split("_")
                tag = time[1]
                if tag not in clans:
                    clan = await self.bot.getClan(clan_tag=tag)
                    clans[tag] = clan
                else:
                    clan = clans[tag]
                if clan is None:
                    continue
                run_time = job.next_run_time.timestamp()
                job_list += f"<t:{int(run_time)}:R> - {clan.name}\n"
        embed = disnake.Embed(title=f"{ctx.guild.name} War Reminder Queue", description=job_list)
        await ctx.edit_original_message(embed=embed)


    @clan_games_reminder.sub_command(name="create", description="Setup reminders for clan games")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clan_games_reminder_create(self, ctx: disnake.ApplicationCommandInteraction,
                              clan: coc.Clan = commands.Param(converter=clan_converter),
                              channel: Union[disnake.TextChannel, disnake.Thread] = None,
                              point_threshold=commands.Param(default=4000, choices=["500", "1000", "1500", "2000", "2500", "3000", "3500", "4000"])):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the reminder to
            point_threshold: only ping people with less than this many points, default 4000
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        if channel is None:
            channel = ctx.channel
        await create_clan_games_reminder(ctx=ctx, channel=channel, clan=clan, point_threshold=int(point_threshold), bot=self.bot)

    @clan_games_reminder.sub_command(name="remove", description="Remove clan games reminder(s) for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clan_games_reminder_remove(self, ctx: disnake.ApplicationCommandInteraction,
                                  clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        await remove_clan_games_reminder(ctx=ctx, clan=clan, bot=self.bot)




    @clan_capital_reminder.sub_command(name="create", description="Setup reminders for clan capital")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clan_capital_reminder_create(self, ctx: disnake.ApplicationCommandInteraction,
                                         clan: coc.Clan = commands.Param(converter=clan_converter),
                                         channel: Union[disnake.TextChannel, disnake.Thread] = None,
                                         attack_threshold=commands.Param(default=6, choices=["1", "2", "3", "4", "5", "6"])):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the reminder to
            attack_threshold: only ping people with less than this many attacks, default 6
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        if channel is None:
            channel = ctx.channel
        await create_clan_capital_reminder(ctx=ctx, channel=channel, clan=clan, attack_threshold=int(attack_threshold), bot=self.bot)


    @clan_capital_reminder.sub_command(name="remove", description="Remove clan capital reminder(s) for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clan_capital_reminder_remove(self, ctx: disnake.ApplicationCommandInteraction,
                                         clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        await remove_clan_capital_reminder(ctx=ctx, clan=clan, bot=self.bot)





    @inactivity_reminder.sub_command(name="create", description="Setup reminders for inactivity")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def inactivity_reminder_create(self, ctx: disnake.ApplicationCommandInteraction,
                                           clan: coc.Clan = commands.Param(converter=clan_converter),
                                           channel: Union[disnake.TextChannel, disnake.Thread] = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the reminder to
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        if channel is None:
            channel = ctx.channel
        await create_inactivity_reminder(ctx=ctx, channel=channel, clan=clan, bot=self.bot)


    @inactivity_reminder.sub_command(name="remove", description="Remove inactivity reminder(s) for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def inactivity_reminder_remove(self, ctx: disnake.ApplicationCommandInteraction,
                                           clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        await remove_inactivity_reminder(ctx=ctx, clan=clan, bot=self.bot)




    @reminder.sub_command(name="list", description="Get the list of reminders set up on the server")
    async def reminder_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        embed = disnake.Embed(title=f"**{ctx.guild.name} Reminders List**")
        all_reminders_tags = await self.bot.reminders.distinct("clan", filter={"$and": [{"server": ctx.guild.id}]})
        for tag in all_reminders_tags:
            clan = await self.bot.getClan(clan_tag=tag)
            if clan is None:
                continue
            reminder_text = ""
            clan_capital_reminders = self.bot.reminders.find(
                {"$and": [{"clan": tag}, {"type": "Clan Capital"}, {"server": ctx.guild.id}]})
            cc_reminder_text = []
            for reminder in await clan_capital_reminders.to_list(length=100):
                cc_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if cc_reminder_text:
                reminder_text += "**Clan Capital:** \n" + "\n".join(cc_reminder_text) + "\n"

            clan_games_reminders = self.bot.reminders.find(
                {"$and": [{"clan": tag}, {"type": "Clan Games"}, {"server": ctx.guild.id}]})
            cg_reminder_text = []
            for reminder in await clan_games_reminders.to_list(length=100):
                cg_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if cg_reminder_text:
                reminder_text += "**Clan Games:** \n" + "\n".join(cc_reminder_text) + "\n"

            inactivity_reminders = self.bot.reminders.find(
                {"$and": [{"clan": tag}, {"type": "inactivity"}, {"server": ctx.guild.id}]})
            ia_reminder_text = []
            for reminder in await inactivity_reminders.to_list(length=100):
                ia_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if ia_reminder_text:
                reminder_text += "**Inactivity:** \n" + "\n".join(cc_reminder_text) + "\n"

            war_reminders = self.bot.reminders.find({"$and": [{"clan": tag}, {"type": "War"}, {"server": ctx.guild.id}]})
            war_reminder_text = []
            for reminder in await war_reminders.to_list(length=100):
                war_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if war_reminder_text:
                reminder_text += "**War:** \n" + "\n".join(war_reminder_text) + "\n"
            emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            embed.add_field(name=f"{emoji}{clan.name}", value=reminder_text, inline=False)
        await ctx.edit_original_message(embed=embed)






    @war_reminder_create.autocomplete("clan")
    @war_reminder_remove.autocomplete("clan")
    @clan_games_reminder_create.autocomplete("clan")
    @clan_games_reminder_remove.autocomplete("clan")
    @clan_capital_reminder_create.autocomplete("clan")
    @clan_capital_reminder_remove.autocomplete("clan")
    @inactivity_reminder_create.autocomplete("clan")
    @inactivity_reminder_remove.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        return clan_list[0:25]

def setup(bot: CustomClient):
    bot.add_cog(ReminderCreation(bot))
