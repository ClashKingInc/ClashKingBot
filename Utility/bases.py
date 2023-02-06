

import coc
import disnake
from disnake.ext import commands
from datetime import datetime
from CustomClasses.CustomBot import CustomClient


class Bases(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='base', description="Upload a base so your clan mates can download it & leave reviews")
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

        await ctx.edit_original_message(content=f"[➼]({photo.url}) {description}", components=[r1, r2])
        msg = await ctx.original_message()
        await self.bot.bases.insert_one({
            "link": base_link,
            "message_id": msg.id,
            "downloads": 0,
            "downloaders": [],
            "feedback": []
        })

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
            await res.send(content=results.get("link"), ephemeral=True)

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