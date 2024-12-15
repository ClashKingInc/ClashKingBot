import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from commands.components.buttons import button_logic
from disnake import ButtonStyle
from disnake.ui import Button, ActionRow
from exceptions.CustomExceptions import *
from utility.discord_utils import check_commands, get_webhook_for_channel, interaction_handler


full_mapping = {
    'clandetailed': 'Clan Detailed',
    'clanbasic': 'Clan Basic',
    'clanmini': 'Clan Minimalistic',
    'clancompo': 'Clan Composition',
    'clanhero': 'Clan Hero Progress',
    'clantroops': 'Clan Troops Progress',
    'clansorted': 'Clan Sorted',
    'clandonos': 'Clan Donations',
    'clanwarpref': 'Clan War Preference',
    'clanactivity': 'Clan Activity',
    'clancapoverview': 'Clan Capital Overview',
    'clancapdonos': 'Clan Capital Donations',
    'clancapraids': 'Clan Capital Raids',
    'clanwarlog': 'Clan War Log',
    'clancwlperf': 'Clan CWL Performance',
    'clansummary': 'Clan Summary',
    'clangames': 'Clan Games',
    'familycompo': 'Family Composition',
    'familysummary': 'Family Summary',
    'familyoverview': 'Family Overview',
    'familyheroprogress': 'Family Hero Progress',
    'familytroopprogress': 'Family Troop Progress',
    'familysorted': 'Family Sorted',
    'familydonos': 'Family Donations',
    'familygames': 'Family Games',
    'familyactivity': 'Family Activity',
    'legendday': 'Legend Day',
    'legendseason': 'Legend Season',
    'legendhistory': 'Legend History',
    'legendclan': 'Legend Clan',
    'legendcutoff': 'Legend Cutoff',
    'legendstreaks': 'Legend Streaks',
    'legendbuckets': 'Legend Buckets',
    'legendeosfinishers': 'Legend EOS Finishers',
    'discordlinks': 'Discord Links',
}

mapping = {
    #day 1
    'clandetailed': 'Clan Detailed',
    'clanbasic': 'Clan Basic',
    'clanmini': 'Clan Minimalistic',
    'clancompo': 'Clan Composition',
    'clandonos': 'Clan Donations',

    #day 2
    'clanactivity': 'Clan Activity',
    'clancapoverview': 'Clan Capital Overview',
    'clancapdonos': 'Clan Capital Donations',
    'clancapraids': 'Clan Capital Raids',
    'familyoverview': 'Family Overview',
    'familyclans': 'Family Clans',

    #day 3
    'legendclan': 'Legend Clan',
}



