
import disnake
from disnake.ext import commands
import asyncio
from CustomClasses.CustomBot import CustomClient

class Donations(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="donations", description="Leaderboard of top 50 donators in family")
    async def dono(self, ctx: disnake.ApplicationCommandInteraction):
        embed = await self.dono_embed(ctx)
        refresh_buttons = [
            disnake.ui.Button(label="", emoji="🔁", style=disnake.ButtonStyle.grey,custom_id="donation"),
        ]
        buttons = disnake.ui.ActionRow()
        for button in refresh_buttons:
            buttons.append_item(button)
        await ctx.edit_original_message(embed=embed, components=buttons)

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if str(ctx.data.custom_id) == "donation":
            await ctx.response.defer()
            embed = await self.dono_embed(ctx)
            await ctx.edit_original_message(embed=embed)

    async def dono_embed(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        clan_tags = await self.bot.clan_db.distinct("tag", {"server" : ctx.guild.id})

        tasks = []
        for tag in clan_tags:
            task = asyncio.ensure_future(self.bot.getClan(tag))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        clan_member_tags = [member.tag for member in [clan.members for clan in responses]]



        donation_list = []
        raid_list = []
        for member in responses:
            player: MyCustomPlayer
            cc_stats = player.clan_capital_stats(week=weekend)
            if cc_stats is None:
                continue
            # donated lines
            donation_text = f"{cc_stats.donated}".ljust(5)
            donation_list.append([f"{self.bot.emoji.capital_gold}`{donation_text}`: {player.name}", cc_stats.donated])
            # raid lines
            if clan.tag == cc_stats.raid_clan:
                raid_text = f"{cc_stats.raided}".ljust(5)
                raid_list.append([f"{self.bot.emoji.capital_gold}`{raid_text}`: {player.name}", cc_stats.raided])

        # donation sort
        donation_ranked = sorted(donation_list, key=lambda l: l[1], reverse=True)
        # raid sort
        raids_ranked = sorted(raid_list, key=lambda l: l[1], reverse=True)

        donated_lines = [line[0] for line in donation_ranked]
        raid_lines = [line[0] for line in raids_ranked]
        if donated_lines == []:
            donated_lines = ["No Capital Gold Donated"]
        if raid_lines == []:
            raid_lines = ["No Capital Gold Raided"]

        raid_embed = self.bot.create_embeds(line_lists=raid_lines, title=f"**{clan.name} Raid Totals**", max_lines=50,
                                            thumbnail_url=clan.badge.url)
        donation_embed = self.bot.create_embeds(line_lists=donated_lines, title="**Clan Capital Donations**",
                                                max_lines=50, thumbnail_url=clan.badge.url)

        await ctx.edit_original_message(embed=raid_embed[0])




def setup(bot: CustomClient):
    bot.add_cog(Donations(bot))