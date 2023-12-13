import disnake

from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from CommandsOlder.Utils.Player import create_profile_stats, create_profile_troops, upgrade_embed, history


async def button_pagination(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, msg, results):
    # statTypes
    profile_pages = ["Info", "Troops", "Upgrades", "History"]
    current_stat = 0
    current_page = 0
    history_cache_embed = {}

    embed = await create_profile_stats(bot, ctx, results[0])

    await msg.edit(embed=embed, components=create_components(bot, results))
    def check(res: disnake.MessageInteraction):
        return res.message.id == msg.id

    while True:
        try:
            res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check,
                                                                      timeout=600)
        except:
            try:
                await ctx.edit_original_message(components=[])
            except:
                pass
            break

        await res.response.defer()
        if res.values[0] in profile_pages:
            current_stat = profile_pages.index(res.values[0])
            try:
                embed = await display_embed(results, profile_pages[current_stat], current_page, ctx, history_cache_embed, bot)
                if profile_pages[current_stat] == "Upgrades":
                    await res.edit_original_message(embeds= embed)
                else:
                    await res.edit_original_message(embed=embed)
            except:
                if profile_pages[current_stat] == "History":
                    embed = disnake.Embed(description="This player has made their clash of stats history private.",
                                          color=disnake.Color.green())
                    player = results[current_page]
                    history_cache_embed[player.tag] = embed
                    await res.edit_original_message(embed=embed)
        else:
            current_page = int(res.values[0])
            embed = await display_embed(results, profile_pages[current_stat], current_page, ctx, history_cache_embed,
                                        bot)
            if profile_pages[current_stat] == "Upgrades":
                await res.edit_original_message(embeds=embed)
            else:
                await res.edit_original_message(embed=embed)


async def display_embed(results, stat_type, current_page, ctx, history_cache_embed, bot: CustomClient):
    if stat_type == "Info":
        return await create_profile_stats(bot, ctx, results[current_page])
    elif stat_type == "Troops":
        return await create_profile_troops(bot, results[current_page])
    elif stat_type == "Upgrades":
        return await upgrade_embed(bot, results[current_page])
    elif stat_type == "History":
        player = results[current_page]
        keys = history_cache_embed.keys()
        if player.tag not in keys:
            history_cache_embed[player.tag] = await history(bot, ctx, results[current_page])
        return history_cache_embed[player.tag]


def create_components(bot: CustomClient, results):
    length = len(results)

    options = [  # the options in your dropdown
        disnake.SelectOption(label="Overview", emoji=bot.emoji.xp.partial_emoji, value="Info"),
        disnake.SelectOption(label="Troops", emoji=bot.emoji.troop.partial_emoji, value="Troops"),
        disnake.SelectOption(label="Upgrades/Rushed", emoji=bot.emoji.clock.partial_emoji, value="Upgrades"),
        disnake.SelectOption(label="Clan History", emoji=bot.emoji.clan_castle.partial_emoji, value="History"),
    ]

    stat_select = disnake.ui.Select(options=options, placeholder="Choose a page", max_values=1)

    st = disnake.ui.ActionRow()
    st.append_item(stat_select)

    if length == 1:
        return st

    player_results = []
    for count, player in enumerate(results):
        player:MyCustomPlayer
        player_results.append(disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji, value=f"{count}"))

    profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)

    st2 = disnake.ui.ActionRow()
    st2.append_item(profile_select)

    return [st, st2]



