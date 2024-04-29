import coc
import disnake
import pendulum as pend


from classes.bot import CustomClient
from classes.player.bans import BannedPlayer
from datetime import timedelta
from exceptions.CustomExceptions import MessageException
from utility.general import get_guild_icon, safe_run


async def add_ban(bot: CustomClient, player: coc.Player, added_by: disnake.User | disnake.Member, guild: disnake.Guild, reason: str, rollover_days: int = None, dm_player: str = None):
    now = pend.now(tz=pend.UTC)
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")

    if rollover_days is not None:
        now = pend.now(tz=pend.UTC)
        rollover_days = now + timedelta(rollover_days)
        rollover_days = int(rollover_days.timestamp())

    find_ban = await bot.banlist.find_one({"$and" : [{"VillageTag" : player.tag}, {"server" : guild.id}]})
    if find_ban:
        await bot.banlist.update_one({"$and" : [{"VillageTag" : player.tag}, {"server" : guild.id}]},
                                     {"$set" : {"Notes" : reason, "rollover_date" : rollover_days},
                                     "$push" : {"edited_by" : {"user" : added_by.id, "previous" : {"reason" : find_ban.get("Notes"), "rollover_days" : find_ban.get("rollover_date")}}}})
        ban_type = "updated"
    else:
        await bot.banlist.insert_one({
            "VillageTag": player.tag,
            "DateCreated": dt_string,
            "Notes": reason,
            "server": guild.id,
            "added_by": added_by.id,
            "rollover_date": rollover_days,
            "name" : player.name
        })
        ban_type = "added"

    if rollover_days is not None:
        rollover_days = f"<t:{rollover_days}:f>"
    else:
        rollover_days = "Never"
    embed = disnake.Embed(
        description=f"**Ban {ban_type} for [{player.name}]({player.share_link}) [{player.clan.name if player.clan else 'No Clan'}] by {added_by.mention}.**\n"
                    f"Rollover: {rollover_days}\n"
                    f"Reason: {reason}",
        color=disnake.Color.brand_red())

    embed.timestamp = now
    if dm_player is not None:
        linked_account = await bot.link_client.get_link(player_tag=player.tag)
        if linked_account:
            server_member = await guild.getch_member(linked_account)
            if server_member:
                try:
                    await server_member.send(content=dm_player, embed=embed)
                    embed.set_footer(text=f"Notified in DM")
                except:
                    embed.set_footer(text=f"DM Notification Failed")
    await send_ban_log(bot=bot, guild=guild, reason=embed)

    return embed


async def remove_ban(bot: CustomClient, player: coc.Player, removed_by: disnake.User, guild: disnake.Guild):
    results = await bot.banlist.find_one({"$and": [
        {"VillageTag": player.tag},
        {"server": guild.id}
    ]})
    if not results:
        raise MessageException(f"{player.name} is not banned on this server.")

    await bot.banlist.find_one_and_delete({"$and": [
        {"VillageTag": player.tag},
        {"server": guild.id}
    ]})

    embed = disnake.Embed(description=f"[{player.name}]({player.share_link}) removed from the banlist by {removed_by.mention}.",
                           color=disnake.Color.orange())

    await send_ban_log(bot=bot, guild=guild, reason=embed)
    return embed


async def send_ban_log(bot: CustomClient, guild: disnake.Guild, reason: disnake.Embed):
    server_db = await bot.ck_client.get_server_settings(server_id=guild.id)
    if server_db.banlist_channel is not None:
        ban_log_channel = await bot.getch_channel(channel_id=server_db.banlist_channel)
        if ban_log_channel is not None:
            await safe_run(func=ban_log_channel.send, embed=reason)



async def create_embeds(bot: CustomClient, bans: list, guild: disnake.Guild, embed_color: disnake.Color):
    embeds = []
    banned_tags = [b.get("VillageTag") for b in bans]
    discord_links = await bot.link_client.get_links(*banned_tags)
    discord_links = dict(discord_links)

    hold = ""
    banned_players: list[BannedPlayer] = await bot.get_players(tags=banned_tags, custom=BannedPlayer, use_cache=True, found_results=bans)
    for count, banned_player in enumerate(banned_players, 1):
        date = banned_player.date_created[0:10]
        notes = banned_player.notes

        if banned_player.clan is not None:
            clan = f"{banned_player.clan.name}, {banned_player.role}"
        else:
            clan = "No Clan"
        discord = ""
        if (discord_id := discord_links.get(banned_player.tag)):
            if discord_id is not None:
                discord_user = guild.get_member(int(discord_id))
                if discord_user:
                    discord = f"Discord: {discord_user.mention} ({discord_user.name})\n"
        added_by = ""
        if banned_player.added_by is not None:
            user = await bot.getch_user(banned_player.added_by)
            added_by = f"\nAdded by: {user}"
        hold += f"{bot.fetch_emoji(banned_player.town_hall)}[{banned_player.name}]({banned_player.share_link}) | {banned_player.tag}\n" \
                f"{discord}" \
                f"{clan}\n" \
                f"Added on: {date}\n" \
                f"Notes: *{notes}*{added_by}\n\n"

        if count % 10 == 0 or count == len(bans):
            embed = disnake.Embed(description=hold, color=embed_color)
            embed.set_author(name=f"{guild.name} Ban List", icon_url=get_guild_icon(guild=guild))
            embeds.append(embed)
            hold = ""

    return embeds