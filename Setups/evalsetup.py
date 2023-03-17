import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from main import check_commands

class EvalSetup(commands.Cog, name="Eval Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    ###Command Groups
    @commands.slash_command(name="family-roles")
    async def family_roles(self, ctx):
        pass

    @commands.slash_command(name="townhall-roles")
    async def townhall_roles(self, ctx):
        pass

    @commands.slash_command(name="league-roles")
    async def league_roles(self, ctx):
        pass

    @commands.slash_command(name="builderhall-roles")
    async def builderhall_roles(self, ctx):
        pass

    @family_roles.sub_command(name="add", description="Add Family Based Eval Roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def family_roles_add(self, ctx: disnake.ApplicationCommandInteraction, type = commands.Param(choices=["Only-Family Roles", "Not-Family Roles", "Ignored Roles"]),
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
    async def family_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, type = commands.Param(choices=["Only-Family Roles", "Not-Family Roles", "Ignored Roles"]),
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
            return disnake.Embed(description=f"{role.mention} is already in the {type} list.", color=disnake.Color.red())

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
        if results is not None:
            return disnake.Embed(description=f"{role.mention} is not currently in the {type} list.", color=disnake.Color.red())

        if role.is_default():
            return disnake.Embed(description=f"Cannot use the @everyone role for {type}", color=disnake.Color.red())

        await database.find_one_and_delete({"role": role.id})

        return disnake.Embed(description=f"{role.mention} removed from the {type} list.", color=disnake.Color.green())


    @family_roles.sub_command(name="list", description="List Family Based Eval Roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def family_role_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

        family_roles = await self.bot.generalfamroles.find({"server": ctx.guild.id}).to_list(length=100)
        not_family_roles = await self.bot.notfamroles.find({"server": ctx.guild.id}).to_list(length=100)
        ignored_roles = await self.bot.ignoredroles.find({"server" : ctx.guild.id}).to_list(length=100)

        list_roles = [family_roles, not_family_roles, ignored_roles]
        role_names = ["Only-Family Roles", "Not-Family Roles", "Ignored Roles"]

        embed = disnake.Embed(title=f"{ctx.guild.name} Family Role List", color= disnake.Color.green())
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

        await ctx.edit_original_message(embed=embed)



    ###Townhall Roles Section
    @townhall_roles.sub_command(name="set", description="Sets roles to add for townhall levels 7 and up")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def townhall_roles_set(self, ctx: disnake.ApplicationCommandInteraction, th7:disnake.Role=None, th8:disnake.Role=None, th9:disnake.Role=None,
                th10:disnake.Role=None, th11:disnake.Role=None, th12:disnake.Role=None, th13:disnake.Role=None, th14:disnake.Role=None, th15:disnake.Role=None):


        if th7 is None and th8 is None and th9 is None and th10 is None and th11 is None and th12 is None and th13 is None and th14 is None and th15 is None:
            return await ctx.send("Please provide a role for at least 1 townhall level.")

        roles_updated = ""

        if th7 is not None:
            roles_updated+=f"TH7: {th7.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th7.id},
                {"th" : "th7"},
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

    @townhall_roles.sub_command(name="remove", description="Remove townhall eval roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def townhall_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, townhall: str =
        commands.Param(choices=["th7", "th8", "th9", "th10", "th11", "th12", "th13", "th14", "th15"])):

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

        embed = disnake.Embed(description=f"{townhall.upper()} eval role removed - <@&{mention}>",
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @townhall_roles.sub_command(name="list", description="List of townhall roles for eval")
    async def townhall_roles_list(self, ctx: disnake.ApplicationCommandInteraction):
        list_ths = ""

        all = self.bot.townhallroles.find({"server": ctx.guild.id})
        all.sort('th', -1)
        limit = await self.bot.townhallroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            roleid = role.get("role")
            th = role.get("th")
            list_ths+= f"{th}: <@&{roleid}>\n"

        if list_ths == "":
            list_ths = "No Townhall Roles."

        embed = disnake.Embed(title=f"Townhall Roles",
                              description=list_ths,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)





    ###Builderhall Roles Section
    @builderhall_roles.sub_command(name="set", description="Sets roles to add for builderhall levels 3 and up")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def builderhall_roles_set(self, ctx: disnake.ApplicationCommandInteraction, bh3: disnake.Role = None,
                                 bh4: disnake.Role = None, bh5: disnake.Role = None,
                                 bh6: disnake.Role = None, bh7: disnake.Role = None, bh8: disnake.Role = None,
                                 bh9: disnake.Role = None):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if bh3 is None and bh4 is None and bh5 is None and bh6 is None and bh7 is None and bh8 is None and bh9 is None:
            return await ctx.send("Please provide a role for at least 1 builderhall level.")

        roles_updated = ""

        spot_to_text = ["bh3", "bh4", "bh5", "bh6", "bh7", "bh8", "bh9"]
        list_roles = [bh3, bh4, bh5, bh6, bh7, bh8, bh9]

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

    @builderhall_roles.sub_command(name="remove", description="Remove builderhall eval roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def builderhall_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, builderhall: str =
    commands.Param(choices=["bh3", "bh4", "bh5", "bh6", "bh7", "bh8", "bh9"])):


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

        embed = disnake.Embed(description=f"{builderhall.upper()} eval role removed - <@&{mention}>",
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @builderhall_roles.sub_command(name="list", description="List of builderhall roles for eval")
    async def builderhall_roles_list(self, ctx: disnake.ApplicationCommandInteraction):
        list_ths = ""

        all = self.bot.builderhallroles.find({"server": ctx.guild.id})
        all.sort('th', -1)
        limit = await self.bot.builderhallroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            roleid = role.get("role")
            th = role.get("bh")
            list_ths += f"{th}: <@&{roleid}>\n"

        if list_ths == "":
            list_ths = "No BuilderHall Roles."

        embed = disnake.Embed(title=f"BuilderHall Roles",
                              description=list_ths,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)




    ###League Roles Section
    @league_roles.sub_command(name="set", description="Sets roles to add for leagues")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def league_roles_set(self, ctx: disnake.ApplicationCommandInteraction, bronze_league:disnake.Role=None, silver_league:disnake.Role=None, gold_league:disnake.Role=None,
                               crystal_league:disnake.Role=None, master_league:disnake.Role=None, champion_league:disnake.Role=None, titan_league:disnake.Role=None,
                               legends_league:disnake.Role=None, trophies_5500:disnake.Role=None, trophies_5700:disnake.Role=None, trophies_6000:disnake.Role=None):

        list_roles = [bronze_league, silver_league, gold_league, crystal_league, master_league, champion_league, titan_league, legends_league, trophies_5500, trophies_5700, trophies_6000]

        if len(set(list_roles)) == 1:
            await ctx.send("Please select at least one role to set.")

        spot_to_text = ["bronze_league", "silver_league", "gold_league", "crystal_league", "master_league", "champion_league",
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

    @league_roles.sub_command(name="remove", description="Remove league eval roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def league_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, league_role_type: str =
        commands.Param(choices=["legends_league", "trophies_5500", "trophies_5700", "trophies_6000"])):

        results = await self.bot.legendleagueroles.find_one({"$and": [
            {"type": f"{league_role_type}"},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("That league role type does not have a role assigned to it for eval currently.")
        else:
            mention = results.get("role")
            await self.bot.legendleagueroles.find_one_and_delete({"$and": [
                {"type": f"{league_role_type}"},
                {"server": ctx.guild.id}
            ]})

        embed = disnake.Embed(description=f"{league_role_type} eval role removed - <@&{mention}>",
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @league_roles.sub_command(name="list", description="List of league roles for eval")
    async def league_roles_list(self, ctx: disnake.ApplicationCommandInteraction):
        list = ""
        all = self.bot.legendleagueroles.find({"server": ctx.guild.id})
        limit = await self.bot.legendleagueroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            roleid = role.get("role")
            type = role.get("type")
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "No Legends & Trophies Roles."

        embed = disnake.Embed(title=f"Legend Eval Roles",
                              description=list,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)


    ###Dono Roles Section



def setup(bot: CustomClient):
    bot.add_cog(EvalSetup(bot))