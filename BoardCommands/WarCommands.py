import datetime

import coc
import disnake
import pytz
import asyncio
import time as te
from utils.search import search_results
from disnake.ext import commands
from Assets.emojiDictionary import emojiDictionary
from collections import defaultdict
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from utils.clash import cwl_league_emojis
from coc.miscmodels import Timestamp

tiz = pytz.utc
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]

class War(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @commands.slash_command(name= "war", description="Stats & info for a clans current war")
    async def clan_war(self, ctx: disnake.ApplicationCommandInteraction, clan:str, previous_wars:str = None):
        await ctx.response.defer()
        clan = await self.bot.getClan(clan_tag=clan)
        if clan is None:
            return await ctx.send("Not a valid clan tag.")
        if previous_wars is not None:
            war_data = await self.bot.clan_wars.find_one({"custom_id" : previous_wars.split("|")[-1].replace(" ","")})
            if war_data is None:
                embed = disnake.Embed(description=f"Previous war for [**{clan.name}**]({clan.share_link}) not found.",
                                      color=disnake.Color.green())
                embed.set_thumbnail(url=clan.badge.large)
                return await ctx.send(embed=embed)
            war = coc.ClanWar(data=war_data.get("data"), client=self.bot.coc_client, clan_tag=clan.tag)
        else:
            war = await self.bot.get_clanwar(clan.tag)
        if war is None or war.start_time is None:
            if not clan.public_war_log:
                embed = disnake.Embed(description=f"[**{clan.name}**]({clan.share_link}) has a private war log.",
                                      color=disnake.Color.green())
                embed.set_thumbnail(url=clan.badge.large)
                return await ctx.send(embed=embed)
            else:
                embed = disnake.Embed(description=f"[**{clan.name}**]({clan.share_link}) is not in War.",
                                      color=disnake.Color.green())
                embed.set_thumbnail(url=clan.badge.large)
                return await ctx.send(embed=embed)

        disc = "<:map:944913638500761600>"
        emoji = ''.join(filter(str.isdigit, disc))
        emoji = self.bot.get_emoji(int(emoji))
        emoji = disnake.PartialEmoji(name=emoji.name, id=emoji.id)


        troop = "<:troop:861797310224400434>"
        troop = ''.join(filter(str.isdigit, troop))
        troop = self.bot.get_emoji(int(troop))
        troop = disnake.PartialEmoji(name=troop.name, id=troop.id)

        swords = "<a:swords:944894455633297418>"
        swords = ''.join(filter(str.isdigit, swords))
        swords = self.bot.get_emoji(int(swords))
        swords = disnake.PartialEmoji(name=swords.name, id=swords.id, animated=True)

        shield = "<:clash:877681427129458739>"
        shield = ''.join(filter(str.isdigit, shield))
        shield = self.bot.get_emoji(int(shield))
        shield = disnake.PartialEmoji(name=shield.name, id=shield.id)

        magnify = "<:magnify:944914253171810384>"
        magnify = ''.join(filter(str.isdigit, magnify))
        magnify = self.bot.get_emoji(int(magnify))
        magnify = disnake.PartialEmoji(name=magnify.name, id=magnify.id)

        surr = "<:surrender:947978096034869249>"
        surr = ''.join(filter(str.isdigit, surr))
        surr = self.bot.get_emoji(int(surr))
        surr = disnake.PartialEmoji(name=surr.name, id=surr.id)

        embed = await self.main_war_page(war=war, clan=clan)

        main = embed

        select = disnake.ui.Select(
            options=[  # the options in your dropdown
                disnake.SelectOption(label="War Overview", emoji=emoji, value="war"),
                disnake.SelectOption(label="Clan Roster", emoji=troop, value="croster"),
                disnake.SelectOption(label="Opponent Roster", emoji=troop, value="oroster"),
                disnake.SelectOption(label="Attacks", emoji=swords, value="attacks"),
                disnake.SelectOption(label="Defenses", emoji=shield, value="defenses"),
                disnake.SelectOption(label="Opponent Defenses", emoji=surr, value="odefenses"),
                disnake.SelectOption(label="Opponent Clan Overview", emoji=magnify, value="opp_over")
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
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.values[0] == "war":
                await res.response.edit_message(embed=main)
            elif res.values[0] == "croster":
                embed = await self.roster_embed(war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "oroster":
                embed = await self.opp_roster_embed(war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "attacks":
                embed = await self.attacks_embed(war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "defenses":
                embed = await self.defenses_embed(war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "opp_over":
                embed = await self.opp_overview(war)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "odefenses":
                embed = await self.opp_defenses_embed(war)
                await res.response.edit_message(embed=embed)



    @clan_war.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if clan_list == [] and len(query) >= 3:
            clan = await self.bot.getClan(query)
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=25)
                for clan in results:
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {clan.war_league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]

    @clan_war.autocomplete("previous_wars")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        if ctx.filled_options["clan"] != "":
            clan = await self.bot.getClan(ctx.filled_options["clan"])
            results = await self.bot.clan_wars.find({"$or" : [{"data.clan.tag" : clan.tag}, {"data.opponent.tag" : clan.tag}]}).sort("data.endTime", -1).limit(25).to_list(length=25)
            options = []
            previous = set()
            prep_list = [
                5 * 60,
                15 * 60,
                30 * 60,
                60 * 60,
                2 * 60 * 60,
                4 * 60 * 60,
                6 * 60 * 60,
                8 * 60 * 60,
                12 * 60 * 60,
                16 * 60 * 60,
                20 * 60 * 60,
                24 * 60 * 60,
            ]

            for result in results:
                custom_id = result.get("custom_id")
                clan_name = result.get("data").get("clan").get("name")
                clan_tag = result.get("data").get("clan").get("tag")
                opponent_name = result.get("data").get("opponent").get("name")
                end_time = result.get("data").get("endTime")
                end_time = Timestamp(data=end_time)
                unique_id = result.get("war_id")
                if unique_id in previous:
                    continue
                previous.add(unique_id)
                days_ago = abs(end_time.seconds_until) // (24 * 3600)
                if days_ago == 0:
                    t = days_ago % (24 * 3600)
                    hour = t // 3600
                    time_text = f"{hour}H ago"
                else:
                    time_text = f"{days_ago}D ago"

                if result.get("data").get("tag") is not None:
                    type = "CWL"
                elif (Timestamp(data=result.get("data").get("startTime")).time - Timestamp(data=result.get("data").get("preparationStartTime")).time).seconds in prep_list:
                    type = "FW"
                else:
                    type = "REG"

                if clan_tag == clan.tag:
                    text = f"{opponent_name} | {time_text} | {type} | {custom_id}"
                else:
                    text = f"{clan_name} | \u200e{time_text} | {type} | {custom_id}"
                if query.lower() in text.lower():
                    options.append(text)
            return options



def setup(bot: CustomClient):
    bot.add_cog(War(bot))