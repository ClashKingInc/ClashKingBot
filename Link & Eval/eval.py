import coc
from disnake.ext import commands
import disnake

from utils.components import create_components
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import CustomServer

class eval(commands.Cog, name="Eval"):
    """A couple of simple commands."""

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="eval")
    async def eval(self, ctx):
        pass

    @eval.sub_command(name="user", description="Evaluate a user's roles")
    async def eval_user(self, ctx: disnake.ApplicationCommandInteraction, user:disnake.Member, test=commands.Param(default="No", choices=["Yes", "No"]), change_nick=commands.Param(default="No", choices=["Yes", "No"])):
        await ctx.response.defer()
        perms = ctx.author.guild_permissions.manage_guild
        if ctx.author.id == self.bot.owner.id:
            perms = True

        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)



        test = (test != "No")
        if change_nick == "Yes":
            server = CustomServer(guild=ctx.guild, bot=self.bot)
            change_nick = await server.nickname_choice
        else:
            change_nick = "Off"
        changes = await self.eval_member(ctx, user, test, change_nick=change_nick)
        embed = disnake.Embed(description=f"Eval Complete for {user.mention}\n"
                                          f"Added: {changes[0]}\n"
                                          f"Removed: {changes[1]}",
                              color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

    @eval.sub_command(name="role", description="Evaluate the roles of all members in a specific role")
    async def eval_role(self, ctx, role:disnake.Role, test=commands.Param(default="No", choices=["Yes", "No"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)
        if role.id == ctx.guild.id:
            role = ctx.guild.default_role
        test = (test != "No")
        await self.eval_roles(ctx, role, test)

    @eval.sub_command(name="tag", description="Evaluate the role of the user connected to a tag")
    async def eval_tag(self, ctx: disnake.ApplicationCommandInteraction, player_tag, test=commands.Param(default="No", choices=["Yes", "No"])):
        await ctx.response.defer()
        perms = ctx.author.guild_permissions.manage_guild
        if ctx.author.id == self.bot.owner.id:
            perms = True

        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        test = (test != "No")
        player = await self.bot.getPlayer(player_tag)
        user = await self.bot.link_client.get_link(player.tag)
        if user is None:
            embed = disnake.Embed(description="Player is not linked to a discord account",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        try:
            user = await ctx.guild.fetch_member(user)
        except:
            user = None
        if user is None:
            embed = disnake.Embed(description="Player is linked but not on this server.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)


        changes = await self.eval_member(ctx, user, test, change_nick="Off")
        embed = disnake.Embed(description=f"Eval Complete for {user.mention}\n"
                                          f"Added: {changes[0]}\n"
                                          f"Removed: {changes[1]}",
                              color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

    @commands.user_command(name="Nickname", description="Change nickname of a user")
    async def auto_nick(self, ctx: disnake.ApplicationCommandInteraction, user: disnake.User):
        perms = ctx.author.guild_permissions.manage_nicknames
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Nickname` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)
        try:
            member = await ctx.guild.fetch_member(user.id)
        except:
            member = None
        if member is None:
            return await ctx.send(f"{user.name} [{user.mention}] is not a member of this server.")
        account_tags = await self.bot.get_tags(str(user.id))
        if len(account_tags) == 0:
            return await ctx.send(content=f"No accounts linked to {user.mention}", ephemeral=True)

        await ctx.response.defer(ephemeral=True)
        member = await ctx.guild.fetch_member(user.id)
        abbreviations = {}
        clan_tags = []
        all = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            tag = role.get("tag")
            clan_tags.append(tag)
            clan_abbreviation = role.get("abbreviation")
            abbreviations[tag] = clan_abbreviation

        GLOBAL_IS_FAMILY = False

        list_accounts = []
        abbreviations_to_have = []
        async for player in self.bot.coc_client.get_players(account_tags):
            list_accounts.append([player.trophies, player])

            # ignore the global if even one account is in family
            is_family_member = await self.is_in_family(player, clan_tags)
            if not GLOBAL_IS_FAMILY:
                GLOBAL_IS_FAMILY = is_family_member

            if not is_family_member:
                continue

            if abbreviations[player.clan.tag] is not None:
                abbreviations_to_have.append(abbreviations[player.clan.tag])

        abbreviations_to_have = list(set(abbreviations_to_have))
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        family_label = await server.family_label
        if family_label == "":
            family_label = []
        else:
            family_label = [family_label]
        list_of_clans = []
        for player in list_accounts:
            player = player[1]
            if player.clan is not None:
                list_of_clans.append(player.clan.name)
        list_of_clans = list(set(list_of_clans))
        abbreviations = []
        if abbreviations_to_have != []:
            abbreviations.append(", ".join(abbreviations_to_have))

        label_list = abbreviations + family_label + list_of_clans

        label_list = list(set(label_list[:25]))
        if label_list == []:
            label_list.append(ctx.guild.name)
        options = []
        for label in label_list:
            options.append(disnake.SelectOption(label=f"{label}", value=f"label_{label}"))

        stat_select = disnake.ui.Select(options=options, placeholder="Nickname Labels", min_values=1,
                                        max_values=1)

        st = disnake.ui.ActionRow()
        st.append_item(stat_select)

        options = []
        list_accounts = list_accounts[:25]
        results = sorted(list_accounts, key=lambda l: l[0], reverse=True)
        for player in results:
            player = player[1]
            options.append(disnake.SelectOption(label=f"{player.name}", value=f"{player.name}",
                                                emoji=self.bot.partial_emoji_gen(
                                                    emoji_string=self.bot.fetch_emoji(player.town_hall))))

        profile_select = disnake.ui.Select(options=options, placeholder="Account List", min_values=1,
                                           max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        all_components = [st2, st]

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        embed = disnake.Embed(description=f"Nickname change for {user.mention}")
        await ctx.edit_original_message(embed=embed, components=all_components)

        name_to_set = results[0][1].name
        label_to_set = ""

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if "label_" in res.values[0]:
                label = res.values[0].replace("label_", "")
                if label_to_set == f" | {label}":
                    label_to_set = ""
                else:
                    label_to_set = f" | {label}"
                try:
                    await member.edit(nick=f"{name_to_set}{label_to_set}")
                    await res.send(content=f"{member.mention} name changed.", ephemeral=True)
                except:
                    await res.send(
                        content=f"Could not edit {member.mention} name. Permissions error or user is above or equal to the bot's highest role.",
                        ephemeral=True)
            else:
                name_to_set = res.values[0]
                try:
                    await member.edit(nick=f"{name_to_set}{label_to_set}")
                    await res.send(content=f"{member.mention} name changed.", ephemeral=True)
                except:
                    await res.send(
                        content=f"Could not edit {member.mention} name. Permissions error or user is above or equal to the bot's highest role.",
                        ephemeral=True)

    @commands.slash_command(name="nickname", description="Change the nickname of a discord user")
    async def nickname(self, ctx: disnake.ApplicationCommandInteraction, user: disnake.User = None):
        if user is not None:
            perms = ctx.author.guild_permissions.manage_nicknames
            if not perms:
                embed = disnake.Embed(description="Command requires you to have `Manage Nickname` permissions.",
                                      color=disnake.Color.red())
                return await ctx.send(embed=embed)

        if user is None:
            user = ctx.author

        account_tags = await self.bot.get_tags(str(user.id))
        if len(account_tags) == 0:
            return await ctx.send(content=f"No accounts linked to {user.mention}", ephemeral=True)

        await ctx.response.defer(ephemeral=True)
        member = await ctx.guild.fetch_member(user.id)
        abbreviations = {}
        clan_tags = []
        all = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            tag = role.get("tag")
            clan_tags.append(tag)
            clan_abbreviation = role.get("abbreviation")
            abbreviations[tag] = clan_abbreviation

        GLOBAL_IS_FAMILY = False

        list_accounts = []
        abbreviations_to_have = []
        async for player in self.bot.coc_client.get_players(account_tags):
            list_accounts.append([player.trophies, player])

            #ignore the global if even one account is in family
            is_family_member = await self.is_in_family(player, clan_tags)
            if not GLOBAL_IS_FAMILY:
                GLOBAL_IS_FAMILY = is_family_member

            if not is_family_member:
                continue

            if abbreviations[player.clan.tag] is not None:
                abbreviations_to_have.append(abbreviations[player.clan.tag])

        abbreviations_to_have = list(set(abbreviations_to_have))
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        family_label = await server.family_label
        if family_label == "":
            family_label = []
        else:
            family_label = [family_label]
        list_of_clans = []
        for player in list_accounts:
            player = player[1]
            if player.clan is not None:
                list_of_clans.append(player.clan.name)
        list_of_clans = list(set(list_of_clans))
        abbreviations = []
        if abbreviations_to_have != []:
            abbreviations.append(", ".join(abbreviations_to_have))

        label_list = abbreviations + family_label + list_of_clans

        label_list = list(set(label_list[:25]))
        if label_list == []:
            label_list.append(ctx.guild.name)
        options = []
        for label in label_list:
            options.append(disnake.SelectOption(label=f"{label}", value=f"label_{label}"))

        stat_select = disnake.ui.Select(options=options, placeholder="Nickname Labels", min_values=1,
                                        max_values=1)

        st = disnake.ui.ActionRow()
        st.append_item(stat_select)

        options = []
        list_accounts = list_accounts[:25]
        results = sorted(list_accounts, key=lambda l: l[0], reverse=True)
        for player in results:
            player = player[1]
            options.append(disnake.SelectOption(label=f"{player.name}", value=f"{player.name}", emoji=self.bot.partial_emoji_gen(emoji_string=self.bot.fetch_emoji(player.town_hall))))

        profile_select = disnake.ui.Select(options=options, placeholder="Account List", min_values=1,
                                           max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        all_components = [st2, st]

        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        embed = disnake.Embed(description=f"Nickname change for {user.mention}")
        await ctx.edit_original_message(embed=embed, components=all_components)

        name_to_set = results[0][1].name
        label_to_set = ""

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if "label_" in res.values[0]:
                label = res.values[0].replace("label_", "")
                if label_to_set == f" | {label}":
                    label_to_set = ""
                else:
                    label_to_set = f" | {label}"
                try:
                    await member.edit(nick=f"{name_to_set}{label_to_set}")
                    await res.send(content=f"{member.mention} name changed.", ephemeral=True)
                except:
                    await res.send(
                        content=f"Could not edit {member.mention} name. Permissions error or user is above or equal to the bot's highest role.", ephemeral=True)
            else:
                name_to_set = res.values[0]
                try:
                    await member.edit(nick=f"{name_to_set}{label_to_set}")
                    await res.send(content=f"{member.mention} name changed.", ephemeral=True)
                except:
                    await res.send(content=f"Could not edit {member.mention} name. Permissions error or user is above or equal to the bot's highest role.", ephemeral=True)


    async def eval_member(self, ctx, member, test, change_nick="Off"):
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        leadership_eval = await server.leadership_eval_choice

        ignored_roles = []
        all = self.bot.ignoredroles.find({"server": ctx.guild.id})
        limit = await self.bot.ignoredroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            ignored_roles.append(r)

        family_roles = []
        all = self.bot.generalfamroles.find({"server": ctx.guild.id})
        limit = await self.bot.generalfamroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            family_roles.append(r)

        not_fam_roles = []
        all = self.bot.notfamroles.find({"server": ctx.guild.id})
        limit = await self.bot.notfamroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            not_fam_roles.append(r)

        clan_roles = []
        clan_tags = []
        clan_role_dict = {}
        abbreviations = {}
        all = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("generalRole")
            tag = role.get("tag")
            clan_abbreviation = role.get("abbreviation")
            abbreviations[tag] = clan_abbreviation
            clan_role_dict[tag] = r
            clan_tags.append(tag)
            clan_roles.append(r)

        leadership_roles = []
        clan_leadership_role_dict = {}
        all = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            tag = role.get("tag")
            r = role.get("leaderRole")
            clan_leadership_role_dict[tag] = r
            leadership_roles.append(r)


        townhall_roles = {}
        th_role_list = []
        all = self.bot.townhallroles.find({"server": ctx.guild.id})
        limit = await self.bot.townhallroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            th = role.get("th")
            th = th.replace("th","")
            th=int(th)
            townhall_roles[th] = r
            th_role_list.append(r)

        legend_roles = {}
        legend_role_list = []
        all = self.bot.legendleagueroles.find({"server": ctx.guild.id})
        limit = await self.bot.legendleagueroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            type = role.get("type")
            legend_roles[type] = r
            legend_role_list.append(r)

        ALL_CLASH_ROLES = family_roles + clan_roles + not_fam_roles + legend_role_list + th_role_list
        if leadership_eval:
            ALL_CLASH_ROLES += leadership_roles

        MASTER_ROLES = []
        #convert master role list to ids
        for m_role in member.roles:
            MASTER_ROLES.append(m_role.id)
        ROLES_TO_ADD = set()
        ROLES_SHOULD_HAVE = set()
        account_tags = await self.bot.get_tags(str(member.id))
        GLOBAL_IS_FAMILY = False

        list_accounts = []
        family_accounts = []
        abbreviations_to_have = []
        async for player in self.bot.coc_client.get_players(account_tags):
            list_accounts.append([player.trophies, player])

            #check if is a family member for 2 things - 1. to check for global roles (Not/is family) and 2. for if they shuld get roles on individual lvl
            #ignore the global if even one account is in family
            is_family_member = await self.is_in_family(player, clan_tags)
            if not GLOBAL_IS_FAMILY:
                GLOBAL_IS_FAMILY = is_family_member

            if not is_family_member:
                continue

            family_accounts.append([player.trophies, player])
            #fetch clan role using dict
            #if the user doesnt have it in their master list - add to roles they should have
            #set doesnt allow duplicates, so no check needed
            clan_role = clan_role_dict[player.clan.tag]
            if abbreviations[player.clan.tag] is not None:
                abbreviations_to_have.append(abbreviations[player.clan.tag])
            ROLES_SHOULD_HAVE.add(clan_role)
            if clan_role not in MASTER_ROLES:
                ROLES_TO_ADD.add(clan_role)

            #if server has leadership_eval turned on
            #check & add any leadership roles
            if leadership_eval:
                in_clan_role = str(player.role)
                if in_clan_role == "Co-Leader" or in_clan_role == "Leader":
                    leadership_clan_role = clan_leadership_role_dict[player.clan.tag]
                    ROLES_SHOULD_HAVE.add(leadership_clan_role)
                    if leadership_clan_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(leadership_clan_role)


            #check if they have any townhall roles setup
            #try/except because dict throws error if it doesnt exist
            #if it exists add the relevant role to the role list to add
            if bool(townhall_roles):
                try:
                    th_role = townhall_roles[player.town_hall]
                    ROLES_SHOULD_HAVE.add(th_role)
                    if th_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(th_role)
                except:
                    pass

            #check if server has any legend roles set up
            #try/except in case it doesnt exist/isnt set up
            #add to role list if found
            if bool(legend_roles):
                if str(player.league) == "Legend League":
                    try:
                        legend_role = legend_roles["legends_league"]
                        ROLES_SHOULD_HAVE.add(legend_role)
                        if legend_role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(legend_role)
                    except:
                        pass

                if player.trophies >= 6000:
                    try:
                        legend_role = legend_roles["trophies_6000"]
                        ROLES_SHOULD_HAVE.add(legend_role)
                        if legend_role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(legend_role)
                    except:
                        pass
                elif player.trophies >= 5700:
                    try:
                        legend_role = legend_roles["trophies_5700"]
                        ROLES_SHOULD_HAVE.add(legend_role)
                        if legend_role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(legend_role)
                    except:
                        pass
                elif player.trophies >= 5500:
                    try:
                        legend_role = legend_roles["trophies_5500"]
                        ROLES_SHOULD_HAVE.add(legend_role)
                        if legend_role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(legend_role)
                    except:
                        pass

        ###ALL INDIVIDUAL ROLE HAVE BEEN FOUND
        ###"Global" roles - family/not family now
        #leadership roles only get removed if a complete absense from family, so add any to the remove list
        ROLES_TO_REMOVE = set()
        if GLOBAL_IS_FAMILY:
            for role in family_roles:
                ROLES_SHOULD_HAVE.add(role)
                if role not in MASTER_ROLES:
                    ROLES_TO_ADD.add(role)
        else:
            for role in not_fam_roles:
                ROLES_SHOULD_HAVE.add(role)
                if role not in MASTER_ROLES:
                    ROLES_TO_ADD.add(role)
            if not leadership_eval:
                for role in leadership_roles:
                    if role in MASTER_ROLES:
                        ROLES_TO_REMOVE.add(role)


        #convert sets to a list
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


        # finish - add & remove what is expected

        added = ""
        removed = ""
        FINAL_ROLES_TO_ADD = []
        FINAL_ROLES_TO_REMOVE  = []
        for role in ROLES_TO_ADD:
            if role == ctx.guild.default_role.id:
                continue
            r = disnake.utils.get(ctx.guild.roles, id=role)
            if r is None:
                continue
            FINAL_ROLES_TO_ADD.append(r)
            added += r.mention +" "

        for role in ROLES_TO_REMOVE:
            if role == ctx.guild.default_role.id:
                continue
            r = disnake.utils.get(ctx.guild.roles, id=role)
            if r is None:
                continue
            FINAL_ROLES_TO_REMOVE.append(r)
            removed += r.mention + " "

        if not test:
            if FINAL_ROLES_TO_ADD != []:
                print(FINAL_ROLES_TO_ADD)
                try:
                    await member.add_roles(*FINAL_ROLES_TO_ADD)
                except:
                    added = ""
            if FINAL_ROLES_TO_REMOVE != []:
                member: disnake.Member
                print(FINAL_ROLES_TO_REMOVE)
                try:
                    await member.remove_roles(*FINAL_ROLES_TO_REMOVE)
                except:
                    removed = ""

        if len(account_tags) >= 1:
            if change_nick == "Clan Abbreviations":
                results = sorted(family_accounts, key=lambda l: l[0], reverse=True)
                abbreviations_to_have = list(set(abbreviations_to_have))
                top_account: coc.Player = results[0][1]
                abbreviations = ", ".join(abbreviations_to_have)
                abbreviations = "| " + abbreviations
                if len(abbreviations_to_have) == 0:
                    new_name = f"{top_account.name}"
                else:
                    new_name = f"{top_account.name} {abbreviations}"
                while len(new_name) > 31:
                    abbreviations_to_have = abbreviations_to_have.pop()
                    abbreviations = ", ".join(abbreviations_to_have)
                    abbreviations = "| " + abbreviations
                    if len(abbreviations_to_have) == 0:
                        new_name = f"{top_account.name}"
                    else:
                        new_name = f"{top_account.name} {abbreviations}"
                try:
                    await member.edit(nick=new_name)
                except:
                    pass
            elif change_nick == "Family Name":
                results = sorted(family_accounts, key=lambda l: l[0], reverse=True)
                family_label = await server.family_label
                top_account: coc.Player = results[0][1]
                try:
                    if family_label == "":
                        await member.edit(nick=f"{top_account.name}")
                    else:
                        await member.edit(nick=f"{top_account.name} | {family_label}")
                except:
                    pass

            if change_nick in ["Clan Abbreviations", "Family Name"] and not GLOBAL_IS_FAMILY:
                results = sorted(list_accounts, key=lambda l: l[0], reverse=True)
                top_account: coc.Player = results[0][1]
                clan_name = ""
                try:
                    clan_name = f"| {top_account.clan.name}"
                except:
                    pass

                try:
                    await member.edit(nick=f"{top_account.name} {clan_name}")
                except:
                    pass

        if added == "":
            added = "None"
        if removed == "":
            removed = "None"


        changes = [added, removed]
        return changes

    async def eval_roles(self, ctx: disnake.ApplicationCommandInteraction, evaled_role, test):
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        leadership_eval = await server.leadership_eval_choice
        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Evaluating...",
            color=disnake.Color.green())
        await ctx.send(embed=embed)
        members = evaled_role.members


        clan = await self.bot.clan_db.find_one({"generalRole": evaled_role.id})
        if clan is not None:
            embed = disnake.Embed(
                description="<a:loading:884400064313819146> Adding current clan members to eval...",
                color=disnake.Color.green())
            await ctx.edit_original_message(embed=embed)
            clanTag = clan.get("tag")
            clan = await self.bot.getClan(clanTag)
            async for player in clan.get_detailed_members():
                tag = player.tag
                member = await self.bot.link_client.get_link(tag)
                member = await self.bot.pingToMember(ctx, str(member))
                if (member not in members) and (member is not None):
                    members.append(member)

        ignored_roles = []
        all = self.bot.ignoredroles.find({"server": ctx.guild.id})
        limit = await self.bot.ignoredroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            ignored_roles.append(r)

        family_roles = []
        all = self.bot.generalfamroles.find({"server": ctx.guild.id})
        limit = await self.bot.generalfamroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            family_roles.append(r)

        not_fam_roles = []
        all = self.bot.notfamroles.find({"server": ctx.guild.id})
        limit = await self.bot.notfamroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            not_fam_roles.append(r)

        clan_roles = []
        clan_tags = []
        clan_role_dict = {}
        all = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("generalRole")
            tag = role.get("tag")
            clan_role_dict[tag] = r
            clan_tags.append(tag)
            clan_roles.append(r)

        leadership_roles = []
        clan_leadership_role_dict = {}
        all = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            tag = role.get("tag")
            r = role.get("leaderRole")
            clan_leadership_role_dict[tag] = r
            leadership_roles.append(r)

        townhall_roles = {}
        th_role_list = []
        all = self.bot.townhallroles.find({"server": ctx.guild.id})
        limit = await self.bot.townhallroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            th = role.get("th")
            th = th.replace("th", "")
            th = int(th)
            townhall_roles[th] = r
            th_role_list.append(r)

        legend_roles = {}
        legend_role_list = []
        all = self.bot.legendleagueroles.find({"server": ctx.guild.id})
        limit = await self.bot.legendleagueroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            type = role.get("type")
            legend_roles[type] = r
            legend_role_list.append(r)

        ALL_CLASH_ROLES = family_roles + clan_roles + not_fam_roles + legend_role_list + th_role_list
        if leadership_eval:
            ALL_CLASH_ROLES += leadership_roles

        text = ""
        embeds = []
        num = 0
        leng = 1
        for member in members:
            if member.bot:
                continue
            embed = disnake.Embed(
                description=f"<a:loading:884400064313819146> Evaluating role members - ({leng}/{len(members)})",
                color=disnake.Color.green())
            await ctx.edit_original_message(embed=embed)
            leng+=1
            try:
                MASTER_ROLES = []
                # convert master role list to ids
                for m_role in member.roles:
                    MASTER_ROLES.append(m_role.id)
                ROLES_TO_ADD = set()
                ROLES_SHOULD_HAVE = set()
                account_tags = await self.bot.get_tags(str(member.id))
                GLOBAL_IS_FAMILY = False

                async for player in self.bot.coc_client.get_players(account_tags):

                    # check if is a family member for 2 things - 1. to check for global roles (Not/is family) and 2. for if they shuld get roles on individual lvl
                    # ignore the global if even one account is in family
                    is_family_member = await self.is_in_family(player, clan_tags)
                    if not GLOBAL_IS_FAMILY:
                        GLOBAL_IS_FAMILY = is_family_member

                    if not is_family_member:
                        continue

                    # fetch clan role using dict
                    # if the user doesnt have it in their master list - add to roles they should have
                    # set doesnt allow duplicates, so no check needed
                    clan_role = clan_role_dict[player.clan.tag]
                    ROLES_SHOULD_HAVE.add(clan_role)
                    if clan_role not in MASTER_ROLES:
                        ROLES_TO_ADD.add(clan_role)

                    # if server has leadership_eval turned on
                    # check & add any leadership roles
                    if leadership_eval:
                        in_clan_role = str(player.role)
                        if in_clan_role == "Co-Leader" or in_clan_role == "Leader":
                            leadership_clan_role = clan_leadership_role_dict[player.clan.tag]
                            ROLES_SHOULD_HAVE.add(leadership_clan_role)
                            if leadership_clan_role not in MASTER_ROLES:
                                ROLES_TO_ADD.add(leadership_clan_role)

                    # check if they have any townhall roles setup
                    # try/except because dict throws error if it doesnt exist
                    # if it exists add the relevant role to the role list to add
                    if bool(townhall_roles):
                        try:
                            th_role = townhall_roles[player.town_hall]
                            ROLES_SHOULD_HAVE.add(th_role)
                            if th_role not in MASTER_ROLES:
                                ROLES_TO_ADD.add(th_role)
                        except:
                            pass

                    # check if server has any legend roles set up
                    # try/except in case it doesnt exist/isnt set up
                    # add to role list if found
                    if bool(legend_roles):
                        if str(player.league) == "Legend League":
                            try:
                                legend_role = legend_roles["legends_league"]
                                ROLES_SHOULD_HAVE.add(legend_role)
                                if legend_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(legend_role)
                            except:
                                pass

                        if player.trophies >= 6000:
                            try:
                                legend_role = legend_roles["trophies_6000"]
                                ROLES_SHOULD_HAVE.add(legend_role)
                                if legend_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(legend_role)
                            except:
                                pass
                        elif player.trophies >= 5700:
                            try:
                                legend_role = legend_roles["trophies_5700"]
                                ROLES_SHOULD_HAVE.add(legend_role)
                                if legend_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(legend_role)
                            except:
                                pass
                        elif player.trophies >= 5500:
                            try:
                                legend_role = legend_roles["trophies_5500"]
                                ROLES_SHOULD_HAVE.add(legend_role)
                                if legend_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(legend_role)
                            except:
                                pass

                ###ALL INDIVIDUAL ROLE HAVE BEEN FOUND
                ###"Global" roles - family/not family now
                # leadership roles only get removed if a complete absense from family, so add any to the remove list
                ROLES_TO_REMOVE = set()
                if GLOBAL_IS_FAMILY:
                    for role in family_roles:
                        ROLES_SHOULD_HAVE.add(role)
                        if role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(role)
                else:
                    for role in not_fam_roles:
                        ROLES_SHOULD_HAVE.add(role)
                        if role not in MASTER_ROLES:
                            ROLES_TO_ADD.add(role)
                    if not leadership_eval:
                        for role in leadership_roles:
                            if role in MASTER_ROLES:
                                ROLES_TO_REMOVE.add(role)

                # convert sets to a list
                ROLES_TO_ADD = list(ROLES_TO_ADD)
                ROLES_TO_REMOVE = list(ROLES_TO_REMOVE)
                ROLES_SHOULD_HAVE = list(ROLES_SHOULD_HAVE)

                for role in MASTER_ROLES:
                    isClashRole = role in ALL_CLASH_ROLES
                    ignored_role = (role in ignored_roles)
                    should_have = role in ROLES_SHOULD_HAVE
                    if (isClashRole) and (should_have is False):
                        if ignored_role:
                            if not GLOBAL_IS_FAMILY:
                                ROLES_TO_REMOVE.append(role)
                        else:
                            ROLES_TO_REMOVE.append(role)

                # finish - add & remove what is expected

                added = ""
                removed = ""
                FINAL_ROLES_TO_ADD = []
                FINAL_ROLES_TO_REMOVE = []
                for role in ROLES_TO_ADD:
                    r = ctx.guild.get_role(role)
                    if r is None:
                        continue
                    FINAL_ROLES_TO_ADD.append(r)
                    added += r.mention + " "

                for role in ROLES_TO_REMOVE:
                    r = ctx.guild.get_role(role)
                    if r is None:
                        continue
                    FINAL_ROLES_TO_REMOVE.append(r)
                    removed += r.mention + " "

                if not test:
                    if FINAL_ROLES_TO_ADD != []:
                        await member.add_roles(*FINAL_ROLES_TO_ADD)
                    if FINAL_ROLES_TO_REMOVE != []:
                        await member.remove_roles(*FINAL_ROLES_TO_REMOVE)

                if added == "":
                    added = "None"
                if removed == "":
                    removed = "None"
                changes = [added, removed]
            except:
                continue
            #print(changes)
            if (changes[0] != "None") or (changes[1] != "None"):
                text+=f"**{member.display_name}** | {member.mention}\nAdded: {changes[0]}\nRemoved: {changes[1]}\n<:blanke:838574915095101470>\n"
                num+=1
            if num == 10:
                embed = disnake.Embed(title=f"Eval Complete",
                                      description=text,
                                      color=disnake.Color.green())
                embeds.append(embed)
                text = ""
                num=0


        if text != "":
            embed = disnake.Embed(title=f"Eval Complete for {evaled_role.name}",
                                  description=text,
                                  color=disnake.Color.green())
            embeds.append(embed)

        if embeds == []:
            text = "No evals needed."
            embed = disnake.Embed(title=f"Eval Complete for {evaled_role.name}",
                                  description=text,
                                  color=disnake.Color.green())
            embeds.append(embed)

        current_page=0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)

    async def is_in_family(self, player, clan_tags):
        try:
            clan = player.clan.tag
        except:
            return False

        return clan in clan_tags






def setup(bot:  CustomClient):
    bot.add_cog(eval(bot))