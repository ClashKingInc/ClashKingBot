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
        #scheduler.add_job(self.clan_capital_reminder, "cron", args=["1 hr"], day_of_week="mon", hour=6)
        #scheduler.add_job(self.clan_capital_reminder, "cron", args=["6 hr"], day_of_week="mon", hour=1)
        #scheduler.add_job(self.clan_capital_reminder, "cron", args=["12 hr"], day_of_week="sun", hour=19)
        #scheduler.add_job(self.clan_capital_reminder, "cron", args=["24 hr"], day_of_week="sun", hour=7)


    @commands.slash_command(name="reminders")
    async def reminder(self, ctx):
        pass

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @reminder.sub_command(name="create", description="Set a reminder for clan games, raid weekend, wars, & more")
    async def reminder_create(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, type:str = commands.Param(choices=["Clan Capital", "Clan Games" , "War", "Inactivity"]), clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            type: Type of reminder you would like to create
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the join/leave log to
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        if type == "Clan Capital":
            await self.create_clan_capital_reminder(ctx=ctx, channel=channel, clan=clan)

    async def create_clan_capital_reminder(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, clan: coc.Clan):
        embed = disnake.Embed(description="**Choose reminder times from list**", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        options = [  # the options in your dropdown
            disnake.SelectOption(label="1 hour remaining", emoji=self.bot.emoji.clock.partial_emoji, value="1 hr"),
            disnake.SelectOption(label="6 hours remaining", emoji=self.bot.emoji.clock.partial_emoji, value="6 hr"),
            disnake.SelectOption(label="12 hours remaining", emoji=self.bot.emoji.clock.partial_emoji, value="12 hr"),
            disnake.SelectOption(label="24 hours remaining", emoji=self.bot.emoji.clock.partial_emoji, value="24 hr")
        ]
        select = disnake.ui.Select(
            options=options,
            placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=4,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.send(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        #delete any previously set ones, so we don't get ones in different channels or times
        await self.bot.reminders.delete_many({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "Clan Capital"}
        ]})
        for value in res.values:
            await self.bot.reminders.insert_one({
                "server" : ctx.guild.id,
                "type" : "Clan Capital",
                "clan" : clan.tag,
                "channel" : channel.id,
                "time" : value
            })

        reminders_created = ", ".join(res.values)
        embed = disnake.Embed(description=f"**`{reminders_created}` Clan Capital Reminders created for {ctx.guild.name}**", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        button = [disnake.ui.ActionRow(disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green, custom_id="custom_text"))]

        await res.edit_original_message(embed=embed, components=button)

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.send_modal(
            title="Customize your text",
            custom_id="customtext-",
            components=[
                disnake.ui.TextInput(
                    label="Extra Custom Text",
                    placeholder="Extra text to send when reminder is sent (gifs, rules, etc)",
                    custom_id=f"custom_text",
                    required=True,
                    style=disnake.TextInputStyle.paragraph,
                    max_length=300,
                )
            ])

        msg = await res.original_message()
        await msg.edit(components=[])

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            return await msg.edit(components=[])

        await modal_inter.response.defer()
        custom_text = modal_inter.text_values["custom_text"]
        ping_reminder = f"{custom_text}\n" \
                        f"**Example Reminder - Remaining Clan Capital Raids**\n" \
                        f"2 raids- Linked Player | {ctx.author.mention}\n" \
                        f"4 raids- Unlinked Player | #playertag"
        return await modal_inter.edit_original_message(content=ping_reminder)


    #async def create_war_reminder(self, ):

    @reminder.sub_command(name="remove", description="Remove a reminder set up on the server")
    async def reminder_remove(self, ctx: disnake.ApplicationCommandInteraction, type:str = commands.Param(choices=["Clan Capital", "Clan Games, War", "Inactivity"]), clan: coc.Clan = commands.Param(converter=clan_converter)):
        pass

    @reminder.sub_command(name="list", description="Get the list of reminders set up on the server")
    async def reminder_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @reminder_create.autocomplete("clan")
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
    bot.add_cog(reminders(bot))