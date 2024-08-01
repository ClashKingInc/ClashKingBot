import asyncio
from typing import List

import coc
import disnake
import pendulum as pend

from assets.emojis import SharedEmojis
from assets.thPicDictionary import thDictionary
from classes.bot import CustomClient
from classes.player.stats import StatsPlayer
from exceptions.CustomExceptions import NoLinkedAccounts
from utility.clash.capital import is_raids, weekend_to_cocpy_timestamp
from utility.clash.other import heroPets, heros, profileSuperTroops
from utility.discord_utils import interaction_handler, register_button
from utility.general import acronym, create_superscript


async def basic_player_board(bot: CustomClient, player: coc.Player, embed_color: disnake.Color):
	clan = player.clan.name if player.clan else "No Clan"
	hero = heros(bot=bot, player=player)
	pets = heroPets(bot=bot, player=player)

	hero = f"**Heroes:**\n{hero}\n" if hero is None else ""
	pets = f"**Pets:**\n{pets}\n" if pets is None else ""

	embed = disnake.Embed(
	    title=f"**Invite {player.name} to your clan:**",
	    description=f"{player.name} - TH{player.town_hall}\n" + f"Tag: {player.tag}\n" + f"Clan: {clan}\n" + f"Trophies: {player.trophies}\n"
	    f"War Stars: {player.war_stars}\n"
	    f"{hero}{pets}",
	    color=embed_color,
	)

	embed.set_thumbnail(url=thDictionary(player.town_hall))
	return embed


async def lookup_components(
    bot: CustomClient,
    ctx: disnake.MessageInteraction,
    custom_player: StatsPlayer,
    **kwargs,
):
	action_rows = disnake.ui.ActionRow().rows_from_message(message=ctx.message)
	if action_rows:
		options = [  # the options in your dropdown
		    disnake.SelectOption(label="Overview",
		                         value=f"playerdetailed:{custom_player.tag}"),
		    # disnake.SelectOption(label="Troops", emoji=bot.emoji.troop.partial_emoji, value="Troops"),
		    # disnake.SelectOption(label="Upgrades/Rushed", emoji=bot.emoji.clock.partial_emoji, value="Upgrades"),
		    # disnake.SelectOption(label="Clan History", emoji=bot.emoji.clan_castle.partial_emoji, value="History"),
		]
		action_rows[0] = [disnake.ui.ActionRow(disnake.ui.Select(options=options, placeholder="Choose a page", max_values=1))]
	return action_rows

	player_results = []
	for count, player in enumerate(results):
		player: StatsPlayer
		player_results.append(disnake.SelectOption(
		    label=f"{player.name}",
		    emoji=player.town_hall_cls.emoji.partial_emoji,
		    value=f"{count}",
		))

	profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)

	st2 = disnake.ui.ActionRow()
	st2.append_item(profile_select)

	return [st, st2]


