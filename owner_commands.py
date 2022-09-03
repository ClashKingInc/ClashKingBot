import disnake
from disnake.ext import commands

clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0
from CustomClasses.CustomBot import CustomClient

class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="track-wars", guild_ids=[1013113692654686271])
    async def track_war(self, ctx: disnake.ApplicationCommandInteraction, clan:str):
        clan = await self.bot.getClan(clan)
        if clan is None:
            return await ctx.send("Not a valid clan tag")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{clan.name} is already linked to this server.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        embed = disnake.Embed(description=f"Tracking for {clan.name} has been sent for approval.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

        channel = await self.bot.fetch_channel(1013152300627402773)
        embed = disnake.Embed(description=f"{ctx.user.mention} has requested tracking for {clan.name}.",
                              color=disnake.Color.green())

        page_buttons = [
            disnake.ui.Button(label="Yes", emoji="✅", style=disnake.ButtonStyle.green,
                              custom_id=f"yestrack_{clan.tag}"),
            disnake.ui.Button(label="No", emoji="❌",
                              style=disnake.ButtonStyle.red,
                              custom_id=f"notrack_{clan.tag}")
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        await channel.send(embed=embed, components=buttons)

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "yestrack" in str(ctx.data.custom_id):
            clan = (str(ctx.data.custom_id).split("_"))[1]
            clan = await self.bot.getClan(clan)
            await ctx.send(content=f"Setting up {clan.name}", ephemeral=True)
            category = await self.bot.fetch_channel(1013167881363652638)
            clan_channel = await ctx.guild.create_text_channel(category=category.category, name=clan.name, topic=clan.tag)
            await self.bot.clan_db.insert_one({
                "name": clan.name,
                "tag": clan.tag,
                "generalRole": 1013113817032573009,
                "leaderRole": 1013113817032573009,
                "category": "War Tracking",
                "server": ctx.guild.id,
                "clanChannel": clan_channel.id,
                "war_log" : clan_channel.id
            })
            await ctx.message.edit(components=[])
        elif "notrack" in str(ctx.data.custom_id):
            clan = (str(ctx.data.custom_id).split("_"))[1]
            clan = await self.bot.getClan(clan)
            await ctx.send(content=f"Declining request...", ephemeral=True)
            await ctx.message.edit(components=[])
            channel = await self.bot.fetch_channel(1013156154177765386)
            embed = disnake.Embed(description=f"Request to set up {clan.name} denied.",color=disnake.Color.red())
            await channel.send(embed=embed)

    @track_war.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):

        clan_list = []
        if len(query) >= 3:
            clan = await self.bot.getClan(query)
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=10)
                for clan in results:
                    league = str(clan.war_league).replace("League ", "")
                    clan_list.append(f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]


    @commands.command(name='reload', hidden=True)
    async def _reload(self,ctx, *, module: str):
        """Reloads a module."""
        if ctx.message.author.id == 706149153431879760:
            try:
                self.bot.unload_extension(module)
                self.bot.load_extension(module)
            except:
                await ctx.send('<a:no:862552093324083221> Could not reload module.')
            else:
                await ctx.send('<a:check:861157797134729256> Reloaded module successfully')
        else:
            await ctx.send("You aren't magic. <:PS_Noob:783126177970782228>")


    '''
    @commands.command(name="testraid")
    async def testraid(self, ctx, tag):

        text = ""
        clan = await getClan(tag)

        tracked = clans.find({"tag": f"{clan.tag}"})
        limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await self.bot.fetch_guild(server)
            except:
                continue
            clancapital_channel = cc.get("clan_capital")
            if clancapital_channel is None:
                continue

            try:
                clancapital_channel = await server.fetch_channel(clancapital_channel)
                if clancapital_channel is None:
                    continue
            except:
                continue

            embed = disnake.Embed(
                description=f"Test Player donated <:capitalgold:987861320286216223>1000"
                , color=disnake.Color.green())

            embed.set_footer(icon_url=clan.badge.url, text=clan.name)

            try:
                member = await server.getch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send =ow.send_messages
                await clancapital_channel.send(embed=embed)
                text += f"{server.name} : Successful\n> Send Messages Perm: {send}\n"
            except Exception as e:
                member = await server.getch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send = ow.send_messages
                text += f"{server.name} : Not Successful\n> Send Messages Perm: {send}\n> {str(e)[0:1000]}\n"

        embed = disnake.Embed(title=f"Test Raid {clan.name}", description=text, color=disnake.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name='leave')
    @commands.is_owner()
    async def leaveg(self,ctx, *, guild_name):
        guild = disnake.utils.get(self.bot.guilds, name=guild_name)  # Get the guild by name
        if guild is None:
            await ctx.send("No guild with that name found.")  # No guild found
            return
        await guild.leave()  # Guild found
        await ctx.send(f"I left: {guild.name}!")
    '''





def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))