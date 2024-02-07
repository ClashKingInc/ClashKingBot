import disnake
import time
import coc
import asyncio

from collections import defaultdict, namedtuple
from typing import List
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from classes.bot import CustomClient
else:
    from disnake.ext.commands import AutoShardedBot as CustomClient
from utility.constants import DEFAULT_EVAL_ROLE_TYPES, ROLE_TREATMENT_TYPES
from utility.general import get_clan_member_tags, create_superscript
from exceptions.CustomExceptions import ExpiredComponents, MessageException
from classes.DatabaseClient.Classes.settings import DatabaseServer
from utility.general import get_guild_icon



async def logic(bot: CustomClient, guild: disnake.Guild, db_server: DatabaseServer, members: List[disnake.Member], role_or_user: disnake.Role | disnake.User,
                eval_types: List = DEFAULT_EVAL_ROLE_TYPES, test: bool = False,**kwargs):
    time_start = time.time()

    IS_AUTOEVAL = kwargs.pop("auto_eval", False)
    auto_eval_tag = kwargs.pop("auto_eval_tag", None)

    ignored_roles = {r.id for r in db_server.ignored_roles}
    family_roles = {r.id for r in db_server.family_roles}
    not_family_roles = {r.id for r in db_server.not_family_roles}
    only_family_roles = {r.id for r in db_server.only_family_roles}

    clan_member_roles = {c.tag: c.member_role for c in db_server.clans}
    clan_leadership_roles = {c.tag: c.leader_role for c in db_server.clans}
    clan_tags = {c.tag for c in db_server.clans}
    townhall_roles = {int(r.townhall.replace("th", "")): r.id for r in db_server.townhall_roles}
    builderhall_roles = {int(r.builderhall.replace("bh", "")): r.id for r in db_server.builderhall_roles}
    league_roles = {r.type: r.id for r in db_server.league_roles}
    builder_league_roles = {r.type: r.id for r in db_server.builder_league_roles}
    clan_category_roles = {c.tag: db_server.category_roles.get(c.category) for c in db_server.clans}

    '''
    How to find roles:
    clan: by clan tag
    family: manually
    townhall, league: by attribute
    status: by month
    '''

    all_discord_links = await bot.link_client.get_many_linked_players(*[m.id for m in members])
    discord_link_dict = defaultdict(list)
    all_tags = []
    for player_tag, discord_id in all_discord_links:
        discord_link_dict[discord_id].append(player_tag)
        all_tags.append(player_tag)



    type_to_roles = {"family": list(family_roles), "not_family": list(not_family_roles),
                     "clan": list(clan_member_roles.values()), "leadership": [r for r in clan_leadership_roles.values() if r is not None],
                     "townhall": list(townhall_roles.values()), "builderhall": list(builderhall_roles.values()),
                     "league": list(league_roles.values()), "category": [r for r in clan_category_roles.values() if r is not None],
                     "builder_league": list(builder_league_roles.values())}

    for eval_type in DEFAULT_EVAL_ROLE_TYPES:
        if eval_type not in eval_types:
            pertinent_roles = type_to_roles.get(eval_type)
            for x in pertinent_roles:
                ignored_roles.add(x)

    ALL_CLASH_ROLES = {inner for type, outer in type_to_roles.items() for inner in outer if type != "leadership"}
    bot_member = await guild.getch_member(bot.user.id)

    if not bot_member.guild_permissions.manage_roles:
        raise MessageException("Missing Manage Roles Permission, Cannot Edit Roles")

    if db_server.change_nickname and not bot_member.guild_permissions.manage_nicknames:
        raise MessageException("Missing Change Nicknames Permission, Cannot Edit Nicknames")


    for role in ALL_CLASH_ROLES:
        role = guild.get_role(role)
        if role is None:
            continue
        if role > bot_member.top_role:
            raise MessageException(f"{role.mention} is higher than {bot_member.mention}'s top role ({bot_member.top_role}), cannot assign that role to users.")

    if "leadership" in eval_types and db_server.leadership_eval:
        ALL_CLASH_ROLES = ALL_CLASH_ROLES | set(type_to_roles.get("leadership", []))

    fresh_tags = []
    if auto_eval_tag is not None:
        fresh_tags = [auto_eval_tag]
        all_tags.remove(auto_eval_tag)
    all_players = await bot.get_players(tags=list(all_tags), fresh_tags=fresh_tags, use_cache=False, custom=False)

    player_dict = {p.tag : p for p in all_players}


    user_settings = await bot.user_settings.find({"discord_user": {"$in": [m.id for m in members]}}).to_list(length=None)
    main_account_lookup = {settings.get("discord_user"): settings.get("server_main_account", {}).get(guild.id)
                            if settings.get("server_main_account", {}).get(guild.id) is not None else settings.get("main_account")
                            for settings in user_settings}

    changed = 0
    num_changes = 0
    text = ""
    embeds = []
    for member in members:
        if member.bot:
            continue

        EvalResult = namedtuple("EvalResult", ["is_family", "roles_to_add"])

        member_accounts = discord_link_dict.get(member.id, [])
        if not member_accounts:
            continue
        member_accounts = [player_dict.get(tag) for tag in member_accounts if player_dict.get(tag) is not None]

        def mini_eval(player: coc.Player) -> EvalResult:
            is_family = False
            if player.clan is not None and player.clan.tag in clan_tags:
                is_family = True

            do_eval = True
            #if not family & they don't want to flair non family, skip
            if not is_family and not db_server.flair_non_family:
                do_eval = False

            ROLES_TO_ADD = set()
            if "townhall" in eval_types and do_eval:
                ROLES_TO_ADD.add(townhall_roles.get(player.town_hall))

            if "builderhall" in eval_types and do_eval:
                ROLES_TO_ADD.add(builderhall_roles.get(player.builder_hall))

            if "league" in eval_types and do_eval:
                league = player.league.name.split(" ")[0].lower()
                if player.league.name != "Unranked":
                    if player.league.name == "Legend League":
                        lookup = "legends_league"
                    else:
                        lookup = f"{league}_league"
                    ROLES_TO_ADD.add(league_roles.get(lookup))

            if "builder_league" in eval_types and do_eval:
                league = player.builder_base_league.name.split(" ")[0].lower()
                ROLES_TO_ADD.add(builder_league_roles.get(f"{league}_league"))

            if player.clan is not None and "clan" in eval_types:
                ROLES_TO_ADD.add(clan_member_roles.get(player.clan.tag))


            if player.clan is not None and "category" in eval_types:
                ROLES_TO_ADD.add(clan_category_roles.get(player.clan.tag))

            if player.clan is not None and db_server.leadership_eval and ("leadership" in eval_types):
                if player.role.in_game_name in ["Co-Leader", "Leader"]:
                    ROLES_TO_ADD.add(clan_leadership_roles.get(player.clan.tag))

            return EvalResult(is_family=is_family, roles_to_add=ROLES_TO_ADD)

        results = []
        family_accounts = []
        for account in member_accounts:
            result = mini_eval(player=account)
            results.append(result)
            if result.is_family:
                family_accounts.append(account)

        has_family_account = any(x.is_family for x in results)
        all_family_accounts = all(x.is_family for x in results)

        ROLES_TO_ADD = set()
        for result in results:
            ROLES_TO_ADD = ROLES_TO_ADD | result.roles_to_add

        if has_family_account and "family" in eval_types:
            ROLES_TO_ADD = ROLES_TO_ADD | family_roles
        elif "not_family" in eval_types:
            ROLES_TO_ADD = ROLES_TO_ADD | not_family_roles

        if all_family_accounts and "family" in eval_types:
            ROLES_TO_ADD = ROLES_TO_ADD | only_family_roles

        ROLES_TO_ADD.discard(None)

        NON_CLASH_ROLES = [r for r in member.roles if r.id not in ALL_CLASH_ROLES]
        CLASH_ROLES = {r.id for r in member.roles if r.id in ALL_CLASH_ROLES}

        removed = ""
        for role in CLASH_ROLES.copy():
            '''
            if they have a role they shouldnt have remove
            unless its an ignored role
            but if it is and they have a family account, ignore by skipping
            '''
            if role not in ROLES_TO_ADD:
                if role in ignored_roles:
                    if has_family_account:
                        continue
                CLASH_ROLES.discard(role)
                removed += f"<@&{role}> "

        added = ""
        for role in ROLES_TO_ADD:
            if role not in CLASH_ROLES:
                added += f"<@&{role}> "

        CLASH_ROLES = CLASH_ROLES | ROLES_TO_ADD
        FINAL_CLASH_ROLES = []
        for role in CLASH_ROLES:
            if role == guild.default_role.id:
                continue
            role = guild.get_role(role)
            if role is None or role.is_bot_managed():
                continue
            FINAL_CLASH_ROLES.append(role)

        new_name = None
        if db_server.change_nickname and "nicknames" in eval_types:
            #if they have a family account or the server allows non family to change nickname, then change it
            if has_family_account or db_server.flair_non_family:
                if member.top_role > bot_member.top_role:
                    new_name = "`Cannot Change`"
                else:
                    local_nickname_convention = db_server.nickname_convention
                    main_account = main_account_lookup.get(member.id)
                    if main_account is not None:
                        main_account = coc.utils.get(member_accounts, tag=main_account)
                    if main_account is None:
                        if len(family_accounts) >= 1:
                            main_account = sorted(family_accounts, key=lambda l: l.trophies, reverse=True)[0]
                        else:
                            main_account = sorted(member_accounts, key=lambda l: l.trophies, reverse=True)[0]

                    types = {"{player_name}": main_account.name,
                             "{player_tag}": main_account.tag,
                             "{player_townhall}": main_account.town_hall,
                             "{player_townhall_small}": create_superscript(main_account.town_hall),
                             "{player_warstars}": main_account.war_stars,
                             "{player_role}": main_account.role if main_account.role is not None else "",
                             "{player_clan}": main_account.clan.name if main_account.clan is not None else "",
                             "{player_league}": main_account.league.name,
                             }
                    for type, replace in types.items():
                        local_nickname_convention = local_nickname_convention.replace(type, str(replace))
                    new_name = local_nickname_convention

        FINAL_ROLES = FINAL_CLASH_ROLES + NON_CLASH_ROLES

        if new_name is None or new_name == member.display_name:
            new_name = "None"
        if not added:
            added = "None"
        if not removed:
            removed = "None"

        if not test:
            try:
                await member.edit(nick=new_name if new_name != "None" else member.display_name, roles=FINAL_ROLES)
            except Exception as e:
                if new_name is not None:
                    new_name = "Error"
                added = str(e)[:1000]
                removed = "Error"

        had_change = False
        for change_text, change in zip(["Added", "Removed", "Name Change"], [added, removed, new_name]):
            if len(members) >= 2 and change == "None":
                continue
            if not had_change:
                text += f"**{member.display_name}** | {member.mention}"
            had_change = True
            if change_text == "Name Change":
                text += f"\n- {change_text}: `{change}`"
            else:
                text += f"\n- {change_text}: {change}"


        if had_change and len(members) >= 2 and changed != 9:
            text += f"\n<:blanke:838574915095101470>\n"
        if had_change:
            changed += 1
            num_changes += 1

        if changed == 10 or member == members[-1]:
            embed = disnake.Embed(title=f"Eval Complete for {role_or_user.name}",
                                  description=text,
                                  color=db_server.embed_color)
            embeds.append(embed)
            text = ""
            changed = 0

    if text != "":
        text = text[:-30]
        embed = disnake.Embed(title=f"Eval Complete for {role_or_user.name}",
                              description=text,
                              color=db_server.embed_color)
        embeds.append(embed)

    if not embeds:
        embed = disnake.Embed(title=f"Eval Complete for {role_or_user.name}",
                              description="No evals needed.",
                              color=db_server.embed_color)
        embeds.append(embed)

    time_elapsed = int(time.time() - time_start)
    for embed in embeds:
        embed.set_footer(text=f"Time Elapsed: {time_elapsed} seconds, {num_changes} changes | Test: {test}")
        if guild.icon is not None:
            embed.set_author(name=f"{guild.name}", icon_url=get_guild_icon(guild))

    return embeds




