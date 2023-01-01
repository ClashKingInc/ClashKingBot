import disnake
from CustomClasses.CustomBot import CustomClient
from Exceptions import ExpiredComponents

async def get_embed_json(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(description="Use the link below to generate a custom panel embed or use the default panel. (This can be changed at a later time)\n"
                                      "https://autocode.com/tools/discord/embed-builder")

    default_embed = disnake.Embed(description="Use the button below to open a ticket!")
    page_buttons = [
            disnake.ui.Button(label="Custom Panel", emoji="◀️", style=disnake.ButtonStyle.grey, custom_id="custom_panel"),
            disnake.ui.Button(label=f"Default Panel", style=disnake.ButtonStyle.green, custom_id="default_panel")
    ]

    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)
    await ctx.edit_original_message(embed=embed, components=[buttons])
    msg = await ctx.original_message()

    embed_data = None

    def check(res: disnake.MessageInteraction):
        return res.message.id == msg.id

    while True:
        try:
            res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            await ctx.edit_original_message(components=[])
            raise ExpiredComponents

        if res.author.id != ctx.author.id:
            await res.send(content="Must run the command to interact with components.", ephemeral=True)
            continue
        await res.response.defer()

        if res.data.custom_id == "custom_panel":
            #ask for panel
            pass
        elif res.data.custom_id == "default_panel":
            embed_data = default_embed.to_dict()

    return embed_data



async def parse_embed_json(json: str, ctx: disnake.ApplicationCommandInteraction):

    embed = disnake.Embed.from_dict(json)
    await ctx.edit_original_message(embed=embed)
    #pass



