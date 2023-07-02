import disnake
import coc

from main import check_commands
from disnake.ext import commands
from typing import Union, List
from FamilyManagement.Reminders import ReminderUtils
from CustomClasses.CustomBot import CustomClient
from Exceptions.CustomExceptions import NotValidReminderTime

class ReminderCreation(commands.Cog, name="Reminders"):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan


    @commands.slash_command(name="reminders")
    async def reminders(self, ctx):
        pass


    @reminders.sub_command(name="create", description="Create reminders for your server - Wars, Raids, Inactivity & More")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setup_reminders(self, ctx: disnake.ApplicationCommandInteraction,
                              type = commands.Param(choices=["War & CWL", "Clan Capital", "Inactivity", "Clan Games"]),
                              times = commands.Param(name="time_left"),
                              channel: Union[disnake.TextChannel, disnake.Thread] = None):
        """
            Parameters
            ----------
            type: type of reminder to create
            times: times for reminder to go off, use commas to enter multiple times
            channel: channel for reminder, if blank will use channel command is run in
        """

        await ctx.response.defer()

        if channel is None:
            channel = ctx.channel
        temp_times = times.split(",")
        new_times = []

        if type == "War & CWL":
            for t in temp_times:
                t = t.replace(" ", "")
                if t not in self.gen_war_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await ReminderUtils.create_war_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times)
        elif type == "Clan Capital":
            for t in temp_times:
                t = t.replace(" ", "")
                new_times.append(t)
                if t not in self.gen_capital_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await ReminderUtils.create_capital_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times)
        elif type == "Clan Games":
            for t in temp_times:
                t = t.replace(" ", "")
                new_times.append(t)
                if t not in self.gen_clan_games_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await ReminderUtils.create_games_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times)
        elif type == "Inactivity":
            for t in temp_times:
                t = t.replace(" ", "")
                new_times.append(t)
                if t not in self.gen_inactivity_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await ReminderUtils.create_inactivity_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times)

        await ctx.edit_original_message(content=f"Setup Complete!", components=[])


    @reminders.sub_command(name="edit", description="edit or delete reminders on your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def delete_reminders(self, ctx: disnake.ApplicationCommandInteraction,
                               clan: coc.Clan = commands.Param(converter=clan_converter),
                               type = commands.Param(choices=["War & CWL", "Clan Capital", "Inactivity", "Clan Games"])):
        type_to_type = {"War & CWL" : "War", "Clan Capital" : "Clan Capital", "Inactivity" : "inactivity", "Clan Games" : "Clan Games"}
        r_type = type_to_type[type]
        await ReminderUtils.edit_reminder(bot=self.bot, clan=clan, ctx=ctx, type=r_type)



    @reminders.sub_command(name="list", description="Get the list of reminders set up on the server")
    async def reminder_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        embed = disnake.Embed(title=f"**{ctx.guild.name} Reminders List**", color=disnake.Color.green())
        all_reminders_tags = await self.bot.reminders.distinct("clan", filter={"$and": [{"server": ctx.guild.id}]})
        for tag in all_reminders_tags:
            clan = await self.bot.getClan(clan_tag=tag)
            if clan is None:
                continue
            reminder_text = ""
            clan_capital_reminders = await self.bot.reminders.find({"$and": [{"clan": tag}, {"type": "Clan Capital"}, {"server": ctx.guild.id}]}).to_list(length=None)
            clan_capital_reminders = sorted(clan_capital_reminders, key=lambda l: float(str(l.get('time')).replace("hr", "")), reverse=False)
            cc_reminder_text = []
            for reminder in clan_capital_reminders:
                channel = await self.bot.getch_channel(reminder.get('channel'))
                if channel is None:
                    continue
                cc_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if cc_reminder_text:
                reminder_text += "**Clan Capital:** \n" + "\n".join(cc_reminder_text) + "\n"

            clan_games_reminders = await self.bot.reminders.find({"$and": [{"clan": tag}, {"type": "Clan Games"}, {"server": ctx.guild.id}]}).to_list(length=None)
            clan_games_reminders = sorted(clan_games_reminders, key=lambda l: float(str(l.get('time')).replace("hr", "")), reverse=False)
            cg_reminder_text = []
            for reminder in clan_games_reminders:
                channel = await self.bot.getch_channel(reminder.get('channel'))
                if channel is None:
                    continue
                cg_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if cg_reminder_text:
                reminder_text += "**Clan Games:** \n" + "\n".join(cg_reminder_text) + "\n"

            inactivity_reminders = await self.bot.reminders.find({"$and": [{"clan": tag}, {"type": "inactivity"}, {"server": ctx.guild.id}]}).to_list(length=None)
            inactivity_reminders = sorted(inactivity_reminders, key=lambda l: float(str(l.get('time')).replace("hr", "")), reverse=False)
            ia_reminder_text = []
            for reminder in inactivity_reminders:
                channel = await self.bot.getch_channel(reminder.get('channel'))
                if channel is None:
                    continue
                ia_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if ia_reminder_text:
                reminder_text += "**Inactivity:** \n" + "\n".join(ia_reminder_text) + "\n"

            war_reminders = await self.bot.reminders.find({"$and": [{"clan": tag}, {"type": "War"}, {"server": ctx.guild.id}]}).to_list(length=None)
            war_reminders = sorted(war_reminders, key=lambda l: float(str(l.get('time')).replace("hr", "")), reverse=False)
            war_reminder_text = []
            for reminder in war_reminders:
                channel = await self.bot.getch_channel(reminder.get('channel'))
                if channel is None:
                    continue
                war_reminder_text.append(f"`{reminder.get('time')}` - <#{reminder.get('channel')}>")
            if war_reminder_text:
                reminder_text += "**War:** \n" + "\n".join(war_reminder_text) + "\n"
            emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            if reminder_text == "":
                continue
            embed.add_field(name=f"{emoji}{clan.name}", value=reminder_text, inline=False)
        await ctx.edit_original_message(embed=embed)



    @setup_reminders.autocomplete("time_left")
    async def reminder_autocomp(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        if ctx.filled_options["type"] == "War & CWL":
            all_times = self.gen_war_times()
        elif ctx.filled_options["type"] == "Clan Capital":
            all_times = self.gen_capital_times()
        elif ctx.filled_options["type"] == "Clan Games":
            all_times = self.gen_clan_games_times()
        elif ctx.filled_options["type"] == "Inactivity":
            all_times = self.gen_inactivity_times()
        else:
            return ["Not a valid reminder type"]
        if len(query.split(",")) >= 2:
            new_query = query.split(",")[-1]
            previous_split = query.split(",")[:-1]
            previous_split = [item.strip() for item in previous_split]
            previous = ", ".join(previous_split)
            return [f"{previous}, {time}" for time in all_times if
                    new_query.lower().strip() in time.lower() and time not in previous_split][:25]
        else:
            return [time for time in all_times if query.lower() in time.lower()][:25]

    def gen_war_times(self):
        all_times = (x * 0.25 for x in range(1, 193))
        all_times = [f"{int(time)}hr" if time.is_integer() else f"{time}hr" for time in all_times]
        return all_times

    def gen_capital_times(self):
        all_times = [1, 2, 4, 6, 8, 12, 16, 24]
        all_times = [f"{int(time)}hr" for time in all_times]
        return all_times

    def gen_clan_games_times(self):
        all_times = [1, 2, 4, 6, 12, 24, 36, 48, 72, 96, 120, 144]
        all_times = [f"{time}hr" for time in all_times]
        return all_times

    def gen_inactivity_times(self):
        return ["24hr", "48hr", "72hr", "144hr", "288hr"]

def setup(bot: CustomClient):
    bot.add_cog(ReminderCreation(bot))
