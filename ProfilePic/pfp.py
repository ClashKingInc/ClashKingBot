from disnake.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
import io
import disnake
from wand.image import Image as Im
from wand.display import display

class pfp(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="pfp")
    async def createPFP(self,ctx, *, name):
        size = 95
        if len(name) >= 20:
            return await ctx.send("Name too long, sorry :/")

        if len(name) >= 14:
            size = 70

        back = Image.open("ProfilePic/logo.png")

        width = 1100
        height = 200
        transparent = (0, 0, 0, 0)
        text = "copyright"
        white = (255, 255, 255)
        font = ImageFont.truetype("ProfilePic/logofont.ttf", size)
        img = Image.new("RGBA", (width, height),transparent)
        draw = ImageDraw.Draw(img)


        draw.text((width/2, height/2), name, anchor="mm", fill=(22, 37, 91), font=font)
        draw = ImageDraw.Draw(img)
        img.save("ProfilePic/text.png")
        #img.show()

        with Im(filename="ProfilePic/text.png") as img:
            img.distort('arc', (20,))
            img.save(filename='ProfilePic/text.png')
            #display(img)

        text = Image.open("ProfilePic/text.png")





        back.paste(text, (163,930), text.convert("RGBA"))
        #back.show()

        pfp = ImageDraw.Draw(back)



        temp = io.BytesIO()
        back.save(temp, format="png")


        temp.seek(0)
        file = disnake.File(fp=temp, filename="ProfilePic/filename.png")
        await ctx.reply(file=file, mention_author= False)




def setup(bot: commands.Bot):
    bot.add_cog(pfp(bot))