async def family_role_add(database, type: str, role: disnake.Role, guild: disnake.Guild) -> disnake.Embed:
    results = await database.find_one({"$and": [
        {"role": role.id},
        {"server": guild.id}
    ]})
    if results is not None:
        return disnake.Embed(description=f"{role.mention} is already in the {type} list.",
                             color=disnake.Color.red())

    if role.is_default():
        return disnake.Embed(description=f"Cannot use the @everyone role for {type}", color=disnake.Color.red())

    await database.insert_one({
        "server": guild.id,
        "role": role.id
    })

    embed = disnake.Embed(
        description=f"{role.mention} added to the {type} list.",
        color=disnake.Color.green())
    return embed



async def family_role_remove(database, type: str, role: disnake.Role, guild: disnake.Guild) -> disnake.Embed:
    results = await database.find_one({"$and": [
        {"role": role.id},
        {"server": guild.id}
    ]})
    if results is None:
        return disnake.Embed(description=f"{role.mention} is not currently in the {type} list.",
                             color=disnake.Color.red())

    if role.is_default():
        return disnake.Embed(description=f"Cannot use the @everyone role for {type}", color=disnake.Color.red())

    await database.find_one_and_delete({"role": role.id})

    return disnake.Embed(description=f"{role.mention} removed from the {type} list.", color=disnake.Color.green())

