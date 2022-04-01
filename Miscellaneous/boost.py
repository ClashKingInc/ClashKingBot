
import disnake
from disnake.ext import commands
from utils.clashClient import client, getClan

from disnake_slash.utils.manage_components import create_button, wait_for_component, create_actionrow
from disnake_slash.model import ButtonStyle

SUPER_TROOPS = ["Super Barbarian", "Super Archer", "Super Giant", "Sneaky Goblin", "Super Wall Breaker", "Rocket Balloon", "Super Wizard", "Inferno Dragon",
                "Super Minion", "Super Valkyrie", "Super Witch", "Ice Hound", "Super Bowler", "Super Dragon"]
REG_VERSION = ["Barbarian", "Archer", "Giant", "Goblin", "Wall Breaker", "Balloon", "Wizard", "Baby Dragon",
                "Minion", "Valkyrie", "Witch", "Lava Hound", "Bowler", "Dragon"]

options = [["barb", "barbs"], ["arch", "archers", "archer"], ["giant", "giants"], ["gob", "goblin", "gobs", "goblins"],
           ["wb", "wallbreaker", "wbs", "wallbreakers"],["loons", "loon", "balloon", "balloons"],
           ["wiz", "wizard", "wizards"], ["inferno", "babydrag", "bdrag"],
           ["minion", "minions"],["valk", "valks"],
           [ "witch", "witches"], ["icehound", "hound", "hounds"], ["bowler","bowlers"], ["drag", "dragon", "dragons", "drags"]]


usafam = client.usafam
clans = usafam.clans



class boost(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="boost")
    async def boosting(self, ctx, clan=None):
        list_clans = []
        if clan == None:
            return await ctx.reply("Clan tag or alias argument required.",
                                   mention_author=False)
        else:
            clan = clan.lower()
            results = await clans.find_one({"$and": [
                {"alias": clan},
                {"server": ctx.guild.id}
            ]})

            if results is not None:
                tag = results.get("tag")
                clan = await getClan(tag)
                list_clans.append(clan)
            else:
                clan = await getClan(clan)
                list_clans.append(clan)

            if clan is None:
                return await ctx.reply("Not a valid clan tag.",
                                       mention_author=False)

        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Loading...",
            color=disnake.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)

        master_text = [[], [], [], [], [], [], [], [],
                        [], [], [], [], [], []]
        for clan in list_clans:
            async for player in clan.get_detailed_members():
                troops = player.troop_cls
                troops = player.troops

                for x in range(len(troops)):
                    troop = troops[x]
                    if (troop.is_active):
                        #print(troop)
                        try:
                            ind = SUPER_TROOPS.index(troop.name)
                            master_text[ind].append(f"{player.clan.name} - {player.name} [{player.tag}]\n")
                        except:
                            pass



        master_embed = []
        y = -1
        for text in master_text:
            y += 1
            if text == []:
                continue
                embed = disnake.Embed(title=f"Players with {SUPER_TROOPS[y]}",
                                      description="None boosted",
                                      color=disnake.Color.green())
                master_embed.append(embed)
            t = ""
            x = 0
            for blocks in text:
                t += blocks
                x+=1
                if x == 25:
                    embed = disnake.Embed(title=f"Players with {SUPER_TROOPS[y]}",
                                          description=t,
                                          color=disnake.Color.green())
                    master_embed.append(embed)
                    x=0
                    t=""
            if t!="":
                embed = disnake.Embed(title=f"Players with {SUPER_TROOPS[y]}",
                                      description=t,
                                      color=disnake.Color.green())
                master_embed.append(embed)



        current_page = 0
        limit = len(master_embed)

        await msg.edit(embed=master_embed[current_page], components=self.create_components(current_page, limit),
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
                await msg.edit(embed=master_embed[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=master_embed[current_page],
                               components=self.create_components(current_page, limit))

    @commands.command(name="super")
    async def super(self, ctx, troop_type=None, clan=None):
        is_valid = False
        ind = 0
        for valid_options in options:
            if troop_type in valid_options:
                is_valid = True
                ind = options.index(valid_options)
        if is_valid == False:
            opt_text = ""
            x = 0
            for opt in options:
                opt_text+=f"{SUPER_TROOPS[x]} aliases: "
                for o in opt:
                    if o == opt[len(opt)-1]:
                        opt_text += f"`{o}`"
                    else:
                        opt_text+= f"`{o}`, "
                x+=1
                opt_text += "\n"
            embed = disnake.Embed(title=f"Not a valid super troop alias.",
                                  description=opt_text,
                                  color=disnake.Color.red())
            return await ctx.reply(embed=embed,
                                   mention_author=False)

        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Loading...",
            color=disnake.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)

        list_clans = []
        if clan == None:
            tracked = clans.find({"server": ctx.guild.id})
            limit = await clans.count_documents(filter={"server": ctx.guild.id})
            for clan in await tracked.to_list(length=limit):
                tag = clan.get("tag")
                clan = await getClan(tag)
                list_clans.append(clan)
        else:
            clan = clan.lower()
            results = await clans.find_one({"$and": [
                {"alias": clan},
                {"server": ctx.guild.id}
            ]})

            if results is not None:
                tag = results.get("tag")
                clan = await getClan(tag)
                list_clans.append(clan)
            else:
                clan = await getClan(clan)
                list_clans.append(clan)

            if clan is None:
                return await msg.edit(content="Not a valid clan tag.", embed=None)

        search = SUPER_TROOPS[ind]

        master_text = []
        for clan in list_clans:
            async for player in clan.get_detailed_members():
                troops = player.troop_cls
                troops = player.troops
                for x in range(len(troops)):
                    troop = troops[x]
                    if (troop.is_active) and (troop.name == search):
                        #print(troop)
                        try:
                            master_text.append(f"{player.clan.name} - {player.name} [{player.tag}]\n")
                        except:
                            pass

        master_embed = []


        if len(master_text) == 0:
            embed = disnake.Embed(title=f"Players with {search}",
                                  description="None boosted",
                                  color=disnake.Color.green())
            master_embed.append(embed)

        t = ""
        x = 0
        for text in master_text:
            t += text
            x += 1
            if x == 25:
                embed = disnake.Embed(title=f"Players with {search}",
                                      description=t,
                                      color=disnake.Color.green())
                master_embed.append(embed)
                x = 0
                t = ""
        if t != "":
            embed = disnake.Embed(title=f"Players with {search}",
                                  description=t,
                                  color=disnake.Color.green())
            master_embed.append(embed)

        current_page = 0
        limit = len(master_embed)

        await msg.edit(embed=master_embed[current_page], components=self.create_components(current_page, limit),
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
                await msg.edit(embed=master_embed[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=master_embed[current_page],
                               components=self.create_components(current_page, limit))


    def create_components(self, current_page, length):
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
    bot.add_cog(boost(bot))