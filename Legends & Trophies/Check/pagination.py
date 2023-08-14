
import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
import asyncio

stat_types = ["Previous Days", "Legends Overview", "Legends History"]

class Pagination(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def button_pagination(self, msg, tags, ez_look, ctx):
        check = self.bot.get_cog("Legends")
        current_page = 0
        stats_page = []
        trophy_results = []

        player_order=0
        results = []
        if len(tags) > 1 and ez_look:
            results.append("x")
            player_order= 1
        text = ""

        responses = await self.bot.get_players(tags=tags, custom=True, use_cache=True)
        for player in responses:
            player: MyCustomPlayer
            if player is None:
                continue
            legend_day = player.legend_day()
            text += f"\u200e**{self.bot.emoji.trophy.emoji_string}{player.trophies} | \u200e{player.name}**\n➼ {self.bot.emoji.sword.emoji_string}{legend_day.attack_sum}{legend_day.num_attacks.superscript}" \
                        f" {self.bot.emoji.shield.emoji_string} {legend_day.defense_sum}{legend_day.num_defenses.superscript}\n"
            trophy_results.append(disnake.SelectOption(label=f"{player.name} | 🏆{player.trophies}", value=f"{player_order}", emoji=player.town_hall_cls.emoji.partial_emoji))
            embed = await check.checkEmbed(player)
            results.append(player)
            stats_page.append(embed)
            player_order += 1

        if len(tags) > 1 and ez_look:
            embed = disnake.Embed(title=f"{len(results) - 1} Results",
                                  description=text)
            trophy_results.insert(0, disnake.SelectOption(label="Results Overview", value="0", emoji=self.bot.emoji.pin.partial_emoji))

            embed.set_footer(text="Use `Player Results` menu Below to switch btw players")
            stats_page.insert(0, embed)
            components = await self.create_components(results, trophy_results, current_page, len(tags) > 1 and ez_look, ctx)
            await msg.edit(embed=embed, components=components)
        else:
            components = await self.create_components(results, trophy_results, current_page, len(tags) > 1 and ez_look, ctx)
            await msg.edit(embed=stats_page[0], components=components)

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

            if res.values[0] in stat_types:
                if "Quick Check & Daily Report" in res.values[0]:
                    await self.add_profile(res, results[current_page], msg, trophy_results, current_page, len(tags) > 1 and ez_look, results)
                else:
                    current_stat = stat_types.index(res.values[0])
                    await res.response.defer()
                    embed = await self.display_embed(results, stat_types[current_stat], current_page)
                    await msg.edit(embed=embed,
                                   components=components)
            else:
                try:
                    current_page = int(res.values[0])
                    components = await self.create_components(results, trophy_results, current_page, len(tags) > 1 and ez_look, res)
                    embed = stats_page[current_page]
                    await res.response.edit_message(embed=embed,
                                   components=components)
                except:
                    continue

    async def add_profile(self, res, player, msg, trophy_results, current_page, is_true, rresult):
        tag = player.tag
        results = await self.bot.legend_profile.find_one({'discord_id': res.author.id})
        if results is None:
            await self.bot.legend_profile.insert_one({'discord_id': res.author.id, "profile_tags": [f"{tag}"]})

            player = await self.bot.getPlayer(tag)
            await res.send(content=f"Added {player.name} to your Quick Check & Daily Report list.", ephemeral=True)

        else:
            profile_tags = results.get("profile_tags")
            if profile_tags is None:
                profile_tags = []
            if tag in profile_tags:
                await self.bot.legend_profile.update_one({'discord_id': res.author.id}, {'$pull': {"profile_tags": tag, "feed_tags" : tag}})
                await res.send(content=f"Removed {player.name} from your Quick Check & Daily Report list.", ephemeral=True)

            elif len(profile_tags) >= 24:
                await res.send(content="Can only have 24 players on your Quick Check & Daily Report list. Please remove one.", ephemeral=True)

            else:
                await self.bot.legend_profile.update_one({'discord_id': res.author.id}, {'$push': {"profile_tags": tag}})
                await res.send(content=f"Added {player.name} to your Quick Check & Daily Report list.", ephemeral=True)

        components = await self.create_components(rresult, trophy_results, current_page, is_true, res)

        await msg.edit(components=components)

    async def display_embed(self, results, stat_type, current_page):
        check = self.bot.get_cog("Legends")

        if stat_type == "Legends Overview":
            return await check.checkEmbed(results[current_page])
        elif stat_type == "Previous Days":
            return await check.checkYEmbed(results[current_page])
        elif stat_type == "Legends History":
            return await check.create_history(results[current_page].tag)

    async def create_components(self, results, trophy_results, current_page, is_many, ctx):
        length = len(results)
        options = []
        for stat in stat_types:
            if stat == "Quick Check & Daily Report Add":
                presults = await self.bot.legend_profile.find_one({'discord_id': ctx.author.id})
                if presults is None:
                    options.append(disnake.SelectOption(label=f"{stat}", value=f"{stat}", emoji=self.bot.emoji.quick_check.partial_emoji))
                    continue
                tags = presults.get("profile_tags")
                if tags is None:
                    tags = []
                result = results[current_page]
                if result == "x":
                    continue
                tag = result.tag
                if tag in tags:
                    continue
                options.append(disnake.SelectOption(label=f"{stat}", value=f"{stat}", emoji=self.bot.emoji.quick_check.partial_emoji))
            elif stat == "Quick Check & Daily Report Remove":
                presults = await self.bot.legend_profile.find_one({'discord_id': ctx.author.id})
                if presults is None:
                    continue
                tags = presults.get("profile_tags")
                if tags is None:
                    tags = []
                result = results[current_page]
                if result == "x":
                    continue
                tag = result.tag
                if tag in tags:
                    options.append(disnake.SelectOption(label=f"{stat}", value=f"{stat}", emoji=self.bot.emoji.quick_check.partial_emoji))
            else:
                emoji = self.bot.fetch_emoji(stat).partial_emoji
                options.append(disnake.SelectOption(label=f"{stat}", value=f"{stat}", emoji=emoji))

        stat_select = disnake.ui.Select(options=options, placeholder="🔎 Stat Pages & Settings", min_values=1, max_values=1)

        st = disnake.ui.ActionRow()
        st.append_item(stat_select)

        if length == 1:
            return st

        profile_select = disnake.ui.Select(options=trophy_results, placeholder="⚙️ Player Results", min_values=1, max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        return [st2] if is_many and current_page==0 else [st, st2]



