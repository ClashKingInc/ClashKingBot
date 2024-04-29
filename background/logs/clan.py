import disnake
import coc

from disnake.ext import commands
from classes.server import DatabaseClan
from classes.bot import CustomClient
from background.logs.events import clan_ee


class clan_events(commands.Cog, name="Clan Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("member_count", self.member_count_warning)


    async def member_count_warning(self, event):
        new_clan = coc.Clan(data=event["new_clan"], client=self.bot.coc_client)
        old_clan = coc.Clan(data=event["old_clan"], client=self.bot.coc_client)

        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_clan.tag}, {f"member_count_warning.channel": {"$ne" : None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            if not db_clan.member_count_warning.channel:
                continue

            if new_clan.member_count > db_clan.member_count_warning.above and old_clan.member_count <= db_clan.member_count_warning.above:
                try:
                    channel = await self.bot.getch_channel(db_clan.member_count_warning.channel, raise_exception=True)
                    text = f"{new_clan.name} is above {db_clan.member_count_warning.above} members"
                    embed = disnake.Embed(description=text, color=disnake.Color.green())
                    embed.set_thumbnail(url=new_clan.badge.url)
                    content = None
                    if db_clan.member_count_warning.role is not None:
                        content = f"<@&{db_clan.member_count_warning.role}>"
                    if content is None:
                        await channel.send(embed=embed)
                    else:
                        await channel.send(embed=embed, content=content)
                except (disnake.NotFound, disnake.Forbidden):
                    await db_clan.member_count_warning.set_channel(id=None)

            if new_clan.member_count < db_clan.member_count_warning.below and old_clan.member_count >= db_clan.member_count_warning.below:
                try:
                    channel = await self.bot.getch_channel(db_clan.member_count_warning.channel, raise_exception=True)
                    text = f"{new_clan.name} is below {db_clan.member_count_warning.below} members"
                    embed = disnake.Embed(description=text, color=disnake.Color.red())
                    embed.set_thumbnail(url=new_clan.badge.url)
                    content = None
                    if db_clan.member_count_warning.role is not None:
                        content = f"<@&{db_clan.member_count_warning.role}>"
                    if content is None:
                        await channel.send(embed=embed)
                    else:
                        await channel.send(embed=embed, content=content)
                except (disnake.NotFound, disnake.Forbidden):
                    await db_clan.member_count_warning.set_channel(id=None)




def setup(bot: CustomClient):
    bot.add_cog(clan_events(bot))