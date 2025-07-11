import disnake
from disnake.ext import commands

from classes.bot import CustomClient


class UtilityButtons(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    """@commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent):
        print(payload)
        results = await self.bot.bases.find_one({'message_id': payload.message_id})
        if results:
            channel = await self.bot.getch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            base_id = results.get('link').split('&id=')[-1]
            file = await message.attachments[0].to_file()
            await channel.send(
                content=f'https://link.clashofclans.com/en?action=OpenLayout&id={base_id}',
                file=file
            )"""

    @commands.Cog.listener()
    async def on_button_click(self, res: disnake.MessageInteraction):
        if res.data.custom_id == 'link':
            results = await self.bot.bases.find_one({'message_id': res.message.id})
            count = results.get('downloads')

            row_one = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label='Link',
                    emoji='🔗',
                    style=disnake.ButtonStyle.grey,
                    custom_id='link',
                ),
                disnake.ui.Button(
                    label=f'{count + 1} Downloads',
                    emoji='📈',
                    style=disnake.ButtonStyle.grey,
                    custom_id='who',
                ),
            )

            await res.message.edit(components=[row_one])
            await self.bot.bases.update_one(
                {'message_id': res.message.id},
                {
                    '$inc': {'downloads': 1},
                    '$push': {'downloaders': f'{res.author.mention} [{res.author.name}]'},
                },
            )
            if not results.get('new', False):
                await res.send(content=results.get('link'), ephemeral=True)
            else:
                base_id = results.get('link').split('&id=')[-1]
                await res.send(
                    content=f'https://link.clashofclans.com/en?action=OpenLayout&id={base_id}',
                    ephemeral=True,
                )

        elif res.data.custom_id == 'who':
            results = await self.bot.bases.find_one({'message_id': res.message.id})
            ds = results.get('downloaders')
            if ds == []:
                embed = disnake.Embed(description='No Downloads Currently.', color=disnake.Color.red())
                return await res.send(embed=embed, ephemeral=True)
            else:
                text = ''
                for down in ds:
                    text += '➼ ' + str(down) + '\n'
                embed = disnake.Embed(
                    title='**Base Downloads:**',
                    description=text,
                    color=disnake.Color.green(),
                )
                return await res.send(embed=embed, ephemeral=True)