@register_button("playerdetailed", parser="_:custom_player")
async def detailed_player_board(bot: CustomClient, custom_player: StatsPlayer, server: disnake.Guild):
	player = custom_player

	discord_id = await bot.link_client.get_link(player.tag)
	member = await bot.getch_user(discord_id)
	super_troop_text = profileSuperTroops(player)

	clan = f"{player.clan.name}, " if player.clan is not None else "None"
	role = player.role if player.role is not None else ""

	if member is not None:
		link_text = f"Linked to {member.mention}"
	elif member is None and discord_id is not None:
		link_text = "*Linked, but not on this server.*"
	else:
		link_text = "Not linked. Owner? Use </link:1033741922180796451>"

	last_online = f"<t:{player.last_online}:R>, {len(player.season_last_online())} times"
	if player.last_online is None:
		last_online = "`Not Seen Yet`"

	loot_text = ""
	if player.gold_looted != 0:
		loot_text += f"- {bot.emoji.gold}Gold Looted: {'{:,}'.format(player.gold_looted())}\n"
	if player.elixir_looted != 0:
		loot_text += f"- {bot.emoji.elixir}Elixir Looted: {'{:,}'.format(player.elixir_looted())}\n"
	if player.dark_elixir_looted != 0:
		loot_text += f"- {bot.emoji.dark_elixir}DE Looted: {'{:,}'.format(player.dark_elixir_looted())}\n"

	capital_stats = player.clan_capital_stats(start_week=0, end_week=4)
	hitrate = (await player.hit_rate())[0]
	profile_text = (
	    f"{link_text}\n"
	    f"Tag: [{player.tag}]({player.share_link})\n"
	    f"Clan: {clan} {role}\n"
	    f"Last Seen: {last_online}\n"
	    f"[Clash Of Stats](https://www.clashofstats.com/players/{player.tag.strip('#')}) [Chocolate Clash](https://fwa.chocolateclash.com/cc_n/member.php?tag={player.tag.strip('#')})\n\n"
	    f"**Season Stats:**\n"
	    f"__Attacks__\n"
	    f"- {SharedEmojis.all_emojis.get(player.league.name)}Trophies: {player.trophies}\n"
	    f"- {bot.emoji.thick_sword}Attack Wins: {player.attack_wins}\n"
	    f"- {bot.emoji.brown_shield}Defense Wins: {player.defense_wins}\n"
	    f"{loot_text}"
	    f"__War__\n"
	    f"- {bot.emoji.hitrate}Hitrate: `{round(hitrate.average_triples * 100, 1)}%`\n"
	    f"- {bot.emoji.avg_stars}Avg Stars: `{round(hitrate.average_stars, 2)}`\n"
	    f"- {bot.emoji.war_stars}Total Stars: `{hitrate.total_stars}, {hitrate.num_attacks} atks`\n"
	    f"__Donations__\n"
	    f"- {bot.emoji.up_green_arrow}Donated: {player.donos().donated}\n"
	    f"- {bot.emoji.down_red_arrow}Received: {player.donos().received}\n"
	    f"- {bot.emoji.ratio}Donation Ratio: {player.donation_ratio()}\n"
	    f"__Event Stats__\n"
	    f"- {bot.emoji.capital_gold}CG Donated: {'{:,}'.format(sum([sum(cap.donated) for cap in capital_stats]))}\n"
	    f"- {bot.emoji.thick_sword}CG Raided: {'{:,}'.format(sum([sum(cap.raided) for cap in capital_stats]))}\n"
	    f"- {bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.clan_games())}\n"
	    f"{super_troop_text}"
	    f"\n**All Time Stats:**\n"
	    f"Best Trophies: {bot.emoji.trophy}{player.best_trophies} | {bot.emoji.versus_trophy}{player.best_builder_base_trophies}\n"
	    f"War Stars: {bot.emoji.war_star}{player.war_stars}\n"
	    f"CWL Stars: {bot.emoji.war_star} {player.get_achievement('War League Legend').value}\n"
	    f"{bot.emoji.troop}Donations: {'{:,}'.format(player.get_achievement('Friend in Need').value)}\n"
	    f"{bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.get_achievement('Games Champion').value)}\n"
	    f"{bot.emoji.thick_sword}CG Raided: {'{:,}'.format(player.get_achievement('Aggressive Capitalism').value)}\n"
	    f"{bot.emoji.capital_gold}CG Donated: {'{:,}'.format(player.get_achievement('Most Valuable Clanmate').value)}"
	)

	embed = disnake.Embed(
	    title=f"{player.town_hall_cls.emoji} **{player.name}**",
	    description=profile_text,
	    color=disnake.Color.green(),
	)
	embed.set_thumbnail(url=player.town_hall_cls.image_url)
	if member is not None:
		embed.set_footer(text=str(member), icon_url=member.display_avatar)

	ban = await bot.banlist.find_one({"$and": [{"VillageTag": f"{player.tag}"}, {"server": server.id}]})

	if ban is not None:
		date = ban.get("DateCreated")
		date = date[:10]
		notes = ban.get("Notes")
		if notes == "":
			notes = "No Reason Given"
		embed.add_field(name="__**Banned Player**__", value=f"Date: {date}\nReason: {notes}")
	return embed


