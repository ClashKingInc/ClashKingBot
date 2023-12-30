import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from datetime import datetime

class erikuh(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="signup", description="Signup for competition", guild_ids=[923019106020638741])
    async def signup(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str):
        await ctx.response.defer()
        player:MyCustomPlayer = await self.bot.getPlayer(player_tag, custom=True)
        if player is None:
            embed = disnake.Embed(
                description=f"**Not a valid player tag :(**",
                color=disnake.Color.red())
            embed.set_thumbnail(url=ctx.guild.icon.url)
            return await ctx.edit_original_message(embed=embed)

        if not player.is_legends():
            embed = disnake.Embed(
                description=f"**Sorry, but you can only sign up if you are in legends :(**",
                color=disnake.Color.red())
            embed.set_thumbnail(url=ctx.guild.icon.url)
            return await ctx.edit_original_message(embed=embed)

        result = await self.bot.erikuh.find_one({"player_tag" : player.tag})
        if result is not None:
            embed = disnake.Embed(
                description=f"**Sorry, but {player.name} ({player.tag}) has already been signed up**",
                color=disnake.Color.red())
            embed.set_thumbnail(url=ctx.guild.icon.url)
            return await ctx.edit_original_message(embed=embed)

        await player.track()
        await self.bot.erikuh.insert_one({"discord_id" : ctx.user.id, "player_tag" : player.tag})
        embed = disnake.Embed(
            description=f"**Successfully signed up {player.name} ({player.tag}) for the Legend League Tournament**",
            color=disnake.Color.from_rgb(248,140,164))
        return await ctx.edit_original_message(embed=embed)

    @commands.slash_command(name="signup-remove", description="remove signup for competition", guild_ids=[900783471708999700])
    async def remove_signup(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)
        await ctx.response.defer()
        player: MyCustomPlayer = await self.bot.getPlayer(player_tag, custom=True)
        if player is None:
            embed = disnake.Embed(
                description=f"**Not a valid player tag :(**",
                color=disnake.Color.red())
            embed.set_thumbnail(url=ctx.guild.icon.url)
            return await ctx.edit_original_message(embed=embed)

        result = await self.bot.erikuh.find_one({"player_tag": player.tag})
        if result is None:
            embed = disnake.Embed(
                description=f"**{player.name} | {player.tag} is not signed up.**",
                color=disnake.Color.red())
            embed.set_thumbnail(url=ctx.guild.icon.url)
            return await ctx.edit_original_message(embed=embed)

        await self.bot.erikuh.delete_one({"player_tag": player.tag})
        embed = disnake.Embed(
            description=f"**Successfully removed {player.name} ({player.tag}) from the February Legend League Tournament**",
            color=disnake.Color.from_rgb(248, 140, 164))
        return await ctx.edit_original_message(embed=embed)

    @commands.slash_command(name="signup-list", description="list of signee's", guild_ids=[900783471708999700])
    async def signup_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        results = self.bot.erikuh.find({})
        limit = await self.bot.server_db.count_documents({})
        text = ""
        for r in await results.to_list(length=limit):
            try:
                tag = r.get("player_tag")
                player = await self.bot.getPlayer(tag)
                discord_id = r.get("discord_id")
                member = self.bot.get_user(discord_id)
                text += f"{player.name} | {player.tag} | {member.name}#{member.discriminator}\n"
            except:
                pass

        if text == "":
            embed = disnake.Embed(description="No players have signed up yet", color=disnake.Color.red())
            embed.set_thumbnail(url=ctx.guild.icon.url)
            return await ctx.edit_original_message(embed=embed)

        embed = disnake.Embed(title="Legend Competition Signup List",description=text, color=disnake.Color.from_rgb(248,140,164))
        embed.set_thumbnail(url=ctx.guild.icon.url)
        return await ctx.edit_original_message(embed=embed)

    @commands.slash_command(name="leaderboard", description="leaderboard of top players in competition", guild_ids=[900783471708999700])
    async def leaderboard(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        all_tags = await self.bot.erikuh.distinct("player_tag")
        all_players = await self.bot.get_players(tags=all_tags)
        ranking = []
        for player in all_players:
            try:
                player: MyCustomPlayer
                legend_day = player.legend_day()
                ranking.append([player.name, player.trophy_start(), legend_day.attack_sum, legend_day.num_attacks.superscript, legend_day.defense_sum, legend_day.num_defenses.superscript, player.trophies])
            except:
                pass

        if ranking == []:
            embed = disnake.Embed(description="No players have signed up yet", color=disnake.Color.red())
            embed.set_thumbnail(url=ctx.guild.icon.url)
            return await ctx.edit_original_message(embed=embed)

        ranking = sorted(ranking, key=lambda l: l[6], reverse=True)

        embeds = await self.create_player_embed(ctx, ranking)

        time = int(datetime.now().timestamp())

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"erikuh_{time}"))

        if len(embeds) == 1:
            embeds[0].description += f"\nLast Refreshed: <t:{int(time)}:R>"
            msg = await ctx.edit_original_message(embed=embeds[0], components=buttons)
        else:
            msg = await ctx.edit_original_message(embed=embeds[0])

        messages = [msg.id]
        if len(embeds) >= 2:
            embeds[-1].description += f"\nLast Refreshed: <t:{int(time)}:R>"
            for embed in embeds[1:]:
                if embed == embeds[-1]:
                    msg = await ctx.followup.send(embed=embed, components=buttons)
                else:
                    msg = await ctx.followup.send(embed=embed)
                messages.append(msg.id)

        await self.bot.button_db.insert_one({"identifier": int(time), "messages": messages})

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        time = datetime.now().timestamp()
        if "erikuh_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            identifier = (str(ctx.data.custom_id).split("_"))[-1]
            results = await self.bot.button_db.find_one({"identifier": int(identifier)})
            messages = results.get("messages")
            for message in messages:
                channel: disnake.TextChannel = ctx.channel
                m = await channel.fetch_message(message)
                if m is None:
                    continue
                await m.delete()

            all_tags = await self.bot.erikuh.distinct("player_tag")
            all_players = await self.bot.get_players(tags=all_tags)
            ranking = []
            for player in all_players:
                try:
                    player: MyCustomPlayer
                    legend_day = player.legend_day()
                    ranking.append(
                        [player.name, player.trophy_start(), legend_day.attack_sum, legend_day.num_attacks.superscript,
                         legend_day.defense_sum, legend_day.num_defenses.superscript, player.trophies])
                except:
                    pass

            if ranking == []:
                embed = disnake.Embed(description="No players have signed up yet", color=disnake.Color.red())
                embed.set_thumbnail(url=ctx.guild.icon.url)
                return await ctx.channel.send(embed=embed)

            ranking = sorted(ranking, key=lambda l: l[6], reverse=True)

            embeds = await self.create_player_embed(ctx, ranking)

            time = int(datetime.now().timestamp())

            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                                  custom_id=f"erikuh_{time}"))

            if len(embeds) == 1:
                embeds[0].description += f"\nLast Refreshed: <t:{int(time)}:R>"
                msg = await ctx.channel.send(embed=embeds[0], components=buttons)
            else:
                msg = await ctx.channel.send(embed=embeds[0])

            messages = [msg.id]
            if len(embeds) >= 2:
                embeds[-1].description += f"\nLast Refreshed: <t:{int(time)}:R>"
                for embed in embeds[1:]:
                    if embed == embeds[-1]:
                        msg = await ctx.channel.send(embed=embed, components=buttons)
                    else:
                        msg = await ctx.channel.send(embed=embed)
                    messages.append(msg.id)

            await self.bot.button_db.insert_one({"identifier": time, "messages": messages})

    @commands.slash_command(name="mod-leaderboardfeed", description="set daily leaderboard feed in channel run",guild_ids=[900783471708999700])
    async def leaderboard_feed(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, remove = commands.Param(default="False", choices=["True", "False"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)
        await ctx.response.defer()
        if remove == "True":
            await self.bot.server_db.update_one({"server" : ctx.guild.id}, {"$set" : {"comp_channel" : channel.id}})
            embed = disnake.Embed(
                description=f"**Competition leaderboard feed set to {channel.mention}**",
                color=disnake.Color.green())
            return await ctx.edit_original_message(embed=embed)
        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {"$set": {"comp_channel": None}})
            embed = disnake.Embed(
                description=f"**Leaderboard feed removed**",
                color=disnake.Color.green())
            return await ctx.edit_original_message(embed=embed)



    async def create_player_embed(self, ctx, ranking):
        text = ""
        initial = f"__**{ctx.guild.name} Legend Leaderboard**__\n"
        embeds = []
        x = 0
        for player in ranking:
            name = player[0]
            hits = player[2]
            numHits = player[3]
            defs = player[4]
            numDefs = player[5]
            trophies = player[6]
            text += f"\u200e**<:trophyy:849144172698402817>\u200e{trophies} | \u200e{name}**\n➼ <:sword_coc:940713893926428782> {hits}{numHits} <:clash:877681427129458739> {defs}{numDefs}\n"
            x += 1
            if x == 25:
                embed = disnake.Embed(title=f"**Erikuh's Legend Competition Leaderboard**",
                                      description=text, color=disnake.Color.from_rgb(248,140,164))
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                x = 0
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"**Erikuh's Legend Competition Leaderboard**",
                                  description=text, color=disnake.Color.from_rgb(248,140,164))
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)
        return embeds



def setup(bot: CustomClient):
    bot.add_cog(erikuh(bot))