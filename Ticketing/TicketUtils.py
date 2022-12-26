import disnake

async def get_embed_json(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(description="Go to xxxxxx.com & get json")
    dict = embed.to_dict()
    await ctx.edit_original_message(embed=embed)



async def parse_embed_json(json: str, ctx: disnake.ApplicationCommandInteraction):
    data = {
      "type": "rich",
      "title": "test",
      "description": "test",
      "color": 0x00FFFF
    }
    embed = disnake.Embed.from_dict(data)
    await ctx.edit_original_message(embed=embed)
    #pass