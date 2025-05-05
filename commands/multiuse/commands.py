from disnake.ext import commands

from discord import options

from .utils import *


class MultiCommands(commands.Cog, name='Multi-Use Commands'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='discord-links', description='Discord for players in a clan')
    async def discord_links(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = options.clan):
        await ctx.response.defer()
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embeds = await linked_players(bot=self.bot, clan=clan, server=ctx.guild, embed_color=embed_color)
        buttons = disnake.ui.ActionRow()
        buttons.add_button(
            label='',
            emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'discordlinks:{clan.tag}:{ctx.guild_id}:refresh',
        )
        buttons.add_button(
            label='',
            emoji=self.bot.emoji.gear.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'discordlinkschoose:{ctx.guild_id}',
        )
        await ctx.edit_original_message(embeds=embeds, components=[buttons])


def setup(bot):
    bot.add_cog(MultiCommands(bot))
