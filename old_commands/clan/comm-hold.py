@clan.sub_command(name='games', description='Clan Games stats for a clan')
async def games(
    self,
    ctx: disnake.ApplicationCommandInteraction,
    clan: coc.Clan = options.clan,
    season: str = options.optional_season,
    townhall: int = None,
    limit: int = commands.Param(default=50, min_value=1, max_value=50),
    sort_by: str = commands.Param(default='Points', choices=['Name', 'Points', 'Time']),
    sort_order: str = commands.Param(default='Descending', choices=['Ascending', 'Descending']),
):
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
    buttons = disnake.ui.ActionRow()
    embed = await clan_games(
        bot=self.bot,
        clan=clan,
        season=season,
        sort_by=sort_by.lower(),
        sort_order=sort_order.lower(),
        limit=limit,
        townhall=townhall,
        embed_color=embed_color,
    )
    buttons.append_item(
        disnake.ui.Button(
            label='',
            emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'clangames:{clan.tag}:{season}:{sort_by.lower()}:{sort_order.lower()}:{limit}:{townhall}',
        )
    )
    await ctx.edit_original_message(embed=embed, components=[buttons])


@clan.sub_command(
    name='war-preference',
    description='War preference, last opted, last war, & war timer data',
)
async def war_preference(
    self,
    ctx: disnake.ApplicationCommandInteraction,
    clan: coc.Clan = options.clan,
    option: str = commands.Param(
        default='Last Opt Change',
        choices=['Last Opt Change', 'Last War', 'War Timer'],
    ),
):
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
    embeds = await clan_warpreference(
        bot=self.bot,
        clan=clan,
        option=option.lower().replace(' ', ''),
        embed_color=embed_color,
    )
    buttons = disnake.ui.ActionRow()
    buttons.add_button(
        label='',
        emoji=self.bot.emoji.opt_in.partial_emoji,
        style=disnake.ButtonStyle.grey,
        custom_id=f'clanwarpref:{clan.tag}:lastoptchange',
    )
    buttons.add_button(
        label='',
        emoji=self.bot.emoji.wood_swords.partial_emoji,
        style=disnake.ButtonStyle.grey,
        custom_id=f'clanwarpref:{clan.tag}:lastwar',
    )
    buttons.add_button(
        label='',
        emoji=self.bot.emoji.clock.partial_emoji,
        style=disnake.ButtonStyle.grey,
        custom_id=f'clanwarpref:{clan.tag}:wartimer',
    )
    await ctx.edit_original_message(embeds=embeds, components=[buttons])


@clan.sub_command(
    name='activity',
    description='Activity related stats for a clan - last online, activity',
)
async def activity(
    self,
    ctx: disnake.ApplicationCommandInteraction,
    clan: coc.Clan = options.clan,
    season: str = options.optional_season,
    townhall: int = None,
    limit: int = commands.Param(default=50, min_value=1, max_value=50),
    sort_by: str = commands.Param(default='Activity', choices=['Name', 'Activity', 'Last Online']),
    sort_order: str = commands.Param(default='Descending', choices=['Ascending', 'Descending']),
):
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
    embed = await clan_activity(
        bot=self.bot,
        clan=clan,
        townhall=townhall,
        limit=limit,
        season=season,
        sort_by=sort_by.lower().replace(' ', ''),
        sort_order=sort_order,
        embed_color=embed_color,
    )
    buttons = disnake.ui.ActionRow()
    buttons.add_button(
        label='',
        emoji=self.bot.emoji.refresh.partial_emoji,
        style=disnake.ButtonStyle.grey,
        custom_id=f"clanactivity:{clan.tag}:{season}:{townhall}:{limit}:{sort_by.lower().replace(' ', '')}:{sort_order}",
    )
    await ctx.edit_original_message(embed=embed, components=[buttons])


@clan.sub_command(name='capital', description='Clan capital info for a clan for a week')
async def capital(
    self,
    ctx: disnake.ApplicationCommandInteraction,
    clan: coc.Clan = options.clan,
    weekend: str = commands.Param(default=None, autocomplete=autocomplete.raid_weekend),
):
    # 3 types - overview, donations, & raids
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
    embed = await clan_capital_overview(bot=self.bot, clan=clan, weekend=weekend, embed_color=embed_color)

    page_buttons = [
        disnake.ui.Button(
            label='',
            emoji=self.bot.emoji.wrench.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'clancapoverview:{clan.tag}:{weekend}',
        ),
        disnake.ui.Button(
            label='Raids',
            emoji=self.bot.emoji.animated_clash_swords.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'clancapraids:{clan.tag}:{weekend}',
        ),
        disnake.ui.Button(
            label='Donos',
            emoji=self.bot.emoji.capital_gold.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'clancapdonos:{clan.tag}:{weekend}',
        ),
    ]
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    return await ctx.edit_original_message(embed=embed, components=[buttons])
