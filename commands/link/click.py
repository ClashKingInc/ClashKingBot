import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from classes.player.stats import StatsPlayer
from utility.search import search_results

from ..eval.utils import logic
from ..player.utils import to_do_embed


class LinkButtonExtended(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot: CustomClient = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        results = await self.bot.welcome.find_one(
            {
                '$and': [
                    {'server': member.guild.id},
                    {'welcome_link_channel': {'$ne': None}},
                ]
            }
        )
        if results is not None:

            link_channel = results.get('welcome_link_channel')
            if link_channel is not None:
                if results.get('welcome_link_embed') is not None:
                    embed = disnake.Embed.from_dict(data=results.get('welcome_link_embed'))
                else:
                    embed = disnake.Embed(
                        title=f'**Welcome to {member.guild.name}!**',
                        description=f'To link your account, press the link button below to get started.',
                        color=disnake.Color.green(),
                    )
                stat_buttons = [
                    disnake.ui.Button(
                        label='Link Account',
                        emoji='🔗',
                        style=disnake.ButtonStyle.green,
                        custom_id='Start Link',
                    ),
                    disnake.ui.Button(
                        label='Help',
                        emoji='❓',
                        style=disnake.ButtonStyle.grey,
                        custom_id='Link Help',
                    ),
                ]
                buttons = disnake.ui.ActionRow()
                for button in stat_buttons:
                    buttons.append_item(button)
                if member.guild.icon is not None:
                    embed.set_thumbnail(url=member.guild.icon.url)
                try:
                    channel = await self.bot.getch_channel(link_channel, raise_exception=True)
                    if member.guild.id == 923764211845312533:
                        await channel.send(
                            content=member.mention,
                            embed=embed,
                            components=[stat_buttons],
                            allowed_mentions=disnake.AllowedMentions.none(),
                        )
                    else:
                        await channel.send(
                            content=member.mention,
                            embed=embed,
                            components=[stat_buttons],
                        )
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.welcome.update_one({'server': member.guild.id}, {'$set': {'link_channel': None}})

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):

        if ctx.data.custom_id == 'Refresh Roles':
            await ctx.response.defer(ephemeral=True)
            server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
            server_member = await ctx.guild.getch_member(ctx.user.id)
            await logic(
                bot=self.bot,
                guild=ctx.guild,
                db_server=server,
                members=[server_member],
                role_or_user=ctx.user,
            )
            await ctx.send(content='Your roles are now up to date!', ephemeral=True)

        elif ctx.data.custom_id == 'MyToDoList':
            await ctx.response.defer(ephemeral=True)
            discord_user = ctx.author
            embed = await to_do_embed(bot=self.bot, discord_user=discord_user, embed_color=disnake.Color.green())
            await ctx.send(embed=embed, ephemeral=True)

        elif ctx.data.custom_id == 'MyRosters':
            await ctx.response.defer(ephemeral=True)
            tags = await self.bot.get_tags(ping=ctx.user.id)
            roster_type_text = ctx.user.display_name
            players = await self.bot.get_players(tags=tags, custom=False)
            text = ''
            for player in players:
                rosters_found = await self.bot.rosters.find({'members.tag': player.tag}).to_list(length=100)
                if not rosters_found:
                    continue
                text += f'{self.bot.fetch_emoji(name=player.town_hall)}**{player.name}**\n'
                for roster in rosters_found:
                    our_member = next(member for member in roster['members'] if member['tag'] == player.tag)
                    group = our_member['group']
                    if group == 'No Group':
                        group = 'Main'
                    text += f"{roster['alias']} | {roster['clan_name']} | {group}\n"
                text += '\n'

            if text == '':
                text = 'Not Found on Any Rosters'
            embed = disnake.Embed(
                title=f'Rosters for {roster_type_text}',
                description=text,
                color=disnake.Color.green(),
            )
            await ctx.send(embed=embed, ephemeral=True)

        elif ctx.data.custom_id == 'Start Link':
            db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild.id)
            components = [
                disnake.ui.TextInput(
                    label='Player Tag',
                    placeholder='Your player tag as found in-game.',
                    custom_id=f'player_tag',
                    required=True,
                    style=disnake.TextInputStyle.single_line,
                    max_length=12,
                )
            ]

            if db_server.use_api_token:
                token_text = 'Api Token'
            else:
                token_text = '(Optional) Api Token'
            components.append(
                disnake.ui.TextInput(
                    label=token_text,
                    placeholder='Your Api Token as found in-game.',
                    custom_id=f'api_token',
                    required=db_server.use_api_token,
                    style=disnake.TextInputStyle.single_line,
                    max_length=12,
                )
            )
            await ctx.response.send_modal(
                title='Link your account',
                custom_id='linkaccount-',
                components=components,
            )

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

            player_tag = modal_inter.text_values['player_tag']
            api_token = modal_inter.text_values['api_token']
            if not modal_inter.response.is_done():
                await modal_inter.response.defer(ephemeral=True)

            player: StatsPlayer = await self.bot.getPlayer(player_tag=player_tag, custom=True)
            if player is None:
                clan = await self.bot.getClan(clan_tag=player_tag)
                if clan is not None:
                    embed = disnake.Embed(
                        description=f'Sorry, `{player_tag}` is invalid and it also appears to be the **clan** tag for {clan.name}\nUse the image below to help find your player tag.',
                        color=disnake.Color.red(),
                    )
                    embed.set_image(url='https://clashking.b-cdn.net/clash-assets/bot/find_player_tag.png')
                    return await modal_inter.send(embed=embed, ephemeral=True)
                else:
                    embed = disnake.Embed(
                        description=f'**Sorry, `{player_tag}` is an invalid player tag** :( \nUse the image below to help find your player tag.',
                        color=disnake.Color.red(),
                    )
                    embed.set_image(url='https://clashking.b-cdn.net/clash-assets/bot/find_player_tag.png')
                    return await modal_inter.send(embed=embed, ephemeral=True)

            link_id = await player.linked()

            if db_server.use_api_token:
                verified = await player.verify(api_token=api_token)
            elif link_id != ctx.author.id and link_id is not None:
                verified = await player.verify(api_token=api_token)
            else:
                verified = True

            if link_id == ctx.author.id:
                embed = await logic(
                    bot=self.bot,
                    guild=ctx.guild,
                    db_server=db_server,
                    members=[ctx.author],
                    role_or_user=ctx.author,
                )
                return await modal_inter.send(embed=embed[0], ephemeral=True)
            elif verified:
                try:
                    await self.bot.link_client.delete_link(player.tag)
                except Exception:
                    pass
                await player.add_link(ctx.author)
                embed = await logic(
                    bot=self.bot,
                    guild=ctx.guild,
                    db_server=db_server,
                    members=[ctx.author],
                    role_or_user=ctx.author,
                )
                embed[0].title = f'**{player.name} successfully linked**'
                await modal_inter.send(embed=embed[0], ephemeral=True)
                try:
                    results = await self.bot.clan_db.find_one(
                        {'$and': [{'tag': player.clan.tag}, {'server': ctx.guild.id}]}
                    )
                    if results is not None:
                        greeting = results.get('greeting')
                        if greeting is None:
                            badge = await self.bot.create_new_badge_emoji(url=player.clan.badge.url)
                            greeting = f', welcome to {badge}{player.clan.name}!'
                        channel = results.get('clanChannel')
                        channel = self.bot.get_channel(channel)
                        await channel.send(f'{ctx.author.mention}{greeting}')
                except Exception:
                    pass
            elif not verified:
                if db_server.use_api_token:
                    embed = disnake.Embed(
                        description=f'The player you are looking for is [{player.name}]({player.share_link}), however it appears u may have made a mistake.\n Double check your api token again.',
                        color=disnake.Color.red(),
                    )
                    await modal_inter.send(embed=embed, ephemeral=True)
                else:
                    embed = disnake.Embed(
                        description=f'[{player.name}]({player.share_link}) is already linked to another user. Please try again with an api token.',
                        color=disnake.Color.red(),
                    )
                    await modal_inter.send(embed=embed, ephemeral=True)

        elif ctx.data.custom_id == 'Link Help':
            embed = disnake.Embed(
                title='Finding a player tag',
                description=f"- Open Game\n- Navigate to your account's profile\n- Near top left click copy icon to copy player tag to clipboard\n"
                f'- Make sure it is the player tag & **not** the clan\n- View photo below for reference',
                color=disnake.Color.red(),
            )
            embed.set_image(url='https://clashking.b-cdn.net/clash-assets/bot/find_player_tag.png')
            embed2 = disnake.Embed(
                title='What is your api token? ',
                description=f'- Reference below for help finding your api token.\n- Open Clash and navigate to Settings > More Settings\n- **OR** use the following link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings'
                + '\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.',
                color=disnake.Color.red(),
            )
            embed2.set_image(url='https://clashking.b-cdn.net/clash-assets/bot/api_token_help.png')
            await ctx.send(embeds=[embed, embed2], ephemeral=True)
