
from disnake.ext import commands
import disnake
from utils.clash import getClan, getPlayer, client, pingToMember, pingToRole, getTags, link_client

from main import check_commands

usafam = client.usafam
clans = usafam.clans
linkrole = usafam.linkrole
removeroles = usafam.removeroles
generalrole = usafam.generalrole
evalignore = usafam.evalignore

class eval(commands.Cog):
    """A couple of simple commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="eval")
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def eval(self, ctx, query=None, test=None):
        test = (test!=None)

        if query == "everyone":
            type = ctx.guild.default_role
            return await self.eval_role(ctx, type, test)


        if query == None:
            return await ctx.reply("Please specify a user or role to evaluate.")

        type = await pingToMember(ctx, query)

        if type == None:
            type = await pingToRole(ctx, query)
            if type == None:
                return await ctx.reply("Not a valid user or role to evaluate.")
            else:
                return await self.eval_role(ctx, type, test)
        else:
             changes = await self.eval_member(ctx, type, test)
             embed = disnake.Embed(description=f"Eval Complete for {type.mention}\n"
                                              f"Added: {changes[0]}\n"
                                              f"Removed: {changes[1]}",
                                  color=disnake.Color.green())
             await ctx.send(embed=embed)

    async def eval_member(self, ctx, member, test):

        roles_to_ignore = []
        all = evalignore.find()
        limit = await evalignore.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            roles_to_ignore.append(r)

        roles_add_to_family = []
        all = generalrole.find()
        limit = await generalrole.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            roles_add_to_family.append(r)

        roles_remove_if_family = []
        all = linkrole.find()
        limit = await linkrole.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            roles_remove_if_family.append(r)

        roles_remove_if_not_family = []
        all = removeroles.find()
        limit = await removeroles.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            roles_remove_if_not_family.append(r)

        clan_roles = []
        all = clans.find()
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("generalRole")
            clan_roles.append(r)

        leadership_roles = []
        all = clans.find()
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("leaderRole")
            leadership_roles.append(r)

        roles_to_remove = []
        roles_should_have = []

        accounts = await getTags(ctx, str(member.id))


        roles_does_have = member.roles

        has_family_account = False
        for tag in accounts:
            player = await getPlayer(tag)
            if player is None:
                continue
            has_family_account = await self.is_in_family(ctx, tag)
            if has_family_account:
                break


        for tag in accounts:
            player = await getPlayer(tag)
            if player is None:
                continue

            is_family_member = await self.is_in_family(ctx, tag)

            if is_family_member:
                for role in roles_add_to_family:
                    if role not in roles_should_have:
                        roles_should_have.append(role)

                clan = await clans.find_one({"tag": player.clan.tag})
                clanRole = clan.get("generalRole")
                if (clanRole not in roles_should_have):
                    roles_should_have.append(clanRole)

                for role in roles_remove_if_family:
                    if role not in roles_to_remove:
                        roles_to_remove.append(role)
            else:
                for role in roles_remove_if_family:
                    if role not in roles_should_have:
                        roles_should_have.append(role)

                for role in roles_add_to_family:
                    if role not in roles_to_remove:
                        roles_to_remove.append(role)

                for role in roles_remove_if_not_family:
                    if role not in roles_to_remove:
                        roles_to_remove.append(role)

                for role in leadership_roles:
                    if role not in roles_to_remove:
                        roles_to_remove.append(role)

            if not is_family_member and has_family_account:
                continue



            # done fetching all the roles they should have
            # now to add them
            # print(member.name)
            # print(roles_should_have)

        print(roles_does_have)
        for role in roles_does_have:
            print(roles_add_to_family)
            isClashRole = (role.id in clan_roles) or (role.id in roles_add_to_family)
            shouldHave = (role.id in roles_should_have)
            if isClashRole and shouldHave:
                roles_should_have.remove(role.id)
            elif isClashRole and not shouldHave:
                print(role.id)
                roles_to_remove.append(role.id)

        true_roles_to_remove = []
        for role in roles_does_have:
            if has_family_account:
                if (role.id in roles_to_remove) and (role.id not in roles_to_ignore):
                    true_roles_to_remove.append(role.id)
            else:
                if role.id in roles_to_remove:
                    true_roles_to_remove.append(role.id)


        # finish - add & remove what is expected
        #print(roles_does_have)
        #print(roles_should_have)
        #print(roles_to_remove)
        greet = False
        added = ""
        removed = ""
        for role in roles_should_have:
            r = ctx.guild.get_role(role)
            if r is None:
                continue
            if r.id in clan_roles:
                greet = True
            if not test:
                await member.add_roles(r)
            added += r.mention +", "
        for role in true_roles_to_remove:
            r = ctx.guild.get_role(role)
            if r is None:
                continue
            if not test:
                await member.remove_roles(r)
            removed += r.mention + ", "

        if added == "":
            added = "None"
        if removed == "":
            removed = "None"

        changes = [added, removed, greet]
        return changes


    async def eval_role(self, ctx, role, test):
        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Evaluating...",
            color=disnake.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)
        members = role.members
        clan = await clans.find_one({"generalRole": role.id})
        if clan is not None:
            embed = disnake.Embed(
                description="<a:loading:884400064313819146> Evaluating clan members...",
                color=disnake.Color.green())
            await msg.edit(embed=embed)
            clanTag = clan.get("tag")
            clan = await getClan(clanTag)
            async for player in clan.get_detailed_members():
                tag = player.tag
                member = await link_client.get_link(tag)
                member = await pingToMember(ctx, str(member))
                if (member not in members) and (member != None):
                    members.append(member)

        text = ""
        embeds = []
        num = 0
        leng = 1
        for member in members:
            if member.bot:
                continue
            embed = discord.Embed(
                description=f"<a:loading:884400064313819146> Evaluating role members - ({leng}/{len(members)})",
                color=discord.Color.green())
            await msg.edit(embed=embed)
            leng+=1
            changes = await self.eval_member(ctx, member, test)
            #print(changes)
            if (changes[0] != "None") or (changes[1] != "None"):
                text+=f"**{member.display_name}** | {member.mention}\nAdded: {changes[0]}\nRemoved: {changes[1]}\n<:blanke:838574915095101470>\n"
                num+=1
            if num == 10:
                embed = discord.Embed(title=f"Eval Complete",
                                      description=text,
                                      color=discord.Color.green())
                embeds.append(embed)
                text = ""
                num=0

        if text != "":
            embed = discord.Embed(title=f"Eval Complete for {role.name}",
                                  description=text,
                                  color=discord.Color.green())
            embeds.append(embed)

        if embeds == []:
            text = "No evals needed."
            embed = discord.Embed(title=f"Eval Complete for {role.name}",
                                  description=text,
                                  color=discord.Color.green())
            embeds.append(embed)

        current_page=0
        limit = len(embeds)
        await msg.edit(embed=embeds[0], components=self.create_components(current_page, limit),
                             mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=self.create_components(current_page, limit),
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()

            # print(res.custom_id)
            if res.custom_id == "Previous":
                current_page -= 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

    async def is_in_family(self, ctx, tag):
        player = await getPlayer(tag)
        try:
            clan = player.clan.tag
        except:
            return False

        results = await clans.find_one({"$and": [
            {"tag": clan},
            {"server": ctx.guild.id}
        ]})

        return results != None

    def create_components(self, current_page, limit):
        length = limit
        if length == 1:
            return []

        page_buttons = [create_button(label="", emoji="◀️", style=ButtonStyle.blue, disabled=(current_page == 0),
                                      custom_id="Previous"),
                        create_button(label=f"Page {current_page + 1}/{length}", style=ButtonStyle.grey,
                                      disabled=True),
                        create_button(label="", emoji="▶️", style=ButtonStyle.blue,
                                      disabled=(current_page == length - 1), custom_id="Next")]
        page_buttons = create_actionrow(*page_buttons)

        return [page_buttons]




def setup(bot: commands.Bot):
    bot.add_cog(eval(bot))