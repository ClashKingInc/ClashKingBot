import coc
from disnake.ext import commands
import disnake
from Utils.components import create_components
from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from main import check_commands
from Utils.constants import EMBED_COLOR
from CustomClasses.ClashKingAPI.Classes.bans import BannedUser, BannedResponse
from typing import List
from .utils import ban_player_extras, create_embeds
from Discord.autocomplete import Autocomplete as autocomplete
from Discord.converters import Convert as convert

class Bans(commands.Cog, name="Bans"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="ban", description="stuff")
    async def ban(self, ctx):
        pass

    @ban.sub_command(name='list', description="List of server banned players")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_list(self, ctx: disnake.ApplicationCommandInteraction):

        await ctx.response.defer()

        bans: List[BannedUser] = await self.bot.ck_client.get_ban_list(server_id=ctx.guild_id)
        if not bans:
            embed = disnake.Embed(
                description="No banned players on this server.",
                color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        server_result = await self.bot.server_db.find_one({"server": ctx.guild.id})
        embeds = await create_embeds(bans=bans, guild=ctx.guild, embed_color=disnake.Color(server_result.get("embed_color", EMBED_COLOR)))

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

    @ban.sub_command(name='add', description="Add player to server ban list")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_add(self, ctx: disnake.ApplicationCommandInteraction,
                      player: coc.Player = commands.Param(autocomplete=autocomplete.family_players, converter=convert.player),
                      reason: str = "No Notes",
                      rollover_days: int = commands.Param(name="rollover_days", default=None)):
        """
            Parameters
            ----------
            player: player to ban
            reason: reason for ban
        """
        await ctx.response.defer()
        banned_user: BannedResponse = await self.bot.ck_client.add_ban(server_id=ctx.guild_id, player_tag=player.tag, reason=reason, added_by=ctx.user.id, rollover_days=rollover_days)
        embed = await ban_player_extras(bot=self.bot, banned_user=banned_user, who=ctx.user)
        await ctx.edit_original_message(embed=embed)


    @ban.sub_command(name='remove', description="Remove player from server ban list")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_remove(self, ctx: disnake.ApplicationCommandInteraction,
                         player: coc.Player = commands.Param(autocomplete=autocomplete.banned_players, converter=convert.player)):
        """
            Parameters
            ----------
            player_tag: player to unban (names are shown as they were when banned)
        """

        results = await self.bot.banlist.find_one({"$and": [
            {"VillageTag": player.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = disnake.Embed(description=f"{player.name} is not banned on this server.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.banlist.find_one_and_delete({"$and": [
            {"VillageTag": player.tag},
            {"server": ctx.guild.id}
        ]})

        embed2 = disnake.Embed(description=f"[{player.name}]({player.share_link}) removed from the banlist by {ctx.author.mention}.",
                               color=disnake.Color.green())
        await ctx.send(embed=embed2)

        results = await self.bot.server_db.find_one({"server": ctx.guild.id})
        banChannel = results.get("banlist")
        channel = await self.bot.pingToChannel(ctx, banChannel)

        if channel is not None:
            x = 0
            async for message in channel.history(limit=200):
                message: disnake.Message
                x += 1
                if x == 101:
                    break
                if message.author.id != self.bot.user.id:
                    continue
                if message.embeds:
                    if "Ban List" in str(message.embeds[0].title) or "banlist" in str(message.embeds[0].description):
                        await message.delete()

            embeds = await self.create_embeds(ctx)
            for embed in embeds:
                await channel.send(embed=embed)
            await channel.send(embed=embed2)






def setup(bot: CustomClient):
    bot.add_cog(Bans(bot))