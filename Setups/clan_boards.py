from disnake.ext import commands, tasks
import disnake
from utils.clash import client, coc_client
usafam = client.usafam
server = usafam.server
clans = usafam.clans


class clan_boards(commands.Cog, name="Clan Board"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.boards.start()

    def cog_unload(self):
        self.boards.cancel()


    @tasks.loop(seconds=600)
    async def boards(self):
        bot =self.bot
        results = clans.find(
            {"new_change": {"$ne": None}})
        limit = await clans.count_documents(filter=
            {"new_change": {"$ne": None}})
        for clan in await results.to_list(length=limit):
            board_channel = clan.get("clanboard")
            try:
                channel = await bot.fetch_channel(board_channel)
            except:
                continue








def setup(bot: commands.Bot):
    bot.add_cog(clan_boards(bot))