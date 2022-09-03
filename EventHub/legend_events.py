import disnake
import calendar

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import player_ee
from CustomClasses.CustomPlayer import MyCustomPlayer
from datetime import datetime

class LegendEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("trophies", self.legend_event)

    async def legend_event(self, event):
        trophy_change = event["new_player"]["trophies"] - event["old_player"]["trophies"]
        attack = trophy_change >= 1

        try:
            clan_tag = event["new_player"]["clan"]["tag"]
        except:
            return

        player_tag = event["new_player"]["tag"]
        player: MyCustomPlayer = await self.bot.getPlayer(player_tag=player_tag, custom=True)

        tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
        for cc in await tracked.to_list(length=limit):
            try:
                legendlog = cc.get("legend_log")
                server = cc.get("server")
                server = await self.bot.fetch_guild(server)
                try:
                    legendlog_channel = await server.fetch_channel(legendlog.get("channel"))
                except:
                    legendlog_channel = None
                legendlog_message = legendlog.get("message")
                legendlog_date = legendlog.get("date")

                try:
                    legendlog_message = await legendlog_channel.fetch_message(legendlog_message)
                except:
                    legendlog_message = None

                if legendlog_date != self.bot.gen_legend_date():
                    legendlog_message = None

                embeds: list = await self.create_embeds(clan_tag, player, attack, legendlog_message is None, legendlog_message)
                if legendlog_message is None:
                    message = await legendlog_channel.send(embeds=embeds)
                    await self.bot.clan_db.update_one({"$and": [
                            {"tag": clan_tag},
                            {"server": server.id}
                        ]},
                        {"$set" : {"legend_log.date" : self.bot.gen_legend_date(), "legend_log.message" : message.id}})
                else:
                    await legendlog_message.edit(embeds=embeds)

            except:
                continue

    async def edit_embeds(self, old_embeds: list, player: MyCustomPlayer):
        return []


    async def create_embeds(self, clan_tag, og_player, attack, new, message):
        clan = await self.bot.getClan(clan_tag)
        member_tags = [member.tag for member in clan.members]
        clan_members = await self.bot.get_players(tags=member_tags, custom=True)

        ranking = []
        for member in clan_members:
            member: MyCustomPlayer

            if not member.is_legends():
                continue

            if member.results is None:
                await member.track()
            import emoji
            name = emoji.get_emoji_regexp().sub('', member.name)
            legend_day = member.legend_day()
            ranking.append([name, member.trophy_start(), legend_day.attack_sum, legend_day.num_attacks.superscript,
                            legend_day.defense_sum, legend_day.num_defenses.superscript, member.trophies])

        ranking = sorted(ranking, key=lambda l: l[6], reverse=True)

        text = ""
        embeds = []
        x = 0
        date_str = datetime.utcnow().date()
        month = calendar.month_name[date_str.month]
        for player in ranking:
            name = player[0]
            hits = player[2]
            numHits = player[3]
            defs = player[4]
            numDefs = player[5]
            trophies = player[6]
            text += f"\u200e**<:trophyy:849144172698402817>{trophies} | \u200e{name}**\n➼ <:cw:948845649229647952> {hits}{numHits} <:sh:948845842809360424> {defs}{numDefs}\n"


            x += 1
            if x == 25:
                embed = disnake.Embed(title=f"**{clan.name} Legend Log | {month} {date_str.day}, {date_str.year}**", description=text)
                embed.set_thumbnail(url=clan.badge.large)
                x = 0
                embeds.append(embed)
                text = ""
        if text != "":
            embed = disnake.Embed(description=text)
            embeds.append(embed)

        legend_day = og_player.legend_day()
        if attack:
            change = f"+{legend_day.attacks[-1]} | {og_player.name}"
            emoji = "<:warwon:932212939899949176>"
        else:
            change = f"-{legend_day.defenses[-1]}"
            emoji = "<:warlost:932212154164183081>"

        if new:
            embed = disnake.Embed(title="**Most Recent Hits/Defenses**",
                                  description=f"{emoji} {change}\n")
            embeds.append(embed)
        else:
            msg_embeds = message.embeds
            new_embed = msg_embeds[-1]
            description = new_embed.description
            description = description.split("\n")
            if len(description) == 10:
                description = description[1:]
            description.append(f"{emoji} {change}\n")
            description = "\n".join(description)
            new_embed.description = description
            embeds.append(new_embed)

        return embeds



def setup(bot: CustomClient):
    bot.add_cog(LegendEvents(bot))