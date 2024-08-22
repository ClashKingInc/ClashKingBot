import disnake

from commands.player.utils import detailed_player_board, create_profile_troops, history, upgrade_embed

from classes.bot import CustomClient
from classes.player.stats import StatsPlayer


class ProfileView(disnake.ui.View):
    def __init__(self, bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, results):
        super().__init__(timeout=600)
        self.bot = bot
        self.ctx = ctx
        self.results: list[StatsPlayer] = results
        self.profile_pages = ['Info', 'Troops', 'Upgrades', 'History']
        self.current_stat = 0
        self.current_page = 0
        self.history_cache_embed = {}

        # Initialize the components
        self.add_item(self.create_stat_select())
        if len(results) > 1:
            self.add_item(self.create_profile_select())

    async def on_timeout(self):
        try:
            await self.ctx.edit_original_message(components=[])
        except:
            pass

    def create_stat_select(self):
        options = [
            disnake.SelectOption(label='Overview', emoji=self.bot.emoji.xp.partial_emoji, value='Info'),
            disnake.SelectOption(label='Troops', emoji=self.bot.emoji.troop.partial_emoji, value='Troops'),
            disnake.SelectOption(label='Upgrades/Rushed', emoji=self.bot.emoji.clock.partial_emoji, value='Upgrades'),
            disnake.SelectOption(label='Clan History', emoji=self.bot.emoji.clan_castle.partial_emoji, value='History'),
        ]

        return StatSelect(self.bot, options)

    def create_profile_select(self):
        player_results = [
            disnake.SelectOption(label=f'{player.name}', emoji=self.bot.fetch_emoji(player.town_hall).partial_emoji, value=f'{count}')
            for count, player in enumerate(self.results)
        ]

        return ProfileSelect(self.bot, player_results)

    async def update_embed(self):
        embed = await self.display_embed(self.profile_pages[self.current_stat])
        if isinstance(embed, list):
            await self.ctx.edit_original_message(embeds=embed, view=self)
        else:
            await self.ctx.edit_original_message(embed=embed, view=self)

    async def display_embed(self, stat_type):
        if stat_type == 'Info':
            return await detailed_player_board(self.bot, self.results[self.current_page], server=self.ctx.guild)
        elif stat_type == 'Troops':
            return await create_profile_troops(self.bot, self.results[self.current_page])
        elif stat_type == 'Upgrades':
            return await upgrade_embed(self.bot, self.results[self.current_page])
        elif stat_type == 'History':
            player = self.results[self.current_page]
            if player.tag not in self.history_cache_embed:
                self.history_cache_embed[player.tag] = await history(self.bot, self.results[self.current_page])
            return self.history_cache_embed[player.tag]


class StatSelect(disnake.ui.Select):
    def __init__(self, bot: CustomClient, options):
        self.bot = bot
        super().__init__(placeholder='Choose a page', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: disnake.MessageInteraction):
        view: ProfileView = self.view  # Retrieve the view object automatically set by disnake
        view.current_stat = view.profile_pages.index(self.values[0])
        await interaction.response.edit_message(view=view)
        await view.update_embed()


class ProfileSelect(disnake.ui.Select):
    def __init__(self, bot: CustomClient, options):
        self.bot = bot
        super().__init__(placeholder='Accounts', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: disnake.MessageInteraction):
        view: ProfileView = self.view  # Retrieve the view object automatically set by disnake
        view.current_page = int(self.values[0])
        await interaction.response.edit_message(view=view)
        await view.update_embed()


async def button_pagination(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, msg, results):
    view = ProfileView(bot, ctx, results)
    embed = await detailed_player_board(bot, results[0], server=ctx.guild)
    await msg.edit(embed=embed, view=view)
