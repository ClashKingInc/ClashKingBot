import disnake

from background.logs.events import reddit_ee
from classes.bot import CustomClient
from disnake.ext import commands
from utility.player_pagination import button_pagination


class reddit_feed(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.reddit_ee = reddit_ee
        self.reddit_ee.on("reddit", self.reddit_task)

    async def reddit_task(self, event: dict):
        player = None
        event = event.get("data")
        if tags := event.get("tags"):
            for tag in tags:
                player = await self.bot.getPlayer(player_tag=tag)
                if player is not None:
                    break

        results = await self.bot.server_db.find({"reddit_feed": {"$ne": None}}).to_list(length=None)
        for r in results:
            server_id = r.get("server")
            if server_id not in self.bot.OUR_GUILDS:
                continue
            try:
                channel = await self.bot.getch_channel(r.get("reddit_feed"), raise_exception=True)
                role = r.get("reddit_role")
                embed = disnake.Embed(title=event.get("title"),
                                      description=f'{event.get("selftext")}\n{event.get("score")} points | [Link]({event.get("url")}) | '
                                                  f'[Comments]({event.get("comments_link")})',
                                      color=disnake.Color.green())
                buttons = disnake.ui.ActionRow(disnake.ui.Button(label="Post Link", emoji=self.bot.emoji.reddit_icon.partial_emoji, url=event.get("url")))
                if player is not None:
                    buttons.append_item(disnake.ui.Button(label="Player Profile", emoji=self.bot.emoji.troop.partial_emoji, style=disnake.ButtonStyle.green, custom_id=f"redditplayer_{player.tag}"))

                if role is not None:
                    await channel.send(content=f"<@&{role}>", embed=embed, components=buttons)
                else:
                    await channel.send(embed=embed, components=buttons)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.server_db.update_one({"server": r.get("server")}, {"$set": {"reddit_feed": None, "reddit_role" : None}})


    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "redditplayer_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True, with_message=True)
            tag = (str(ctx.data.custom_id).split("_"))[-1]
            msg = await ctx.original_message()
            player = await self.bot.getPlayer(player_tag=tag, custom=True)
            if player is None:
                return await ctx.edit_original_response(content="No player found.")
            await button_pagination(self.bot, ctx, msg, [player])


def setup(bot: CustomClient):
    bot.add_cog(reddit_feed(bot))