@register_button("playeraccounts", parser="_:discord_user")
async def player_accounts(bot: CustomClient, discord_user: disnake.Member, embed_color: disnake.Color):
	linked_accounts = await bot.link_client.get_linked_players(discord_id=discord_user.id)

	players = await bot.get_players(tags=linked_accounts, custom=True, use_cache=True)
	if not players:
		raise NoLinkedAccounts

	players.sort(key=lambda x: (x.town_hall, x.trophies), reverse=True)
	total_stats = {
	    "donos": 0,
	    "rec": 0,
	    "war_stars": 0,
	    "th": 0,
	    "attacks": 0,
	    "trophies": 0,
	    "total_donos": 0,
	}
	text = ""
	for count, player in enumerate(players):
		if count < 20:
			opt_emoji = bot.emoji.opt_in if player.war_opted_in else bot.emoji.opt_out
			heros = ""
			for hero in player.heroes:
				if hero.is_home_base:
					level = f"{hero.level}" if hero.is_max_for_townhall else f"{hero.level}"
					heros += f"{acronym(hero.name)}{level} "
			if heros != "" and len([h for h in player.heroes if h.is_home_base]) >= 2:
				heros += f"{sum([h.level for h in player.heroes if h.is_home_base])}"

			text += (
			    f"{opt_emoji}**[{player.clear_name}{create_superscript(player.town_hall)}]({player.share_link})**\n"
			    f"{bot.fetch_emoji(player.league_as_string)}{player.trophies}"
			)
			'''if heros != "":
                text += f"- `{heros}`\n"'''

			if player.clan:
				text += f" | {player.clan.name} ({player.role_as_string})"

			text += "\n"
	embed = disnake.Embed(description=text, color=embed_color)
	embed.set_author(
	    name=f"{discord_user.display_name} Accounts ({len(players)})",
	    icon_url=discord_user.display_avatar,
	)
	if len(players) > 20:
		embed.set_footer(text="Only top 20 accounts are shown due to character limitations")
	return embed


@register_button("playertodo", parser="_:discord_user")
async def to_do_embed(bot: CustomClient, discord_user: disnake.Member, embed_color: disnake.Color):

	user_settings = await bot.user_settings.find_one({"discord_id": discord_user.id})
	if user_settings:
		linked_accounts = user_settings.get("to_do_accounts")
	else:
		linked_accounts = await bot.link_client.get_linked_players(discord_id=discord_user.id)

	linked_accounts = await bot.get_players(tags=linked_accounts, custom=True, use_cache=True)
	if not linked_accounts:
		raise NoLinkedAccounts

	embed = disnake.Embed(title=f"{discord_user.display_name} To-Do List", color=embed_color)

	war_hits_to_do = await get_war_hits(bot=bot, linked_accounts=linked_accounts)
	if war_hits_to_do != "":
		embed.add_field(name="War Hits", value=war_hits_to_do, inline=False)

	legend_hits_to_do = await get_legend_hits(linked_accounts=linked_accounts)
	if legend_hits_to_do != "":
		embed.add_field(name="Legend Hits", value=legend_hits_to_do, inline=False)

	if is_raids():
		raid_hits_to_do = await get_raid_hits(bot=bot, linked_accounts=linked_accounts)
		if raid_hits_to_do != "":
			embed.add_field(name="Raid Hits", value=raid_hits_to_do, inline=False)

	clangames_to_do = await get_clan_games(linked_accounts=linked_accounts)
	if clangames_to_do != "":
		embed.add_field(name="Clan Games", value=clangames_to_do, inline=False)

	pass_to_do = await get_pass(bot=bot, linked_accounts=linked_accounts)
	if pass_to_do != "":
		embed.add_field(name="Season Pass (Top 10)", value=pass_to_do, inline=False)

	inactive_to_do = await get_inactive(linked_accounts=linked_accounts)
	if inactive_to_do != "":
		embed.add_field(name="Inactive Accounts (48+ hr)", value=inactive_to_do, inline=False)

	donation_to_do = await get_last_donated(bot=bot, linked_accounts=linked_accounts)
	if donation_to_do != "":
		embed.add_field(name="Capital Dono (24+ hr)", value=donation_to_do, inline=False)

	if len(embed.fields) == 0:
		embed.description = "You're all caught up chief!"
	embed.timestamp = pend.now(tz=pend.UTC)
	return embed


async def get_war_hits(bot: CustomClient, linked_accounts: List[StatsPlayer]):

	async def get_clan_wars(clan_tag, player):
		war = await bot.get_clanwar(clanTag=clan_tag)
		if war is not None and str(war.state) == "notInWar":
			war = None
		if war is not None and war.end_time is None:
			war = None
		if war is not None and war.end_time.seconds_until <= 0:
			war = None
		return (player, war)

	tasks = []
	for player in linked_accounts:
		if player.clan is not None:
			task = asyncio.ensure_future(get_clan_wars(clan_tag=player.clan.tag, player=player))
			tasks.append(task)
	wars = await asyncio.gather(*tasks)

	war_hits = ""
	for player, war in wars:
		if war is None:
			continue
		war: coc.ClanWar
		our_player = coc.utils.get(war.members, tag=player.tag)
		if our_player is None:
			continue
		attacks = our_player.attacks
		required_attacks = war.attacks_per_member
		if len(attacks) < required_attacks:
			war_hits += f"({len(attacks)}/{required_attacks}) | <t:{int(war.end_time.time.replace(tzinfo=pend.UTC).timestamp())}:R> - {player.name}\n"
	return war_hits


