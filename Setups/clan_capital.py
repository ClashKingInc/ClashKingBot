
from disnake.ext import commands
from utils.clash import create_weekends
import disnake
import asyncio

from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient


class clan_capital_commands(commands.Cog, name="Clan Capital Commands"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    Weekends = commands.option_enum(create_weekends())
    @commands.slash_command(name="clan_capital", description="See clan capital stats for a week")
    async def clan_capital(self, ctx: disnake.ApplicationCommandInteraction, clan, weekend:Weekends=None):
        await ctx.response.defer()
        clan = await self.bot.getClan(clan)

        if clan is None or clan.member_count == 0:
            return await ctx.send("Not a valid clan tag.")

        clan_member_tags = [player.tag for player in clan.members]

        tasks = []
        for tag in clan_member_tags:
            results = await self.bot.player_stats.find_one({"tag": tag})
            task = asyncio.ensure_future(self.bot.coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=self.bot, results=results))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        donation_list = []
        raid_list = []
        for player in responses:
            player: MyCustomPlayer
            cc_stats = player.clan_capital_stats(week=weekend)
            if cc_stats is None:
                continue
            #donated lines
            donation_text = f"{cc_stats.donated}".ljust(5)
            donation_list.append([f"{self.bot.emoji.capital_gold}`{donation_text}`: {player.name}", cc_stats.donated])
            #raid lines
            if clan.tag == cc_stats.raid_clan:
                raid_text = f"{cc_stats.raided}".ljust(5)
                raid_list.append([f"{self.bot.emoji.capital_gold}`{raid_text}`: {player.name}", cc_stats.raided])

        #donation sort
        donation_ranked = sorted(donation_list, key=lambda l: l[1], reverse=True)
        #raid sort
        raids_ranked = sorted(raid_list, key=lambda l: l[1], reverse=True)

        donated_lines = [line[0] for line in donation_ranked]
        raid_lines = [line[0] for line in raids_ranked]
        if donated_lines == []:
            donated_lines = ["No Capital Gold Donated"]
        if raid_lines == []:
            raid_lines = ["No Capital Gold Raided"]

        raid_embed = self.bot.create_embeds(line_lists=raid_lines, title=f"**{clan.name} Raid Totals**", max_lines=50, thumbnail_url=clan.badge.url)
        donation_embed = self.bot.create_embeds(line_lists=donated_lines, title="**Clan Capital Donations**", max_lines=50, thumbnail_url=clan.badge.url)

        await ctx.edit_original_message(embed=raid_embed[0])

    @clan_capital.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]


def setup(bot: CustomClient):
    bot.add_cog(clan_capital_commands(bot))