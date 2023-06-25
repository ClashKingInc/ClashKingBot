from disnake.ext import commands
import disnake
from utils.components import create_components
from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from main import check_commands
from datetime import timedelta
import pytz
utc = pytz.utc
import coc
import random
import string
from main import scheduler

class Strikes(commands.Cog, name="Strikes"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.rollover_remover, 'interval', minutes=5)

    async def rollover_remover(self):
        now = datetime.utcnow().replace(tzinfo=utc)
        await self.bot.strikelist.delete_many({"rollover_date" : {"$lte" : int(now.timestamp())}})

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    async def player_converter(self, player_tag: str):
        player = await self.bot.getPlayer(player_tag=player_tag, raise_exceptions=True)
        return player

    @commands.slash_command(name="strike", description="stuff")
    async def strike(self, ctx):
        pass

    @strike.sub_command(name="add", description="Issue strikes to a player")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_add(self, ctx: disnake.ApplicationCommandInteraction,
                         player: coc.Player = commands.Param(converter=player_converter),
                         reason: str = commands.Param(name="reason"),
                         rollover_days: int = commands.Param(name="rollover_days", default=None),
                         strike_weight: int = commands.Param(name="strike_weight", default=1)):
        """
            Parameters
            ----------
            player: player to issue a strike to
            reason: reason for strike
            rollover_days: number of days until this strike is removed (auto), (default - never)
            strike_weight: number of strikes this should count as (default 1)
        """
        await ctx.response.defer()
        embed = await self.strike_player(ctx, player, reason, rollover_days, strike_weight)
        await ctx.edit_original_message(embed=embed)


    @strike.sub_command(name='list', description="List of server (or clan) striked players")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_list(self, ctx: disnake.ApplicationCommandInteraction, view = commands.Param(choices=["Strike View", "Player View"]),
                          clan = commands.Param(default=None, converter=clan_converter),
                          strike_amount:int = commands.Param(default=1)):
        """
            Parameters
            ----------
            view: show in strike view (each strike individually) or by player
            clan: clan to pull strikes for
            strike_amount: only show strikes with more than this amount (only for player view)
        """
        if clan is not None:
            results = await self.bot.clan_db.find_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
        
        await ctx.response.defer()
        embeds = await self.create_embeds(ctx=ctx, strike_clan=clan, view=view, strike_amount=strike_amount)
        if embeds == []:
            embed = disnake.Embed(
                description="No striked players on this server.",
                color=disnake.Color.red())
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

    @strike.sub_command(name="remove", description="Remove a strike by ID")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_remove(self, ctx: disnake.ApplicationCommandInteraction, strike_id: str):
        strike_id = strike_id.upper()
        result_ = await self.bot.strikelist.find_one({"$and": [
            {"strike_id": strike_id},
            {"server": ctx.guild.id}
        ]})
        if result_ is None:
            embed = disnake.Embed(description=f"Strike with ID {strike_id} does not exist.", color=disnake.Color.red())
            return await ctx.send(embed=embed)
        await self.bot.strikelist.delete_one({"$and": [
            {"strike_id": strike_id},
            {"server": ctx.guild.id}
        ]})
        embed = disnake.Embed(description=f"Strike {strike_id} removed.", color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @strike_add.autocomplete("player")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names

    async def strike_player(self, ctx, player: coc.Player, reason: str, rollover_days, strike_weight):
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")

        source = string.ascii_letters
        strike_id = str(''.join((random.choice(source) for i in range(5)))).upper()

        is_used = await self.bot.strikelist.find_one({"strike_id": strike_id})
        while is_used is not None:
            strike_id = str(''.join((random.choice(source) for i in range(5)))).upper()
            is_used = await self.bot.strikelist.find_one({"strike_id": strike_id})

        if rollover_days is not None:
            now = datetime.utcnow().replace(tzinfo=utc)
            rollover_days = now + timedelta(rollover_days)
            rollover_days = int(rollover_days.timestamp())

        await self.bot.strikelist.insert_one({
            "tag": player.tag,
            "date_created": dt_string,
            "reason": reason,
            "server": ctx.guild.id,
            "added_by": ctx.author.id,
            "strike_weight": strike_weight,
            "rollover_date": rollover_days,
            "strike_id": strike_id
        })

        results = await self.bot.strikelist.find({"$and": [
            {"tag": player.tag},
            {"server": ctx.guild.id}
        ]}).to_list(length=100)
        num_strikes = sum([result.get("strike_weight") for result in results])

        if rollover_days is not None:
            rollover_days = f"<t:{rollover_days}:f>"
        else:
            rollover_days = "Never"
        embed = disnake.Embed(
            description=f"**Strike added to [{player.name}]({player.share_link}) by {ctx.author.mention}.**\n"
                        f"Strike Weight: {strike_weight}, Total Strikes Now: {num_strikes}\n"
                        f"Rollover: {rollover_days}\n"
                        f"Reason: {reason}",
            color=disnake.Color.green())
        embed.set_footer(text=f"Strike ID: {strike_id}")
        return embed

    async def create_embeds(self, ctx, strike_clan, view, strike_amount):
        text = []
        hold = ""
        num = 0
        tags = await self.bot.strikelist.distinct("tag", filter={"server": ctx.guild.id})
        all = self.bot.strikelist.find({"server": ctx.guild.id}).sort("date_created", 1)
        limit = await self.bot.strikelist.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return []

        players = await self.bot.get_players(tags=tags)
        if view == "Strike View":
            for strike in await all.to_list(length=limit):
                tag = strike.get("tag")
                player = coc.utils.get(players, tag=tag)
                if player is None:
                    continue
                if strike_clan is not None:
                    if player.clan is None:
                        continue
                    if player.clan.tag != strike_clan.tag:
                        continue
                name = player.name
                for char in ["`", "*", "_", "~", "´"]:
                    name = name.replace(char, "", len(player.name))
                date = strike.get("date_created")
                date = date[:10]
                reason = strike.get("reason")

                added_by = ""
                if strike.get("added_by") is not None:
                    user = await self.bot.getch_user(strike.get("added_by"))
                    added_by = f"{user}"
                clan = f"{player.clan.name}, {str(player.role)}" if player.clan is not None else "No Clan"

                rollover_days = strike.get("rollover_date")
                if rollover_days is not None:
                    rollover_days = f"<t:{rollover_days}:f>"
                else:
                    rollover_days = "Never"

                hold += f"{self.bot.fetch_emoji(player.town_hall)}[{name}]({player.share_link}) | {player.tag}\n" \
                        f"{clan} | ID: {strike.get('strike_id')}\n" \
                        f"Added on: {date}, by {added_by}\n" \
                        f"Rollover Date: {rollover_days}\n" \
                        f"*{reason}*\n\n"
                num += 1
                if num == 10:
                    text.append(hold)
                    hold = ""
                    num = 0

        elif view == "Player View":
            for tag in tags:
                player = coc.utils.get(players, tag=tag)
                if player is None:
                    continue
                if strike_clan is not None:
                    if player.clan is None:
                        continue
                    if player.clan.tag != strike_clan.tag:
                        continue
                name = player.name
                for char in ["`", "*", "_", "~", "´"]:
                    name = name.replace(char, "", len(player.name))

                results = await self.bot.strikelist.find({"$and": [
                    {"tag": tag},
                    {"server": ctx.guild.id}
                ]}).sort("date_created", 1).to_list(length=100)

                total_strike_weight = sum([result.get("strike_weight") for result in results])
                num_strikes = len(results)
                if num_strikes < strike_amount:
                    continue
                strike_reason_ids = "\n".join([f"`{result.get('strike_id')}` - {result.get('reason')}" for result in results])
                most_recent = results[0].get("date_created")[:10]
                clan = f"{player.clan.name}, {str(player.role)}" if player.clan is not None else "No Clan"

                hold += f"{self.bot.fetch_emoji(player.town_hall)}[{name}]({player.share_link}) | {clan}\n" \
                        f"Most Recent Strike: {most_recent}\n" \
                        f"# of Strikes: {num_strikes}, Weight: {total_strike_weight}\nStrikes:\n" \
                        f"{strike_reason_ids}\n\n"
                num += 1
                if num == 10:
                    text.append(hold)
                    hold = ""
                    num = 0

        if num != 0:
            text.append(hold)

        embeds = []
        for t in text:
            embed = disnake.Embed(title=f"{ctx.guild.name} Strike List",
                                  description=t,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        return embeds

    @strike_list.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id}).sort("name", 1)
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=5)
                for clan in results:
                    league = str(clan.war_league).replace("League ", "")
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]

def setup(bot: CustomClient):
    bot.add_cog(Strikes(bot))