import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from main import check_commands

class EvalSetup(commands.Cog, name="Eval Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    ###Command Groups
    @commands.slash_command(name="family-roles")
    async def general_fam_roles(self, ctx):
        pass

    @commands.slash_command(name="notfamily-roles")
    async def not_fam_roles(self, ctx):
        pass

    @commands.slash_command(name="ignored-roles")
    async def ignored_roles(self, ctx):
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

    ###General Family Role Section
    @general_fam_roles.sub_command(name="add", description="Add a role to be given to family members")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def general_fam_roles_add(self, ctx: disnake.ApplicationCommandInteraction, role:disnake.Role):

        results = await self.bot.generalfamroles.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{role.mention} is already in the general family roles list.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.generalfamroles.insert_one({
            "server": ctx.guild.id,
            "role": role.id
        })

        embed = disnake.Embed(
            description=f"{role.mention} added to the general family role list.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @general_fam_roles.sub_command(name="remove", description="Remove a role from general family role list")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def general_fam_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):

        results = await self.bot.generalfamroles.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = disnake.Embed(description=f"{role.mention} is not currently in the general family roles list.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.generalfamroles.find_one_and_delete({"role": role.id})

        embed = disnake.Embed(
            description=f"{role.mention} removed from the general family roles list.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @general_fam_roles.sub_command(name="list", description="List of roles that are given to family members")
    async def general_fam_roles_list(self, ctx: disnake.ApplicationCommandInteraction):
        text = ""
        all = self.bot.generalfamroles.find({"server": ctx.guild.id})
        limit = await self.bot.generalfamroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            text += f"<@&{r}>\n"

        if text == "":
            text = "No General Family roles."

        embed = disnake.Embed(title=f"General Family Roles",
                              description=text,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)






    ###Not Family Role Section
    @not_fam_roles.sub_command(name="add", description="Add a role to be given to non family members")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def not_fam_roles_add(self, ctx: disnake.ApplicationCommandInteraction, role:disnake.Role):

        results = await self.bot.notfamroles.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{role.mention} is already in the not family roles list.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.notfamroles.insert_one({
            "server": ctx.guild.id,
            "role": role.id
        })

        embed = disnake.Embed(
            description=f"{role.mention} added to the not family roles list.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @not_fam_roles.sub_command(name="remove", description="Remove a role from non family role list")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def not_fam_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):

        results = await self.bot.notfamroles.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = disnake.Embed(description=f"{role.mention} is not currently in the not family roles list.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.notfamroles.find_one_and_delete({"role": role.id})

        embed = disnake.Embed(
            description=f"{role.mention} removed from the not family roles list.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @not_fam_roles.sub_command(name="list", description="List of roles that are given to non family members")
    async def not_fam_roles_list(self, ctx: disnake.ApplicationCommandInteraction):
        text = ""
        all = self.bot.notfamroles.find({"server": ctx.guild.id})
        limit = await self.bot.notfamroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            text += f"<@&{r}>\n"

        if text == "":
            text = "No Not Family Roles."

        embed = disnake.Embed(title=f"Not Family Roles",
                              description=text,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)






    ###Ignored Roles Section
    @ignored_roles.sub_command(name="add", description="Add a role to be ignored during eval for family members")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ignored_roles_add(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):

        results = await self.bot.ignoredroles.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{role.mention} role is already ignored during eval.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.ignoredroles.insert_one({
            "server": ctx.guild.id,
            "role" : role.id
        })

        embed = disnake.Embed(
            description=f"{role.mention} added as a role to ignore during evaluation for family members.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @ignored_roles.sub_command(name="remove", description="Removes a role from the ignore during eval role list")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ignored_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):

        results = await self.bot.ignoredroles.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = disnake.Embed(description=f"{role.mention} is not currently ignored during eval.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.ignoredroles.find_one_and_delete({"role" : role.id})

        embed = disnake.Embed(
            description=f"{role.mention} removed as a role to ignore during evaluation for family members.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @ignored_roles.sub_command(name="list", description="List of roles that are ignored for family members during eval")
    async def ignored_roles_list(self, ctx: disnake.ApplicationCommandInteraction):
        text = ""
        all = self.bot.ignoredroles.find({"server" : ctx.guild.id})
        limit = await self.bot.ignoredroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            text += f"<@&{r}>\n"

        if text == "":
            text = "No Eval Ignored Roles."

        embed = disnake.Embed(title=f"Eval Ignored Roles",
                              description=text,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)





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
            {"type": f"{legend_role_type}"},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("That legend role type does not have a role assigned to it for eval currently.")
        else:
            mention = results.get("role")
            await self.bot.legendleagueroles.find_one_and_delete({"$and": [
                {"type": f"{legend_role_type}"},
                {"server": ctx.guild.id}
            ]})

        embed = disnake.Embed(description=f"{legend_role_type} eval role removed - <@&{mention}>",
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