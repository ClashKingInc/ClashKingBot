from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
import io
import discord
from wand.image import Image as Im
from wand.display import display

class pfp(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="pfp")
    async def createPFP(self,ctx, *, name):
        if ctx.guild.id != 328997757048324101:
            return
        size = 95
        if len(name) >= 20:
            return await ctx.send("Name too long, sorry :/")

        if len(name) >= 14:
            size = 70

        back = Image.open("logo.png")

        width = 1100
        height = 200
        transparent = (0, 0, 0, 0)
        text = "copyright"
        white = (255, 255, 255)
        font = ImageFont.truetype("logofont.ttf", size)
        img = Image.new("RGBA", (width, height),transparent)
        draw = ImageDraw.Draw(img)


        draw.text((width/2, height/2), name, anchor="mm", fill=(22, 37, 91), font=font)
        draw = ImageDraw.Draw(img)
        img.save("text.png")
        #img.show()

        with Im(filename="text.png") as img:
            img.distort('arc', (20,))
            img.save(filename='text.png')
            #display(img)

        text = Image.open("text.png")





        back.paste(text, (163,930), text.convert("RGBA"))
        #back.show()

        pfp = ImageDraw.Draw(back)



        temp = io.BytesIO()
        back.save(temp, format="png")


        temp.seek(0)
        file = discord.File(fp=temp, filename="filename.png")
        await ctx.reply(file=file, mention_author= False)




def setup(bot: commands.Bot):
    bot.add_cog(pfp(bot))