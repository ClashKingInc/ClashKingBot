import time
import coc
from disnake.ext import commands
import disnake
import asyncio

from main import check_commands
from utils.components import create_components
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import CustomServer
from typing import List
from collections import defaultdict

class eval(commands.Cog, name="Eval"):
    """A couple of simple commands."""

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="eval")
    async def eval(self, ctx):
        pass

    @eval.sub_command(name="user", description="Evaluate a user's roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def eval_user(self, ctx: disnake.ApplicationCommandInteraction, user:disnake.Member, test=commands.Param(default="No", choices=["Yes", "No"])):
        await ctx.response.defer()
        test = (test != "No")
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        change_nick = await server.nickname_choice
        changes = await self.eval_logic(ctx=ctx, members_to_eval=[user], role_or_user=user, test=test, change_nick=change_nick)

    @eval.sub_command(name="role", description="Evaluate the roles of all members in a specific role")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def eval_role(self, ctx: disnake.ApplicationCommandInteraction, role:disnake.Role, test=commands.Param(default="No", choices=["Yes", "No"]), advanced_mode = commands.Param(default="No", choices=["Yes", "No"])):
        if role.id == ctx.guild.id:
            role = ctx.guild.default_role
        test = (test != "No")
        await ctx.response.defer()
        default_eval = ["family" , "not_family", "clan", "leadership", "townhall", "builderhall", "category", "league", "nicknames"]
        if advanced_mode == "Yes":
            options = []
            for option in default_eval:
                value = option
                option = option.capitalize()
                if option == "Not_family":
                    option = "Not Family"
                options.append(disnake.SelectOption(label=option, value=value))

            select = disnake.ui.Select(
                options=options,
                placeholder="Eval Options",
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            embed =disnake.Embed(description="**Choose which role types you would like to eval:**", color=disnake.Color.green())
            msg = await ctx.edit_original_message(embed=embed, components=dropdown)
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", timeout=600)
            except:
                return
            default_eval = res.values
            await res.response.edit_message(components = [])
        else:
            default_eval = None
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        change_nick = await server.nickname_choice
        members = role.members
        clan = await self.bot.clan_db.find_one({"generalRole": role.id})
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
        await self.eval_logic(ctx=ctx, members_to_eval=members, role_or_user=role, test=test, change_nick=change_nick, role_types_to_eval=default_eval)

    @eval.sub_command(name="tag", description="Evaluate the role of the user connected to a tag")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def eval_tag(self, ctx: disnake.ApplicationCommandInteraction, player_tag, test=commands.Param(default="No", choices=["Yes", "No"])):
        await ctx.response.defer()

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

        server = CustomServer(guild=ctx.guild, bot=self.bot)
        change_nick = await server.nickname_choice
        await self.eval_logic(ctx=ctx, members_to_eval=[user], role_or_user=user, test=test,
                                        change_nick=change_nick)

    @eval.sub_command(name="settings", description="Change settings for autoeval")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def eval_settings(self, ctx: disnake.ApplicationCommandInteraction, options = commands.Param(choices=["Blacklist Roles", "Role Treatment", "Nickname Change"])):
        pass


    #SETTINGS
    @eval.sub_command_group(name="family-roles")
    async def family_roles(self, ctx):
        pass

    @eval.sub_command_group(name="townhall-roles")
    async def townhall_roles(self, ctx):
        pass

    @eval.sub_command_group(name="league-roles")
    async def league_roles(self, ctx):
        pass

    @eval.sub_command_group(name="builderhall-roles")
    async def builderhall_roles(self, ctx):
        pass

    @eval.sub_command_group(name="builder-league-roles")
    async def builder_league_roles(self, ctx):
        pass

    @eval.sub_command_group(name="achievement-roles")
    async def achievement_roles(self, ctx):
        pass

    @eval.sub_command_group(name="status-roles")
    async def status_roles(self, ctx):
        pass

    @eval.sub_command(name="role-list", description="List of eval affiliated roles for this server")
    async def eval_role_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

        family_roles = await self.bot.generalfamroles.find({"server": ctx.guild.id}).to_list(length=100)
        not_family_roles = await self.bot.notfamroles.find({"server": ctx.guild.id}).to_list(length=100)
        ignored_roles = await self.bot.ignoredroles.find({"server": ctx.guild.id}).to_list(length=100)

        list_roles = [family_roles, not_family_roles, ignored_roles]
        role_names = ["Only-Family Roles", "Not-Family Roles", "Ignored Roles"]

        embed = disnake.Embed(title=f"{ctx.guild.name} Family Role List", color=disnake.Color.green())
        for role_list, role_name in zip(list_roles, role_names):
            text = ""
            for result in role_list:
                role = ctx.guild.get_role(result.get("role"))
                if role is None:
                    continue
                text += f"{role.mention}\n"
            if text == "":
                text = "No Roles"
            embed.add_field(name=f"**{role_name}**", value=text)

        list_ths = ""
        all = await self.bot.townhallroles.find({"server": ctx.guild.id}).to_list(length=None)
        all = sorted(all, key= lambda x : int(x.get("th")[2:]))
        for role in all:
            roleid = role.get("role")
            th = role.get("th")
            list_ths += f"{th.capitalize()}: <@&{roleid}>\n"

        if list_ths == "":
            list_ths = "None Set"
        embed.add_field(name=f"**Townhall Roles**", value=list_ths)

        list_ths = ""
        all = await self.bot.builderhallroles.find({"server": ctx.guild.id}).to_list(length=None)
        all = sorted(all, key=lambda x: int(x.get("bh")[2:]))
        for role in all:
            roleid = role.get("role")
            th = role.get("bh")
            list_ths += f"{th.capitalize()}: <@&{roleid}>\n"

        if list_ths == "":
            list_ths = "None Set"
        embed.add_field(name=f"**Builderhall Roles**", value=list_ths)

        list = ""
        all = await self.bot.legendleagueroles.find({"server": ctx.guild.id}).to_list(length=None)
        for role in all:
            roleid = role.get("role")
            type = role.get("type")
            type = type.split("_")[0].capitalize() + " " + type.split("_")[1].capitalize()
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "None Set"
        embed.add_field(name=f"**League & Trophy Roles**", value=list)

        list = ""
        all = await self.bot.builderleagueroles.find({"server": ctx.guild.id}).to_list(length=None)
        for role in all:
            roleid = role.get("role")
            type = role.get("type")
            type = type.split("_")[0].capitalize() + " " + type.split("_")[1].capitalize()
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "None Set"
        embed.add_field(name=f"**Builder League Roles**", value=list)


        list = ""
        all = await self.bot.statusroles.find({"server": ctx.guild.id}).to_list(length=None)
        for role in all:
            roleid = role.get("role")
            type = role.get("type")
            type = type.split("_")[0].capitalize() + " " + type.split("_")[1].capitalize()
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "None Set"
        embed.add_field(name=f"**Status Roles**", value=list)

        list = ""
        all = await self.bot.achievementroles.find({"server": ctx.guild.id}).to_list(length=None)
        for role in all:
            roleid = role.get("role")
            type = role.get("type")
            type = type.split("_")[0].capitalize() + " " + type.split("_")[1].capitalize()
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "None Set"
        embed.add_field(name=f"**Achievement Roles**", value=list)

        await ctx.edit_original_message(embed=embed)


    @eval.sub_command(name="role-remove", description="Remove an eval affiliated role")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def eval_role_remove(self, ctx: disnake.ApplicationCommandInteraction,
                               townhall: str = commands.Param(default=None, choices=["th7", "th8", "th9", "th10", "th11", "th12", "th13", "th14", "th15"]),
                               builderhall: str = commands.Param(default=None, choices=["bh3", "bh4", "bh5", "bh6", "bh7", "bh8", "bh9", "bh10"]),
                               league_role: str = commands.Param(default=None,
                                   choices=["bronze_league", "silver_league", "gold_league", "crystal_league",
                                            "master_league", "champion_league", "titan_league",
                                            "legends_league", "trophies_5500", "trophies_5700", "trophies_6000"]),
                               builder_league: str = commands.Param(default=None, choices=["wood_league", "clay_league", "stone_league", "copper_league", "brass_league", "iron_league",
                                        "steel_league", "titanium_league", "platinum_league", "emerald_league", "ruby_league", "diamond_league"]),
                               status_roles: str = commands.Param(default=None, choices=["one_month", "two_months", "three_months", "six_months", "nine_months", "one_year"]),
                               achievement_roles: str = commands.Param(default=None, choices=["donos_10000", "donos_25000", "top_donator_last_season", "top_donator_ongoing_season", "top_activity_last_season", "top_activity_current_season"])
                               ):
        await ctx.response.defer()

        role_types = [townhall, builderhall, league_role, builder_league, status_roles, achievement_roles]
        if role_types.count(None) == len(role_types):
            return await ctx.send("Must provide at least one role type to remove!")

        removed_text = ""
        if townhall:
            results = await self.bot.townhallroles.find_one({"$and": [
                {"th": f"{townhall}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That townhall does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.townhallroles.find_one_and_delete({"$and": [
                    {"th": f"{townhall}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{townhall.capitalize()} eval role removed - <@&{mention}>\n"

        if builderhall:
            results = await self.bot.builderhallroles.find_one({"$and": [
                {"th": f"{builderhall}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That builderhall does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.builderhallroles.find_one_and_delete({"$and": [
                    {"th": f"{builderhall}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{builderhall.capitalize()} eval role removed - <@&{mention}>\n"

        if league_role:
            results = await self.bot.legendleagueroles.find_one({"$and": [
                {"type": f"{league_role}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That league role type does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.legendleagueroles.find_one_and_delete({"$and": [
                    {"type": f"{league_role}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{league_role} eval role removed - <@&{mention}>\n"

        if builder_league:
            results = await self.bot.builderleagueroles.find_one({"$and": [
                {"type": f"{builder_league}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That league role type does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.builderleagueroles.find_one_and_delete({"$and": [
                    {"type": f"{builder_league}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{builder_league} eval role removed - <@&{mention}>\n"

        if status_roles:
            results = await self.bot.statusroles.find_one({"$and": [
                {"type": f"{status_roles}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That status role type does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.statusroles.find_one_and_delete({"$and": [
                    {"type": f"{status_roles}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{status_roles} eval role removed - <@&{mention}>\n"

        if achievement_roles:
            results = await self.bot.statusroles.find_one({"$and": [
                {"type": f"{achievement_roles}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That achievement role type does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.statusroles.find_one_and_delete({"$and": [
                    {"type": f"{achievement_roles}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{achievement_roles} eval role removed - <@&{mention}>\n"

        embed = disnake.Embed(title="Eval Role Removals", description=removed_text, color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)



    @family_roles.sub_command(name="add", description="Add Family Based Eval Roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def family_roles_add(self, ctx: disnake.ApplicationCommandInteraction,
                               type=commands.Param(choices=["Only-Family Roles", "Not-Family Roles", "Ignored Roles"]),
                               role: disnake.Role = commands.Param(name="role")):

        await ctx.response.defer()
        if type == "Only-Family Roles":
            database = self.bot.generalfamroles
        elif type == "Not-Family Roles":
            database = self.bot.notfamroles
        elif type == "Ignored Roles":
            database = self.bot.ignoredroles

        embed = await self.family_role_add(database=database, role=role, guild=ctx.guild, type=type)

        await ctx.edit_original_message(embed=embed)

    @family_roles.sub_command(name="remove", description="Remove Family Based Eval Roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def family_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, type=commands.Param(
        choices=["Only-Family Roles", "Not-Family Roles", "Ignored Roles"]),
                                  role: disnake.Role = commands.Param(name="role")):

        await ctx.response.defer()
        if type == "Only-Family Roles":
            database = self.bot.generalfamroles
        elif type == "Not-Family Roles":
            database = self.bot.notfamroles
        elif type == "Ignored Roles":
            database = self.bot.ignoredroles

        embed = await self.family_role_remove(database=database, role=role, guild=ctx.guild, type=type)
        await ctx.edit_original_message(embed=embed)

    async def family_role_add(self, database, type: str, role: disnake.Role, guild: disnake.Guild) -> disnake.Embed:
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

    async def family_role_remove(self, database, type: str, role: disnake.Role, guild: disnake.Guild) -> disnake.Embed:
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



    ###Townhall Roles Section
    @townhall_roles.sub_command(name="set", description="Sets roles to add for townhall levels 7 and up")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def townhall_roles_set(self, ctx: disnake.ApplicationCommandInteraction, th7: disnake.Role = None,
                                 th8: disnake.Role = None, th9: disnake.Role = None,
                                 th10: disnake.Role = None, th11: disnake.Role = None, th12: disnake.Role = None,
                                 th13: disnake.Role = None, th14: disnake.Role = None, th15: disnake.Role = None):

        if th7 is None and th8 is None and th9 is None and th10 is None and th11 is None and th12 is None and th13 is None and th14 is None and th15 is None:
            return await ctx.send("Please provide a role for at least 1 townhall level.")

        roles_updated = ""

        if th7 is not None:
            roles_updated += f"TH7: {th7.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th7.id},
                {"th": "th7"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th7.id,
                     "th": "th7",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th7"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th7.id}})
        if th8 is not None:
            roles_updated += f"TH8: {th8.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th8.id},
                {"th": "th8"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th8.id,
                     "th": "th8",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th8"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th8.id}})
        if th9 is not None:
            roles_updated += f"TH9: {th9.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th9.id},
                {"th": "th9"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th9.id,
                     "th": "th9",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th9"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th9.id}})
        if th10 is not None:
            roles_updated += f"TH10: {th10.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th10.id},
                {"th": "th10"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th10.id,
                     "th": "th10",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th10"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th10.id}})
        if th11 is not None:
            roles_updated += f"TH11: {th11.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th11.id},
                {"th": "th11"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th11.id,
                     "th": "th11",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th11"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th11.id}})
        if th12 is not None:
            roles_updated += f"TH12: {th12.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th12.id},
                {"th": "th12"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th12.id,
                     "th": "th12",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th12"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th12.id}})
        if th13 is not None:
            roles_updated += f"TH13: {th13.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th13.id},
                {"th": "th13"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th13.id,
                     "th": "th13",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th13"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th13.id}})
        if th14 is not None:
            roles_updated += f"TH14: {th14.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th14.id},
                {"th": "th14"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th14.id,
                     "th": "th14",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th14"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th14.id}})
        if th15 is not None:
            roles_updated += f"TH15: {th15.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th15.id},
                {"th": "th15"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th15.id,
                     "th": "th15",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th15"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th15.id}})

        embed = disnake.Embed(title="**Townhall Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)


    ###Builderhall Roles Section
    @builderhall_roles.sub_command(name="set", description="Sets roles to add for builderhall levels 3 and up")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def builderhall_roles_set(self, ctx: disnake.ApplicationCommandInteraction, bh3: disnake.Role = None,
                                    bh4: disnake.Role = None, bh5: disnake.Role = None,
                                    bh6: disnake.Role = None, bh7: disnake.Role = None, bh8: disnake.Role = None,
                                    bh9: disnake.Role = None, bh10: disnake.Role = None):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if bh3 is None and bh4 is None and bh5 is None and bh6 is None and bh7 is None and bh8 is None and bh9 is None and bh10 is None:
            return await ctx.send("Please provide a role for at least 1 builderhall level.")

        roles_updated = ""

        spot_to_text = ["bh3", "bh4", "bh5", "bh6", "bh7", "bh8", "bh9", "bh10"]
        list_roles = [bh3, bh4, bh5, bh6, bh7, bh8, bh9, bh10]

        for count, role in enumerate(list_roles):
            if role is None:
                continue
            role_text = spot_to_text[count]
            roles_updated += f"{role_text.upper()}: {role.mention}\n"
            results = await self.bot.builderhallroles.find_one({"$and": [
                {"role": role.id},
                {"bh": f"{role_text}"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.builderhallroles.insert_one(
                    {"role": role.id,
                     "bh": f"{role_text}",
                     "server": ctx.guild.id})
            else:
                await self.bot.builderhallroles.update_one({"$and": [
                    {"bh": f"{role_text}"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": role.id}})

        embed = disnake.Embed(title="**Builderhall Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)


    ###League Roles Section
    @league_roles.sub_command(name="set", description="Sets roles to add for leagues")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def league_roles_set(self, ctx: disnake.ApplicationCommandInteraction, bronze_league: disnake.Role = None,
                               silver_league: disnake.Role = None, gold_league: disnake.Role = None,
                               crystal_league: disnake.Role = None, master_league: disnake.Role = None,
                               champion_league: disnake.Role = None, titan_league: disnake.Role = None,
                               legends_league: disnake.Role = None, trophies_5500: disnake.Role = None,
                               trophies_5700: disnake.Role = None, trophies_6000: disnake.Role = None):

        list_roles = [bronze_league, silver_league, gold_league, crystal_league, master_league, champion_league,
                      titan_league, legends_league, trophies_5500, trophies_5700, trophies_6000]

        if len(set(list_roles)) == 1:
            await ctx.send("Please select at least one role to set.")

        spot_to_text = ["bronze_league", "silver_league", "gold_league", "crystal_league", "master_league",
                        "champion_league",
                        "titan_league", "legends_league", "trophies_5500", "trophies_5700", "trophies_6000"]

        roles_updated = ""
        for count, role in enumerate(list_roles):
            if role is None:
                continue
            role_text = spot_to_text[count]
            roles_updated += f"{role_text}: {role.mention}\n"
            results = await self.bot.legendleagueroles.find_one({"$and": [
                {"role": role.id},
                {"type": role_text},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.legendleagueroles.insert_one(
                    {"role": role.id,
                     "type": role_text,
                     "server": ctx.guild.id})
            else:
                await self.bot.legendleagueroles.update_one({"$and": [
                    {"type": role_text},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": role.id}})

        embed = disnake.Embed(title="**League Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)



    @builder_league_roles.sub_command(name="set", description="Sets roles to add for builder leagues")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def builder_league_roles_set(self, ctx: disnake.ApplicationCommandInteraction, wood_league: disnake.Role = None,
                               clay_league: disnake.Role = None, stone_league: disnake.Role = None,
                               copper_league: disnake.Role = None, brass_league: disnake.Role = None,
                               iron_league: disnake.Role = None, steel_league: disnake.Role = None,
                               titanium_league: disnake.Role = None, platinum_league: disnake.Role = None,
                               emerald_league: disnake.Role = None, ruby_league: disnake.Role = None, diamond_league: disnake.Role = None):

        list_roles = [wood_league, clay_league, stone_league, copper_league, brass_league, iron_league,
                      steel_league, titanium_league, platinum_league, emerald_league, ruby_league, diamond_league]

        if list_roles.count(None) == len(list_roles):
            return await ctx.send("Please select at least one role to set.")

        spot_to_text = ["wood_league", "clay_league", "stone_league", "copper_league", "brass_league",
                        "iron_league",
                        "steel_league", "titanium_league", "platinum_league", "emerald_league", "ruby_league", "diamond_league"]

        roles_updated = ""
        for count, role in enumerate(list_roles):
            if role is None:
                continue
            role_text = spot_to_text[count]
            roles_updated += f"{role_text}: {role.mention}\n"
            results = await self.bot.builderleagueroles.find_one({"$and": [
                {"role": role.id},
                {"type": role_text},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.builderleagueroles.insert_one(
                    {"role": role.id,
                     "type": role_text,
                     "server": ctx.guild.id})
            else:
                await self.bot.builderleagueroles.update_one({"$and": [
                    {"type": role_text},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": role.id}})

        embed = disnake.Embed(title="**Builder League Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)


    @status_roles.sub_command(name="set", description="Includes longevity & max hero (for th) roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def status_roles(self, ctx: disnake.ApplicationCommandInteraction,
                           one_month: disnake.Role = None, two_months: disnake.Role = None, three_months: disnake.Role =None,
                           six_months: disnake.Role = None, nine_months: disnake.Role = None, one_year: disnake.Role = None):

        list_roles = [one_month, two_months, three_months, six_months, nine_months, one_year]

        if list_roles.count(None) == len(list_roles):
            return await ctx.send("Please select at least one role to set.")

        spot_to_text = ["one_month", "two_months", "three_months", "six_months", "nine_months", "one_year"]
        roles_updated = ""
        for count, role in enumerate(list_roles):
            if role is None:
                continue
            role_text = spot_to_text[count]
            roles_updated += f"{role_text}: {role.mention}\n"
            results = await self.bot.statusroles.find_one({"$and": [
                {"role": role.id},
                {"type": role_text},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.statusroles.insert_one(
                    {"role": role.id,
                     "type": role_text,
                     "server": ctx.guild.id})
            else:
                await self.bot.statusroles.update_one({"$and": [
                    {"type": role_text},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": role.id}})

        embed = disnake.Embed(title="**Status Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)


    @achievement_roles.sub_command(name="set", description="Set role for top donators/activity & more")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def achievement_roles(self, ctx: disnake.ApplicationCommandInteraction, donos_10000: disnake.Role = None,
                                donos_25000: disnake.Role = None, top_donator_last_season: disnake.Role = None,
                                top_donator_ongoing_season: disnake.Role = None, top_activity_last_season: disnake.Role = None, top_activity_current_season: disnake.Role = None):

        list_roles = [donos_10000, donos_25000, top_donator_last_season, top_donator_ongoing_season, top_activity_last_season, top_activity_current_season]

        if list_roles.count(None) == len(list_roles):
            return await ctx.send("Please select at least one role to set.")

        spot_to_text = ["donos_10000", "donos_25000", "top_donator_last_season", "top_donator_ongoing_season", "top_activity_last_season", "top_activity_current_season"]
        roles_updated = ""
        for count, role in enumerate(list_roles):
            if role is None:
                continue
            role_text = spot_to_text[count]
            roles_updated += f"{role_text}: {role.mention}\n"
            results = await self.bot.statusroles.find_one({"$and": [
                {"role": role.id},
                {"type": role_text},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.statusroles.insert_one(
                    {"role": role.id,
                     "type": role_text,
                     "server": ctx.guild.id})
            else:
                await self.bot.statusroles.update_one({"$and": [
                    {"type": role_text},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": role.id}})

        embed = disnake.Embed(title="**Achievement Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)



    @commands.user_command(name="Nickname", description="Change nickname of a user")
    async def auto_nick(self, ctx: disnake.ApplicationCommandInteraction, user: disnake.User):
        await ctx.response.defer(ephemeral=True)
        perms = ctx.author.guild_permissions.manage_nicknames
        if user.id == ctx.author.id:
            perms = True
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Nickname` permissions.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        try:
            member = await ctx.guild.fetch_member(user.id)
        except:
            member = None
        if member is None:
            return await ctx.edit_original_message(f"{user.name} [{user.mention}] is not a member of this server.")

        account_tags = await self.bot.get_tags(user.id)
        abbreviations = {}
        clan_tags = []
        for role in await self.bot.clan_db.find({"server": ctx.guild.id}).to_list(length=200):
            clan_tags.append(role.get("tag"))
            clan_abbreviation = role.get("abbreviation")
            abbreviations[role.get("tag")] = clan_abbreviation

        GLOBAL_IS_FAMILY = False
        abbreviations_to_have = []
        player_accounts = await self.bot.get_players(tags=account_tags, custom=False, use_cache=False)
        if len(player_accounts) == 0:
            return await ctx.send(content=f"No accounts linked to {user.mention}")

        list_of_clans = []
        for player in player_accounts:
            # ignore the global if even one account is in family
            is_family_member = await self.is_in_family(player, clan_tags)
            if not GLOBAL_IS_FAMILY:
                GLOBAL_IS_FAMILY = is_family_member

            if player.clan is not None:
                list_of_clans.append(player.clan.name)

            if not is_family_member:
                continue

            if abbreviations[player.clan.tag] is not None:
                abbreviations_to_have.append(abbreviations[player.clan.tag])

        list_of_clans = list(set(list_of_clans))
        abbreviations_to_have = list(set(abbreviations_to_have))

        server = CustomServer(guild=ctx.guild, bot=self.bot)
        family_label = await server.family_label
        if family_label == "":
            family_label = []
        else:
            family_label = [family_label]

        abbreviations = []
        if abbreviations_to_have != []:
            abbreviations.append(", ".join(abbreviations_to_have))


        label_list = abbreviations + family_label + list_of_clans
        label_list = list(set(label_list))[:25]
        if label_list == []:
            label_list.append(ctx.guild.name)

        options = []
        for label in label_list:
            options.append(disnake.SelectOption(label=f"{label}", value=f"label_{label}"))

        stat_select = disnake.ui.Select(options=options, placeholder="Nickname Labels", min_values=1, max_values=1)

        st = disnake.ui.ActionRow()
        st.append_item(stat_select)

        options = []
        player_accounts = sorted(player_accounts, key= lambda x : x.trophies, reverse=True)[:25]
        names_taken = set()
        for player in player_accounts:
            if player.name in names_taken:
                continue
            names_taken.add(player.name)
            options.append(disnake.SelectOption(label=f"{player.name}", value=f"{player.name}", emoji=self.bot.fetch_emoji(player.town_hall).partial_emoji))

        profile_select = disnake.ui.Select(options=options, placeholder="Account List", min_values=1,max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        all_components = [st2, st]

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        embed = disnake.Embed(description=f"Nickname change for {user.mention}")
        await ctx.edit_original_message(embed=embed, components=all_components)

        name_to_set = player_accounts[0].name
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
        await ctx.response.defer(ephemeral=True)
        if user is None:
            user = ctx.author
        perms = ctx.author.guild_permissions.manage_nicknames
        if user.id == ctx.author.id:
            perms = True
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Nickname` permissions.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        try:
            member = await ctx.guild.fetch_member(user.id)
        except:
            member = None
        if member is None:
            return await ctx.edit_original_message(f"{user.name} [{user.mention}] is not a member of this server.")

        account_tags = await self.bot.get_tags(user.id)
        abbreviations = {}
        clan_tags = []
        for role in await self.bot.clan_db.find({"server": ctx.guild.id}).to_list(length=200):
            clan_tags.append(role.get("tag"))
            clan_abbreviation = role.get("abbreviation")
            abbreviations[role.get("tag")] = clan_abbreviation

        GLOBAL_IS_FAMILY = False
        abbreviations_to_have = []
        player_accounts = await self.bot.get_players(tags=account_tags, custom=False, use_cache=False)
        if len(player_accounts) == 0:
            return await ctx.send(content=f"No accounts linked to {user.mention}")

        list_of_clans = []
        for player in player_accounts:
            # ignore the global if even one account is in family
            is_family_member = await self.is_in_family(player, clan_tags)
            if not GLOBAL_IS_FAMILY:
                GLOBAL_IS_FAMILY = is_family_member

            if player.clan is not None:
                list_of_clans.append(player.clan.name)

            if not is_family_member:
                continue

            if abbreviations[player.clan.tag] is not None:
                abbreviations_to_have.append(abbreviations[player.clan.tag])

        list_of_clans = list(set(list_of_clans))
        abbreviations_to_have = list(set(abbreviations_to_have))

        server = CustomServer(guild=ctx.guild, bot=self.bot)
        family_label = await server.family_label
        if family_label == "":
            family_label = []
        else:
            family_label = [family_label]

        abbreviations = []
        if abbreviations_to_have != []:
            abbreviations.append(", ".join(abbreviations_to_have))

        label_list = abbreviations + family_label + list_of_clans
        label_list = list(set(label_list))[:25]
        if label_list == []:
            label_list.append(ctx.guild.name)

        options = []
        for label in label_list:
            options.append(disnake.SelectOption(label=f"{label}", value=f"label_{label}"))

        stat_select = disnake.ui.Select(options=options, placeholder="Nickname Labels", min_values=1, max_values=1)

        st = disnake.ui.ActionRow()
        st.append_item(stat_select)

        options = []
        player_accounts = sorted(player_accounts, key=lambda x: x.trophies, reverse=True)[:25]
        names_taken = set()
        for player in player_accounts:
            if player.name in names_taken:
                continue
            names_taken.add(player.name)
            options.append(disnake.SelectOption(label=f"{player.name}", value=f"{player.name}",
                                                emoji=self.bot.fetch_emoji(player.town_hall).partial_emoji))

        profile_select = disnake.ui.Select(options=options, placeholder="Account List", min_values=1, max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        all_components = [st2, st]

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        embed = disnake.Embed(description=f"Nickname change for {user.mention}")
        await ctx.edit_original_message(embed=embed, components=all_components)

        name_to_set = player_accounts[0].name
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


    async def eval_logic(self,  role_or_user, members_to_eval: List[disnake.Member],
                         test: bool, change_nick, ctx: disnake.ApplicationCommandInteraction = None, guild: disnake.Guild = None, role_types_to_eval = None,
                         return_array=False, return_embed=None, role_treatment=None, reason=""):
        time_start = time.time()
        bot_member = await ctx.guild.getch_member(self.bot.user.id)
        if role_types_to_eval is None:
            role_types_to_eval = ["family" , "not_family", "clan", "leadership", "townhall", "builderhall", "category", "league", "nicknames"]
        if role_treatment is None:
            role_treatment = ["Add", "Remove"]
        if guild is None:
            guild = ctx.guild
        await guild.fetch_roles()
        server = CustomServer(guild=guild, bot=self.bot)
        leadership_eval = await server.leadership_eval_choice

        ignored_roles = []
        all = self.bot.ignoredroles.find({"server": guild.id})
        limit = await self.bot.ignoredroles.count_documents(filter={"server": guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            ignored_roles.append(r)

        family_roles = []
        all = self.bot.generalfamroles.find({"server": guild.id})
        limit = await self.bot.generalfamroles.count_documents(filter={"server": guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            family_roles.append(r)

        if "family" not in role_types_to_eval:
            ignored_roles += family_roles

        not_fam_roles = []
        all = self.bot.notfamroles.find({"server": guild.id})
        limit = await self.bot.notfamroles.count_documents(filter={"server": guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            not_fam_roles.append(r)

        if "not_family" not in role_types_to_eval:
            ignored_roles += not_fam_roles

        clan_roles = []
        clan_tags = []
        clan_role_dict = {}
        abbreviations = {}
        clan_to_category = {}
        all = self.bot.clan_db.find({"server": guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("generalRole")
            tag = role.get("tag")
            category = role.get("category")
            clan_to_category[tag] = category
            clan_abbreviation = role.get("abbreviation")
            abbreviations[tag] = clan_abbreviation
            clan_role_dict[tag] = r
            clan_tags.append(tag)
            clan_roles.append(r)

        if "clan" not in role_types_to_eval:
            ignored_roles += clan_roles

        leadership_roles = []
        clan_leadership_role_dict = {}
        all = self.bot.clan_db.find({"server": guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": guild.id})
        for role in await all.to_list(length=limit):
            tag = role.get("tag")
            r = role.get("leaderRole")
            clan_leadership_role_dict[tag] = r
            leadership_roles.append(r)

        if "leadership" not in role_types_to_eval:
            ignored_roles += leadership_roles

        townhall_roles = {}
        th_role_list = []
        all = self.bot.townhallroles.find({"server": guild.id})
        limit = await self.bot.townhallroles.count_documents(filter={"server": guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            th = role.get("th")
            th = th.replace("th", "")
            th = int(th)
            townhall_roles[th] = r
            th_role_list.append(r)

        if "townhall" not in role_types_to_eval:
            ignored_roles += th_role_list

        builderhall_roles = {}
        bh_role_list = []
        all = self.bot.builderhallroles.find({"server": guild.id})
        limit = await self.bot.builderhallroles.count_documents(filter={"server": guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            bh = role.get("bh")
            bh = bh.replace("bh", "")
            bh = int(bh)
            builderhall_roles[bh] = r
            bh_role_list.append(r)

        if "builderhall" not in role_types_to_eval:
            ignored_roles += bh_role_list

        league_roles = {}
        league_role_list = []
        all = self.bot.legendleagueroles.find({"server": guild.id})
        limit = await self.bot.legendleagueroles.count_documents(filter={"server": guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            type = role.get("type")
            league_roles[type] = r
            league_role_list.append(r)

        if "league" not in role_types_to_eval:
            ignored_roles += league_role_list

        category_roles = {}
        category_role_list = []
        server_find = await self.bot.server_db.find_one({"server": guild.id})
        category_roles_find = server_find.get("category_roles")
        if category_roles_find is not None:
            categories = await self.bot.clan_db.distinct("category", filter={"server": guild.id})
            for category in categories:
                try:
                    role_id = category_roles_find.get(f"{category}")
                    if role_id is None:
                        continue
                    category_roles[category] = role_id
                    category_role_list.append(role_id)
                except:
                    pass

        if "category" not in role_types_to_eval:
            ignored_roles += category_role_list

        ALL_CLASH_ROLES = family_roles + clan_roles + not_fam_roles + league_role_list + th_role_list + category_role_list + bh_role_list
        if "leadership" in role_types_to_eval:
            if leadership_eval:
                ALL_CLASH_ROLES += leadership_roles

        text = ""
        num = 0
        embeds = []
        msg = await ctx.original_message()
        embed = disnake.Embed(
            description=f"<a:loading:884400064313819146> Fetching discord links for {len(members_to_eval)} users.",
            color=disnake.Color.green())
        if ctx is not None:
            await ctx.edit_original_message(embed=embed)
        all_discord_links = await self.bot.link_client.get_many_linked_players(*[member.id for member in members_to_eval])
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
        all_players = await self.bot.get_players(tags=all_tags, use_cache=(len(all_tags) >= 10))
        player_dict = {}
        for player in all_players:
            player_dict[player.tag] = player
        num_changes = 0

        tasks = []
        for count, member in enumerate(members_to_eval, 1):
            if member.bot:
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
            #try:
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
                if isinstance(player, coc.errors.NotFound):
                    continue
                if player is None:
                    continue
                list_accounts.append([player.trophies, player])
                # check if is a family member for 2 things - 1. to check for global roles (Not/is family) and 2. for if they shuld get roles on individual lvl
                # ignore the global if even one account is in family
                is_family_member = await self.is_in_family(player, clan_tags)
                if not GLOBAL_IS_FAMILY:
                    GLOBAL_IS_FAMILY = is_family_member

                # check if they have any townhall roles setup
                # try/except because dict throws error if it doesnt exist
                # if it exists add the relevant role to the role list to add
                if "townhall" in role_types_to_eval:
                    if bool(townhall_roles):
                        try:
                            th_role = townhall_roles[player.town_hall]
                            ROLES_SHOULD_HAVE.add(th_role)
                            if th_role not in MASTER_ROLES:
                                ROLES_TO_ADD.add(th_role)
                        except:
                            pass

                # check if they have any builderhall roles set up
                # try except because dict throws error if it doesnt exist
                # also because they could have no builder hall
                # if it exists on both ends, add the role to the role list to add
                if "builderhall" in role_types_to_eval:
                    if bool(builderhall_roles):
                        try:
                            bh_role = builderhall_roles[player.builder_hall]
                            ROLES_SHOULD_HAVE.add(bh_role)
                            if bh_role not in MASTER_ROLES:
                                ROLES_TO_ADD.add(bh_role)
                        except:
                            pass

                # check if server has any league roles set up
                # try/except in case it doesnt exist/isnt set up
                # add to role list if found
                if "league" in role_types_to_eval:
                    if bool(league_roles):
                        if str(player.league) != "Unranked":
                            league = str(player.league).split(" ")
                            league = league[0].lower()
                            try:
                                league_role = league_roles[f"{league}_league"]
                                ROLES_SHOULD_HAVE.add(league_role)
                                if league_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(league_role)
                            except:
                                pass

                        if str(player.league) == "Legend League":
                            try:
                                legend_role = league_roles["legends_league"]
                                ROLES_SHOULD_HAVE.add(legend_role)
                                if legend_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(legend_role)
                            except:
                                pass

                        if player.trophies >= 6000:
                            try:
                                legend_role = league_roles["trophies_6000"]
                                ROLES_SHOULD_HAVE.add(legend_role)
                                if legend_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(legend_role)
                            except:
                                pass
                        elif player.trophies >= 5700:
                            try:
                                legend_role = league_roles["trophies_5700"]
                                ROLES_SHOULD_HAVE.add(legend_role)
                                if legend_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(legend_role)
                            except:
                                pass
                        elif player.trophies >= 5500:
                            try:
                                legend_role = league_roles["trophies_5500"]
                                ROLES_SHOULD_HAVE.add(legend_role)
                                if legend_role not in MASTER_ROLES:
                                    ROLES_TO_ADD.add(legend_role)
                            except:
                                pass


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

                # if server has leadership_eval turned on
                # check & add any leadership roles
                if leadership_eval and ("leadership" in role_types_to_eval):
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
                    if leadership_eval:
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

            # finish - add & remove what is expected

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

            if not test:
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
                            #tasks.append(asyncio.ensure_future(member.add_roles(*FINAL_ROLES_TO_ADD)))
                        else:
                            added = "Could not add role(s)"

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
                                    current_member_roles.remove(role)
                            #tasks.append(asyncio.ensure_future(member.remove_roles(*FINAL_ROLES_TO_REMOVE)))
                        else:
                            removed = "Could not remove role(s)"


            name_changes = "None"
            #role_types_to_eval.remove("nicknames")
            if "nicknames" in role_types_to_eval:
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

                        if bot_member.top_role < member.top_role:
                            name_changes = "`Cannot Change`"
                        else:
                            if not test:
                                tasks.append(asyncio.ensure_future(member.edit(nick=new_name)))
                            name_changes = f"`{new_name}`"
                    elif change_nick == "Family Name":
                        results = sorted(family_accounts, key=lambda l: l[0], reverse=True)
                        family_label = await server.family_label
                        top_account: coc.Player = results[0][1]

                        if bot_member.top_role < member.top_role:
                            name_changes = "`Cannot Change`"
                        else:
                            if family_label == "":
                                if not test:
                                    tasks.append(asyncio.ensure_future(member.edit(nick=f"{top_account.name}")))
                                name_changes = f"`{top_account.name}`"
                            else:
                                if not test:
                                    tasks.append(asyncio.ensure_future(member.edit(nick=f"{top_account.name} | {family_label}")))
                                name_changes = f"`{top_account.name} | {family_label}`"

                if change_nick in ["Clan Abbreviations", "Family Name"] and not GLOBAL_IS_FAMILY and len(
                        list_accounts) >= 1:
                    results = sorted(list_accounts, key=lambda l: l[0], reverse=True)
                    top_account: coc.Player = results[0][1]
                    clan_name = ""
                    try:
                        clan_name = f"| {top_account.clan.name}"
                    except:
                        pass

                    if bot_member.top_role < member.top_role:
                        name_changes = "`Cannot Change`"
                    else:
                        if not test:
                            tasks.append(asyncio.ensure_future(member.edit(nick=f"{top_account.name} {clan_name}")))
                        name_changes = f"`{top_account.name} {clan_name}`"

            if name_changes[1:-1] == member.display_name:
                name_changes = "None"
            if added == "":
                added = "None"
            if removed == "":
                removed = "None"

            changes = [added, removed, name_changes]
            if return_array:
                return changes
            '''except:
                continue'''
            if ((changes[0] != "None") or (changes[1] != "None") or (changes[2] != "None")) or len(members_to_eval) >= 1:
                if changes[0] == "None" and changes[1] == "None" and changes[2] == "None" and len(members_to_eval) >= 2:
                    pass
                else:
                    text += f"**{member.display_name}** | {member.mention}"
                    if changes[0] != "None" or len(members_to_eval) == 1:
                        text += f"\nAdded: {changes[0]}"
                    if changes[1] != "None" or len(members_to_eval) == 1:
                        text += f"\nRemoved: {changes[1]}"
                    if changes[2] != "None":
                        text += f"\nNick Change: {changes[2]}"
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
            description=f"<a:loading:884400064313819146> Completing {len(tasks)} Eval Changes, Approx {int(len(tasks) % 60)} Minutes...",
            color=disnake.Color.green())
        if ctx is not None:
            await ctx.edit_original_message(embed=embed)

        await asyncio.gather(*tasks, return_exceptions=True)
        if return_embed:
            return embeds[0]

        time_elapsed = int(time.time() - time_start)
        for embed in embeds:
            embed.set_footer(text=f"Time Elapsed: {time_elapsed} seconds,  {num_changes} changes | Test: {test}")
            if ctx.guild.icon is not None:
                embed.set_author(name=f"{ctx.guild.name}", icon_url=ctx.guild.icon.url)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

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

    async def is_in_family(self, player, clan_tags):
        try:
            clan = player.clan.tag
        except:
            return False

        return clan in clan_tags

    @eval_tag.autocomplete("player_tag")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names




def setup(bot:  CustomClient):
    bot.add_cog(eval(bot))
