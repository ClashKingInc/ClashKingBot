from Utility.profile_embeds import *

async def button_pagination(bot, ctx: disnake.ApplicationCommandInteraction, msg, results):
    # statTypes
    profile_pages = ["Info", "Troops", "History"]
    current_stat = 0
    current_page = 0
    history_cache_embed = {}

    embed = await create_profile_stats(ctx, results[0])

    await msg.edit(embed=embed, components=create_components(results, current_page))
    def check(res: disnake.MessageInteraction):
        return res.message.id == msg.id

    while True:
        try:
            res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check,
                                                                      timeout=600)
        except:
            await ctx.edit_original_message(components=[])
            break

        await res.response.defer()
        #print(res.custom_id)
        if res.data.custom_id == "Previous":
            current_page -= 1
            embed = await display_embed(results, profile_pages[current_stat], current_page, ctx, history_cache_embed)
            await res.edit_original_message(embed=embed,
                           components=create_components(results, current_page))

        elif res.data.custom_id == "Next":
            current_page += 1
            embed = await display_embed(results, profile_pages[current_stat], current_page, ctx, history_cache_embed)
            await res.edit_original_message(embed=embed,
                           components=create_components(results, current_page))

        elif res.data.custom_id in profile_pages:
            current_stat = profile_pages.index(res.data.custom_id)
            try:
                embed = await display_embed(results, profile_pages[current_stat], current_page, ctx, history_cache_embed)
                await res.edit_original_message(embed=embed,
                               components=create_components(results, current_page))
            except:
                if profile_pages[current_stat] == "History":
                    embed = disnake.Embed(description="This player has made their clash of stats history private.",
                                          color=disnake.Color.green())
                    await res.edit_original_message(embed=embed,
                                   components=create_components(results, current_page))


async def display_embed(results, stat_type, current_page, ctx, history_cache_embed):
    if stat_type == "Info":
        return await create_profile_stats(ctx, results[current_page])
    elif stat_type == "Troops":
        return await create_profile_troops(results[current_page])
    elif stat_type == "History":
        tag = results[current_page]
        keys = history_cache_embed.keys()
        if tag not in keys:
            history_cache_embed[tag] = await history(ctx, results[current_page])
            return history_cache_embed[tag]
        else:
            return history_cache_embed[tag]


def create_components(results, current_page):
    length = len(results)

    page_buttons = [
        disnake.ui.Button(label="", emoji="◀️", style=disnake.ButtonStyle.grey, disabled=(current_page == 0),
                          custom_id="Previous"),
        disnake.ui.Button(label=f"Page {current_page + 1}/{length}", style=disnake.ButtonStyle.grey,
                          disabled=True),
        disnake.ui.Button(label="", emoji="▶️", style=disnake.ButtonStyle.grey,
                          disabled=(current_page == length - 1), custom_id="Next")
    ]
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    stat_buttons = [disnake.ui.Button(label="Info", style=disnake.ButtonStyle.grey, custom_id="Info", disabled=False),
                    disnake.ui.Button(label="Troops", style=disnake.ButtonStyle.grey, custom_id="Troops"),
                    disnake.ui.Button(label="History", style=disnake.ButtonStyle.grey, custom_id="History", disabled=False)]

    stat_button = disnake.ui.ActionRow()
    for button in stat_buttons:
        stat_button.append_item(button)

    if length == 1:
        return [stat_button]

    return [stat_button, buttons]


