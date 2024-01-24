import disnake
from datetime import datetime
import coc
from classes.ClashKingAPI.Classes.bans import BannedResponse, BannedUser
from classes.bot import CustomClient
from typing import List
from utility.general import get_guild_icon

async def ban_player_extras(bot: CustomClient, banned_user: BannedResponse, who: disnake.User):
    if banned_user.new_entry:
        pass
    else:
        pass


    log_embed = disnake.Embed(
        description=f"[{banned_user.name}]({banned_user.share_link}) added to the banlist by {who.mention}.\nNotes: {banned_user.notes}",
        color=disnake.Color.orange())

    results = await self.bot.server_db.find_one({"server": ctx.guild.id})
    banChannel = results.get("banlist")
    channel = await self.bot.pingToChannel(ctx, banChannel)

    if channel is not None:
        x = 0
        async for message in channel.history(limit=200):
            message: disnake.Message
            x += 1
            if x == 101:
                break
            if message.author.id != self.bot.user.id:
                continue
            if message.embeds:
                if "Ban List" in str(message.embeds[0].title) or "banlist" in str(message.embeds[0].description):
                    await message.delete()

        embeds = await self.create_embeds(ctx)
        for embed in embeds:
            await channel.send(embed=embed)
        await channel.send(embed=embed2)

    return embed2



async def create_embeds(bot: CustomClient, bans: List[BannedUser], guild: disnake.Guild, embed_color: disnake.Color):
    embeds = []

    hold = ""
    for count, banned_user in enumerate(bans, 1):
        date = banned_user.date[0:10]
        notes = banned_user.notes

        if banned_user.clan is not None:
            clan = f"{banned_user.clan.name}, {banned_user.clan.role}"
        else:
            clan = "No Clan"

        added_by = ""
        if banned_user.added_by is not None:
            user = await bot.getch_user(banned_user.added_by)
            added_by = f"\nAdded by: {user}"
        hold += f"{bot.fetch_emoji(banned_user.townhall)}[{banned_user.name}]({banned_user.share_link}) | {banned_user.tag}\n" \
                f"{clan}\n" \
                f"Added on: {date}\n" \
                f"Notes: *{notes}*{added_by}\n\n"

        if count % 10 == 0 or count == len(bans):
            embed = disnake.Embed(description=hold, color=embed_color)
            embed.set_author(name=f"{guild.name} Ban List", icon_url=get_guild_icon(guild=guild))
            embeds.append(embed)
            hold = ""

    return embeds