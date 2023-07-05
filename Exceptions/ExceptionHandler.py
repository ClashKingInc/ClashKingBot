import disnake
import coc
from disnake.ext import commands
from Exceptions.CustomExceptions import *
from CustomClasses.CustomBot import CustomClient
import sentry_sdk

class ExceptionHandler(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: disnake.ApplicationCommandInteraction, error):
        if isinstance(error, disnake.ext.commands.ConversionError):
            error = error.original
            print(error)

        if isinstance(error, coc.errors.NotFound):
            embed = disnake.Embed(description="Not a valid clan/player tag.", color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if isinstance(error, coc.errors.Maintenance):
            embed = disnake.Embed(description=f"Game is currently in Maintenance.", color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.CheckAnyFailure):
            if isinstance(error.errors[0], disnake.ext.commands.MissingPermissions):
                embed = disnake.Embed(description=error.errors[0], color=disnake.Color.red())
                return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.MissingPermissions):
            embed = disnake.Embed(description=error, color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.CommandError):
            error = error.original
            print(error)

        if isinstance(error, NoLinkedAccounts):
            embed = disnake.Embed(description=f"No Accounts Linked To This User",
                                  color=disnake.Color.red())
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, NotValidReminderTime):
            embed = disnake.Embed(description="Not a valid reminder time, please use options from the autocomplete.", color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if isinstance(error, ThingNotFound):
            embed = disnake.Embed(description=f"{str(error)}", color=disnake.Color.red())
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, MessageException):
            embed = disnake.Embed(description=f"{str(error)}", color=disnake.Color.red())
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, MissingWebhookPerms):
            embed = disnake.Embed(description=f"Missing Permissions to Create or Edit Webhooks", color=disnake.Color.red())
            if not ctx.response.is_done():
                return await ctx.edit_original_message(embed=embed)
            else:
                return await ctx.send(embed=embed)

        if isinstance(error, ExportTemplateAlreadyExists):
            embed = disnake.Embed(description=f"Export Template with this name already exists.", color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=False)

        if isinstance(error, RosterAliasAlreadyExists):
            embed = disnake.Embed(description=f"Roster with this alias already exists.", color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, RosterDoesNotExist):
            embed = disnake.Embed(description=f"Roster with this alias does not exist. Use `/roster create`",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PlayerAlreadyInRoster):
            embed = disnake.Embed(description=f"Player has already been added to this roster.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PlayerNotInRoster):
            embed = disnake.Embed(description=f"Player not found in this roster.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, RosterSizeLimit):
            embed = disnake.Embed(description=f"Roster has hit max size limit",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PanelNotFound):
            embed = disnake.Embed(description=f"Panel not found!",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, ButtonNotFound):
            embed = disnake.Embed(description=f"Button not found!",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PanelAlreadyExists):
            embed = disnake.Embed(description=f"Panel of this name already exists!",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, ButtonAlreadyExists):
            embed = disnake.Embed(description=f"Button of this name already exists!",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, FaultyJson):
            embed = disnake.Embed(
                description=f"Custom Embed Code is Faulty - > be sure to use this site -> https://autocode.com/tools/discord/embed-builder/ , "
                            f"create your embed, then click `copy code`",
                color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        sentry_sdk.capture_exception(error)


def setup(bot: CustomClient):
    bot.add_cog(ExceptionHandler(bot))
