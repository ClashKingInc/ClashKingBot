import asyncio
from aiohttp import web, ClientSession
import xmltodict
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
import disnake
import re

class YoutubeHook(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        # Set for storing video ids
        self.memory = set()

    # Function to start the web server async
    async def web_server(self):
        # This is required to use decorators for routes
        routes = web.RouteTableDef()

        # The youtube API sends a get request for the initial authorization
        @routes.get('/')
        async def authenticate(request):
            if 'hub.challenge' not in request.query:
                return web.Response(status=400)
            print("Authenticated")
            challenge_response = request.query.get('hub.challenge')
            return web.Response(text=challenge_response, status=200)

        # The youtube API sends post requests when new videos are posted
        @routes.post('/')
        async def receive(request):
            # Ensure the post is of the proper type
            content_type = request.content_type
            if content_type != 'application/atom+xml':
                return web.Response(status=400)

            # Read all the data in the body and convert it to a dict
            body_content = await request.content.read(n=-1)
            data = xmltodict.parse(body_content, 'UTF-8')

            # Ensure this is a proper video and its not already been announced before
            if 'entry' in data['feed'] and data['feed']['entry']['yt:videoId'] not in self.memory:
                entry = data['feed']['entry']
                # Add video id to memory to prevent duplicates
                self.memory.add(entry['yt:videoId'])
                # store wanted data in a simple dict
                video_data = {
                    'title': entry['title'],
                    'video_url': entry['link']['@href'],
                    'channel_name': entry['author']['name'],
                    'channel_url': entry['author']['uri'],
                    'date_published': entry['published'],
                    'video_id': entry['yt:videoId']
                }
                # Trigger the new_video event with video data
                self.bot.dispatch('new_video', video_data)
            return web.Response(status=200)

        # Create application and connect the routes
        app = web.Application()
        app.add_routes(routes)

        # Prepare the app runner
        runner = web.AppRunner(app)
        await runner.setup()

        # Prepare the website
        self.site = web.TCPSite(runner, '127.0.0.1', 8080)

        # Wait until the discord bot is fully started
        #await self.bot.wait_until_ready()
        # Start the web server
        await self.site.start()
        # Send subscribe request to API
        await self.subscribe()

    # Function to subscribe to the website
    async def subscribe(self):
        # Start web client to send post request
        async with ClientSession() as session:
            # Grab the ID from the channel url
            utube_channels = await self.bot.youtube_channels.distinct("channel")
            for channel in utube_channels:
                channel_id = channel.split('/')[-1]
                # Prepare the form data required to subscribe
                payload = {
                    'hub.callback': self.bot.callback_url,
                    'hub.mode': 'subscribe',
                    'hub.topic': f'https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}',
                    'hub.lease_seconds': '',  # Might want to define this, max 828000 seconds
                    'hub.secret': '',
                    'hub.verify': 'async',
                    'hub.verify_token': ''
                }
                # Send post request to the API
                async with session.post('https://pubsubhubbub.appspot.com/subscribe', data=payload) as response:
                    # if status is 202 it worked
                    if response.status == 202:
                        print("Subscribe request sent")
                    else:
                        print("Failed to subscribe")

    # If Cog is unloaded this runs
    def __unload(self):
        # Run site stopper in background without awaiting
        asyncio.ensure_future(self.site.stop())

    @commands.slash_command(name="add-ytchannel", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def add_ytchannel(self, ctx: disnake.ApplicationCommandInteraction, channel_url:str):
        await self.bot.youtube_channels.insert_one({"channel" : channel_url})
        await ctx.send(f"{channel_url} added.", ephemeral=True)

    @commands.Cog.listener()
    async def on_new_video(self, video_data):
        # Grab the channel from bot
        video = self.bot.yt_api.get_video_by_id(video_id=video_data["video_id"], return_json=True)
        print(video)
        description = video["items"][0]["snippet"]["description"]
        links = self.get_links(description=description)

        results = self.bot.server_db.find({"yt_feed": {"$ne": None}})
        limit = await self.bot.server_db.count_documents(filter={"yt_feed": {"$ne": None}})
        for r in await results.to_list(length=limit):
            try:
                channel = r.get("yt_feed")
                channel = self.bot.get_channel(channel)
                for link in links:
                    # Build embed message
                    embed = disnake.Embed(
                        title=f"New base link from {video_data['channel_name']}",
                        color=disnake.Colour.green()
                    )
                    embed.set_author(name=video_data['title'])
                    # https://img.youtube.com/vi/<Video ID here>/1.jpg
                    embed.set_thumbnail(url=f'https://img.youtube.com/vi/{video_data["video_id"]}/1.jpg')

                    # Send message
                    buttons = disnake.ui.ActionRow()
                    buttons.append_item(disnake.ui.Button(label="Base Link", emoji=link[0], url=link[1]))
                    buttons.append_item(disnake.ui.Button(label="Video Link", emoji="<:yt:1017600077033910312>",
                                                          url=f"https://www.youtube.com/watch?v={video_data['video_id']}"))
                    await channel.send(embed=embed, components=buttons)

            except (disnake.NotFound, disnake.Forbidden):
                serv = r.get("server")
                await self.bot.server_db.update_one({"server": serv},
                                                    {"$set": {"yt_feed": None}})


    def get_links(self, description):
        links = re.findall(r'(https?://\S+)', description)
        link_list = []
        for link in links:
            link: str
            if "https://link.clashofclans.com" in link and "OpenLayout&id" in link:
                th = link.split("=")
                th = th[-1][2:4]
                emoji = self.bot.fetch_emoji(int(th))
                link_list.append([emoji, link])

        return link_list

def setup(bot: CustomClient):
    hook = YoutubeHook(bot)  # Create hook
    bot.add_cog(hook)  # add hook to bot to get context
    bot.loop.create_task(hook.web_server())  # Create web server and attach it to bot event loop