import asyncio
import coc
import disnake
import pendulum as pend
import random

from classes.bot import CustomClient
from discord.options import autocomplete, convert
from disnake.ext import commands
from pymongo import UpdateOne
from utility.discord_utils import interaction_handler
from utility.constants import leagues
from .utils import (
    plan_text,
    create_components,
    open_modal,
    main_war_page,
    roster_embed,
    opp_roster_embed,
    attacks_embed,
    opp_overview,
    defenses_embed,
    opp_defenses_embed,
    get_cwl_wars,
    get_latest_war,
    get_wars_at_round,
    component_handler,
    page_manager,
    create_cwl_status,
    cwl_ranking_create,
)


class War(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="war")
    async def war(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @war.sub_command(name="search", description="Search for a clan's war (current or past)")
    async def war_search(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: str = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan),
        previous_wars: str = commands.Param(default=None, autocomplete=autocomplete.previous_wars),
    ):
        await ctx.response.defer()
        if previous_wars is not None:
            war_data = await self.bot.clan_wars.find_one(
                {
                    "$and": [
                        {"custom_id": previous_wars.split("|")[-1].replace(" ", "")},
                        {
                            "$or": [
                                {"data.clan.tag": clan.tag},
                                {"data.opponent.tag": clan.tag},
                            ]
                        },
                    ]
                }
            )
            if war_data is None:
                embed = disnake.Embed(
                    description=f"Previous war for [**{clan.name}**]({clan.share_link}) not found.",
                    color=disnake.Color.green(),
                )
                embed.set_thumbnail(url=clan.badge.large)
                return await ctx.send(embed=embed)
            war = coc.ClanWar(data=war_data.get("data"), client=self.bot.coc_client, clan_tag=clan.tag)
        else:
            war = await self.bot.get_clanwar(clan.tag)
        if war is None or war.start_time is None:
            if not clan.public_war_log:
                embed = disnake.Embed(
                    description=f"[**{clan.name}**]({clan.share_link}) has a private war log.",
                    color=disnake.Color.green(),
                )
                embed.set_thumbnail(url=clan.badge.large)
                return await ctx.send(embed=embed)
            else:
                embed = disnake.Embed(
                    description=f"[**{clan.name}**]({clan.share_link}) is not in War.",
                    color=disnake.Color.green(),
                )
                embed.set_thumbnail(url=clan.badge.large)
                return await ctx.send(embed=embed)
        embed = await main_war_page(bot=self.bot, war=war, war_league=str(clan.war_league))

        main = embed

        select = disnake.ui.Select(
            options=[  # the options in your dropdown
                disnake.SelectOption(
                    label="War Overview",
                    emoji=self.bot.emoji.hashmark.partial_emoji,
                    value="war",
                ),
                disnake.SelectOption(
                    label="Clan Roster",
                    emoji=self.bot.emoji.troop.partial_emoji,
                    value="croster",
                ),
                disnake.SelectOption(
                    label="Opponent Roster",
                    emoji=self.bot.emoji.troop.partial_emoji,
                    value="oroster",
                ),
                disnake.SelectOption(
                    label="Attacks",
                    emoji=self.bot.emoji.wood_swords.partial_emoji,
                    value="attacks",
                ),
                disnake.SelectOption(
                    label="Defenses",
                    emoji=self.bot.emoji.shield.partial_emoji,
                    value="defenses",
                ),
                disnake.SelectOption(
                    label="Opponent Defenses",
                    emoji=self.bot.emoji.clan_castle.partial_emoji,
                    value="odefenses",
                ),
                disnake.SelectOption(
                    label="Opponent Clan Overview",
                    emoji=self.bot.emoji.magnify_glass.partial_emoji,
                    value="opp_over",
                ),
            ],
            placeholder="Choose a page",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.send(embed=embed, components=dropdown)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for(
                    "message_interaction", check=check, timeout=600
                )
            except:
                await msg.edit(components=[])
                break

            if res.values[0] == "war":
                await res.response.edit_message(embed=main)
            elif res.values[0] == "croster":
                embed = await roster_embed(bot=self.bot, war=war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "oroster":
                embed = await opp_roster_embed(bot=self.bot, war=war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "attacks":
                embed = await attacks_embed(bot=self.bot, war=war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "defenses":
                embed = await defenses_embed(bot=self.bot, war=war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "opp_over":
                embed = await opp_overview(bot=self.bot, war=war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "odefenses":
                embed = await opp_defenses_embed(bot=self.bot, war=war)
                await res.response.edit_message(embed=embed)

    @war.sub_command(name="plan", description="Set a war plan")
    async def war_plan(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan),
        option=commands.Param(choices=["Post Plan", "Manual Set"]),
    ):
        war = await self.bot.get_clanwar(clanTag=clan.tag)
        if war is None:
            return await ctx.send(ephemeral=True, content=f"{clan.name} is not currently in a war.")
        await ctx.response.defer()

        result = await self.bot.lineups.find_one(
            {
                "$and": [
                    {
                        "server_id": ctx.guild.id,
                        "clan_tag": clan.tag,
                        "warStart": f"{int(war.preparation_start_time.time.timestamp())}",
                    }
                ]
            }
        )
        if result is None:
            await self.bot.lineups.insert_one(
                {
                    "server_id": ctx.guild.id,
                    "clan_tag": clan.tag,
                    "warStart": f"{int(war.preparation_start_time.time.timestamp())}",
                }
            )
            result = {
                "server_id": ctx.guild.id,
                "clan_tag": clan.tag,
                "warStart": f"{int(war.preparation_start_time.time.timestamp())}",
            }

        if option == "Manual Set":
            await ctx.edit_original_message(
                content=await plan_text(bot=self.bot, plans=result.get("plans", []), war=war),
                components=await create_components(bot=self.bot, plans=result.get("plans", []), war=war),
            )
            done = False
            while not done:
                res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, no_defer=True)
                plan_one, plan_two = await open_modal(bot=self.bot, res=res)
                if plan_one == "" and plan_two == "":
                    continue
                value_tags = set([x.split("_")[-1] for x in res.values])
                to_remove = []
                for plan in result.get("plans", []):
                    if plan.get("player_tag") in value_tags:
                        to_remove.append(
                            UpdateOne(
                                {
                                    "server_id": ctx.guild.id,
                                    "clan_tag": clan.tag,
                                    "warStart": f"{int(war.preparation_start_time.time.timestamp())}",
                                },
                                {"$pull": {"plans": {"player_tag": plan.get("player_tag")}}},
                            )
                        )
                if to_remove:
                    await self.bot.lineups.bulk_write(to_remove)
                to_update = []
                for tag in value_tags:
                    war_member = coc.utils.get(war.clan.members, tag=tag)
                    to_update.append(
                        UpdateOne(
                            {
                                "server_id": ctx.guild.id,
                                "clan_tag": clan.tag,
                                "warStart": f"{int(war.preparation_start_time.time.timestamp())}",
                            },
                            {
                                "$push": {
                                    "plans": {
                                        "name": war_member.name,
                                        "player_tag": war_member.tag,
                                        "townhall_level": war_member.town_hall,
                                        "plan": plan_one,
                                        "plan_two": plan_two,
                                        "map_position": war_member.map_position,
                                    }
                                }
                            },
                        )
                    )

                if to_update:
                    await self.bot.lineups.bulk_write(to_update)

                result = await self.bot.lineups.find_one(
                    {
                        "$and": [
                            {
                                "server_id": ctx.guild.id,
                                "clan_tag": clan.tag,
                                "warStart": f"{int(war.preparation_start_time.time.timestamp())}",
                            }
                        ]
                    }
                )
                await ctx.edit_original_message(
                    content=await plan_text(bot=self.bot, plans=result.get("plans", []), war=war),
                    components=await create_components(bot=self.bot, plans=result.get("plans", []), war=war),
                )
        elif option == "Post Plan":
            result = await self.bot.lineups.find_one(
                {
                    "$and": [
                        {
                            "server_id": ctx.guild.id,
                            "clan_tag": clan.tag,
                            "warStart": f"{int(war.preparation_start_time.time.timestamp())}",
                        }
                    ]
                }
            )
            await ctx.edit_original_message(
                content=await plan_text(bot=self.bot, plans=result.get("plans", []), war=war),
                components=[],
            )

    # CWL COMMANDS
    @commands.slash_command(name="cwl")
    async def cwl(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

    @cwl.sub_command(name="search", description="Search for a clan's cwl (current or past)")
    async def cwl_search(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan),
        season: str = commands.Param(
            default=None,
            convert_defaults=True,
            converter=convert.season,
            autocomplete=autocomplete.season,
        ),
    ):

        (group, clan_league_wars, fetched_clan, war_league) = await get_cwl_wars(bot=self.bot, clan=clan, season=season)

        if not clan_league_wars:
            embed = disnake.Embed(
                description=f"[**{clan.name}**]({clan.share_link}) is not in CWL.",
                color=disnake.Color.green(),
            )
            embed.set_thumbnail(url=clan.badge.large)
            return await ctx.edit_original_message(embed=embed)

        overview_round = get_latest_war(clan_league_wars=clan_league_wars)
        ROUND = overview_round
        CLAN = clan
        PAGE = "cwlround_overview"

        (current_war, next_war) = get_wars_at_round(clan_league_wars=clan_league_wars, round=ROUND)
        dropdown = await component_handler(
            bot=self.bot,
            page=PAGE,
            current_war=current_war,
            next_war=next_war,
            group=group,
            league_wars=clan_league_wars,
            fetched_clan=fetched_clan,
        )
        embeds = await page_manager(
            bot=self.bot,
            page=PAGE,
            group=group,
            war=current_war,
            next_war=next_war,
            league_wars=clan_league_wars,
            clan=CLAN,
            fetched_clan=fetched_clan,
            war_league=war_league,
        )

        await ctx.send(embeds=embeds, components=dropdown)

        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, any_run=True)
            if "cwlchoose_" in res.values[0]:
                clan_tag = (str(res.values[0]).split("_"))[-1]
                CLAN = await self.bot.getClan(clan_tag)
                (group, clan_league_wars, x, y) = await get_cwl_wars(
                    bot=self.bot,
                    clan=CLAN,
                    season=season,
                    group=group,
                    fetched_clan=fetched_clan,
                )
                PAGE = "cwlround_overview"
                ROUND = get_latest_war(clan_league_wars=clan_league_wars)

            elif "cwlround_" in res.values[0]:
                round = res.values[0].split("_")[-1]
                if round != "overview":
                    PAGE = "round"
                    ROUND = int(round) - 1
                else:
                    PAGE = "cwlround_overview"
                    ROUND = overview_round

            elif res.values[0] == "excel":
                await res.send(content="Coming Soon!", ephemeral=True)
                continue
            else:
                PAGE = res.values[0]

            (current_war, next_war) = get_wars_at_round(clan_league_wars=clan_league_wars, round=ROUND)
            embeds = await page_manager(
                bot=self.bot,
                page=PAGE,
                group=group,
                war=current_war,
                next_war=next_war,
                league_wars=clan_league_wars,
                clan=CLAN,
                fetched_clan=fetched_clan,
                war_league=war_league,
            )
            dropdown = await component_handler(
                bot=self.bot,
                page=PAGE,
                current_war=current_war,
                next_war=next_war,
                group=group,
                league_wars=clan_league_wars,
                fetched_clan=fetched_clan,
            )

            await res.edit_original_message(embeds=embeds, components=dropdown)

    @cwl.sub_command(name="rankings", description="Rankings in cwl for a family")
    async def cwl_rankings(self, ctx: disnake.ApplicationCommandInteraction):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        if len(clan_tags) == 0:
            return await ctx.send("No clans linked to this server.")

        clans = await self.bot.get_clans(tags=clan_tags)
        cwl_list = []
        tasks = []
        for clan in clans:
            cwl_list.append([clan.name, clan.tag, clan.war_league.name, clan])
            task = asyncio.ensure_future(cwl_ranking_create(bot=self.bot, clan=clan))
            tasks.append(task)
        rankings = await asyncio.gather(*tasks)
        new_rankings = {}
        for item in rankings:
            new_rankings[list(item.keys())[0]] = list(item.values())[0]

        clans_list = sorted(cwl_list, key=lambda l: l[2], reverse=False)

        main_embed = disnake.Embed(title=f"__**{ctx.guild.name} CWL Rankings**__", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            main_embed.set_thumbnail(url=ctx.guild.icon.url)

        embeds = []
        leagues_present = ["All"]
        for league in leagues:
            text = ""
            for clan in clans_list:
                # print(clan)
                if clan[2] == league:
                    tag = clan[1]
                    placement = new_rankings[tag]
                    if placement is None:
                        continue
                    if len(text) + len(f"{placement}{clan[0]}\n") >= 1020:
                        main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                        text = ""
                    text += f"{placement}{clan[0]}\n"
                if (clan[0] == clans_list[len(clans_list) - 1][0]) and (text != ""):
                    leagues_present.append(league)
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                    embed = disnake.Embed(
                        title=f"__**{ctx.guild.name} {league} Clans**__",
                        description=text,
                        color=disnake.Color.green(),
                    )
                    if ctx.guild.icon is not None:
                        embed.set_thumbnail(url=ctx.guild.icon.url)
                    embeds.append(embed)

        embeds.append(main_embed)
        await ctx.send(embed=main_embed)

    @cwl.sub_command(name="status", description="Spin/War status for a family")
    async def cwl_status(self, ctx: disnake.ApplicationCommandInteraction):
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="",
                emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"cwlstatusfam_",
            )
        )
        embed = await create_cwl_status(bot=self.bot, guild=ctx.guild)
        await ctx.edit_original_message(embed=embed, components=[buttons])

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "cwlstatusfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await create_cwl_status(bot=self.bot, guild=ctx.guild)
            await ctx.edit_original_message(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(War(bot))
