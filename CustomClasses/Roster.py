import disnake
import coc
import emoji
import io

from urllib.request import Request, urlopen
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer, HitRate
from datetime import datetime, timedelta
from Exceptions import *
from collections import defaultdict
from disnake.ext import commands

class Roster():
    def __init__(self, bot: CustomClient):
        self.roster_result = None
        self.bot = bot

    async def create_roster(self, guild: disnake.Guild, clan: coc.Clan, alias: str, add_members: bool):
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id":guild.id}, {"alias": alias}]})
        if roster_result is not None:
            raise RosterAliasAlreadyExists
        roster_result = await self.bot.rosters.insert_one({
            "clan_name" : clan.name,
            "clan_tag" : clan.tag,
            "clan_badge" : clan.badge.url,
            "members" : [],
            "alias" : alias,
            "server_id" : guild.id,
            "th_restriction" : "1-max"
        })
        inserted_id = roster_result.inserted_id
        roster_result = await self.bot.rosters.find_one({"_id" : inserted_id})
        self.roster_result = roster_result
        if add_members:
            players = await self.bot.get_players(tags=[member.tag for member in clan.members])
            for player in players:
                await self.add_member(player)
            roster_result = await self.bot.rosters.find_one({"_id": inserted_id})
            self.roster_result = roster_result

    async def find_roster(self, guild: disnake.Guild, alias: str):
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": guild.id}, {"alias": alias}]})
        if roster_result is None:
            raise RosterDoesNotExist
        self.roster_result = roster_result

    async def clear_roster(self):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"members": []}})

    async def delete(self):
        await self.bot.rosters.delete_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})

    async def embed(self, move_text: str = ""):
        members = self.roster_result.get("members")
        if not members:
            embed = disnake.Embed(title=f"__{self.roster_result.get('alias')} Roster__", description="No roster members.")
            embed.set_footer(text=f"Linked to {self.roster_result.get('clan_name')}", icon_url=self.roster_result.get("clan_badge"))
            return embed

        roster_text = []

        thcount = defaultdict(int)
        group_text = defaultdict(list)
        subs = 0
        columns = self.columns
        emojis_columns = ["Townhall Level", "War Opt Status"]
        for member in members:
            text = ""
            all_fields = self.all_fields(member)
            for x, column in enumerate(columns):
                col = self.column_to_item(member, column, all_fields)
                #if its the first column, and the column isnt an emoji, add tick
                if columns[0] not in emojis_columns and x == 0:
                    text = f"`{text}"

                # if its not first column, and the previous column is an emoji, add tick
                if x != 0 and columns[x - 1] in emojis_columns:
                    text += "`"

                #add text, we have backticks
                text += f"{col}"
                if x != 0 and columns[x - 1] not in emojis_columns:
                    text += " "
                if x + 1 < len(columns) and columns[x + 1] in emojis_columns:
                    text += "`"
                if x + 1 == len(columns) and columns[x] not in emojis_columns:
                    text += "`"

            if member.get("sub") is True:
                group_text["SUBS"].append([f"{text}\n"] + all_fields)
            elif member.get("group") not in ["No Group", "Sub", None]:
                group_text[str(member.get("group")).upper()].append([f"{text}\n"] + all_fields)
            else:
                roster_text.append([f"{text}\n"] + all_fields)
            thcount[member.get('townhall')] += 1

        convert_column = {"Name": "NAME", "Player Tag": "TAG", "Heroes": "HEROES", "Townhall Level": "TH",
                          "Discord": "DISCORD", "30 Day Hitrate": "HITRATE",
                          "Current Clan": "CLAN", "War Opt Status": "WAROPT", "Trophies": "TROPHIES",  "Clan Tag" : "CLAN TAG"}
        legend = " | ".join(convert_column[column] for column in columns)
        roster_text = self.sort_(roster_text)
        r_text = ""
        for count, text in enumerate(roster_text):
            text = text[0]
            count = f"{count + 1}".ljust(2)
            if columns[0] not in emojis_columns:
                co = f"`{count} "
                text = text[1:]
            else:
                co = f"`{count}`"
            r_text += f"{co}{text}"
        roster_text = f"`Legend: {legend}`\n{r_text}"
        if list(group_text.keys()) != []:
            for group_name, text in group_text.items():
                sub_text = self.sort_(text)
                s_text = ""
                for count, text in enumerate(sub_text):
                    text = text[0]
                    count = f"{count + 1}".ljust(2)
                    if columns[0] not in emojis_columns:
                        co = f"`{count} "
                        text = text[1:]
                    else:
                        co = f"`{count}`"
                    s_text += f"{co}{text}"
                roster_text = f"{roster_text}\n**{group_name}**\n{s_text}"

        embed = disnake.Embed(title=f"__{self.roster_result.get('alias')} Roster__", description=roster_text)
        footer_text = "".join(f"Th{index}: {th} " for index, th in sorted(thcount.items(), reverse=True) if th != 0)
        embed.set_footer(text=f"{footer_text}\nLinked to {self.roster_result.get('clan_name')}\nTh{self.th_min}-Th{self.th_max} | {self.roster_size} Account Limit\n{move_text}", icon_url=self.roster_result.get("clan_badge"))
        if self.image is not None and move_text == "":
            embed.set_image(url=self.image)
        return embed


    def column_to_item(self, player_dict, field, all_fields):
        #["Name", "Player Tag", "Heroes", "Townhall Level", "Discord", "30 Day Hitrate", "Current Clan", "Clan Tag, "War Opt Status", "Trophies"]

        if field == "Name":
            name = player_dict.get('name')
            for char in ["`", "*", "_", "~", "ッ"]:
                name = name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:11]
            name = name.ljust(12)
            return name
        elif field == "Player Tag":
            return player_dict.get("tag").ljust(10)
        elif field == "Heroes":
            return player_dict.get("hero_lvs")
        elif field == "Townhall Level":
            return self.bot.fetch_emoji(name=player_dict.get('townhall')).emoji_string
        elif field == "Current Clan":
            name = str(player_dict.get("current_clan"))
            for char in ["`", "*", "_", "~", "ッ"]:
                name = name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:15]
            name = name.ljust(16)
            return name
        elif field == "Discord":
            return str(player_dict.get("discord"))[:14].ljust(15)
        elif field == "30 Day Hitrate":
            hr = player_dict.get("hitrate")
            return "0.0%" if hr is None else f"{hr}%"
        elif field == "War Opt Status":
            wp = player_dict.get("war_pref")
            if wp is True:
                if "Townhall Level" in all_fields:
                    return "IN "
                else:
                    return "<:opt_in:944905885367537685>"
            elif wp is False:
                if "Townhall Level" in all_fields:
                    return "OUT"
                else:
                    return "<:opt_out:944905931265810432>"
            else:
                return None
        elif field == "Trophies":
            return player_dict.get("trophies")
        elif field == "Clan Tag":
            return str(player_dict.get("current_clan_tag"))

    def sort_(self, text_list):
        master_col = ["Name", "Player Tag", "Heroes", "Townhall Level", "Current Clan", "Clan Tag", "Discord", "30 Day Hitrate",
         "War Opt Status", "Trophies"]
        spots = []
        for column in self.sort:
            spots.append(master_col.index(column))
        text_list = sorted(text_list, key=lambda l: tuple(l[spot_idx + 1] for spot_idx in spots), reverse=False)
        return text_list

    def all_fields(self, player_dict):
        #["Name", "Player Tag", "Heroes", "Townhall Level", "Discord", "30 Day Hitrate", "Current Clan", "Clan Tag" "War Opt Status", "Trophies"]
        item_list = []

        name = player_dict.get('name')
        for char in ["`", "*", "_", "~", "ッ"]:
            name = name.replace(char, "", 10)
        name = emoji.replace_emoji(name, "")
        name = name[:12]
        name = name.ljust(12)
        item_list.append(name.upper())

        item_list.append(player_dict.get("tag").ljust(10))
        item_list.append(player_dict.get("hero_lvs") * -1)
        item_list.append(player_dict.get('townhall') * -1)

        name = str(player_dict.get("current_clan"))
        for char in ["`", "*", "_", "~", "ッ"]:
            name = name.replace(char, "", 10)
        name = emoji.replace_emoji(name, "")
        name = name[:12]
        name = name.ljust(12)
        item_list.append(name.upper())

        clan_tag =str(player_dict.get("current_clan_tag"))
        item_list.append(clan_tag)

        item_list.append(str(player_dict.get("discord"))[:12].ljust(12))
        hr = player_dict.get("hitrate")
        if hr is None:
            item_list.append(0)
        else:
            item_list.append(hr * -1)
        item_list.append(str(player_dict.get("war_pref")))
        if player_dict.get("trophies") is None:
            item_list.append(0)
        else:
            item_list.append(player_dict.get("trophies") * -1)
        return item_list

    async def set_missing_text(self, text: str):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"missing_text": text}})
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})
        self.roster_result = roster_result

    async def missing_embed(self, reverse: bool):
        missing = await self.missing_list(reverse=reverse)
        if not missing:
            if not reverse:
                embed = disnake.Embed(description=f"**Roster is not missing in any players in {self.roster_result.get('clan_name')}**", color=disnake.Color.red())
            else:
                embed = disnake.Embed(
                    description=f"**Roster has no out of place players in {self.roster_result.get('clan_name')}**",
                    color=disnake.Color.red())
            return embed
        longest_tag = 0
        for member in missing:
            tag = member["tag"]
            if len(tag) > longest_tag:
                longest_tag = len(tag)

        missing_text = ""
        for member in missing:
            name = member["name"]
            for char in ["`", "*", "_", "~", "ッ"]:
                name = name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:12]
            name = name.ljust(12)
            tag = str(member["tag"]).ljust(longest_tag)
            missing_text += f"{self.bot.fetch_emoji(name=member['townhall'])}`{name} {tag}`\n"

        tag = "TAG".ljust(longest_tag)
        missing_text = f"`TH NAME         {tag}`\n{missing_text}"
        miss_text = "Missing"
        if reverse:
            miss_text = "Out of Place"
        embed = disnake.Embed(title=f"**{self.roster_result.get('alias')} Roster {miss_text} Members**", description=missing_text)
        embed.set_footer(text=f"Linked to {self.roster_result.get('clan_name')}", icon_url=self.roster_result.get("clan_badge"))
        return embed

    async def refresh_roster(self, force=False):
        members = self.players
        if not members:
            return
        columns = self.columns
        members = await self.bot.get_players(tags=[member.get("tag") for member in members], custom=("30 Day Hitrate" in columns))
        has_ran = False
        if "Discord" in columns:
            has_ran = True
            tag_to_id = await self.bot.link_client.get_links(*[member.tag for member in members])
            tag_to_id = dict(tag_to_id)
            for member in members:
                discord_user = await self.bot.getch_user(tag_to_id[member.tag])
                await self.update_member(player=member, field="discord", field_value=str(discord_user))

        if "30 Day Hitrate" in columns:
            has_ran = True
            for member in members:
                member: MyCustomPlayer
                if member is None:
                    continue
                hr = await member.hit_rate(start_timestamp=int((datetime.utcnow() - timedelta(days=30)).timestamp()), end_timestamp=int(datetime.utcnow().timestamp()))
                await self.update_member(player=member, field="hitrate", field_value=round(((hr[0].average_triples) * 100), 1))

        if has_ran is False:
            for player in members:
                await self.update_member(player=player)

    async def add_member(self, player: coc.Player, sub=False, group="No Group"):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        if len(roster_member_tags) == self.roster_size:
            raise RosterSizeLimit
        if player.tag in roster_member_tags:
            raise PlayerAlreadyInRoster
        hero_lvs = sum(hero.level for hero in player.heroes if hero.village == "home")
        current_clan = "No Clan"
        clan_tag = "No Clan"
        if player.clan is not None:
            current_clan = player.clan.name
            clan_tag = player.clan.tag
        war_pref = player.war_opted_in
        if war_pref is None:
            war_pref = False
        discord = await self.bot.link_client.get_link(player.tag)
        #["Name", "Player Tag", "Heroes", "Townhall Level", "Discord", "30 Day Hitrate", "Current Clan", "Clan Tag", "War Opt Status", "Trophies"]
        await self.bot.rosters.update_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
                                          {"$push": {"members": {"name": player.name, "tag": player.tag,
                                                                  "hero_lvs": hero_lvs, "townhall": player.town_hall, "discord" : discord, "hitrate" : None,
                                                                 "current_clan": current_clan, "current_clan_tag" : clan_tag,
                                                                 "war_pref": war_pref, "trophies": player.trophies, "sub" : sub, "group" : group}}})
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})
        self.roster_result = roster_result

    async def update_member(self, player: coc.Player, field = None, field_value = None):
        hero_lvs = sum(hero.level for hero in player.heroes if hero.village == "home")
        current_clan = "No Clan"
        clan_tag = "No Clan"
        if player.clan is not None:
            current_clan = player.clan.name
            clan_tag = player.clan.tag
        war_pref = player.war_opted_in
        if war_pref is None:
            war_pref = False

        if field is not None:
            await self.bot.rosters.update_one(
                {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}, {"members.tag" : player.tag}]},
                {"$set": {"members.$.townhall": player.town_hall, "members.$.hero_lvs": hero_lvs,
                                       "members.$.current_clan": current_clan, "members.$.current_clan_tag" : clan_tag,
                                       "members.$.war_pref": war_pref, "members.$.trophies" : player.trophies, f"members.$.{field}": field_value}})
        else:
            await self.bot.rosters.update_one(
                {"$and": [{"server_id": self.roster_result.get("server_id")},
                          {"alias": self.roster_result.get("alias")}, {"members.tag": player.tag}]},
                {"$set": {"members.$.townhall": player.town_hall, "members.$.hero_lvs": hero_lvs,
                           "members.$.current_clan": current_clan, "members.$.current_clan_tag" : clan_tag,
                           "members.$.war_pref": war_pref, "members.$.trophies": player.trophies}})

        roster_result = await self.bot.rosters.find_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})
        self.roster_result = roster_result

    async def remove_member(self, player: coc.Player):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        if player.tag not in roster_member_tags:
            raise PlayerNotInRoster
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$pull": {"members": {"tag": player.tag}}})
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})
        self.roster_result = roster_result

    async def move_member(self, player: coc.Player, new_roster, group = "No Group"):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        if player.tag not in roster_member_tags:
            raise PlayerNotInRoster
        new_roster_member_tags = [member.get("tag") for member in new_roster.roster_result.get("members")]
        if self.roster_result.get("alias") != new_roster.roster_result.get("alias"):
            if player.tag in new_roster_member_tags:
                raise PlayerAlreadyInRoster
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$pull": {"members": {"tag": player.tag}}})
        hero_lvs = sum(hero.level for hero in player.heroes if hero.village == "home")
        current_clan = "No Clan"
        clan_tag = "No Clan"
        if player.clan is not None:
            current_clan = player.clan.name
            clan_tag = player.clan.tag
        war_pref = player.war_opted_in
        if war_pref is None:
            war_pref = False

        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": new_roster.roster_result.get("alias")}]},
            {"$push": {"members": {"name": player.name, "tag": player.tag,
                                   "hero_lvs": hero_lvs, "townhall": player.town_hall, "discord": None, "hitrate": None,
                                   "current_clan": current_clan, "current_clan_tag": clan_tag,
                                   "war_pref": war_pref, "trophies": player.trophies, "sub": (group == "Sub"), "group": group}}})

    async def restrict_th(self, min:int = 0, max="max"):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"th_restriction": f"{min}-{max}"}})

    async def restrict_size(self, roster_size: int):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"roster_size": roster_size}})

    async def rename(self, new_name):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"alias": new_name}})

    async def change_linked_clan(self, new_clan: coc.Clan):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"clan_name": new_clan.name}})
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"clan_tag": new_clan.tag}})
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"clan_badge": new_clan.badge.url}})

    async def set_image(self, url: str):
        try:
            req = Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})
            f = io.BytesIO(urlopen(req).read())
            file = disnake.File(fp=f, filename="pic.png")
            pic_channel = await self.bot.fetch_channel(884951195406458900)
            msg = await pic_channel.send(file=file)
            pic = msg.attachments[0].url
        except:
            pic = "https://cdn.discordapp.com/attachments/1028905437300531271/1028905577662922772/unknown.png"
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"image": pic}})

    async def set_columns(self, columns: list):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"columns": columns}})

    async def set_role(self, role: disnake.Role):
        if role is not None:
            await self.bot.rosters.update_one(
                {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
                {"$set": {"role": role.id}})
        else:
            await self.bot.rosters.update_one(
                {"$and": [{"server_id": self.roster_result.get("server_id")},
                          {"alias": self.roster_result.get("alias")}]},
                {"$set": {"role": None}})

    async def set_sort(self, columns: list):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"sort": columns}})

    async def other_rosters(self):
        guild = self.roster_result.get("server_id")
        aliases: list = await self.bot.rosters.distinct("alias", filter={"server_id": guild})
        aliases.remove(self.roster_result.get("alias"))
        return aliases

    async def mode_components(self, mode: str, player_page: 0):
        other_rosters = await self.other_rosters()
        roster_options = []
        for roster in other_rosters:
            roster_options.append(disnake.SelectOption(label=f"{roster}", emoji=self.bot.emoji.troop.partial_emoji, value=f"roster_{roster}"))
        if roster_options != []:
            roster_select = disnake.ui.Select(
                options=roster_options,
                placeholder="Roster to Edit",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
        if mode == "move":
            button_text = "Remove Player Mode"
            mode_text = "mode_remove"
            color = disnake.ButtonStyle.red
        elif mode == "remove":
            button_text = "Move Player Mode"
            mode_text = "mode_move"
            color = disnake.ButtonStyle.green

        mode_buttons = [
            disnake.ui.Button(label=button_text, emoji=self.bot.emoji.gear.partial_emoji,
                              style=color,
                              custom_id=mode_text)
        ]
        buttons = disnake.ui.ActionRow()
        for button in mode_buttons:
            buttons.append_item(button)

        player_options = []
        length = 24
        if player_page >= 1:
            length = length - 1
        players = self.players[(length*player_page):(length*player_page) + length]
        if player_page >= 1:
            player_options.append(disnake.SelectOption(label=f"Previous 25 Players", emoji=self.bot.emoji.back.partial_emoji, value=f"players_{player_page - 1}"))
        for count, player in enumerate(players):
            player_options.append(disnake.SelectOption(label=f"{player.get('name')}",
                                                       emoji=self.bot.fetch_emoji(name=player.get('townhall')).partial_emoji,
                                                       value=f"edit_{player.get('tag')}"))
        if len(players) == length and (len(self.players) > (length * player_page) + length):
            player_options.append(disnake.SelectOption(label=f"Next 25 Players", emoji=self.bot.emoji.forward.partial_emoji, value=f"players_{player_page + 1}"))

        player_select = disnake.ui.Select(
            options=player_options,
            placeholder=f"Select Player(s) to {mode}",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(players),  # the maximum number of options a user can select
        )

        if len(roster_options) > 0:
            dropdown = [disnake.ui.ActionRow(roster_select), disnake.ui.ActionRow(player_select)]
        else:
            dropdown = [disnake.ui.ActionRow(player_select)]

        if mode == "move":
            roster_options = []
            other_rosters += [self.roster_result.get("alias")]
            for roster in other_rosters:
                roster_options.append(disnake.SelectOption(label=f"{roster}", emoji=self.bot.emoji.troop.partial_emoji,
                                                           value=f"rostermove_{roster}"))

            roster_select = disnake.ui.Select(
                options=roster_options,
                placeholder="Select Roster To Move To",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            dropdown.append(disnake.ui.ActionRow(roster_select))

            grouping_options = []
            for group in await self.grouping:
                grouping_options.append(disnake.SelectOption(label=f"{group}", emoji=self.bot.emoji.pin.partial_emoji,
                                                           value=f"rostergroup_{group}"))

            group_select = disnake.ui.Select(
                options=grouping_options,
                placeholder="Select Grouping to Move Player to",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            dropdown.append(disnake.ui.ActionRow(group_select))

        dropdown.append(buttons)
        if not self.players:
            dropdown = [dropdown[0], dropdown[-1]]
        return dropdown


    @property
    def players(self):
        return self.roster_result.get("members")

    @property
    def th_min(self):
        restriction = self.roster_result.get("th_restriction")
        restriction = restriction.split("-")
        return int(restriction[0])

    @property
    def th_max(self):
        restriction = self.roster_result.get("th_restriction")
        restriction = restriction.split("-")
        if restriction[1] == "max":
            max = 15
        else:
            max = int(restriction[1])

        return max

    @property
    def roster_size(self):
        if self.roster_result.get("roster_size") is None:
            return 50
        return self.roster_result.get('roster_size')

    @property
    def missing_text(self):
        if self.roster_result.get("missing_text") is None:
            return ""
        return f"**{self.roster_result.get('missing_text')}**" + "\n\n"

    @property
    def columns(self):
        if self.roster_result.get("columns") is None:
            return ["Townhall Level", "Name", "Player Tag", "Heroes"]
        return self.roster_result.get('columns')

    @property
    def sort(self):
        if self.roster_result.get("sort") is None:
            return ["Townhall Level", "Name", "Heroes", "Player Tag"]
        return self.roster_result.get('sort')

    @property
    def image(self):
        if self.roster_result.get("image") is None:
            return None
        return self.roster_result.get('image')

    @property
    def role(self):
        return self.roster_result.get("role")

    @property
    async def grouping(self):
        guild_id = self.roster_result.get("server_id")
        results = await self.bot.server_db.find_one({"server": guild_id})
        groups = results.get("player_groups")
        if groups is None:
            return ["No Group", "Sub"]
        return ["No Group", "Sub"] + groups


    async def missing_list(self, reverse: bool):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        clan = await self.bot.getClan(self.roster_result.get("clan_tag"))
        clan_members = [member.tag for member in clan.members]

        missing_tags = []
        if not reverse:
            missing_tags = list(set(roster_member_tags).difference(clan_members))
            return [member for member in roster_members if member.get("tag") in missing_tags]
        else:
            for tag in clan_members:
                if tag not in roster_member_tags:
                    missing_tags.append(tag)
            hold_player = []
            async for player in self.bot.coc_client.get_players(missing_tags):
                hold_player.append(player)
            return [{"name": player.name, "tag": player.tag,"townhall": player.town_hall} for player in hold_player]




