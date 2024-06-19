import disnake
import coc
import sentry_sdk

from disnake.ext import commands
from exceptions.CustomExceptions import *
from classes.bot import CustomClient


class ExceptionHandler(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_slash_command_error(
        self, ctx: disnake.ApplicationCommandInteraction, error
    ):
        if isinstance(error, disnake.ext.commands.ConversionError):
            error = error.original

        if isinstance(error, disnake.ext.commands.CommandInvokeError):
            error = error.original

        if isinstance(error, coc.errors.NotFound):
            embed = disnake.Embed(
                description="Not a valid clan/player tag.", color=disnake.Color.red()
            )
            return await ctx.send(embed=embed)

        if isinstance(error, disnake.HTTPException):
            embed = disnake.Embed(
                description=f"{error.text}", color=disnake.Color.red()
            )
            return await ctx.send(embed=embed)

        if isinstance(error, coc.errors.Maintenance):
            embed = disnake.Embed(
                description=f"Game is currently in Maintenance.",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.CheckAnyFailure):
            if isinstance(error.errors[0], disnake.ext.commands.MissingPermissions):
                embed = disnake.Embed(
                    description=error.errors[0], color=disnake.Color.red()
                )
                return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.MissingPermissions):
            embed = disnake.Embed(description=error, color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.CommandError):
            error = error.original

        if isinstance(error, APITokenRequired):
            embed = disnake.Embed(
                title="**API Token is required for this server**",
                description=f"- Reference below for help finding your api token.\n"
                f"- Open Clash and navigate to Settings > More Settings [in-game link](https://link.clashofclans.com/?action=OpenMoreSettings)\n"
                "- Scroll down to the bottom and copy the api token.\n"
                "- View the picture below for reference.",
                color=disnake.Color.red(),
            )
            embed.set_image(
                url="https://cdn.clashking.xyz/clash-assets/bot/api_token_help.png"
            )
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, InvalidAPIToken):
            embed = disnake.Embed(
                title="**Invalid API Token!**",
                description=f"- Reference below for help finding your api token.\n"
                f"- Open Clash and navigate to Settings > More Settings [in-game link](https://link.clashofclans.com/?action=OpenMoreSettings)\n"
                "- Scroll down to the bottom and copy the api token.\n"
                "- View the picture below for reference.",
                color=disnake.Color.red(),
            )
            embed.set_image(
                url="https://cdn.clashking.xyz/clash-assets/bot/api_token_help.png"
            )
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, NoLinkedAccounts):
            embed = disnake.Embed(
                description=f"No Accounts Linked To This User",
                color=disnake.Color.red(),
            )
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, coc.errors.PrivateWarLog):
            embed = disnake.Embed(
                description=f"This Clan has a Private War Log :/",
                color=disnake.Color.red(),
            )
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.NotOwner):
            embed = disnake.Embed(
                description=f"You are not the owner of this bot. {self.bot.owner.mention} is.",
                color=disnake.Color.red(),
            )
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, NotValidReminderTime):
            embed = disnake.Embed(
                description="Not a valid reminder time, please use options from the autocomplete.",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed)

        if isinstance(error, PlayerNotInLegends):
            embed = disnake.Embed(
                description=f"Player is not in legends.", color=disnake.Color.red()
            )
            return await ctx.send(embed=embed)

        if isinstance(error, ThingNotFound):
            embed = disnake.Embed(
                description=f"{str(error)}", color=disnake.Color.red()
            )
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, MessageException):
            embed = disnake.Embed(
                description=f"{str(error)}", color=disnake.Color.red()
            )
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, MissingWebhookPerms):
            embed = disnake.Embed(
                description=f"Missing Permissions to Create or Edit Webhooks",
                color=disnake.Color.red(),
            )
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, ExportTemplateAlreadyExists):
            embed = disnake.Embed(
                description=f"Export Template with this name already exists.",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed, ephemeral=False)

        if isinstance(error, RosterAliasAlreadyExists):
            embed = disnake.Embed(
                description=f"Roster with this alias already exists.",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, RosterDoesNotExist):
            embed = disnake.Embed(
                description=f"Roster with this alias does not exist. Use `/roster create`",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PlayerAlreadyInRoster):
            embed = disnake.Embed(
                description=f"Player has already been added to this roster.",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PlayerNotInRoster):
            embed = disnake.Embed(
                description=f"Player not found in this roster.",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, RosterSizeLimit):
            embed = disnake.Embed(
                description=f"Roster has hit max size limit", color=disnake.Color.red()
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PanelNotFound):
            embed = disnake.Embed(
                description=f"Panel not found!", color=disnake.Color.red()
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, ButtonNotFound):
            embed = disnake.Embed(
                description=f"Button not found!", color=disnake.Color.red()
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PanelAlreadyExists):
            embed = disnake.Embed(
                description=f"Panel of this name already exists!",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, ButtonAlreadyExists):
            embed = disnake.Embed(
                description=f"Button of this name already exists!",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, FaultyJson):
            embed = disnake.Embed(
                description=f"Custom Embed Code is Faulty - > be sure to use this site -> https://autocode.com/tools/discord/embed-builder/ , "
                f"create your embed, then click `copy code`",
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, ExpiredComponents):
            return await ctx.edit_original_message(components=[])

        if isinstance(error, disnake.NotFound):
            return

        event_id = sentry_sdk.capture_exception(error)
        embed = disnake.Embed(
            description=f"An internal error occurred, it has been reported to the developer. You can follow updates & bug fixes in the [support server](https://discord.gg/clashking)",
            color=disnake.Color.red(),
        )

        if self.bot.user.public_flags.verified_bot:
            buttons = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Sentry",
                    url=f"https://clashking.sentry.io/4504206148829184/?query={event_id}",
                    style=disnake.ButtonStyle.url,
                )
            )
            channel = await self.bot.getch_channel(1206771175259246642)
            error_embed = disnake.Embed(
                title="Error",
                description=f"{str(error)[:1000]}",
                color=disnake.Color.red(),
            )
            error_embed.add_field(
                name="User",
                value=f"{ctx.user.global_name} | {ctx.user.mention}",
                inline=False,
            )
            error_embed.add_field(
                name="Server", value=f"{ctx.guild.name} | {ctx.guild.id}", inline=False
            )
            error_embed.add_field(
                name="Command",
                value=f"{ctx.application_command.qualified_name}",
                inline=False,
            )
            error_embed.add_field(
                name="Bot",
                value=f"{ctx.bot.user.name} | {ctx.bot.user.mention}",
                inline=False,
            )
            error_embed.add_field(
                name="Options", value=f"{str(ctx.filled_options)[:1020]}", inline=False
            )
            await channel.send(embed=error_embed, components=[buttons])

        if not ctx.response.is_done():
            await ctx.edit_original_message(embed=embed)
        else:
            await ctx.send(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(ExceptionHandler(bot))
