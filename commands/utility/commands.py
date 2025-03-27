import uuid

import coc
import disnake
from disnake.ext import commands
import pendulum as pend
from classes.bot import CustomClient
from discord import options, autocomplete
from exceptions.CustomExceptions import MessageException
from utility.components import create_components
from utility.constants import SUPER_TROOPS
from utility.discord_utils import interaction_handler

from .click import UtilityButtons
from .utils import army_embed, clan_boost_embeds, super_troop_embed
from hashids import Hashids


class UtilityCommands(UtilityButtons, commands.Cog, name='Utility'):
    def __init__(self, bot: CustomClient):
        super().__init__(bot)
        self.bot = bot

    @commands.slash_command(
        name='army',
        description='Create & share visual representations of an army link',
        install_types=disnake.ApplicationInstallTypes.all(),
        contexts=disnake.InteractionContextTypes.all(),
    )
    async def army(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @army.sub_command(name="link",description='Create a visual message representation of an army link')
    @commands.cooldown(10, 5, commands.BucketType.user)
    async def army_link(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        link: str,
        nickname: str = 'Army Link Results',
        notes: str = commands.Param(default=None, max_length=450),
    ):
        """
        Parameters
        ----------
        link: an army link copied from in-game
        nickname: (optional) nickname for this army,
        notes: (optional) notes about this army
        """
        await ctx.response.defer()
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await army_embed(bot=self.bot,
                                 nick=nickname,
                                 link=link,
                                 notes=notes,
                                 embed_color=embed_color)
        """
        we save the saved army as an embed, this is in case underlying implementations change
        """
        hasher = Hashids(min_length=6)
        id = hasher.encode(ctx.id)
        await self.bot.army_share.insert_one({
            "_id": id,
            "link": link,
            "nickname": nickname,
            "embed": embed.to_dict(),
        })
        buttons = [
            disnake.ui.Button(label=f'Copy Link', emoji=self.bot.emoji.troop.partial_emoji, url=link),
            disnake.ui.Button(label="Save Army", style=disnake.ButtonStyle.green, custom_id=f"armyshare_{id}")
        ]
        await ctx.send(embed=embed, components=buttons)

    @army.sub_command(name="share", description='Share your saved armies')
    async def army_share(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            army: str = commands.Param(autocomplete=autocomplete.user_armies)
    ):
        """
        Parameters
        ----------
        army: an army to share and post
        """
        await ctx.response.defer()
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        army_id = army.split("|")[-1].strip()
        result = await self.bot.army_share.find_one({"_id": army_id})
        if not result:
            raise MessageException(f"No matching army found for `{army}`")
        embed = disnake.Embed().from_dict(data=result.get("embed"))
        embed.colour = embed_color
        buttons = [
            disnake.ui.Button(label=f'Copy Link', emoji=self.bot.emoji.troop.partial_emoji, url=result.get("link")),
            disnake.ui.Button(label="Save Army", style=disnake.ButtonStyle.green,
                              custom_id=f"armyshare_{army_id}")
        ]
        await ctx.send(embed=embed, components=buttons)

    @commands.slash_command(
        name='boosts',
        description='Get list of troops listed in a certain clan (or all family clans if blank)',
    )
    async def super_troop_boosts(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.optional_clan,
        super_troop=commands.Param(default=None, choices=SUPER_TROOPS),
    ):
        """
        Parameters
        ----------
        clan: (optional) a clan
        super_troop: (optional) super troop to filter results for
        """
        await ctx.response.defer()
        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        if clan is None:
            clan_tags = [c.tag for c in db_server.clans]
            clans = await self.bot.get_clans(tags=clan_tags)
        else:
            clans = [clan]

        if super_troop is not None:
            embeds = await super_troop_embed(
                bot=self.bot,
                clans=clans,
                super_troop=super_troop,
                embed_color=db_server.embed_color,
            )
        else:
            embeds = await clan_boost_embeds(bot=self.bot, clans=clans)

        if len(embeds) >= 2:
            await ctx.send(embed=embeds[0], components=create_components(0, embeds, True))
        else:
            custom_id = f'clan_{uuid.uuid4()}'
            components = disnake.ui.ActionRow()
            components.append_item(
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=custom_id,
                )
            )
            as_dict = {
                'button_id': custom_id,
                'command': f'{ctx.application_command.qualified_name}',
                'clans': [c.tag for c in clans],
                'fields': ['clans'],
            }
            await self.bot.button_store.insert_one(as_dict)
            return await ctx.send(embeds=embeds, components=components)

        current_page = 0
        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, any_run=True)
            if res.data.custom_id == 'Previous':
                current_page -= 1
                await res.edit_original_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == 'Next':
                current_page += 1
                await res.edit_original_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == 'Print':
                await res.delete_original_message()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)

    @commands.slash_command(name='base', description='Post a base with link & keep track of downloads')
    async def base(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        base_link: str,
        description: str,
        photo: disnake.Attachment,
    ):
        await ctx.response.defer()

        if 'https://link.clashofclans.com/' not in base_link or '=OpenLayout&id=' not in base_link:
            raise MessageException('Not a Valid Base Link')

        description = description[0:1900]
        description = description.replace('&&', '\n')

        r1 = disnake.ui.ActionRow()
        link_button = disnake.ui.Button(label='Link', emoji='🔗', style=disnake.ButtonStyle.grey, custom_id='link')
        downloads = disnake.ui.Button(
            label='0 Downloads',
            emoji='📈',
            style=disnake.ButtonStyle.grey,
            custom_id='who',
        )
        r1.append_item(link_button)
        r1.append_item(downloads)

        attachment = await photo.to_file(use_cached=True)

        await ctx.edit_original_message(
            file=attachment,
            content=f'{description}',
            components=[r1],
        )
        msg = await ctx.original_message()
        await self.bot.bases.insert_one(
            {
                'link': base_link,
                'message_id': msg.id,
                'downloads': 0,
                'downloaders': [],
                'feedback': [],
                'new': True,
            }
        )

    """@commands.slash_command(
        name="equipment",
        description="See how different equipment combos affect heroes",
        install_types=disnake.ApplicationInstallTypes.all(),
        contexts=disnake.InteractionContextTypes.all()
    )
    async def equipment(self, ctx: disnake.ApplicationCommandInteraction):
        hero = self.bot.coc_client.get_hero()"""


def setup(bot: CustomClient):
    bot.add_cog(UtilityCommands(bot))
