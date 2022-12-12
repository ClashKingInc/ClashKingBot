
import disnake
from disnake.ext import commands
from utils.components import create_components
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import CustomServer
from datetime import datetime

SUPER_TROOPS = ["Super Barbarian", "Super Archer", "Super Giant", "Sneaky Goblin", "Super Wall Breaker", "Rocket Balloon", "Super Wizard", "Inferno Dragon",
                "Super Minion", "Super Valkyrie", "Super Witch", "Ice Hound", "Super Bowler", "Super Dragon", "Super Miner"]
REG_VERSION = ["Barbarian", "Archer", "Giant", "Goblin", "Wall Breaker", "Balloon", "Wizard", "Baby Dragon",
                "Minion", "Valkyrie", "Witch", "Lava Hound", "Bowler", "Dragon"]



class boost(commands.Cog, name="Super Troops"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="boost", description="Get list of troops listed in a certain clan (or all family clans if blank)")
    async def boosting(self, ctx: disnake.ApplicationCommandInteraction, clan:str=None):
        server = CustomServer(ctx.guild, self.bot)
        list_clans = []
        if clan is None:
            list_clans = await server.clan_list
        else:
            clan = await self.bot.getClan(clan)
            if clan is None:
                return await ctx.send("Not a valid clan tag.")
            list_clans.append(clan.tag)

        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Loading...",
            color=disnake.Color.green())
        await ctx.send(embed=embed)


        embeds = await self.boost_embed(list_clans)

        current_page = 0

        if len(embeds) >= 2:
            await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        else:
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"boost_{clan.tag}"))
            return await ctx.edit_original_message(embed=embeds[0], components=buttons)

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


    @commands.slash_command(name="super", description="Find all players with a super troop in the family or a specific clan")
    async def super(self, ctx: disnake.ApplicationCommandInteraction=None, super_troop=commands.Param(choices=SUPER_TROOPS), clan:str=None):
        first_clan = clan
        list_clans = []
        if clan is None:
            tracked = self.bot.clan_db.find({"server": ctx.guild.id})
            limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
            list = []
            for tClan in await tracked.to_list(length=limit):
                tag = tClan.get("tag")
                list.append(tag)
            async for clan in self.bot.coc_client.get_clans(list):
                list_clans.append(clan)
        else:
            clan = clan.lower()
            results = await self.bot.clan_db.find_one({"$and": [
                {"alias": clan},
                {"server": ctx.guild.id}
            ]})

            if results is not None:
                tag = results.get("tag")
                clan = await self.bot.getClan(tag)
                list_clans.append(clan)
            else:
                clan = await self.bot.getClan(clan)
                if clan is not None:
                    list_clans.append(clan)

            if clan is None:
                if "|" in first_clan:
                    search = first_clan.split("|")
                    tag = search[1]
                    clan = await self.bot.getClan(tag)
                    list_clans.append(clan)

            if clan is None:
                return await ctx.send("Not a valid clan tag.")

        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Loading...",
            color=disnake.Color.green())
        await ctx.send(embed=embed)

        search = super_troop

        master_text = []
        for clan in list_clans:
            async for player in clan.get_detailed_members():
                troops = player.troop_cls
                troops = player.troops
                for x in range(len(troops)):
                    troop = troops[x]
                    if (troop.is_active) and (troop.name == search):
                        try:
                            master_text.append(f"{player.clan.name} - {player.name} [{player.tag}]\n")
                        except:
                            pass

        embeds = []

        if len(master_text) == 0:
            embed = disnake.Embed(title=f"Players with {search}",
                                  description="None boosted",
                                  color=disnake.Color.green())
            embeds.append(embed)

        t = ""
        x = 0
        for text in master_text:
            t += text
            x += 1
            if x == 50:
                embed = disnake.Embed(title=f"Players with {search}",
                                      description=t,
                                      color=disnake.Color.green())
                embeds.append(embed)
                x = 0
                t = ""
        if t != "":
            embed = disnake.Embed(title=f"Players with {search}",
                                  description=t,
                                  color=disnake.Color.green())
            embeds.append(embed)

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

    @boosting.autocomplete("clan")
    @super.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                    clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]

    async def boost_embed(self, list_clans):
        time = datetime.now().timestamp()
        embeds = []
        async for clan in self.bot.coc_client.get_clans(list_clans):
            members = []
            members += [member.tag for member in clan.members]
            players = await self.bot.get_players(tags=members, custom=False)
            clan_boosted = {}
            for player in players:
                troops = player.troop_cls
                troops = player.troops
                for troop in troops:
                    if (troop.is_active):
                        try:
                            if troop.name in SUPER_TROOPS:
                                if troop.name in clan_boosted:
                                    clan_boosted[troop.name].append(player.name)
                                else:
                                    clan_boosted[troop.name] = [player.name]
                        except:
                            pass
            if bool(clan_boosted):
                if len(list_clans) == 1:
                    desc = f"Last Refreshed: <t:{int(time)}:R>"
                else:
                    desc = ""
                embed = disnake.Embed(title=f"{clan.name} Boosted Troops", description=desc, color=disnake.Color.green())
                for troop in clan_boosted:
                    members = clan_boosted[troop]
                    text = ""
                    emoji = emojiDictionary(troop)
                    for member in members:
                        text += f"{member}\n"
                    embed.add_field(name=f"{emoji} {troop}", value=text, inline=False)
                embeds.append(embed)

        if len(embeds) == 0:
            embed = disnake.Embed(
                description=f"No Troops Boosted\nLast Refreshed: <t:{int(time)}:R>",
                color=disnake.Color.red())
            embeds.append(embed)

        return embeds

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "boost" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed = await self.boost_embed([clan.tag])
            await ctx.edit_original_message(embed=embed[0])

def setup(bot: CustomClient):
    bot.add_cog(boost(bot))