import coc
from disnake.ext import commands
import disnake
from utils.components import create_components
from datetime import datetime
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.CustomBot import CustomClient
from main import check_commands

class banlists(commands.Cog, name="Bans"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="ban", description="stuff")
    async def ban(self, ctx):
        pass

    @ban.sub_command(name='list', description="List of server banned players")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_list(self, ctx: disnake.ApplicationCommandInteraction):

        await ctx.response.defer()

        embeds = await self.create_embeds(ctx)
        if embeds == []:
            embed = disnake.Embed(
                description="No banned players on this server.",
                color=disnake.Color.green())
            return await ctx.edit_original_message(embed=embed)


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
    async def ban_add(self, ctx: disnake.ApplicationCommandInteraction, tag: str, reason: str = "None", rollover_days: int = commands.Param(name="rollover_days", default=None)):
        """
            Parameters
            ----------
            tag: player_tag to ban
            reason: reason for ban
        """

        player = await self.bot.getPlayer(tag, raise_exceptions=True)
        await ctx.response.defer()
        embed = await self.ban_player(ctx, player, reason)
        await ctx.edit_original_message(embed=embed)

    @ban.sub_command(name='remove', description="Remove player from server ban list")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_remove(self, ctx: disnake.ApplicationCommandInteraction, tag: str):
        """
            Parameters
            ----------
            tag: player_tag to unban
        """

        player = await self.bot.getPlayer(tag, raise_exceptions=True)
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

    @ban_add.autocomplete("tag")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names

    async def ban_player(self, ctx, player: coc.Player, reason):
        results = await self.bot.banlist.find_one({"$and": [
            {"VillageTag": player.tag},
            {"server": ctx.guild.id}
        ]})

        if results is not None and reason == "None":
            embed = disnake.Embed(
                description=f"{player.name} is already banned on this server.\nProvide `reason` to update ban notes.",
                color=disnake.Color.red())
            return embed
        elif results is not None and reason != "None":
            await self.bot.banlist.update_one({"$and": [
                {"VillageTag": player.tag},
                {"server": ctx.guild.id}
            ]}, {'$set': {"Notes": reason, "added_by": ctx.author.id}})
            embed = disnake.Embed(
                description=f"[{player.name}]({player.share_link}) ban reason updated by {ctx.author.mention}.\n"
                            f"Notes: {reason}",
                color=disnake.Color.green())
            return embed

        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")

        await self.bot.banlist.insert_one({
            "VillageTag": player.tag,
            "DateCreated": dt_string,
            "Notes": reason,
            "server": ctx.guild.id,
            "added_by": ctx.author.id
        })
        embed2 = disnake.Embed(
            description=f"[{player.name}]({player.share_link}) added to the banlist by {ctx.author.mention}.\n"
                        f"Notes: {reason}",
            color=disnake.Color.green())

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

        return embed2


    async def create_embeds(self, ctx):
        text = []
        hold = ""
        num = 0
        all = self.bot.banlist.find({"server": ctx.guild.id}).sort("DateCreated", 1)
        limit = await self.bot.banlist.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return []

        for ban in await all.to_list(length=limit):
            tag = ban.get("VillageTag")
            player = await self.bot.getPlayer(tag)
            if player is None:
                continue
            name = player.name
            # name = name.replace('*', '')
            date = ban.get("DateCreated")
            date = date[0:10]
            notes = ban.get("Notes")
            if notes == "":
                notes = "No Notes"
            clan = ""
            try:
                clan = player.clan.name
                clan = f"{clan}, {str(player.role)}"
            except:
                clan = "No Clan"
            added_by = ""
            if ban.get("added_by") is not None:
                user = await self.bot.getch_user(ban.get("added_by"))
                added_by = f"\nAdded by: {user}"
            hold += f"{emojiDictionary(player.town_hall)}[{name}]({player.share_link}) | {player.tag}\n" \
                    f"{clan}\n" \
                    f"Added on: {date}\n" \
                    f"Notes: *{notes}*{added_by}\n\n"
            num += 1
            if num == 10:
                text.append(hold)
                hold = ""
                num = 0

        if num != 0:
            text.append(hold)

        embeds = []
        for t in text:
            embed = disnake.Embed(title=f"{ctx.guild.name} Ban List",
                                  description=t,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        return embeds



def setup(bot: CustomClient):
    bot.add_cog(banlists(bot))