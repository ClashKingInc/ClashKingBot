import coc
import disnake

from classes.bot import CustomClient
from discord.options import autocomplete
from disnake.ext import commands
from utility.constants import DISCORD_STATUS_TYPES
from utility.discord_utils import check_commands


class Settings(commands.Cog, name="Settings"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="set")
    async def set(self, ctx):
        await ctx.response.defer()
        pass

    @set.sub_command(
        name="webhook-profiles",
        description="Set the profile pictures/name for all CK webhooks in server",
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_webhook_profiles(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        picture: disnake.Attachment,
        name: str,
    ):
        await ctx.edit_original_message(
            content="<a:loading:948121999526461440> Updating, this can take several minutes."
        )
        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        for clan in db_server.clans:
            logs = [
                clan.join_log,
                clan.leave_log,
                clan.capital_attacks,
                clan.capital_donations,
                clan.capital_weekly_summary,
                clan.raid_panel,
                clan.donation_log,
                clan.super_troop_boost_log,
                clan.role_change,
                clan.donation_log,
                clan.troop_upgrade,
                clan.th_upgrade,
                clan.league_change,
                clan.spell_upgrade,
                clan.hero_upgrade,
                clan.name_change,
                clan.war_log,
                clan.war_panel,
                clan.legend_log_defenses,
                clan.legend_log_attacks,
            ]
            real_logs = set()
            for log in logs:
                if log.webhook is not None:
                    real_logs.add(log.webhook)

            for log in real_logs:
                webhook = await self.bot.getch_webhook(log)
                await webhook.edit(name=name, avatar=(await picture.read()))
        await ctx.edit_original_message(
            content=f"All logs profile pictures set to {name} with the following image:",
            file=(await picture.to_file()),
        )

    @set.sub_command(
        name="bot-status",
        description="Set the bot status for a custom bot (only works if you have one)",
    )
    @commands.is_owner()
    async def set_status(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        activity_text: str = commands.Param(),
        status: str = commands.Param(choices=["Online", "Offline", "Idle", "DND"]),
    ):

        await self.bot.change_presence(
            activity=disnake.CustomActivity(state=activity_text, name="Custom Status"),
            status=DISCORD_STATUS_TYPES.get(status),
        )
        await self.bot.custom_bots.update_one(
            {"token": self.bot._config.bot_token},
            {"$set": {"state.activity_text": activity_text, "state.status": status}},
        )
        await ctx.edit_original_message("Status changed")

    @commands.slash_command(name="whitelist")
    async def whitelist(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @whitelist.sub_command(
        name="add", description="Adds a role that can run a specific command."
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def whitelist_add(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        ping: disnake.Member | disnake.Role,
        command: str = commands.Param(
            default=None, autocomplete=autocomplete.command_autocomplete
        ),
    ):

        results = await self.bot.whitelist.find_one(
            {
                "$and": [
                    {"command": command},
                    {"server": ctx.guild.id},
                    {"role_user": ping.id},
                ]
            }
        )

        if results is not None:
            embed = disnake.Embed(
                description=f"{ping.mention} is already whitelisted for `{command}`.",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed)

        await self.bot.whitelist.insert_one(
            {
                "command": command,
                "server": ctx.guild.id,
                "role_user": ping.id,
                "is_role": isinstance(ping, disnake.Role),
            }
        )

        embed = disnake.Embed(
            description=f"{ping.mention} added to `{command}` whitelist.",
            color=disnake.Color.green(),
        )
        return await ctx.send(embed=embed)

    @whitelist.sub_command(
        name="remove", description="Deletes a role/user that can run a specific command"
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def whitelist_remove(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        ping: disnake.Member | disnake.Role,
        command: str = commands.Param(
            default=None, autocomplete=autocomplete.command_autocomplete
        ),
    ):

        results = await self.bot.whitelist.find_one(
            {
                "$and": [
                    {"command": command},
                    {"server": ctx.guild.id},
                    {"role_user": ping.id},
                ]
            }
        )

        if results is None:
            embed = disnake.Embed(
                description=f"{ping.mention} has no active whitelist for `{command}`.",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed)

        await self.bot.whitelist.find_one_and_delete(
            {"command": command, "server": ctx.guild.id, "role_user": ping.id}
        )

        embed = disnake.Embed(
            description=f"{ping.mention} removed from `{command}` whitelist.",
            color=disnake.Color.green(),
        )
        return await ctx.send(embed=embed)

    @whitelist.sub_command(
        name="list",
        description="Displays the list of commands that have whitelist overrides.",
    )
    async def whitelist_list(self, ctx: disnake.ApplicationCommandInteraction):
        text = ""
        results = self.bot.whitelist.find({"server": ctx.guild.id})
        limit = await self.bot.whitelist.count_documents(
            filter={"server": ctx.guild.id}
        )
        for role in await results.to_list(length=limit):
            r = role.get("role_user")
            command = role.get("command")
            if role.get("is_role"):
                text += f"<@&{r}> | `{command}`\n"
            else:
                text += f"<@{r}> | `{command}`\n"

        if text == "":
            text = "Whitelist is empty."

        embed = disnake.Embed(
            title=f"Command Whitelist", description=text, color=disnake.Color.green()
        )

        await ctx.send(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(Settings(bot))
