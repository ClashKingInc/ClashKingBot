import emoji
import disnake

from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from main import scheduler
from disnake.ext import commands


class DMFeed(commands.Cog, name="DM Feed & Reports"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.dm_check, "cron", hour=4, minute=55)

    @commands.slash_command(name="dm")
    async def dm(self, ctx):
        pass

    @dm.sub_command(name="daily_report", description="Opt in/out of daily legend report on tracked players sent to your dm.")
    async def daily_report(self, ctx: disnake.ApplicationCommandInteraction, opt = commands.Param(description="Opt In/Out",choices=["Opt-In", "Opt-Out"])):
        results = await self.bot.legend_profile.find_one({'discord_id': ctx.author.id})
        if results is None:
            if opt == "Opt-In":
                try:
                    await ctx.author.send(content="Opted you in. You don't have any players tracked, use `/quick_check` to get started.")
                    await ctx.send(content="Opted you in. You don't have any players tracked, use `/quick_check` to get started.", ephemeral=True)
                except:
                    return await ctx.send(content="Could not send you a dm. Make sure you have dm's enabled.\n"
                                           "`User Settings> Privacy & Safety> Toggle “Allow DMs from server members”`", ephemeral=True)
            else:
                await ctx.send(content="Opted you out of daily DM reports", ephemeral=True)

            await self.bot.legend_profile.insert_one({'discord_id': ctx.author.id,
                                         "profile_tags": [],
                                         "opt": opt})
        else:
            profile_tags = results.get("profile_tags")
            if opt == "Opt-In" and profile_tags == []:
                try:
                    await ctx.author.send(content="Opted you in. You don't have any players tracked, use `/quick_check` to get started.")
                    await ctx.send(content="Opted you in. You don't have any players tracked, use `/quick_check` to get started.",ephemeral=True)
                except:
                    return await ctx.send(content="Could not send you a dm. Make sure you have dm's enabled.\n"
                                           "`User Settings> Privacy & Safety> Toggle “Allow DMs from server members”`", ephemeral=True)
            elif opt == "Opt-In":
                try:
                    await ctx.author.send(content="Opted you in for daily DM reports")
                    await ctx.send(content="Opted you in for daily DM reports",ephemeral=True)
                except:
                    return await ctx.send(content="Could not send you a dm. Make sure you have dm's enabled.\n"
                                           "`User Settings> Privacy & Safety> Toggle “Allow DMs from server members”`", ephemeral=True)
            else:
                await ctx.send(content="Opted you out of daily DM reports", ephemeral=True)

            await self.bot.legend_profile.update_one({'discord_id': ctx.author.id},
                                        {'$set': {"opt": opt}})

    @dm.sub_command(name="legend_feed", description="Add players from your quick_check list to your dm feed.")
    async def legend_feed(self, ctx: disnake.ApplicationCommandInteraction):
        results = await self.bot.legend_profile.find_one({'discord_id': ctx.author.id})
        if results is None:
            return await ctx.send(content="You don't have any players tracked, use `/quick_check` to get started.", ephemeral=True)

        profile_tags = results.get("profile_tags")
        if profile_tags is None or profile_tags == []:
                return await ctx.send(content="You don't have any players tracked, use `/quick_check` to get started.", ephemeral=True)

        feed_tags = results.get("feed_tags")
        if feed_tags is None:
            feed_tags = []
        players = await self.bot.get_players(tags=profile_tags, custom=False)

        build = self.legend_feed_embed_and_components(feed_tags=feed_tags, players=players)
        embed = disnake.Embed(title="Edit Legend Feed Tracking (up to 3 players)", description=build[1])

        await ctx.send(embed=embed, components=build[0], ephemeral=True)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if "addleg_" in res.values[0]:
                player_tag = res.values[0].split("_")[-1]
                if len(feed_tags) == self.bot.MAX_FEED_LEN:
                    await res.send(content="Can only have 3 people in your dm feed at this time. Please remove one first.", ephemeral=True)
                else:
                    await self.bot.legend_profile.update_one({'discord_id': res.author.id}, {'$push': {"feed_tags": player_tag}})
                    feed_tags.append(player_tag)
                    build = self.legend_feed_embed_and_components(feed_tags=feed_tags, players=players)
                    embed = disnake.Embed(title="Edit Legend Feed Tracking (up to 3 players)", description=build[1])
                    await res.response.edit_message(embed=embed, components=build[0])

            elif "removeleg_" in res.values[0]:
                player_tag = res.values[0].split("_")[-1]
                await self.bot.legend_profile.update_one({'discord_id': res.author.id},
                                                         {'$pull': {"feed_tags": player_tag}})
                feed_tags.remove(player_tag)
                build = self.legend_feed_embed_and_components(feed_tags=feed_tags, players=players)
                embed = disnake.Embed(title="Edit Legend Feed Tracking (up to 3 players)", description=build[1])
                await res.response.edit_message(embed=embed, components=build[0])


    def legend_feed_embed_and_components(self, feed_tags, players):
        text = ""
        components = []
        for player in players:
            if player is None:
                continue
            if player.tag in feed_tags:
                text += f"<:status_green:948031949140799568> {player.name} | 🏆{player.trophies}\n"
                components.append(disnake.SelectOption(label=f"{player.name} | 🏆{player.trophies}", value=f"removeleg_{player.tag}", emoji=self.bot.partial_emoji_gen("<:status_green:948031949140799568>")))
            else:
                text += f"<:status_red:948032012160204840> {player.name} | 🏆{player.trophies}\n"
                components.append(disnake.SelectOption(label=f"{player.name} | 🏆{player.trophies}", value=f"addleg_{player.tag}", emoji=self.bot.partial_emoji_gen("<:status_red:948032012160204840>")))

        profile_select = disnake.ui.Select(options=components, placeholder="Players", min_values=1,
                                           max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        return [[st2], text]




    async def dm_check(self):

        results = self.bot.legend_profile.find({"opt": "Opt-In"})
        limit = await self.bot.legend_profile.count_documents(filter={"opt": "Opt-In"})
        for document in await results.to_list(length=limit):
            tracked_players = document.get("profile_tags")
            user_id = document.get("discord_id")
            button = disnake.ui.Button(label="Opt Out", style=disnake.ButtonStyle.red, custom_id=f"dm_{user_id}")
            buttons = disnake.ui.ActionRow()
            buttons.append_item(button)
            if len(tracked_players) == 0:
                continue

            ranking = []

            players = await self.bot.get_players(tags=tracked_players, custom=True)
            for player in players:
                player: MyCustomPlayer
                if player is None:
                    continue
                legend_day = player.legend_day()

                if not player.is_legends():
                    continue

                name = player.name
                name = emoji.get_emoji_regexp().sub('', name)

                ranking.append([name, player.trophy_start(), legend_day.attack_sum, legend_day.num_attacks.superscript, legend_day.defense_sum, legend_day.num_defenses.superscript, player.trophies])

            ranking = sorted(ranking, key=lambda l: l[6], reverse=True)

            text = ""
            initial = f"__**Quick Check Daily Report**__"
            for person in ranking:
                name = person[0]
                hits = person[2]
                hits = person[2]
                numHits = person[3]
                defs = person[4]
                numDefs = person[5]
                trophies = person[6]
                text += f"\u200e**<:trophyy:849144172698402817>{trophies} | \u200e{name}**\n➼ <:cw:948845649229647952> {hits}{numHits} <:sh:948845842809360424> {defs}{numDefs}\n"

            embed = disnake.Embed(title=initial,
                                  description=text)
            embed.set_footer(text="Opt out at any time.")
            user = await self.bot.get_or_fetch_user(user_id=user_id)
            try:
                await user.send(embed=embed, components=[buttons])
            except:
                continue

    @commands.Cog.listener()
    async def on_message_interaction(self, res: disnake.MessageInteraction):
        if "report_" in res.data.custom_id:
            data = res.data.custom_id
            data = data.split("_")
            user_id = data[1]
            await self.bot.legend_profile.update_one({'discord_id': int(user_id)},
                                        {'$set': {"opt": "Opt-Out"}})
            await res.send(content="Opted out of daily legend report.", ephemeral=True)



def setup(bot: CustomClient):
    bot.add_cog(DMFeed(bot))