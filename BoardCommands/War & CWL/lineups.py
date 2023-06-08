import coc
import disnake
import pytz

from datetime import datetime
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from typing import List
from coc import utils
from utils.discord_utils import interaction_handler
from CustomClasses.MongoModels import Lineups as LineupsModel, Plans

tiz = pytz.utc
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]

class Lineups(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @commands.slash_command(name="war-plan", description="Set a war plan")
    async def lineup_create(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                            plan = commands.Param(choices=["Mirrors", "Manual Set"])):
        war = await self.bot.get_clanwar(clanTag=clan.tag)
        if war is None:
            return await ctx.send(ephemeral=True, content=f"{clan.name} is not currently in a war.")
        await ctx.response.defer()
        #result = await self.bot.lineups.find

        result: LineupsModel = await self.bot.static_engine.find_one(LineupsModel, LineupsModel.server_id == ctx.guild_id, LineupsModel.clan_tag == clan.tag)
        if result is None:
            await self.bot.static_engine.save(LineupsModel(server_id=ctx.guild_id, clan_tag=clan.tag))
            result = await self.bot.static_engine.find_one(LineupsModel, LineupsModel.server_id == ctx.guild_id,LineupsModel.clan_tag == clan.tag)

        await ctx.edit_original_message(embed=await self.plan_embed(plans=result.plans, war=war),
                                        components=await self.create_components(plans=result.plans, war=war))

        if plan == "Manual Set":
            done = False
            while not done:
                res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, no_defer=True)
                stars, targets = await self.open_modal(res=res)
                value_tags = set([x.split("_")[-1] for x in res.values])
                for plan in result.plans:
                    if plan.player_tag in value_tags:
                        del plan
                for tag in value_tags:
                    war_member = coc.utils.get(war.clan.members, tag=tag)
                    result.plans.append(Plans(name=war_member.name, player_tag=war_member.tag, townhall_level=war_member.town_hall,
                                              stars=stars, targets=targets, map_position=war_member.map_position))
                await self.bot.static_engine.save(result)
                await ctx.edit_original_message(embed=await self.plan_embed(plans=result.plans, war=war),
                                                components=await self.create_components(plans=result.plans, war=war))


    async def plan_embed(self, plans: List[Plans], war: coc.ClanWar) -> disnake.Embed:
        text = ""
        for plan in sorted(plans, key= lambda x: x.map_position):
            text += f"({plan.map_position}){self.bot.fetch_emoji(name=plan.townhall_level)}{plan.name} | {plan.plan_text}\n"

        if text == "":
            text = "No Plans Inserted Yet"
        embed = disnake.Embed(title=f"{war.clan.name} vs {war.opponent.name} WarPlan", description=text)
        return embed

    async def create_components(self, plans: List[Plans], war: coc.ClanWar):
        player_options = []
        player_options_two = []

        for count, player in enumerate(war.clan.members, 1):
            plan = coc.utils.get(plans, player_tag=player.tag)
            plan_done = "✅" if plan is not None else "❌"

            if count <= 25:
                player_options.append(disnake.SelectOption(label=f"({count}.) {player.name} {plan_done}",
                                                            emoji=self.bot.fetch_emoji(name=player.town_hall).partial_emoji,
                                                            value=f"lineup_{player.tag}"))
            else:
                player_options_two.append(disnake.SelectOption(label=f"({count}.) {player.name} {plan_done}",
                                                                emoji=self.bot.fetch_emoji(
                                                                name=player.town_hall).partial_emoji,
                                                                value=f"lineup_{player.tag}"))

        player_select = disnake.ui.Select(
            options=player_options,
            placeholder=f"Set Plan for Players",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(player_options),  # the maximum number of options a user can select
        )
        if player_options_two:
            player_select_two = disnake.ui.Select(
                options=player_options_two,
                placeholder=f"Set Plan for Players #2",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(player_options_two),  # the maximum number of options a user can select
            )
            return [disnake.ui.ActionRow(player_select), disnake.ui.ActionRow(player_select_two)]
        return [disnake.ui.ActionRow(player_select)]

    async def open_modal(self, res: disnake.MessageInteraction):
        components = [
            disnake.ui.TextInput(
                label=f"Expected Stars",
                placeholder='can be a range like "1-2" or single like "2"',
                custom_id=f"stars",
                required=True,
                style=disnake.TextInputStyle.single_line,
                max_length=50,
            ),
            disnake.ui.TextInput(
                label=f"Enter the target(s)",
                placeholder='can be a range like "1-10" or single like "5"',
                custom_id=f"target",
                required=True,
                style=disnake.TextInputStyle.single_line,
                max_length=50,
            )
        ]
        custom_id = f"warplan-{int(datetime.now().timestamp())}"
        await res.response.send_modal(
            title="Enter Plan for Selected Players",
            custom_id=custom_id,
            components=components)

        def check(modal_res: disnake.ModalInteraction):
            return res.author.id == modal_res.author.id and custom_id == modal_res.custom_id

        modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
            "modal_submit",
            check=check,
            timeout=300,
        )
        await modal_inter.send(content="Added.", ephemeral=True, delete_after=1)
        stars = modal_inter.text_values["stars"]
        target = modal_inter.text_values["target"]
        return (stars, target)




    @lineup_create.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id}).sort("name", 1)
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=5)
                for clan in results:
                    league = str(clan.war_league).replace("League ", "")
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]



def setup(bot: CustomClient):
    bot.add_cog(Lineups(bot))
