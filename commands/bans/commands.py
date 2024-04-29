import coc
import disnake

from classes.bot import CustomClient
from discord.options import autocomplete, convert
from disnake.ext import commands
from exceptions.CustomExceptions import MessageException
from utility.components import create_components
from utility.discord_utils import check_commands
from .utils import create_embeds, add_ban, remove_ban


class Bans(commands.Cog, name="Bans"):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="ban", description="ban related commands")
    async def ban(self, ctx):
        await ctx.response.defer()


    @ban.sub_command(name='add', description="Add player to server ban list")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_add(self, ctx: disnake.ApplicationCommandInteraction,
                      player: coc.Player = commands.Param(autocomplete=autocomplete.family_players, converter=convert.player),
                      reason: str = "No Notes",
                      dm_player: str = commands.Param(default=None)):
        """
            Parameters
            ----------
            player: player to ban
            reason: reason for ban
            dm_player: message to DM the recipient
        """
        embed = await add_ban(bot=self.bot,
                              player=player,
                              added_by=ctx.user,
                              guild=ctx.guild,
                              reason=reason,
                              rollover_days=None,
                              dm_player=dm_player)
        await ctx.edit_original_message(embed=embed)



    @ban.sub_command(name='remove', description="Remove player from server ban list")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_remove(self, ctx: disnake.ApplicationCommandInteraction,
                         player: coc.Player = commands.Param(autocomplete=autocomplete.banned_players, converter=convert.player)):
        """
            Parameters
            ----------
            player: player to unban (names are shown as they were when banned)
        """

        embed = await remove_ban(bot=self.bot,
                                 player=player,
                                 removed_by=ctx.user,
                                 guild=ctx.guild)
        await ctx.edit_original_message(embed=embed)



    @ban.sub_command(name='list', description="List of server banned players")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_list(self, ctx: disnake.ApplicationCommandInteraction):

        bans = await self.bot.banlist.find({"server" : ctx.guild.id}).to_list(length=None)
        if not bans:
            raise MessageException("No banned players on this servers. Use `/ban add` to get started.")

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embeds = await create_embeds(bot=self.bot, bans=bans, guild=ctx.guild, embed_color=embed_color)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)



def setup(bot: CustomClient):
    bot.add_cog(Bans(bot))