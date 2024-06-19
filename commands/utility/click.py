import disnake

from disnake.ext import commands
from classes.bot import CustomClient


class UtilityButtons(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, res: disnake.MessageInteraction):
        if res.data.custom_id == "link":
            results = await self.bot.bases.find_one({"message_id": res.message.id})
            count = results.get("downloads")
            feedback = results.get("feedback")

            row_one = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Link",
                    emoji="🔗",
                    style=disnake.ButtonStyle.grey,
                    custom_id="link",
                ),
                disnake.ui.Button(
                    label=f"{count + 1} Downloads",
                    emoji="📈",
                    style=disnake.ButtonStyle.grey,
                    custom_id="who",
                ),
            )

            row_two = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=f"Feedback - {len(feedback)}",
                    emoji="💬",
                    style=disnake.ButtonStyle.grey,
                    custom_id="feedback",
                ),
                disnake.ui.Button(
                    label="Leave Feedback",
                    emoji="📩",
                    style=disnake.ButtonStyle.grey,
                    custom_id="leave",
                ),
            )
            await res.message.edit(components=[row_one, row_two])
            await self.bot.bases.update_one(
                {"message_id": res.message.id},
                {
                    "$inc": {"downloads": 1},
                    "$push": {
                        "downloaders": f"{res.author.mention} [{res.author.name}]"
                    },
                },
            )
            if not results.get("new", False):
                await res.send(content=results.get("link"), ephemeral=True)
            else:
                base_id = results.get("link").split("&id=")[-1]
                await res.send(
                    content=f"https://link.clashofclans.com/en?action=OpenLayout&id={base_id}",
                    ephemeral=True,
                )

        elif res.data.custom_id == "leave":
            results = await self.bot.bases.find_one({"message_id": res.message.id})
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
                    )
                ],
            )

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
            link_button = disnake.ui.Button(
                label="Link",
                emoji="🔗",
                style=disnake.ButtonStyle.green,
                custom_id="link",
            )
            downloads = disnake.ui.Button(
                label=f"{count} Downloads",
                emoji="📈",
                style=disnake.ButtonStyle.green,
                custom_id="who",
            )
            r1.append_item(link_button)
            r1.append_item(downloads)

            r2 = disnake.ui.ActionRow()
            feedback = disnake.ui.Button(
                label=f"Feedback - {len(feedback) + 1}",
                emoji="💬",
                style=disnake.ButtonStyle.green,
                custom_id="feedback",
            )
            feedback_button = disnake.ui.Button(
                label="Leave Feedback",
                emoji="📩",
                style=disnake.ButtonStyle.green,
                custom_id="leave",
            )
            r2.append_item(feedback)
            r2.append_item(feedback_button)
            components = [r1, r2]
            await res.message.edit(components=components)

            await modal_inter.send(content="Feedback Submitted!", ephemeral=True)
            f = modal_inter.text_values["feedback"]
            await self.bot.bases.update_one(
                {"message_id": res.message.id},
                {"$push": {"feedback": f"{f} - {modal_inter.author.display_name}"}},
            )

        elif res.data.custom_id == "feedback":
            results = await self.bot.bases.find_one({"message_id": res.message.id})
            feedback = results.get("feedback")
            if feedback == []:
                embed = disnake.Embed(
                    description=f"No Feedback Currently.", color=disnake.Color.red()
                )
                return await res.send(embed=embed, ephemeral=True)
            else:
                text = ""
                for feed in feedback:
                    text += "➼ " + feed + "\n\n"
                embed = disnake.Embed(
                    title="**Base Feedback:**",
                    description=text,
                    color=disnake.Color.green(),
                )
                return await res.send(embed=embed, ephemeral=True)

        elif res.data.custom_id == "who":
            results = await self.bot.bases.find_one({"message_id": res.message.id})
            ds = results.get("downloaders")
            if ds == []:
                embed = disnake.Embed(
                    description=f"No Downloads Currently.", color=disnake.Color.red()
                )
                return await res.send(embed=embed, ephemeral=True)
            else:
                text = ""
                for down in ds:
                    text += "➼ " + str(down) + "\n"
                embed = disnake.Embed(
                    title="**Base Downloads:**",
                    description=text,
                    color=disnake.Color.green(),
                )
                return await res.send(embed=embed, ephemeral=True)
