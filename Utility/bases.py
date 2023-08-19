
import coc
from urllib.request import Request, urlopen
import io
import disnake
from disnake.ext import commands
from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from utils.constants import TOWNHALL_LEVELS
from utils.discord_utils import upload_to_cdn, interaction_handler
import time
from utils.components import wbb_components
import pymongo
from Exceptions.CustomExceptions import MessageException

class DBase():
    def __init__(self, data: dict):
        self.data = data
        self.downloads = data.get("downloads")
        self.builder = data.get("builder")
        self.picture = f"https://cdn.clashking.xyz/{data.get('pic_id')}.png?{int(datetime.now().timestamp())}"
        self.townhall = data.get("townhall")
        self.type = ", ".join(data.get("type"))
        self.link = f"https://api.clashking.xyz/base?action=OpenLayout&id={data.get('base_id')}"
        self.notes = data.get("notes")

    def __eq__(self, other):
        if isinstance(other, DBase):
            return self.data.get('base_id') == other.data.get('base_id')
        return False

    @property
    def last_downloaded(self):
        if self.data.get("unix_time") is None:
            return "Never"
        return f"<t:{self.data.get('unix_time')}:R>"


class Bases(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="base")
    async def base(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @base.sub_command(name='post', description="Upload a base so your clan mates can download it & leave reviews")
    async def uploadBase(self, ctx: disnake.ApplicationCommandInteraction, base_link: str, description: str, photo: disnake.Attachment):
        if 'https://link.clashofclans.com/' and "=OpenLayout&id=" not in base_link:
            await ctx.response.defer(ephemeral=True)
            return await ctx.send("Not a valid base link")
        await ctx.response.defer()
        description = description[0:1900]
        description = description.replace("&&", "\n")

        r1 = disnake.ui.ActionRow()
        link_button = disnake.ui.Button(label="Link", emoji="🔗", style=disnake.ButtonStyle.green, custom_id="link")
        downloads = disnake.ui.Button(label="0 Downloads", emoji="📈", style=disnake.ButtonStyle.green, custom_id="who")
        r1.append_item(link_button)
        r1.append_item(downloads)

        r2 = disnake.ui.ActionRow()
        feedback = disnake.ui.Button(label="Feedback", emoji="💬", style=disnake.ButtonStyle.green,
                                     custom_id="feedback")
        feedback_button = disnake.ui.Button(label="Leave Feedback", emoji="📈", style=disnake.ButtonStyle.green,
                                            custom_id="leave")
        r2.append_item(feedback)
        r2.append_item(feedback_button)

        await upload_to_cdn(picture=photo)

        await ctx.edit_original_message(content=f"[➼](https://cdn.clashking.xyz/{photo.id}.png) {description}", components=[r1, r2])
        msg = await ctx.original_message()
        await self.bot.bases.insert_one({
            "link": base_link,
            "message_id": msg.id,
            "downloads": 0,
            "downloaders": [],
            "feedback": [],
            "new" : True
        })
        base_id = base_link.split("&id=")[-1]
        th = int(base_id.split("%")[0].replace("TH", ""))
        r = await self.bot.base_stats.find_one({"base_id" : base_id})
        if r is None:
            await self.bot.base_stats.update_one({"base_id" : base_id}, {"$set" : {"type" : ["Home Village"], "builder" : ctx.guild.name, "townhall" : th, "pic_id" : photo.id}}, upsert=True)



    @base.sub_command(name="search", description="Search WBB's vault of bases by th & other filters")
    async def search(self, ctx: disnake.ApplicationCommandInteraction, townhall: int, type: str = None, builder: str = None,
                     downloads= commands.Param(default=None, choices=["Ascending", "Descending"]),
                     last_downloaded= commands.Param(default=None, choices=["Ascending", "Descending"]),
                     uploaded = commands.Param(default=None, choices=["Ascending", "Descending"])):
        r = time.time()
        await ctx.response.defer()
        sort_array = []
        if last_downloaded == "Descending":
            sort_array.append(("unix_time", pymongo.DESCENDING))
        elif last_downloaded == "Ascending":
            sort_array.append(("unix_time", pymongo.ASCENDING))

        if downloads == "Descending":
            sort_array.append(("downloads", pymongo.DESCENDING))
        elif downloads == "Ascending":
            sort_array.append(("downloads", pymongo.ASCENDING))

        if uploaded == "Descending":
            sort_array.append(("_id", pymongo.DESCENDING))
        elif uploaded == "Ascending":
            sort_array.append(("_id", pymongo.ASCENDING))

        if not sort_array:
            sort_array.append(("_id", pymongo.DESCENDING))

        search_query = [{"$or" : [{"unix_time" : {"$gte" : (int(datetime.now().timestamp()) - 7689600)}}, {"unix_time" :{"$eq" : None}}]}, {"townhall" : int(townhall)}]
        search_query.append({"is_user_upload" : {"$ne" : True}})
        if type:
            type_list = []
            for t in type.split(","):
                t = t.removeprefix(" ")
                t = t.removesuffix(" ")
                type_list.append(t)
            search_query.append({"type" : {"$in" : type_list}})

        if builder:
            builder_list = []
            for b in builder.split(","):
                b = b.removeprefix(" ")
                b = b.removesuffix(" ")
                builder_list.append(b)
            search_query.append({"builder" : {"$in" : builder_list}})

        bases = await self.bot.base_stats.find({"$and" : search_query}).sort(sort_array).limit(200).to_list(length=None)
        if not bases:
            raise MessageException("No bases found for that search query. Try modifying your search or check back later for newly added bases :)")
        master_embeds = []
        embeds = []
        break_num = 1
        bases = [DBase(data=base) for base in bases]
        for base in bases:
            embed = disnake.Embed(
                                  description=f"- Built by {base.builder}\n"
                                              f"- Downloaded {base.downloads} times\n"
                                              f"- Last Downloaded: {base.last_downloaded}\n"
                                              f"- Uploaded on {self.bot.timestamper(unix_time=int(datetime.now().timestamp())).text_date}\n"
                                              f"- Notes: {base.notes}\n"
                                              f"- **[Click this for Base Link]({base.link})**",
                                  color=disnake.Color.from_rgb(r=43, g=45, b=49))
            embed.set_author(name=f"{base.type} | TH{base.townhall} Base")
            embed.set_image(url=base.picture)
            embed.set_footer(text="discord.gg/worldbb", icon_url=self.bot.emoji.wbb_red.partial_emoji.url)
            embeds.append(embed)
            if len(embeds) == break_num or base == bases[-1]:
                master_embeds.append(embeds)
                embeds = []


        content = f"{len(bases)} results found in {round(time.time() - r, 2)} sec"
        current_page = 0
        await ctx.edit_original_message(content=content, embeds=master_embeds[0], components=wbb_components(self.bot, current_page, master_embeds))
        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            # print(res.custom_id)
            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.edit_original_message(embeds=master_embeds[current_page], components=wbb_components(self.bot, current_page, master_embeds))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.edit_original_message(embeds=master_embeds[current_page], components=wbb_components(self.bot, current_page, master_embeds))



    @base.sub_command(name="upload", description="for WBB to upload bases", guild_ids=[1103679645439754335])
    async def upload(self, ctx: disnake.ApplicationCommandInteraction, picture: disnake.Attachment,
                     type: str, builder: str, notes:str, base_link: str):
        await ctx.response.defer()
        if 'https://link.clashofclans.com/' and "=OpenLayout&id=" not in base_link:
            return await ctx.edit_original_message("Not a valid base link")

        base_id = base_link.split("&id=")[-1]
        th = int(base_id.split("%")[0].replace("TH", ""))
        type_list = []
        for t in type.split(","):
            t = t.removeprefix(" ")
            t = t.removesuffix(" ")
            type_list.append(t)

        embed = disnake.Embed(title=f"{', '.join(type_list)} | TH{th} Base",
                              description=f"- Built by {builder}\n"
                                          f"- Uploaded on {self.bot.timestamper(unix_time=int(datetime.now().timestamp())).text_date}\n"
                                          f"- Notes: {notes}\n"
                                          f"- **by [World Base Building](https://discord.gg/worldbb)**",
                              color=disnake.Color.from_rgb(r=43, g=45, b=49))
        await upload_to_cdn(picture=picture)
        embed.set_image(url=f"https://cdn.clashking.xyz/{picture.id}.png?{int(datetime.now().timestamp())}")
        embed.set_thumbnail(url="https://clashking.b-cdn.net/Logo_WBB_23.png")
        embed.set_footer(text="/base search, for more bases!")
        url = disnake.ui.ActionRow(disnake.ui.Button(label="Base Link", emoji=self.bot.emoji.wbb_red.partial_emoji, style=disnake.ButtonStyle.url, url=f"https://api.clashking.xyz/base?action=OpenLayout&id={base_id}"))
        await self.bot.base_stats.update_one({"base_id" : base_id}, {"$set" : {"type" : type_list, "builder" : builder, "downloads" : 0, "townhall" : th, "notes" : notes, "pic_id" : picture.id}}, upsert=True)
        await ctx.edit_original_message(embed=embed, components=[url])
        await self.base_post(embed=embed, components=[url])


    @search.autocomplete("type")
    @upload.autocomplete("type")
    async def autocomp_type(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        results = await self.bot.base_stats.distinct("type", filter={"is_user_upload" : {"$ne" : True}})
        if len(query.split(",")) >= 2:
            new_query = query.split(",")[-1]
            previous_split = query.split(",")[:-1]
            previous_split = [item.strip() for item in previous_split]
            previous = ", ".join(previous_split)
            return [f"{previous}, {r}" for r in results if new_query.lower().strip() in r.lower() and r not in previous_split][:25]
        else:
            return [r for r in results if query.lower() in r.lower()][:25]

    @search.autocomplete("builder")
    @upload.autocomplete("builder")
    async def autocomp_built(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        results = await self.bot.base_stats.distinct("builder", filter={"is_user_upload" : {"$ne" : True}})
        if len(query.split(",")) >= 2:
            new_query = query.split(",")[-1]
            previous_split = query.split(",")[:-1]
            previous_split = [item.strip() for item in previous_split]
            previous = ", ".join(previous_split)
            return [f"{previous}, {r}" for r in results if
                    new_query.lower().strip() in r.lower() and r not in previous_split][:25]
        else:
            return [r for r in results if query.lower() in r.lower()][:25]

    @search.autocomplete("townhall")
    async def autocomp_built(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        results = [str(th) for th in reversed(TOWNHALL_LEVELS)]
        return [r for r in results if query.lower() in r.lower()][:25]


    async def base_post(self, embed, components):
        channel = await self.bot.getch_channel(1135250639920824371)
        await channel.send(embed=embed, components=components)


    @commands.Cog.listener()
    async def on_message_interaction(self, res: disnake.MessageInteraction):
        results = await self.bot.bases.find_one({"message_id": res.message.id})
        if res.data.custom_id == "link":
            count = results.get("downloads")
            feedback = results.get("feedback")

            r1 = disnake.ui.ActionRow()
            link_button = disnake.ui.Button(label="Link", emoji="🔗", style=disnake.ButtonStyle.green, custom_id="link")
            downloads = disnake.ui.Button(label=f"{count + 1} Downloads", emoji="📈", style=disnake.ButtonStyle.green,
                                          custom_id="who")
            r1.append_item(link_button)
            r1.append_item(downloads)

            r2 = disnake.ui.ActionRow()
            feedback = disnake.ui.Button(label=f"Feedback - {len(feedback)}", emoji="💬",
                                         style=disnake.ButtonStyle.green,
                                         custom_id="feedback")
            feedback_button = disnake.ui.Button(label="Leave Feedback", emoji="📩", style=disnake.ButtonStyle.green,
                                                custom_id="leave")
            r2.append_item(feedback)
            r2.append_item(feedback_button)
            components = [r1, r2]
            await res.message.edit(components=components)
            await self.bot.bases.update_one({'message_id': res.message.id},
                                   {'$inc': {'downloads': 1}})
            await self.bot.bases.update_one({'message_id': res.message.id},
                                   {'$push': {'downloaders': f"{res.author.mention} [{res.author.name}]"}})
            if not results.get("new", False):
                await res.send(content=results.get("link"), ephemeral=True)
            else:
                base_id = results.get("link").split("&id=")[-1]
                await res.send(content=f'https://api.clashking.xyz/base?action=OpenLayout&id={base_id}', ephemeral=True)


        elif res.data.custom_id == "leave":
            await res.response.send_modal(
                title="Leave Base Feedback",
                custom_id="feedback-",
                components=[
                    disnake.ui.TextInput(
                        label="Leave Base Feedback",
                        placeholder="Leave feedback here:\n"
                                    "- Where did you run it? (cwl, league, war)\n"
                                    "- How did it do? (stars, percent)\n",
                        custom_id=f"feedback",
                        style=disnake.TextInputStyle.paragraph,
                        max_length=250,
                    )])

            def check(ctx):
                return res.author.id == ctx.author.id

            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )

            feedback = results.get("feedback")
            count = results.get("downloads")

            r1 = disnake.ui.ActionRow()
            link_button = disnake.ui.Button(label="Link", emoji="🔗", style=disnake.ButtonStyle.green, custom_id="link")
            downloads = disnake.ui.Button(label=f"{count} Downloads", emoji="📈", style=disnake.ButtonStyle.green,
                                          custom_id="who")
            r1.append_item(link_button)
            r1.append_item(downloads)

            r2 = disnake.ui.ActionRow()
            feedback = disnake.ui.Button(label=f"Feedback - {len(feedback) + 1}", emoji="💬",
                                         style=disnake.ButtonStyle.green,
                                         custom_id="feedback")
            feedback_button = disnake.ui.Button(label="Leave Feedback", emoji="📩", style=disnake.ButtonStyle.green,
                                                custom_id="leave")
            r2.append_item(feedback)
            r2.append_item(feedback_button)
            components = [r1, r2]
            await res.message.edit(components=components)

            await modal_inter.send(content="Feedback Submitted!", ephemeral=True)
            f = modal_inter.text_values["feedback"]
            await self.bot.bases.update_one({'message_id': res.message.id},
                                   {'$push': {'feedback': f"{f} - {modal_inter.author.display_name}"}})



        elif res.data.custom_id == "feedback":
            feedback = results.get("feedback")
            if feedback == []:
                embed = disnake.Embed(
                    description=f"No Feedback Currently.",
                    color=disnake.Color.red())
                return await res.send(embed=embed, ephemeral=True)
            else:
                text = ""
                for feed in feedback:
                    text += "➼ " + feed + "\n\n"
                embed = disnake.Embed(title="**Base Feedback:**",
                                      description=text,
                                      color=disnake.Color.green())
                return await res.send(embed=embed, ephemeral=True)

        elif res.data.custom_id == "who":
            ds = results.get("downloaders")
            if ds == []:
                embed = disnake.Embed(
                    description=f"No Downloads Currently.",
                    color=disnake.Color.red())
                return await res.send(embed=embed, ephemeral=True)
            else:
                text = ""
                for down in ds:
                    text += "➼ " + str(down) + "\n"
                embed = disnake.Embed(title="**Base Downloads:**",
                                      description=text,
                                      color=disnake.Color.green())
                return await res.send(embed=embed, ephemeral=True)


def setup(bot: CustomClient):
    bot.add_cog(Bases(bot))