@register_button("playertodosettings", parser="_:ctx", ephemeral=True, no_embed=True)
async def player_todo_settings(bot: CustomClient, ctx: disnake.MessageInteraction):

	user_accounts = await bot.link_client.get_linked_players(discord_id=ctx.user.id)
	user_accounts = await bot.get_players(tags=user_accounts, use_cache=True, custom=False)
	if not user_accounts:
		raise NoLinkedAccounts

	def player_component(bot: CustomClient, all_players: List[coc.Player]):
		all_players.sort(key=lambda x: (x.town_hall, x.trophies), reverse=True)
		all_players = all_players[:100]
		player_chunked = [all_players[i:i + 25] for i in range(0, len(all_players), 25)]

		dropdown = []
		for chunk_list in player_chunked:
			player_options = []
			for player in chunk_list:
				player_options.append(disnake.SelectOption(
				    label=f"{player.name} ({player.tag})",
				    emoji=bot.fetch_emoji(player.town_hall).partial_emoji,
				    value=f"{player.tag}",
				))

			player_select = disnake.ui.Select(
			    options=player_options,
			    placeholder=f"Select Player(s)",  # the placeholder text to show when no options have been chosen
			    min_values=1,  # the minimum number of options a user must select
			    max_values=len(player_options),  # the maximum number of options a user can select
			)
			dropdown.append(disnake.ui.ActionRow(player_select))

		dropdown.append(disnake.ui.ActionRow(disnake.ui.Button(
		    label="Save",
		    emoji=bot.emoji.yes.partial_emoji,
		    style=disnake.ButtonStyle.green,
		    custom_id="Save",
		)))
		return dropdown

	msg = await ctx.followup.send(
	    content="Choose which account you want visible on your to-do list (max 15)\n",
	    components=player_component(bot=bot, all_players=user_accounts),
	    ephemeral=True,
	    wait=True,
	)
	clicked_save = False
	players = set()
	while not clicked_save:
		res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, msg=msg)
		if res.component.type == disnake.ComponentType.button:
			break
		for value in res.values:
			players.add(value)
			if len(players) == 15:
				break

	await bot.user_settings.update_one(
	    {"discord_id": ctx.author.id},
	    {"$set": {
	        "to_do_accounts": list(players)
	    }},
	    upsert=True,
	)
	await msg.edit(content="Player To-Do Accounts Updated!", components=None)


async def get_legend_hits(linked_accounts: List[StatsPlayer]):
	legend_hits_remaining = ""
	for player in linked_accounts:
		if player.is_legends():
			if player.legend_day().num_attacks.integer < 8:
				legend_hits_remaining += f"({player.legend_day().num_attacks.integer}/8) - {player.name}\n"
	return legend_hits_remaining


