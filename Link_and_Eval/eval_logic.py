import disnake
import time
import coc
import asyncio

from collections import defaultdict
from typing import List
from CustomClasses.CustomBot import CustomClient
from utils.components import create_components
from utils.constants import DEFAULT_EVAL_ROLE_TYPES, ROLE_TREATMENT_TYPES
from utils.general import get_clan_member_tags
from Exceptions.CustomExceptions import ExpiredComponents

async def eval_logic(bot: CustomClient, role_or_user, members_to_eval: List[disnake.Member],
                     test: bool, change_nick, ctx: disnake.ApplicationCommandInteraction = None,
                     guild: disnake.Guild = None, role_types_to_eval=None,
                     return_array=False, return_embed=None, role_treatment=None, reason="", auto_eval=False, auto_eval_tag=None):

    guild = ctx.guild if guild is None else guild
    #inititalization steps
    time_start = time.time()
    bot_member = await guild.getch_member(bot.user.id)
    role_types_to_eval = DEFAULT_EVAL_ROLE_TYPES if role_types_to_eval is None else role_types_to_eval
    role_treatment = ROLE_TREATMENT_TYPES if role_treatment is None else role_treatment
    await guild.fetch_roles()

    db_server = await bot.get_custom_server(guild_id=guild.id)

    ignored_roles = [role.id for role in db_server.ignored_roles]
    family_roles = [role.id for role in db_server.family_roles]
    not_fam_roles = [role.id for role in db_server.not_family_roles]
    clan_roles = [clan.member_role for clan in db_server.clans]
    clan_tags = [clan.tag for clan in db_server.clans]
    clan_role_dict = {clan.tag : clan.member_role for clan in db_server.clans}
    abbreviations = {clan.tag: clan.abbreviation for clan in db_server.clans}
    clan_to_category = {clan.tag: clan.category for clan in db_server.clans}
    leadership_roles = [clan.leader_role for clan in db_server.clans]
    clan_leadership_role_dict = {clan.tag : clan.leader_role for clan in db_server.clans}
    townhall_roles = {int(role.townhall.replace("th","")) : role.id for role in db_server.townhall_roles}
    th_role_list = [role.id for role in db_server.townhall_roles]
    bh_role_list = [role.id for role in db_server.builderhall_roles]
    builderhall_roles = {int(role.builderhall.replace("bh","")) : role.id for role in db_server.builderhall_roles}
    league_roles = {role.type : role.id for role in db_server.league_roles}
    league_role_list = [role.id for role in db_server.league_roles]
    builder_league_roles = {role.type : role.id for role in db_server.builder_league_roles}
    builder_league_role_list = [role.id for role in db_server.builder_league_roles]

    achievement_roles = {role.type : role.id for role in db_server.achievement_roles}
    achievement_role_list = [role.id for role in db_server.achievement_roles]

    status_roles = {role.type: role.id for role in db_server.status_roles}
    status_role_list = [role.id for role in db_server.status_roles]

    if not auto_eval:
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans: List[coc.Clan] = await bot.get_clans(tags=clan_tags)
        member_tags = get_clan_member_tags(clans=clans)
        last_season = bot.gen_season_date(1, as_text=False)[-1]
        this_season = bot.gen_season_date()
        top_donator_last_season = await bot.player_stats.find({"tag": {"$in": member_tags}}, {"tag": 1}).sort(f"donations.{last_season}.donated", -1).limit(1).to_list(length=1)
        top_donator_last_season = top_donator_last_season[0] if top_donator_last_season else top_donator_last_season

        top_donator_this_season = await bot.player_stats.find({"tag": {"$in": member_tags}}, {"tag": 1}).sort(f"donations.{this_season}.donated", -1).limit(1).to_list(length=1)
        top_donator_this_season = top_donator_this_season[0].get("tag") if top_donator_this_season else top_donator_this_season


    category_roles = {}
    category_role_list = []
    if db_server.category_roles is not None:
        categories = await bot.clan_db.distinct("category", filter={"server": guild.id})
        for category in categories:
            role_id = db_server.category_roles.get(f"{category}")
            if role_id is None:
                continue
            category_roles[category] = role_id
            category_role_list.append(role_id)

    #ADD THESE ROLES TO BE IGNORED, IF THEY DIDNT CHOOSE THEM TO BE EVALED
    type_to_item = {"family" : family_roles, "not_family" : not_fam_roles, "clan" : clan_roles, "leadership" : leadership_roles, "townhall" : th_role_list,
                    "builderhall" : bh_role_list, "league" : league_role_list, "category" : category_role_list, "builder_league" : builder_league_role_list,
                    "achievement" : achievement_role_list, "status" : status_role_list}

    for eval_type in DEFAULT_EVAL_ROLE_TYPES:
        if eval_type == "nicknames":
            continue
        if eval_type not in role_types_to_eval:
            ignored_roles += type_to_item.get(eval_type)

    ALL_CLASH_ROLES = family_roles + clan_roles + not_fam_roles + league_role_list + th_role_list + category_role_list + \
        bh_role_list + builder_league_role_list + achievement_role_list + status_role_list

    if "leadership" in role_types_to_eval:
        if db_server.leadership_eval:
            ALL_CLASH_ROLES += leadership_roles

    text = ""
    num = 0
    embeds = []
    if ctx is not None:
        msg = await ctx.original_message()
        embed = disnake.Embed(
            description=f"<a:loading:884400064313819146> Fetching discord links for {len(members_to_eval)} users.",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)
    all_discord_links = await bot.link_client.get_many_linked_players(*[member.id for member in members_to_eval if member is not None])
    discord_link_dict = defaultdict(list)
    all_tags = []
    for player_tag, discord_id in all_discord_links:
        all_tags.append(player_tag)
        discord_link_dict[discord_id].append(player_tag)

    embed = disnake.Embed(
        description=f"<a:loading:884400064313819146> Fetching {len(all_tags)} players for eval.",
        color=disnake.Color.green())
    if ctx is not None:
        await ctx.edit_original_message(embed=embed)
    if auto_eval and (isinstance(role_or_user, disnake.User) or isinstance(role_or_user, disnake.Member)):
        fresh = await bot.getPlayer(auto_eval_tag, custom=True)
        all_tags.remove(auto_eval_tag)
        all_players = await bot.get_players(tags=all_tags, use_cache=(len(all_tags) >= 10), custom=True)
        all_players += [fresh]
    else:
        all_players = await bot.get_players(tags=all_tags, use_cache=(len(all_tags) >= 10), custom=True)
    player_dict = {}
    for player in all_players:
        player_dict[player.tag] = player
    num_changes = 0

    tasks = 0
    for count, member in enumerate(members_to_eval, 1):
        if member is None or member.bot:
            continue
        if count % 10 == 0:
            embed = disnake.Embed(
                description=f"<a:loading:884400064313819146> Gathering eval changes for {role_or_user.mention} - ({count}/{len(members_to_eval)})",
                color=disnake.Color.green())
            if ctx is not None:
                if ctx.is_expired():
                    await msg.edit(embed=embed)
                else:
                    await ctx.edit_original_message(embed=embed)
        # try:
        MASTER_ROLES = []
        # convert master role list to ids
        for m_role in member.roles:
            MASTER_ROLES.append(m_role.id)
        ROLES_TO_ADD = set()
        ROLES_SHOULD_HAVE = set()

        GLOBAL_IS_FAMILY = False
        list_accounts = []
        family_accounts = []
        abbreviations_to_have = []

        account_tags = discord_link_dict[member.id]
        players = [player_dict.get(tag) for tag in account_tags]

        for player in players:
            if isinstance(player, coc.errors.NotFound) or player is None:
                continue
            list_accounts.append([player.trophies, player])

            # check if is a family member for 2 things - 1. to check for global roles (Not/is family) and 2. for if they shuld get roles on individual lvl
            # ignore the global if even one account is in family
            is_family_member = await is_in_family(player, clan_tags)
            #once one family member found, mark as a family member
            if not GLOBAL_IS_FAMILY:
                GLOBAL_IS_FAMILY = is_family_member

            if not is_family_member and not db_server.eval_non_members:
                continue
            # check if they have any townhall roles setup
            # try/except because dict throws error if it doesnt exist
            # if it exists add the relevant role to the role list to add
            if "townhall" in role_types_to_eval:
                if bool(townhall_roles) and townhall_roles.get(player.town_hall) is not None:
                    th_role = townhall_roles[player.town_hall]
                    ROLES_SHOULD_HAVE.add(th_role)
                    if th_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(th_role)


            # check if they have any builderhall roles set up
            # try except because dict throws error if it doesnt exist
            # also because they could have no builder hall
            # if it exists on both ends, add the role to the role list to add
            if "builderhall" in role_types_to_eval:
                if bool(builderhall_roles) and builderhall_roles.get(player.builder_hall) is not None:
                    bh_role = builderhall_roles[player.builder_hall]
                    ROLES_SHOULD_HAVE.add(bh_role)
                    if bh_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(bh_role)

            # check if server has any league roles set up
            # try/except in case it doesnt exist/isnt set up
            # add to role list if found
            if "league" in role_types_to_eval:
                league = str(player.league).split(" ")
                league = league[0].lower()
                if str(player.league) != "Unranked" and league_roles.get(f"{league}_league") is not None:
                    league_role = league_roles[f"{league}_league"]
                    ROLES_SHOULD_HAVE.add(league_role)
                    if league_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(league_role)

                if str(player.league) == "Legend League" and league_roles.get("legends_league") is not None:
                    legend_role = league_roles["legends_league"]
                    ROLES_SHOULD_HAVE.add(legend_role)
                    if legend_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(legend_role)


                if player.trophies >= 6000 and league_roles.get("trophies_6000") is not None:
                        legend_role = league_roles["trophies_6000"]
                        ROLES_SHOULD_HAVE.add(legend_role)
                        if legend_role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(legend_role)

                elif player.trophies >= 5700 and league_roles.get("trophies_5700") is not None:
                    try:
                        legend_role = league_roles["trophies_5700"]
                        ROLES_SHOULD_HAVE.add(legend_role)
                        if legend_role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(legend_role)
                    except:
                        pass

                elif player.trophies >= 5500 and league_roles.get("trophies_5500") is not None:
                    try:
                        legend_role = league_roles["trophies_5500"]
                        ROLES_SHOULD_HAVE.add(legend_role)
                        if legend_role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(legend_role)
                    except:
                        pass

            if "builder_league" in role_types_to_eval:
                league = player.builder_league.name.split(" ")
                league = league[0].lower()
                league_role = builder_league_roles.get(f"{league}_league")
                if league_role is not None:
                    ROLES_SHOULD_HAVE.add(league_role)
                    if league_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(league_role)

            if not is_family_member:
                continue

            family_accounts.append([player.trophies, player])
            # fetch clan role using dict
            # if the user doesnt have it in their master list - add to roles they should have
            # set doesnt allow duplicates, so no check needed
            if "clan" in role_types_to_eval:
                clan_role = clan_role_dict[player.clan.tag]
                if abbreviations[player.clan.tag] is not None:
                    abbreviations_to_have.append(abbreviations[player.clan.tag])
                ROLES_SHOULD_HAVE.add(clan_role)
                if clan_role not in MASTER_ROLES:
                    ROLES_TO_ADD.add(clan_role)

            if "category" in role_types_to_eval:
                if bool(category_roles):
                    try:
                        category_role = category_roles[clan_to_category[player.clan.tag]]
                        ROLES_SHOULD_HAVE.add(category_role)
                        if category_role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(category_role)
                    except:
                        pass

            if "achievement" in role_types_to_eval and not auto_eval:
                if player.donos().donated >= 10000 and achievement_roles.get("donos_10000") is not None:
                    dono_role = achievement_roles.get("donos_10000")
                    ROLES_SHOULD_HAVE.add(dono_role)
                    if dono_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(dono_role)

                if player.donos().donated >= 25000 and achievement_roles.get("donos_25000") is not None:
                    dono_role = achievement_roles.get("donos_25000")
                    ROLES_SHOULD_HAVE.add(dono_role)
                    if dono_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(dono_role)


                if player.tag == top_donator_last_season and achievement_roles.get("top_donator_last_season") is not None:
                    dono_role = achievement_roles.get("top_donator_last_season")
                    ROLES_SHOULD_HAVE.add(dono_role)
                    if dono_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(dono_role)

                if player.tag == top_donator_this_season and achievement_roles.get("top_donator_ongoing_season") is not None:
                    dono_role = achievement_roles.get("top_donator_ongoing_season")
                    ROLES_SHOULD_HAVE.add(dono_role)
                    if dono_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(dono_role)

            # if server has leadership_eval turned on
            # check & add any leadership roles
            if db_server.leadership_eval and ("leadership" in role_types_to_eval):
                in_clan_role = str(player.role)
                if in_clan_role == "Co-Leader" or in_clan_role == "Leader":
                    leadership_clan_role = clan_leadership_role_dict[player.clan.tag]
                    ROLES_SHOULD_HAVE.add(leadership_clan_role)
                    if leadership_clan_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(leadership_clan_role)

        ###ALL INDIVIDUAL ROLE HAVE BEEN FOUND
        ###"Global" roles - family/not family now
        # leadership roles only get removed if a complete absense from family, so add any to the remove list
        ROLES_TO_REMOVE = set()
        if GLOBAL_IS_FAMILY and "family" in role_types_to_eval:
            for role in family_roles:
                ROLES_SHOULD_HAVE.add(role)
                if role not in MASTER_ROLES:
                    ROLES_TO_ADD.add(role)
        elif not GLOBAL_IS_FAMILY:
            for role in not_fam_roles:
                if "not_family" not in role_types_to_eval:
                    continue
                ROLES_SHOULD_HAVE.add(role)
                if role not in MASTER_ROLES:
                    ROLES_TO_ADD.add(role)
            if "leadership" in role_types_to_eval:
                if db_server.leadership_eval:
                    for role in leadership_roles:
                        if role in MASTER_ROLES:
                            ROLES_TO_REMOVE.add(role)

        # convert sets to a list
        ROLES_TO_ADD = list(ROLES_TO_ADD)
        ROLES_TO_REMOVE = list(ROLES_TO_REMOVE)
        ROLES_SHOULD_HAVE = list(ROLES_SHOULD_HAVE)

        for role in MASTER_ROLES:
            isClashRole = role in ALL_CLASH_ROLES
            ignored_role = role in ignored_roles
            should_have = role in ROLES_SHOULD_HAVE
            if (isClashRole) and (ignored_role is False) and (should_have is False):
                if ignored_role:
                    if not GLOBAL_IS_FAMILY:
                        ROLES_TO_REMOVE.append(role)
                else:
                    ROLES_TO_REMOVE.append(role)

        added = ""
        removed = ""
        FINAL_ROLES_TO_ADD = []
        FINAL_ROLES_TO_REMOVE = []
        for role in ROLES_TO_ADD:
            if role == guild.default_role.id:
                continue
            r: disnake.Role = guild.get_role(role)
            if r is None or r.is_bot_managed():
                continue
            FINAL_ROLES_TO_ADD.append(r)
            added += r.mention + " "

        for role in ROLES_TO_REMOVE:
            if role == guild.default_role.id:
                continue
            r: disnake.Role = guild.get_role(role)
            if r is None or r.is_bot_managed():
                continue
            FINAL_ROLES_TO_REMOVE.append(r)
            removed += r.mention + " "

        current_member_roles = member.roles

        if FINAL_ROLES_TO_ADD != [] and ("Add" in role_treatment):
            invalid = not bot_member.guild_permissions.manage_roles
            if invalid:
                added = "Missing manage_roles perm"
            else:
                for r in FINAL_ROLES_TO_ADD:
                    if r > bot_member.top_role:
                        invalid = True
                        break
                if not invalid:
                    current_member_roles += FINAL_ROLES_TO_ADD
                else:
                    added = "Can not add role(s)"

        if FINAL_ROLES_TO_REMOVE != [] and ("Remove" in role_treatment):
            member: disnake.Member
            invalid = not bot_member.guild_permissions.manage_roles
            if invalid:
                removed = "Missing manage_roles perm"
            else:
                for r in FINAL_ROLES_TO_ADD:
                    if r > bot_member.top_role:
                        invalid = True
                        break
                if not invalid:
                    for role in FINAL_ROLES_TO_REMOVE:
                        if role not in FINAL_ROLES_TO_ADD:
                            try:
                                current_member_roles.remove(role)
                            except:
                                pass
                else:
                    removed = "Can not remove role(s)"
        name_changes = "None"
        new_name = None
        # role_types_to_eval.remove("nicknames")
        if "nicknames" in role_types_to_eval:
            if member.top_role > bot_member.top_role or not bot_member.guild_permissions.manage_nicknames:
                name_changes = "`Cannot Change`"
            else:
                if len(family_accounts) >= 1:
                    if change_nick == "Clan Abbreviations":
                        results = sorted(family_accounts, key=lambda l: l[0], reverse=True)
                        abbreviations_to_have = list(set(abbreviations_to_have))
                        top_account: coc.Player = results[0][1]
                        _abbreviations = ", ".join(abbreviations_to_have)
                        _abbreviations = "| " + _abbreviations
                        if len(abbreviations_to_have) == 0:
                            new_name = f"{top_account.name}"
                        else:
                            new_name = f"{top_account.name} {_abbreviations}"
                        while len(new_name) > 31:
                            to_remove = max(abbreviations_to_have, key=len)
                            abbreviations_to_have.remove(to_remove)
                            _abbreviations = ", ".join(abbreviations_to_have)
                            _abbreviations = "| " + _abbreviations
                            if len(abbreviations_to_have) == 0:
                                new_name = f"{top_account.name}"
                            else:
                                new_name = f"{top_account.name} {_abbreviations}"
                            name_changes = f"`{new_name}`"
                    elif change_nick == "Family Name":
                        results = sorted(family_accounts, key=lambda l: l[0], reverse=True)
                        family_label = db_server.family_label
                        top_account: coc.Player = results[0][1]

                        if family_label == "":
                            new_name =f"{top_account.name}"
                            name_changes = f"`{top_account.name}`"
                        else:
                            new_name = f"{top_account.name} | {family_label}"
                            name_changes = f"`{top_account.name} | {family_label}`"

                if change_nick in ["Clan Abbreviations", "Family Name"] and not GLOBAL_IS_FAMILY and len(list_accounts) >= 1:
                    results = sorted(list_accounts, key=lambda l: l[0], reverse=True)
                    top_account: coc.Player = results[0][1]
                    clan_name = ""
                    try:
                        clan_name = f"| {top_account.clan.name}"
                    except:
                        pass
                    new_name = f"{top_account.name} {clan_name}"
                    name_changes = f"`{top_account.name} {clan_name}`"

        old_name = member.display_name
        if not test and (new_name or FINAL_ROLES_TO_ADD or FINAL_ROLES_TO_REMOVE):
            try:
                if new_name is None and current_member_roles == member.roles:
                    pass
                elif new_name is not None:
                    await member.edit(nick=new_name, roles=current_member_roles)
                elif new_name is None:
                    await member.edit(roles=current_member_roles)
                tasks += 1
            except:
                name_changes = "Permissions Error"
                added = "Permissions Error"
                removed = "Permissions Error"

        if name_changes[1:-1] == old_name:
            name_changes = "None"
        if added == "":
            added = "None"
        if removed == "":
            removed = "None"

        changes = [added, removed, name_changes]
        if return_array:
            return changes

        if ((changes[0] != "None") or (changes[1] != "None") or (changes[2] != "None")) or len(members_to_eval) >= 1:
            if changes[0] == "None" and changes[1] == "None" and changes[2] == "None" and len(members_to_eval) >= 2:
                pass
            else:
                text += f"**{member.display_name}** | {member.mention}"
                if changes[0] != "None" or len(members_to_eval) == 1:
                    text += f"\n- Added: {changes[0]}"
                if changes[1] != "None" or len(members_to_eval) == 1:
                    text += f"\n- Removed: {changes[1]}"
                if changes[2] != "None":
                    text += f"\n- Nick Change: {changes[2]}"
                if len(members_to_eval) >= 2 and num != 9:
                    text += f"\n<:blanke:838574915095101470>\n"
                num += 1
                num_changes += 1
        if num == 10 or len(members_to_eval) == 1:
            embed = disnake.Embed(title=f"Eval Complete",
                                  description=text,
                                  color=disnake.Color.green())
            embeds.append(embed)
            text = ""
            num = 0

    if text != "":
        text = text[:-30]
        embed = disnake.Embed(title=f"Eval Complete for {role_or_user.name}",
                              description=text,
                              color=disnake.Color.green())
        embeds.append(embed)

    if embeds == []:
        text = "No evals needed."
        embed = disnake.Embed(title=f"Eval Complete for {role_or_user.name}",
                              description=text,
                              color=disnake.Color.green())
        embeds.append(embed)

    embed = disnake.Embed(
        description=f"<a:loading:884400064313819146> Completing {tasks} Eval Changes, Approx {int(tasks % 60)} Minutes...",
        color=disnake.Color.green())
    if ctx is not None and not return_embed:
        await ctx.edit_original_message(embed=embed)

    if return_embed:
        return embeds[0]

    time_elapsed = int(time.time() - time_start)
    for embed in embeds:
        embed.set_footer(text=f"Time Elapsed: {time_elapsed} seconds,  {num_changes} changes | Test: {test}")
        if guild.icon is not None:
            embed.set_author(name=f"{guild.name}", icon_url=guild.icon.url)

    current_page = 0
    await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
    msg = await ctx.original_message()

    def check(res: disnake.MessageInteraction):
        return res.message.id == msg.id

    while True:
        try:
            res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check,
                                                                      timeout=600)
        except:
            raise ExpiredComponents

        await res.response.defer()
        if res.data.custom_id == "Previous":
            current_page -= 1
            await res.edit_original_message(embed=embeds[current_page],
                                            components=create_components(current_page, embeds, True))

        elif res.data.custom_id == "Next":
            current_page += 1
            await res.edit_original_message(embed=embeds[current_page],
                                            components=create_components(current_page, embeds, True))

        elif res.data.custom_id == "Print":
            await msg.delete()
            for embed in embeds:
                await ctx.channel.send(embed=embed)


async def is_in_family(player, clan_tags):
    try:
        clan = player.clan.tag
    except:
        return False

    return clan in clan_tags