class MessageCommands(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.message_command(name='Automation', dm_permission=False)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def automation(self, ctx: disnake.MessageCommandInteraction, message: disnake.Message):
        check = await self.bot.white_list_check(ctx, 'setup server')
        await ctx.response.defer(ephemeral=True)
        if not check and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(
                content='You cannot use this command. Missing Permissions. Must have `Manage Server` permissions or be whitelisted for `/setup server-settings`',
                ephemeral=True,
            )

        if not message.components:
            raise MessageException('This message has no components')

        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        autoboard_count = await self.bot.autoboards.count_documents({"$and" : [{'webhook_id': {'$ne': None}}, {"server_id" : ctx.guild_id}]})
        if autoboard_count >= db_server.autoboard_limit:
            raise MessageException('You have reached your automation limit, this feature is in beta, please reach out to support.')

        options = []
        options_added = set() #this is to let us force page 0 on pagination
        for child in message.components[0].children:
            if child.custom_id is None:
                continue
            name = child.custom_id.split(':')[0]
            if mapping.get(name) is not None:
                mapped_name = mapping.get(name)
                custom_id = child.custom_id
                if "page=" in child.custom_id:
                    split_view = child.custom_id.split(":")
                    split_view[-1] = "page=0"
                    custom_id = ":".join(split_view)
                if custom_id not in options_added:
                    options.append(disnake.SelectOption(label=mapped_name, value=f"choosecustom_{custom_id}"))
                    options_added.add(custom_id)

        options.sort(key=lambda x: x.label)
        if not options:
            raise MessageException('This command does not support auto refreshing currently')

        if len(options) >= 2:
            option_select = disnake.ui.Select(
                options=options,
                placeholder=f'Select Type',  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            await ctx.edit_original_message(
                content='Choose which button to make an auto refreshing automation for?',
                components=[disnake.ui.ActionRow(option_select)],
            )
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, ephemeral=True)
            custom_id = res.values[0].split("_")[-1]
        else:
            custom_id = options[0].value.split("_")[-1]

        components = [
            ActionRow(
                Button(style=ButtonStyle.grey, label="Auto Post", custom_id="auto_post"),
                Button(style=ButtonStyle.grey, label="Auto Refresh", custom_id="auto_refresh")
            )
        ]

        await ctx.edit_original_response(content="How would you like to automate this?\n"
                                                 "- Auto Post: post on days of your choice at the daily reset (5 AM UTC)\n"
                                                 "- Auto Refresh: Refresh every 30-60 minutes", components=components)

        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

        if res.data.custom_id == "auto_post":
            select = disnake.ui.Select(
                placeholder="Select days",
                min_values=1,
                max_values=8,
                options=[
                    disnake.SelectOption(label="Monday", value="monday"),
                    disnake.SelectOption(label="Tuesday", value="tuesday"),
                    disnake.SelectOption(label="Wednesday", value="wednesday"),
                    disnake.SelectOption(label="Thursday", value="thursday"),
                    disnake.SelectOption(label="Friday", value="friday"),
                    disnake.SelectOption(label="Saturday", value="saturday"),
                    disnake.SelectOption(label="Sunday", value="sunday"),
                    disnake.SelectOption(label="End of Season", value="endofseason"),
                ]
            )
            await ctx.edit_original_response(content="When would you like to autopost?\n"
                                                     "You can choose as many options as you would like, if any 2 days overlap (like friday + cwl end), it will still only send once",
                                             components=[disnake.ui.ActionRow(select)]
                                             )
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

            webhook = await get_webhook_for_channel(channel=message.channel, bot=self.bot)
            thread = None
            if isinstance(message.channel, disnake.Thread):
                await message.channel.add_user(self.bot.user)
                thread = message.channel.id

            await self.bot.autoboards.insert_one({
                'type': "post",
                'server_id': ctx.guild.id,
                'button_id': custom_id,
                "webhook_id" : webhook.id,
                "thread_id" : thread,
                'days' : res.values,
                'locale' : str(ctx.locale)
            })
            await message.delete()
            await ctx.edit_original_message('Auto Post Automation Created', components=[])

        elif res.data.custom_id == "auto_refresh":
            webhook = await get_webhook_for_channel(channel=message.channel, bot=self.bot)
            thread = None
            if isinstance(message.channel, disnake.Thread):
                await message.channel.add_user(self.bot.user)
                thread = message.channel.id

            placeholder, _ = await button_logic(button_data=custom_id, bot=self.bot, guild=ctx.guild, locale=ctx.locale)
            if thread is not None:
                thread = await self.bot.getch_channel(thread)
                webhook_message = await webhook.send(embed=placeholder, components=[], thread=thread, wait=True)
                thread = thread.id
            else:
                webhook_message = await webhook.send(embed=placeholder, components=[], wait=True)
            await self.bot.autoboards.update_one(
                {'$and': [{'button_id': custom_id}, {'server_id': ctx.guild_id}, {'type' : "refresh"}]},
                {
                    '$set': {
                        'webhook_id': webhook.id,
                        'thread_id': thread,
                        'message_id': webhook_message.id,
                        'locale': str(ctx.locale)
                    }
                },
                upsert=True,
            )
            await message.delete()
            await ctx.edit_original_message('Refresh Automation Created!', components=[])




def setup(bot: CustomClient):
    bot.add_cog(MessageCommands(bot))
