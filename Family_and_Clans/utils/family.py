import disnake
import coc
import pytz
import emoji
import asyncio
import statistics

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
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        donated_text = []
        received_text = []
        ratio_text = []
        total_donated = sum(player.donos().donated for player in responses if not isinstance(player, coc.errors.NotFound))
        total_received = sum(player.donos().received for player in responses if not isinstance(player, coc.errors.NotFound))

        for player in responses:
            if isinstance(player, coc.errors.NotFound):
                print()
                continue
            player: MyCustomPlayer
            if player is None:
                continue
            if player.clan is None:
                continue
            for char in ["`", "*", "_", "~"]:
                name = player.name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:13]
            name = name.ljust(13)
            donated_text.append(
                [f"`{str(player.donos().donated).ljust(5)} | {str(player.donos().received).ljust(5)} | \u200e{name}`",
                 player.donos().donated])
            received_text.append(
                [f"`{str(player.donos().received).ljust(5)} | {str(player.donos().donated).ljust(5)} | \u200e{name}`",
                 player.donos().received])
            ratio_text.append([f"`{str(player.donation_ratio()).ljust(5)} | \u200e{name}`", player.donation_ratio()])

        if type == "donated":
            donated_text = sorted(donated_text, key=lambda l: l[1], reverse=True)
            donated_text = [f"{self.bot.get_number_emoji(color='gold', number=count)} {line[0]}" for count, line in enumerate(donated_text[:50], 1)]
            donated_text = "\n".join(donated_text)
            donated_text = "<:un:1036115340360429628>` DON   | REC   | Name` \n" + donated_text
            donation_embed = disnake.Embed(title=f"**{guild.name} Top 50 Donated**", description=f"{donated_text}",
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
            received_text = [f"{self.bot.get_number_emoji(color='gold', number=count)} {line[0]}" for count, line in enumerate(received_text[:50], 1)]
            received_text = "\n".join(received_text)
            received_text = "<:un:1036115340360429628>` REC   | DON   | Name`\n" + received_text
            received_embed = disnake.Embed(title=f"**{guild.name} Top 50 Received**", description=f"{received_text}",
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
            ratio_text = [f"{self.bot.get_number_emoji(color='gold', number=count)} {line[0]}" for count, line in enumerate(ratio_text[:50], 1)]
            ratio_text = "\n".join(ratio_text)
            ratio_text = "<:un:1036115340360429628>` Ratio | Name`\n" + ratio_text
            ratio_embed = disnake.Embed(title=f"**{guild.name} Top 50 Ratios**", description=f"{ratio_text}",
                                        color=disnake.Color.green())
            if guild.icon is not None:
                icon = guild.icon.url
            else:
                icon = self.bot.user.avatar.url
            ratio_embed.set_footer(icon_url=icon,
                                   text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return ratio_embed

    async def create_last_online(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans = await self.bot.get_clans(tags=clan_tags)
        member_tags = []
        for clan in clans:
            member_tags.extend(member.tag for member in clan.members)

        players = await self.bot.get_players(tags=member_tags, custom=True)
        text = []
        avg_time = []
        for member in players:
            last_online = member.last_online
            last_online_sort = last_online
            if last_online is None:
                last_online_sort = 0
                text.append([f"Not Seen `{member.name}`", last_online_sort])
            else:
                avg_time.append(last_online)
                text.append([f"<t:{last_online}:R> `{member.name}`", last_online_sort])

        text = sorted(text, key=lambda l: l[1], reverse=True)
        text = text[0:50]
        text = [line[0] for line in text]
        text = "\n".join(text)
        if avg_time != []:
            avg_time.sort()
            avg_time = statistics.median(avg_time)
            avg_time = f"\n\n**Median L.O.** <t:{int(avg_time)}:R>"
        else:
            avg_time = ""
        embed = disnake.Embed(title=f"**{guild.name} Last 50 Online**",
                              description=text + avg_time,
                              color=disnake.Color.green())
        return embed

def setup(bot: CustomClient):
    bot.add_cog(getFamily(bot))