import io
import disnake
from disnake.ext import commands
from PIL import Image, ImageDraw, ImageFont

class pepe(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="pepe",
                       description="Fun Command. Create a pepe holding a sign w/ text.")
    async def createPFP(self,ctx, sign_text : str, hidden : str=commands.Param(choices=["Yes", "No"])):
        """
            Parameters
            ----------
            sign_text: Text to write on sign (up to 25 char)
            hidden : If yes, message will be visible only to you
        """
        size = 40
        if len(sign_text) > 25:
            return await ctx.send("Too long, sorry :/")

        if len(sign_text) >= 11:
            size = 30

        if len(sign_text) > 14:
            size = 23

        if len(sign_text) > 19:
            size = 16


        back = Image.open("pepe/pepesign.png")

        width = 250
        height = 250
        font = ImageFont.truetype("pepe/pepefont.ttf", size)
        draw = ImageDraw.Draw(back)

        draw.text(((width/2)-5, 55), sign_text, anchor="mm", fill=(0, 0, 0), font=font)

        temp = io.BytesIO()
        back.save(temp, format="png")

        temp.seek(0)
        file = disnake.File(fp=temp, filename="filename.png")

        if hidden == "Yes":
            await ctx.send(content="Save image or copy link & send wherever you like :)",file=file, ephemeral=True)
        else:
            await ctx.send(file=file)


def setup(bot: commands.Bot):
    bot.add_cog(pepe(bot))
