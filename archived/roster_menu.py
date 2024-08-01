'''elif 'Menu_' in str(ctx.data.custom_id):
alias = str(ctx.data.custom_id).split('_')[1]
roster = Roster(bot=self.bot)
await roster.find_roster(guild=ctx.guild, alias=alias)
message = ctx.message
perms = ctx.permissions.manage_guild
if ctx.author.id == self.bot.owner.id:
    perms = True
if not perms:
    return await ctx.send(
        content='Must have `Manage Guild` perms to use the menu',
        ephemeral=True,
    )
options = [
    disnake.SelectOption(label='Remove Signup Buttons', value='remove_buttons'),
    disnake.SelectOption(label='Refresh Components', value='re_comp'),
    disnake.SelectOption(label='Add Discord User', value='add_discord'),
    disnake.SelectOption(label='Remove Discord User', value='remove_discord'),
]
select = disnake.ui.Select(
    options=options,
    placeholder='Menu Options',
    # the placeholder text to show when no options have been chosen
    min_values=1,  # the minimum number of options a user must select
    max_values=1,  # the maximum number of options a user can select
)
dropdown = [disnake.ui.ActionRow(select)]
await ctx.send(content='Menu Options', components=dropdown, ephemeral=True)

try:
    res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', timeout=600)
except:
    return

if res.values[0] == 'remove_buttons':
    await message.edit(components=[])
    await res.send(content='Components Removed', ephemeral=True)
elif res.values[0] == 're_comp':
    signup_buttons = [
        disnake.ui.Button(
            label='Add',
            emoji=self.bot.emoji.yes.partial_emoji,
            style=disnake.ButtonStyle.green,
            custom_id=f'Signup_{alias}',
        ),
        disnake.ui.Button(
            label='Remove',
            emoji=self.bot.emoji.no.partial_emoji,
            style=disnake.ButtonStyle.red,
            custom_id=f'RemoveMe_{alias}',
        ),
        disnake.ui.Button(
            label='Sub',
            emoji=self.bot.emoji.switch.partial_emoji,
            style=disnake.ButtonStyle.blurple,
            custom_id=f'SubMe_{alias}',
        ),
        disnake.ui.Button(
            label='',
            emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'Refresh_{alias}',
        ),
        disnake.ui.Button(
            label='',
            emoji=self.bot.emoji.menu.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'Menu_{alias}',
        ),
    ]
    buttons = disnake.ui.ActionRow()
    for button in signup_buttons:
        buttons.append_item(button)
    await message.edit(components=[buttons])
    await res.send(content='Components Refreshed', ephemeral=True)

elif res.values[0] == 'add_discord':

    carryover_text = ''
    await res.response.defer()
    while True:
        role_select = disnake.ui.UserSelect(placeholder='Choose User', max_values=1)
        dropdown = [disnake.ui.ActionRow(role_select)]
        await res.edit_original_message(
            content=f'{carryover_text}Choose Member to add Accounts for',
            components=dropdown,
        )
        res = await interaction_handler(bot=self.bot, ctx=res)
        linked_accounts = await self.bot.link_client.get_linked_players(res.values[0])
        if not linked_accounts:
            carryover_text = '**No accounts linked to that user**\n'
            continue
        accounts = await self.bot.get_players(tags=linked_accounts)
        options = []
        player_dict = {}
        roster_tags = [member.get('tag') for member in roster.players]
        for account in accounts:
            account: coc.Player
            if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                continue
            if account.tag in roster_tags:
                continue
            player_dict[account.tag] = account
            options.append(
                disnake.SelectOption(
                    label=account.name,
                    emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji,
                    value=f'{account.tag}',
                )
            )

        if not options:
            carryover_text = "**All of that user's accounts are already on the roster**\n"
            continue

        options = options[:25]
        select = disnake.ui.Select(
            options=options,
            placeholder='Select Account(s)',
            # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await res.edit_original_message(content='Select Account(s) to Add', components=dropdown)

        res = await interaction_handler(bot=self.bot, ctx=res)

        await roster.find_roster(guild=ctx.guild, alias=alias)
        accounts_to_add = res.values
        added = []
        for account in accounts_to_add:
            added.append(player_dict[account].name)
            await roster.add_member(player_dict[account])
        carryover_text = f"**Added {', '.join(added)}**\n"
        await roster.refresh_roster()
        embed = await roster.embed()
        await message.edit(embed=embed)

elif res.values[0] == 'remove_discord':

    carryover_text = ''
    await res.response.defer()
    while True:
        role_select = disnake.ui.UserSelect(placeholder='Choose User', max_values=1)
        dropdown = [disnake.ui.ActionRow(role_select)]
        await res.edit_original_message(
            content=f'{carryover_text}Choose Member to remove Accounts for',
            components=dropdown,
        )
        res = await interaction_handler(bot=self.bot, ctx=res)
        linked_accounts = await self.bot.link_client.get_linked_players(res.values[0])
        if not linked_accounts:
            carryover_text = '**No accounts linked to that user**\n'
            continue
        accounts = await self.bot.get_players(tags=linked_accounts)
        options = []
        player_dict = {}
        roster_tags = [member.get('tag') for member in roster.players]
        for account in accounts:
            account: coc.Player
            if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                continue
            if account.tag not in roster_tags:
                continue
            player_dict[account.tag] = account
            options.append(
                disnake.SelectOption(
                    label=account.name,
                    emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji,
                    value=f'{account.tag}',
                )
            )

        if not options:
            carryover_text = "**None of that user's accounts are on this roster**\n"
            continue

        options = options[:25]
        select = disnake.ui.Select(
            options=options,
            placeholder='Select Account(s)',
            # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await res.edit_original_message(content='Select Account(s) to Remove', components=dropdown)

        res = await interaction_handler(bot=self.bot, ctx=res)

        await roster.find_roster(guild=ctx.guild, alias=alias)
        accounts_to_add = res.values
        added = []
        for account in accounts_to_add:
            added.append(player_dict[account].name)
            await roster.remove_member(player_dict[account])
        carryover_text = f"**Removed: {', '.join(added)}**\n"
        await roster.refresh_roster()
        embed = await roster.embed()
        await message.edit(embed=embed)
'''