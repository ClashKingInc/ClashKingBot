import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient

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

    @commands.slash_command(name="legend-roles")
    async def legend_roles(self, ctx):
        pass

    ###General Family Role Section
    @general_fam_roles.sub_command(name="add", description="Add a role to be given to family members")
    async def general_fam_roles_add(self, ctx: disnake.ApplicationCommandInteraction, role:disnake.Role):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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
    async def general_fam_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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
    async def not_fam_roles_add(self, ctx: disnake.ApplicationCommandInteraction, role:disnake.Role):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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
    async def not_fam_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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
    async def ignored_roles_add(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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
    async def ignored_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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
    async def townhall_roles_set(self, ctx: disnake.ApplicationCommandInteraction, th7:disnake.Role=None, th8:disnake.Role=None, th9:disnake.Role=None,
                th10:disnake.Role=None, th11:disnake.Role=None, th12:disnake.Role=None, th13:disnake.Role=None, th14:disnake.Role=None):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if th7 is None and th8 is None and th9 is None and th10 is None and th11 is None and th12 is None and th13 is None and th14 is None:
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

        embed = disnake.Embed(title="**Townhall Roles that were set:**",
            description=roles_updated,
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @townhall_roles.sub_command(name="remove", description="Remove townhall eval roles")
    async def townhall_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, townhall: str =
        commands.Param(choices=["th7", "th8", "th9", "th10", "th11", "th12", "th13", "th14"])):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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


    ###Legend Roles Section
    @legend_roles.sub_command(name="set", description="Sets roles to add for legends")
    async def legend_roles_set(self, ctx: disnake.ApplicationCommandInteraction, legends_league:disnake.Role=None, trophies_5500:disnake.Role=None, trophies_5700:disnake.Role=None, trophies_6000:disnake.Role=None):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if legends_league is None and trophies_5500 is None and trophies_5700 is None and trophies_6000 is None:
            await ctx.send("Please select at least one role to set.")

        roles_updated = ""

        if legends_league is not None:
            roles_updated+=f"Legend League: {legends_league.mention}\n"
            results = await self.bot.legendleagueroles.find_one({"$and": [
                {"role": legends_league.id},
                {"type" : "legends_league"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.legendleagueroles.insert_one(
                    {"role": legends_league.id,
                    "type": "legends_league",
                    "server": ctx.guild.id})
            else:
                await self.bot.legendleagueroles.update_one({"$and": [
                    {"type": "legends_league"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": legends_league.id}})
        if trophies_5500 is not None:
            roles_updated+=f"5500+ Trophies: {trophies_5500.mention}\n"
            results = await self.bot.legendleagueroles.find_one({"$and": [
                {"role": trophies_5500.id},
                {"type" : "trophies_5500"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.legendleagueroles.insert_one(
                    {"role": trophies_5500.id,
                    "type": "trophies_5500",
                    "server": ctx.guild.id})
            else:
                await self.bot.legendleagueroles.update_one({"$and": [
                    {"type": "trophies_5500"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": trophies_5500.id}})
        if trophies_5700 is not None:
            roles_updated+=f"5700+ Trophies: {trophies_5700.mention}\n"
            results = await self.bot.legendleagueroles.find_one({"$and": [
                {"role": trophies_5700.id},
                {"type" : "trophies_5700"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.legendleagueroles.insert_one(
                    {"role": trophies_5700.id,
                    "type": "trophies_5700",
                    "server": ctx.guild.id})
            else:
                await self.bot.legendleagueroles.update_one({"$and": [
                    {"type": "trophies_5700"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": trophies_5700.id}})
        if trophies_6000 is not None:
            roles_updated+=f"6000+ Trophies: {trophies_6000.mention}\n"
            results = await self.bot.legendleagueroles.find_one({"$and": [
                {"role": trophies_6000.id},
                {"type" : "trophies_6000"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.legendleagueroles.insert_one(
                    {"role": trophies_6000.id,
                    "type": "trophies_6000",
                    "server": ctx.guild.id})
            else:
                await self.bot.legendleagueroles.update_one({"$and": [
                    {"type": "trophies_6000"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": trophies_6000.id}})

    @legend_roles.sub_command(name="remove", description="Remove legends eval roles")
    async def legend_roles_remove(self, ctx: disnake.ApplicationCommandInteraction, legend_role_type: str =
        commands.Param(choices=["legends_league", "trophies_5500", "trophies_5700", "trophies_6000"])):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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

    @legend_roles.sub_command(name="list", description="List of legend roles for eval")
    async def legend_roles_list(self, ctx: disnake.ApplicationCommandInteraction):
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