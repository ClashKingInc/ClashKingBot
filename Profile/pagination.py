from discord.ext import commands
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle
import discord


class pagination(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def button_pagination(self, ctx, msg, results):
        # statTypes
        profile_pages = ["Info", "Troops", "History"]

        profile_stats = self.bot.get_cog("profileStats")

        current_stat = 0
        current_page = 0

        embed = await profile_stats.create_profile_stats(ctx, results[0])

        await msg.edit(embed=embed, components=self.create_components(results, current_page), mention_author=False)


        while True:
            try:
                res = await wait_for_component(self.bot, components=self.create_components(results, current_page),messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()


            #print(res.custom_id)
            if res.custom_id == "Previous":
                current_page -= 1
                embed = await self.display_embed(results, profile_pages[current_stat], current_page, ctx)
                await msg.edit(embed=embed,
                               components=self.create_components(results, current_page))

            elif res.custom_id == "Next":
                current_page += 1
                embed = await self.display_embed(results, profile_pages[current_stat], current_page, ctx)
                await msg.edit(embed=embed,
                               components=self.create_components(results, current_page))

            elif res.custom_id in profile_pages:
                current_stat = profile_pages.index(res.custom_id)
                try:
                    embed = await self.display_embed(results, profile_pages[current_stat], current_page, ctx)
                    await msg.edit(embed=embed,
                                   components=self.create_components(results, current_page))
                except:
                    if profile_pages[current_stat] == "History":
                        embed = discord.Embed(description="This player has made their clash of stats history private.",
                                              color=discord.Color.green())
                        await msg.edit(embed=embed,
                                       components=self.create_components(results, current_page))

    async def display_embed(self, results, stat_type, current_page, ctx):

        profile_stats = self.bot.get_cog("profileStats")
        profile_troops = self.bot.get_cog("profileTroops")
        profile_history = self.bot.get_cog("profileHistory")

        if stat_type == "Info":
            return await profile_stats.create_profile_stats(ctx, results[current_page])
        elif stat_type == "Troops":
            return await profile_troops.create_profile_troops(results[current_page])
        elif stat_type == "History":
            return await profile_history.history(ctx, results[current_page])


    def create_components(self, results, current_page):
        length = len(results)

        page_buttons = [create_button(label="Prev", emoji="◀️", style=ButtonStyle.blue, disabled=(current_page == 0),
                                      custom_id="Previous"),
                        create_button(label=f"Page {current_page + 1}/{len(results)}", style=ButtonStyle.grey,
                                      disabled=True),
                        create_button(label="Next", emoji="▶️", style=ButtonStyle.blue,
                                      disabled=(current_page == length - 1), custom_id="Next")]
        page_buttons = create_actionrow(*page_buttons)

        stat_buttons = [create_button(label="Info", style=ButtonStyle.grey, custom_id="Info", disabled=False),
                        create_button(label="Troops", style=ButtonStyle.grey, custom_id="Troops"),
                        create_button(label="History", style=ButtonStyle.grey, custom_id="History", disabled=False)]
        stat_buttons = create_actionrow(*stat_buttons)

        if length == 1:
            return [stat_buttons]

        return [stat_buttons, page_buttons]


def setup(bot: commands.Bot):
    bot.add_cog(pagination(bot))