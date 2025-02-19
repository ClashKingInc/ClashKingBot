@clan.sub_command(name='progress', description='Progress by clan ')
async def progress(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        type=commands.Param(choices=['Heroes & Pets', 'Troops, Spells, & Sieges']),
        season: str = options.optional_season,
        limit: int = commands.Param(default=50, min_value=1, max_value=50),
):
    """
    Parameters
    ----------
    clan: Use clan tag or select an option from the autocomplete
    type: progress type
    season: clash season to view data for
    limit: change amount of results shown
    """
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)

    if type == 'Heroes & Pets':
        custom_id = f'clanhero:{clan.tag}:{season}:{limit}'
        embeds = await clan_hero_progress(
            bot=self.bot,
            clan=clan,
            season=season,
            limit=limit,
            embed_color=embed_color,
        )

    elif type == 'Troops, Spells, & Sieges':
        custom_id = f'clantroops:{clan.tag}:{season}:{limit}'
        embeds = await troops_spell_siege_progress(
            bot=self.bot,
            clan=clan,
            season=season,
            limit=limit,
            embed_color=embed_color,
        )

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(
            label='',
            emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=custom_id,
        ),
    )
    await ctx.edit_original_message(embeds=embeds, components=[buttons])


@clan.sub_command(name='sorted', description='List of clan members, sorted by any attribute')
async def sorted(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        sort_by: str = commands.Param(choices=sorted(item_to_name.keys())),
        townhall: int = None,
        limit: int = commands.Param(default=50, min_value=1, max_value=50),
):
    """
    Parameters
    ----------
    clan: Use clan tag or select an option from the autocomplete
    sort_by: Sort by any attribute
    limit: change amount of results shown
    """
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
    embed = await clan_sorted(
        bot=self.bot,
        clan=clan,
        sort_by=sort_by,
        limit=limit,
        townhall=townhall,
        embed_color=embed_color,
    )

    buttons = disnake.ui.ActionRow()
    buttons.append_item(
        disnake.ui.Button(
            label='',
            emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'clansorted:{clan.tag}:{sort_by}:{limit}:{townhall}',
        )
    )

    await ctx.edit_original_message(embed=embed, components=[buttons])


@clan.sub_command(name='donations', description='Donation stats for a clan')
async def donations(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        season: str = options.optional_season,
        townhall: int = None,
        limit: int = commands.Param(default=50, min_value=1, max_value=50),
        sort_by: str = commands.Param(default='Donations', choices=['Name', 'Townhall', 'Donations', 'Received']),
        sort_order: str = commands.Param(default='Descending', choices=['Ascending', 'Descending']),
):
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
    embed = await clan_donations(
        bot=self.bot,
        clan=clan,
        season=season,
        townhall=townhall,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        embed_color=embed_color,
    )
    buttons = disnake.ui.ActionRow()
    buttons.append_item(
        disnake.ui.Button(
            label='',
            emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'clandonos:{clan.tag}:{season}:{townhall}:{limit}:{sort_by}:{sort_order}',
        )
    )
    await ctx.edit_original_message(embed=embed, components=[buttons])


@clan.sub_command(name='war-log', description='Past war info for clan')
async def war(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        option: str = commands.Param(choices=['War Log', 'CWL History']),
        limit: int = commands.Param(default=25, min_value=1, max_value=25),
):
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
    buttons = disnake.ui.ActionRow()
    if option == 'War Log':
        embed = await war_log(bot=self.bot, clan=clan, embed_color=embed_color)
        buttons.append_item(
            disnake.ui.Button(
                label='',
                emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f'clanwarlog:{clan.tag}:{limit}',
            )
        )
    elif option == 'CWL History':
        embed = await cwl_performance(bot=self.bot, clan=clan, embed_color=embed_color)
        buttons.append_item(
            disnake.ui.Button(
                label='',
                emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f'clancwlperf:{clan.tag}',
            )
        )

    await ctx.edit_original_message(embed=embed, components=[buttons])


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


@clan.sub_command(name='summary', description='Summary of stats for a clan')
async def summary(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        season: str = options.optional_season,
        limit: int = commands.Param(default=5, min_value=1, max_value=15),
):
    embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
    embeds = await clan_summary(bot=self.bot, clan=clan, limit=limit, season=season, embed_color=embed_color)
    buttons = disnake.ui.ActionRow()
    buttons.add_button(
        label='',
        emoji=self.bot.emoji.refresh.partial_emoji,
        style=disnake.ButtonStyle.grey,
        custom_id=f'clansummary:{clan.tag}:{season}:{limit}',
    )
    await ctx.edit_original_message(embeds=embeds, components=[buttons])