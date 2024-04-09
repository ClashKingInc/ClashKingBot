import coc
import disnake
import pendulum as pend

from classes.bot import CustomClient
from disnake.ext import commands
from discord.options import convert, autocomplete
from exceptions.CustomExceptions import NotValidReminderTime
from .send import war_reminder
from typing import Union, List
from .utils import create_war_reminder, create_games_reminder, create_roster_reminder, create_capital_reminder, create_inactivity_reminder, edit_reminder
from .utils import gen_war_times, gen_capital_times, gen_roster_times, gen_inactivity_times, gen_clan_games_times
from utility.discord_utils import check_commands, interaction_handler
from utility.components import clan_component
from utility.time import time_difference


class ReminderCommands(commands.Cog, name="Reminders"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="reminders")
    async def reminders(self, ctx):
        pass


    @reminders.sub_command(name="create", description="Create reminders for your server - Wars, Raids, Inactivity & More")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setup_reminders(self, ctx: disnake.ApplicationCommandInteraction,
                              type=commands.Param(choices=["War & CWL", "Clan Capital", "Inactivity", "Clan Games", "Roster"]),
                              times=commands.Param(name="time_left", autocomplete=autocomplete.reminder_times),
                              channel: Union[disnake.TextChannel, disnake.Thread] = None):
        """
            Parameters
            ----------
            type: type of reminder to create
            times: times for reminder to go off, use commas to enter multiple times
            channel: channel for reminder, if blank will use channel command is run in
        """
        await ctx.response.defer()
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)

        channel = channel or ctx.channel
        temp_times = times.split(",")
        new_times = []

        if type == "War & CWL":
            for t in temp_times:
                t = t.replace(" ", "")
                if t not in gen_war_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await create_war_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times, embed_color=embed_color)
        elif type == "Clan Capital":
            for t in temp_times:
                t = t.replace(" ", "")
                if t not in gen_capital_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await create_capital_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times, embed_color=embed_color)
        elif type == "Clan Games":
            for t in temp_times:
                t = t.replace(" ", "")
                if t not in gen_clan_games_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await create_games_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times, embed_color=embed_color)
        elif type == "Inactivity":
            for t in temp_times:
                t = t.replace(" ", "")
                if t not in gen_inactivity_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await create_inactivity_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times, embed_color=embed_color)
        elif type == "Roster":
            for t in temp_times:
                t = t.replace(" ", "")
                if t not in gen_roster_times():
                    raise NotValidReminderTime
                new_times.append(f"{t[:-2]} hr")
            await create_roster_reminder(bot=self.bot, ctx=ctx, channel=channel, times=new_times, embed_color=embed_color)

        await ctx.edit_original_message(content=f"Setup Complete!", components=[])


    @reminders.sub_command(name="edit", description="edit or delete reminders on your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def edit_reminders(self, ctx: disnake.ApplicationCommandInteraction,
                             clan: coc.Clan = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan),
                             type=commands.Param(choices=["War & CWL", "Clan Capital", "Inactivity", "Clan Games", "Roster"])):
        await ctx.response.defer()
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        type_to_type = {"War & CWL": "War", "Clan Capital": "Clan Capital", "Inactivity": "inactivity", "Clan Games": "Clan Games", "Roster": "roster"}
        r_type = type_to_type[type]
        await edit_reminder(bot=self.bot, clan=clan, ctx=ctx, type=r_type, embed_color=embed_color)


    @reminders.sub_command(name="manual", description="send a manual reminder")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def manual_reminders(self, ctx: disnake.ApplicationCommandInteraction,
                               clan: coc.Clan = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan),
                               type = commands.Param(choices=["War & CWL"]),
                               channel: disnake.TextChannel | disnake.Thread = None):
        await ctx.response.defer(ephemeral=True)
        channel = channel or ctx.channel
        war = await self.bot.coc_client.get_current_war(clan_tag=clan.tag)
        event = {
            "time" : time_difference(start=pend.now(tz=pend.UTC), end=war.end_time.time.replace(tzinfo=pend.UTC)),
            "clan_tag" : clan.tag,
            "data" : war._raw_data
        }
        await war_reminder(bot=self.bot, event=event, manual_send=True, channel=channel)
        await ctx.edit_original_message(content=f"Reminder sent to {channel.mention}")


    @reminders.sub_command(name="list", description="Get the list of reminders set up on the server")
    async def reminder_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        all_reminders_tags = await self.bot.reminders.distinct("clan", filter={"$and": [{"server": ctx.guild.id}]})
        clans = await self.bot.get_clans(tags=all_reminders_tags)
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)

        dropdown = [clan_component(bot=self.bot, all_clans=clans, clan_page=0, max_choose=1)]

        async def reminder_list_embed(clan: coc.Clan, embed_color: disnake.Color):
            tag = clan.tag

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

            if reminder_text == "":
                reminder_text = "No Reminders"

            embed = disnake.Embed(title=f"**{clan.name} Reminders List**", description=reminder_text, color=embed_color)
            embed.set_thumbnail(url=clan.badge.url)
            return embed

        await ctx.edit_original_message(embed=(await reminder_list_embed(clans[0], embed_color=embed_color)), components=dropdown)
        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            clan_tag = res.values[0].split("_")[-1]
            embed = await reminder_list_embed(clan=coc.utils.get(clans, tag=clan_tag), embed_color=embed_color)
            await res.edit_original_message(embed=embed)



def setup(bot: CustomClient):
    bot.add_cog(ReminderCommands(bot))
