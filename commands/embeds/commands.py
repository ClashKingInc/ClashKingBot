import aiohttp
import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from discord import autocomplete
from exceptions.CustomExceptions import MessageException
from utility.discord_utils import check_commands

from .utils import encoded_data, reverse_encoding, shorten_link


class Embeds(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='embed', description='Embed Command')
    async def embed(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @embed.sub_command(name='create', description='Create an embed')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def embed_create(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        name: str,
        discohook_url_or_messsage_link: str,
    ):
        await ctx.response.defer(ephemeral=True)

        lookup = await self.bot.custom_embeds.find_one({'$and': [{'server': ctx.guild_id}, {'name': name}]})
        if lookup is not None:
            raise MessageException('Cannot have 2 embeds with the same name')

        if discohook_url_or_messsage_link.startswith('https://share.discohook.app'):
            async with aiohttp.ClientSession() as session:
                async with session.get(discohook_url_or_messsage_link, allow_redirects=True) as response:
                    discohook_url = str(response.url)
            data = discohook_url.split('data=')
            decoded_embed = reverse_encoding(base64_encoded=data[-1])
        elif 'discord.com' in discohook_url_or_messsage_link:
            try:
                link_split = discohook_url_or_messsage_link.split('/')
                message_id = link_split[-1]
                channel_id = link_split[-2]
                channel = await self.bot.getch_channel(channel_id=int(channel_id))
                if channel is None:
                    raise MessageException('Cannot access the channel this embed is in')

                message = await channel.fetch_message(int(message_id))
                if not message.embeds:
                    raise MessageException('Message has no embeds')

                data = {'embeds': [e.to_dict() for e in message.embeds]}
                if message.content is not None:
                    data['content'] = message.content
                decoded_embed = data
            except Exception:
                raise MessageException(f'Something went wrong :/ An error occured with the message link.')
        else:
            raise MessageException('Invalid Discohook or Message Link')

        await self.bot.custom_embeds.insert_one({'server': ctx.guild_id, 'name': name, 'data': decoded_embed})
        await ctx.send('Embed Created! View with `/embed post`', ephemeral=True)

    @embed.sub_command(name='edit', description='Edit an embed')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def embed_edit(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(autocomplete=autocomplete.embeds),
        discohook_url: str = commands.Param(default=None),
    ):
        await ctx.response.defer()
        lookup = await self.bot.custom_embeds.find_one({'$and': [{'server': ctx.guild_id}, {'name': name}]})
        if lookup is None:
            raise MessageException('No embed with that name found on this server')

        if discohook_url is None:
            encoding = encoded_data(data=lookup.get('data'))
            shortened_url = await shorten_link(url=f'https://discohook.org/?data={encoding}')
            buttons = disnake.ui.ActionRow(disnake.ui.Button(label='Edit Embed', url=shortened_url, style=disnake.ButtonStyle.url))
            await ctx.edit_original_message(
                content='Click the button below to edit your embed',
                components=[buttons],
            )
        else:
            if discohook_url.startswith('https://share.discohook.app'):
                async with aiohttp.ClientSession() as session:
                    async with session.get(discohook_url, allow_redirects=True) as response:
                        discohook_url = str(response.url)
            data = discohook_url.split('data=')
            decoded_embed = reverse_encoding(base64_encoded=data[-1])
            await self.bot.custom_embeds.update_one(
                {'$and': [{'server': ctx.guild_id}, {'name': name}]},
                {'$set': {'data': decoded_embed}},
            )
            embeds = [disnake.Embed.from_dict(data=e) for e in decoded_embed.get('embeds', [])]
            await ctx.send(
                content=f'**Your new embed**\n\n' + (decoded_embed.get('content') or ''),
                embeds=embeds,
            )

    @embed.sub_command(name='post', description='Post an embed')
    async def embed_post(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(autocomplete=autocomplete.embeds),
    ):
        await ctx.response.defer(ephemeral=True)
        lookup = await self.bot.custom_embeds.find_one({'$and': [{'server': ctx.guild_id}, {'name': name}]})
        lookup = lookup.get('data')
        embeds = [disnake.Embed.from_dict(data=e) for e in lookup.get('embeds', [])]
        await ctx.send('Embed Created', ephemeral=True)
        await ctx.channel.send(content=lookup.get('content', ''), embeds=embeds)

    @embed.sub_command(name='delete', description='Delete an embed')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def embed_delete(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(autocomplete=autocomplete.embeds),
    ):
        await ctx.response.defer(ephemeral=True)
        await self.bot.custom_embeds.delete_one({'$and': [{'server': ctx.guild_id}, {'name': name}]})
        await ctx.edit_original_message(content='Embed Deleted')

    @embed.sub_command(name='help', description='Help creating an embed')
    async def embed_help(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.send('https://docs.clashking.xyz/utility/embeds')


def setup(bot: CustomClient):
    bot.add_cog(Embeds(bot))
