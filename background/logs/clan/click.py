@commands.Cog.listener()
async def on_button_click(self, ctx: disnake.MessageInteraction):
    if 'jlban_' in ctx.data.custom_id:
        check = await self.bot.white_list_check(ctx, 'ban add')
        if not check and not ctx.author.guild_permissions.manage_guild:
            await ctx.send(
                content='You cannot use this component. Missing Permissions.',
                ephemeral=True,
            )
        player = ctx.data.custom_id.split('_')[-1]
        player = await self.bot.getPlayer(player_tag=player)
        components = [
            disnake.ui.TextInput(
                label=f'Reason to ban {player.name}',
                placeholder='Ban Reason (i.e. missed 25 war attacks)',
                custom_id='ban_reason',
                required=True,
                style=disnake.TextInputStyle.single_line,
                max_length=100,
            )
        ]
        await ctx.response.send_modal(title='Ban Form', custom_id='banform-', components=components)

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                'modal_submit',
                check=check,
                timeout=300,
            )
        except:
            return

        # await modal_inter.response.defer()
        ban_reason = modal_inter.text_values['ban_reason']
        ban_cog = self.bot.get_cog(name='Bans')
        embed = await ban_cog.ban_player(ctx, player, ban_reason)
        await modal_inter.send(embed=embed)

    if 'jlstrike_' in ctx.data.custom_id:
        check = await self.bot.white_list_check(ctx, 'strike add')
        if not check and not ctx.author.guild_permissions.manage_guild:
            await ctx.send(
                content='You cannot use this component. Missing Permissions.',
                ephemeral=True,
            )
        player = ctx.data.custom_id.split('_')[-1]
        player = await self.bot.getPlayer(player_tag=player)
        components = [
            disnake.ui.TextInput(
                label=f'Reason for strike on {player.name}',
                placeholder='Strike Reason (i.e. low donation ratio)',
                custom_id='strike_reason',
                required=True,
                style=disnake.TextInputStyle.single_line,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label='Rollover Days',
                placeholder='In how many days you want this to expire',
                custom_id='rollover_days',
                required=False,
                style=disnake.TextInputStyle.single_line,
                max_length=3,
            ),
            disnake.ui.TextInput(
                label='Strike Weight',
                placeholder='Weight you want for this strike (default is 1)',
                custom_id='strike_weight',
                required=False,
                style=disnake.TextInputStyle.single_line,
                max_length=2,
            ),
        ]
        await ctx.response.send_modal(title='Strike Form', custom_id='strikeform-', components=components)

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                'modal_submit',
                check=check,
                timeout=300,
            )
        except:
            return

        # await modal_inter.response.defer()
        strike_reason = modal_inter.text_values['strike_reason']
        rollover_days = modal_inter.text_values['rollover_days']
        if rollover_days != '':
            if not str(rollover_days).isdigit():
                return await modal_inter.send(content='Rollover Days must be an integer', ephemeral=True)
            else:
                rollover_days = int(rollover_days)
        else:
            rollover_days = None
        strike_weight = modal_inter.text_values['strike_weight']
        if strike_weight != '':
            if not str(strike_weight).isdigit():
                return await modal_inter.send(content='Strike Weight must be an integer', ephemeral=True)
            else:
                strike_weight = int(strike_weight)
        else:
            strike_weight = 1
        strike_cog = self.bot.get_cog(name='Strikes')
        embed = await strike_cog.strike_player(ctx, player, strike_reason, rollover_days, strike_weight)
        await modal_inter.send(embed=embed)
