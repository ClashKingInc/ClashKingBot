import disnake
import coc
import pytz
import emoji
import asyncio

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer

tiz = pytz.utc

class getFamily(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def create_donations(self, guild: disnake.Guild, type: str):
        date = self.bot.gen_season_date()
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        tasks = []
        members = []
        async for clan in self.bot.coc_client.get_clans(tags=clan_tags):
            members += [member.tag for member in clan.members]

        for tag in members:
            results = await self.bot.player_stats.find_one({"tag": tag})
            task = asyncio.ensure_future(
                self.bot.coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=self.bot,
                                               results=results))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        donated_text = []
        received_text = []
        ratio_text = []
        total_donated = sum(player.donos.donated for player in responses)
        total_received = sum(player.donos.received for player in responses)

        for player in responses:
            player: MyCustomPlayer
            for char in ["`", "*", "_", "~"]:
                name = player.name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:13]
            donated_text.append(
                [f"{str(player.donos.donated).ljust(5)} | {str(player.donos.received).ljust(5)} | {name}",
                 player.donos.donated])
            received_text.append(
                [f"{str(player.donos.received).ljust(5)} | {str(player.donos.donated).ljust(5)} | {name}",
                 player.donos.received])
            ratio_text.append([f"{str(player.donation_ratio).ljust(5)} | {name}", player.donation_ratio])

        if type == "donated":
            donated_text = sorted(donated_text, key=lambda l: l[1], reverse=True)
            donated_text = [line[0] for line in donated_text[:50]]
            donated_text = "\n".join(donated_text)
            donated_text = "DON   | REC   | Name\n" + donated_text
            donation_embed = disnake.Embed(title=f"**{guild.name} Top 50 Donated**", description=f"```{donated_text}```",
                                           color=disnake.Color.green())
            if guild.icon is not None:
                icon = guild.icon.url
            else:
                icon = self.bot.user.avatar.url
            donation_embed.set_footer(icon_url=icon,
                                      text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return donation_embed
        elif type == "received":
            received_text = sorted(received_text, key=lambda l: l[1], reverse=True)
            received_text = [line[0] for line in received_text[:50]]
            received_text = "\n".join(received_text)
            received_text = "REC   | DON   | Name\n" + received_text
            received_embed = disnake.Embed(title=f"**{guild.name} Top 50 Received**", description=f"```{received_text}```",
                                           color=disnake.Color.green())
            if guild.icon is not None:
                icon = guild.icon.url
            else:
                icon = self.bot.user.avatar.url
            received_embed.set_footer(icon_url=icon,
                                      text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return received_embed
        else:
            ratio_text = sorted(ratio_text, key=lambda l: l[1], reverse=True)
            ratio_text = [line[0] for line in ratio_text[:50]]
            ratio_text = "\n".join(ratio_text)
            ratio_text = "Ratio | Name\n" + ratio_text
            ratio_embed = disnake.Embed(title=f"**{guild.name} Top 50 Ratios**", description=f"```{ratio_text}```",
                                        color=disnake.Color.green())
            if guild.icon is not None:
                icon = guild.icon.url
            else:
                icon = self.bot.user.avatar.url
            ratio_embed.set_footer(icon_url=icon,
                                   text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return ratio_embed



def setup(bot: CustomClient):
    bot.add_cog(getFamily(bot))