async def get_raid_hits(bot: CustomClient, linked_accounts: List[StatsPlayer]):

	current_week = bot.gen_raid_date()

	# only pull current raid weekends, in case somehow old ones get stuck there
	"""raids_in = await bot.capital_cache.find({"$and" : [
        {"data.members.tag": {"$in": [p.tag for p in linked_accounts]}},
        {"data.startTime" : weekend_to_cocpy_timestamp(weekend=current_week)}
    ]})"""

	linked_tags = [p.tag for p in linked_accounts]  # Assume this list is already computed
	weekend_timestamp = weekend_to_cocpy_timestamp(weekend=current_week)

	raids_in = await bot.capital_cache.aggregate([
	    {
	        "$match": {
	            "$and": [
	                {
	                    "data.members.tag": {
	                        "$in": linked_tags
	                    }
	                },
	                {
	                    "data.startTime": weekend_timestamp.time.strftime("%Y%m%dT%H%M%S.000Z")
	                },
	            ]
	        }
	    },
	    {
	        "$project": {
	            "data": {
	                "startTime": 1,
	                "members": {
	                    "$filter": {
	                        "input": "$data.members",
	                        "as": "member",
	                        "cond": {
	                            "$in": ["$$member.tag", linked_tags]
	                        },
	                    }
	                },
	            },
	            "tag": 1,
	        }
	    },
	    {
	        "$match": {
	            "data.members": {
	                "$not": {
	                    "$size": 0
	                }
	            }
	        }
	    },
	]).to_list(length=None)
	raid_hits = ""

	for raw_raid in raids_in:
		clan_tag = raw_raid.get("tag")
		members = raw_raid.get("data", {}).get("members", [])
		members = [coc.raid.RaidMember(data=m, raid_log_entry=None, client=None) for m in members]

		for member in members:
			linked_tags.remove(member.tag)
			attacks = member.attack_count
			required_attacks = member.attack_limit + member.bonus_attack_limit
			if attacks < required_attacks:
				raid_hits += f"({attacks}/{required_attacks}) - {member.name}\n"

	for player in linked_accounts:
		if player.tag in linked_tags and player.clan is not None:
			raid_hits += f"({0}/{5}) - {player.name}\n"
	return raid_hits


async def get_inactive(linked_accounts: List[StatsPlayer]):
	now = int(pend.now(tz=pend.UTC).timestamp())
	inactive_text = ""
	for player in linked_accounts:
		last_online = player.last_online
		# 48 hours in seconds
		if last_online is None:
			continue
		if now - last_online >= (48 * 60 * 60):
			inactive_text += f"<t:{last_online}:R> - {player.name}\n"
	return inactive_text


async def get_clan_games(linked_accounts: List[StatsPlayer]):
	missing_clan_games = ""
	zeros = ""
	num_zeros = 0
	if is_clan_games():
		for player in linked_accounts:
			points = player.clan_games()
			if points < 4000:
				if points == 0:
					zeros += f"({points}/4000) - {player.name}\n"
					num_zeros += 1
				else:
					missing_clan_games += f"({points}/4000) - {player.name}\n"

	if num_zeros == len(linked_accounts):
		missing_clan_games = "(0/4000) on All Accounts "
	elif num_zeros >= 5:
		missing_clan_games += "(0/4000) on All Other Accounts"
	else:
		missing_clan_games += zeros

	return missing_clan_games


async def get_pass(bot: CustomClient, linked_accounts: List[StatsPlayer]):
	pass_text = ""
	points = 3000 if bot.gen_games_season() == "2023-06" else 4000
	l = sorted(linked_accounts, key=lambda x: x.season_pass(), reverse=True)[:10]
	for player in l:
		season_pass_points = player.season_pass()
		if season_pass_points < points and season_pass_points != 0:
			pass_text += f"({season_pass_points}/{points}) - {player.name}\n"
	return pass_text


async def get_last_donated(bot: CustomClient, linked_accounts: List[StatsPlayer]):
	pass_text = ""
	now = int(pend.now(tz=pend.UTC).timestamp())
	pipeline = [
	    {
	        "$match": {
	            "$and": [
	                {
	                    "tag": {
	                        "$in": [p.tag for p in linked_accounts]
	                    }
	                },
	                {
	                    "type": "clanCapitalContributions"
	                },
	            ]
	        }
	    },
	    {
	        "$group": {
	            "_id": "$tag", "last_change": {
	                "$last": "$time"
	            }
	        }
	    },
	    {
	        "$sort": {
	            "last_change": -1
	        }
	    },
	]
	results = await bot.player_history.aggregate(pipeline=pipeline).to_list(length=None)
	tag_to_player = {p.tag: p for p in linked_accounts}
	for result in results:
		time = result.get("last_change")
		if now - time >= (24 * 60 * 60):
			pass_text += f"<t:{time}:R> - {tag_to_player.get(result.get('_id')).name}\n"
	return pass_text


def is_clan_games():
	now = pend.now(tz=pend.UTC)
	year = now.year
	month = now.month
	day = now.day
	hour = now.hour
	first = pend.datetime(year, month, 22, hour=8, tz=pend.UTC)
	end = pend.datetime(year, month, 28, hour=8, tz=pend.UTC)
	if day >= 22 and day <= 28:
		if (day == 22 and hour < 8) or (day == 28 and hour >= 8):
			is_games = False
		else:
			is_games = True
	else:
		is_games = False
	return is_games



