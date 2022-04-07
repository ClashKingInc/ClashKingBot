
from disnake.ext import commands
import disnake

import inspect

class help(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='help')
    async def help(self, ctx):
        embeds = []

        prefix = ctx.prefix
        embed = disnake.Embed(title="Family & Clan Commands",
                              description="Family & Clan specific commands",
                              color=disnake.Color.blue())

        text = ""
        if ctx.guild.id == 328997757048324101:
            text = f"\n**{prefix}pfp `customtext`**\nCreate a custom usa profile pic."
        embed.add_field(name=f"__**Family Commands**__",
                        value=f"**{prefix}family**\n"
                              "Get all clans registered to this server\n"
                              f"**{prefix}leaderboard, alias = [{prefix}lb]**\n"
                              f"Display all clans in the top 25 by country\n"
                              f"**{prefix}alias**\n"
                              f"Display a list of clans & their alias\n"
                              f"**{prefix}getclan #clanTag**\n"
                              "Get information about a clan\n"
                              f"**{prefix}compo [Clantag, Alias, Blank]**\n"
                              f"Calculate townhall composition for a clan, or if left blank for family.{text}",
                        inline=False)

        embed.add_field(name=f"__**SuperTroop Commands**__",
                        value=f"**{prefix}boost [#ClanTag or Alias]**\n"
                              "Get all super troops in a clan\n"
                              f"**{prefix}super [TroopName] <ClanTag or Alias>**\n"
                              f"Get the super troops in a clan or family\n",
                        inline=False)

        embed.add_field(name=f"__**CWL Commands**__",
                        value=f"**{prefix}cwl**\n"
                              "Display family clans sorted by league.\n"
                              f"**{prefix}cwl status**\n"
                              f"Current Cwl Spin Results (only during cwl week)\n",
                        inline=False)

        embed.add_field(name=f"__**Family Rank Commands**__",
                        value=f"**{prefix}crank**\n"
                              "Get list of family clans in top leaderboard\n"
                              f"**{prefix}prank**\n"
                              f"Get list of players on this server who are in the top leaderboard\n"
                              f"**{prefix}top [NumberOfPlayers]**\n"
                              f"Get the list of top players on this server.\n",
                        inline=False)


        embed.set_thumbnail(url=ctx.guild.icon_url_as())
        embeds.append(embed)

        embed2 = disnake.Embed(title="Player Commands",
                              description="Player related commands",
                              color=disnake.Color.blue())

        embed2.add_field(name=f"__**Player Commands**__",
                        value=f"**{prefix}rank @DiscordName**\n"
                              "Show the various rankings for a player\n"
                              f"**{prefix}invite #playerTag**\n"
                              f"Display basic player info and a link to their in-game profile\n"
                              f"**{prefix}lookup [#PLAYERTAG, @DiscordName, nothing]**\n"
                              f"Display detailed player info\n"
                              f"**{prefix}list [@DiscordName, nothing]**\n"
                              "List of accounts & average th/count\n"
                              f"**{prefix}link**\n"
                              "Start link wizard to link a player tag to a Discord account\n"
                              f"**{prefix}refresh**\n"
                              f"Update/Refresh your discord roles."
                              f"**{prefix}army**\n"
                              f"Show a breakdown of the troops in an army quick train link.\n"
                              f"**{prefix}roleusers @RoleName**\n"
                              f"List users in a specific role",
                        inline=False)

        embed2.set_thumbnail(url=ctx.guild.icon_url_as())
        embeds.append(embed2)

        embed3 = discord.Embed(title="Clan Management",
                               description="Commands to manage clans linked to server",
                               color=discord.Color.blue())

        embed3.add_field(name=f"__**Clan Mgmt.**__",
                         value=f"**{prefix}addclan**\n"
                               "Register a new clan on this server.\n"
                               f"**{prefix}removeclan [CLANTAG, ALIAS]**\n"
                               f"Unregister a clan from your Discord server.",
                         inline=False)
        embed3.add_field(name=f"__**Autoboard Commands**__",
                         value=f"**{prefix}autoboard**\n"
                               "Autoboard wizard to setup `.top` or `.lb` to post daily in a channel.\n"
                               f"**{prefix}autoboard remove**\n"
                               f"To remove `.top` or `.lb` autoboards from server.\n"
                               f"**{prefix}autoboard list**\n"
                               f"List & details about current autoboards.",
                         inline=False)

        embed3.add_field(name=f"__**CWL Roster Creation**__",
                         value=f"**{prefix}roster create**\n"
                               "Roster wizard to initialize roster w/ players.\n"
                               f"**{prefix}roster list**\n"
                               f"List of Rosters on server.\n"
                               f"**{prefix}roster [listalias]**\n"
                               f"Display selected roster.\n"
                               f"**{prefix}roster edit [listalias]**\n"
                               f"Edit wizard for selected roster.\n"
                               f"**{prefix}roster delete [listalias]**\n"
                               f"Delete selected roster.\n"
                               f"**{prefix}roster compare [clan] [listalias]**\n"
                               f"Compare roster to members currently in clan & see who is missing. Supports"
                               f" clan tag or alias of a clan linked to server.",
                         inline=False)

        embed3.set_thumbnail(url=ctx.guild.icon_url_as())
        embeds.append(embed3)

        embed4 = discord.Embed(title="Moderator Commands",
                               description="Assorted Moderation commands",
                               color=discord.Color.blue())

        embed4.add_field(name=f"__**Eval & Link Commands**__",
                         value=f"**{prefix}eval [@User or @Role]**\n"
                               "Evaluate a user's roles or Evaluate all the users in a specific role\n"
                               f"**{prefix}modlink @DiscordName #PLAYERTAG**\n"
                               f"Link a player tag to a Discord account.\n"
                               f"**{prefix}unlink #PLAYERTAG**\n"
                               f"Unlink a player tag from Discord.",
                         inline=False)

        embed4.add_field(name=f"__**Ban Commands**__",
                         value=f"**{prefix}banlist add #PLAYERTAG <Notes>**\n"
                               "Ban a player from your guild's clans\n"
                               f"**{prefix}banlist remove #PLAYERTAG**\n"
                               f"Remove a player from your guild's ban list\n"
                               f"**{prefix}banlist**\n"
                               f"Get the list of players banned on this server\n"
                               f"**{prefix}setbanlist #CHANNEL**\n"
                               f"Set a channel for server ban list to auto-update in.",
                         inline=False)

        embed4.add_field(name=f"__**Award Commands**__",
                         value=f"**{prefix}award list Emoji**\n"
                               "Lists users with a specific emoji in their nickname\n"
                               f"**{prefix}award give #CLANTAG Emoji <@GrantDiscordRole>**\n"
                               f"Add an emoji in front of the users in a given clan.\n"
                               f"**{prefix}award remove Emoji <@RemoveDiscordRole>**\n"
                               f"Remove an emoji in front of the users in a given role.",
                         inline=False)

        embed4.add_field(name=f"__**Setting Commands**__",
                         value=f"**{prefix}setprefix NEWPREFIX**\n"
                               "Set a new prefix for the bot.\n"
                               f"**{prefix}setgreeting GREETING**\n"
                               f"Set a custom greeting for people who join & link on your server.\n",
                         inline=False)

        embed4.set_thumbnail(url=ctx.guild.icon_url_as())
        embeds.append(embed4)

        embed5 = discord.Embed(title="Role Management Commands",
                               description="Player related commands",
                               color=discord.Color.blue())

        embed5.add_field(name=f"__**LinkRole Commands**__",
                         value=f"**{prefix}linkroles add @RoleName**\n"
                                "Adds a role to remove when a player is linked to a family clan.\n"
                                f"**{prefix}linkroles delete @RoleName**\n"
                                "Deletes a role from the list of roles to remove when a player is linked to a family clan.\n"
                                f"**{prefix}linkroles list**\n"
                                "Displays the list of roles to remove when a player is linked to a family clan.",
                         inline=False)

        embed5.add_field(name=f"__**GeneralRole Commands**__",
                         value=f"**{prefix}generalrole add @RoleName**\n"
                                "Adds a role to add when a player is linked to a family clan.\n"
                                f"**{prefix}generalrole remove @RoleName**\n"
                                "Deletes a role from the list of roles to add when a player is linked to a family clan.\n"
                                f"**{prefix}generalrole list**\n"
                                "Displays the list of roles to add when a player is linked to a family clan.",
                         inline=False)

        embed5.add_field(name=f"__**EvalIgnore Commands**__",
                         value=f"**{prefix}evalignore add @RoleName**\n"
                                "Adds a role to ignore when a user or role is evaluated.\n"
                                f"**{prefix}evalignore remove @RoleName**\n"
                                "Deletes a role to ignore when a user or role is evaluated.\n"
                                f"**{prefix}evalignore list**\n"
                                "Displays the list of roles to ignore when a user or role is evaluated.",
                         inline=False)

        embed5.add_field(name=f"__**RemoveRoles Commands**__",
                         value=f"**{prefix}removeroles add @RoleName**\n"
                            "Adds a role to remove when a player is no longer in a family clan.\n"
                            f"**{prefix}removeroles remove @RoleName**\n"
                            "Deletes a role from the list of roles to remove when a player is no longer in a family clan.\n"
                            f"**{prefix}removeroles list**\n"
                            "Displays the list of roles to remove when a player is no longer in a family clan.",
                         inline=False)

        embed5.add_field(name=f"__**Whitelist Commands**__",
                         value=f"**{prefix}whitelist add @RoleName command**\n"
                            "Adds a role that can run a specific command.\n"
                            f"**{prefix}whitelist remove @RoleName command**\n"
                            "Deletes a role that can run a specific command.\n"
                            f"**{prefix}whitelist list**\n"
                            "Displays the list of commands/roles that have whitelist overrides.",
                         inline=False)

        embed5.set_thumbnail(url=ctx.guild.icon_url_as())
        embeds.append(embed5)

        embed6 = discord.Embed(title="Misc Commands",
                              description=f"**{prefix}supportserver**\n"
                                          f"Link to support server\n"
                                          f"**{prefix}invitebot**\n"
                                          f"Link to invite bot to your server.",
                              color=discord.Color.blue())

        embeds.append(embed6)


        dropdown = create_actionrow(select)

        msg = await ctx.send(embed=embed, components=[dropdown])

        while True:
            try:
                res = await wait_for_component(self.bot, components=select, messages=msg, timeout=600)
            except:
                await msg.edit(components=None)
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()
            #print(res.selected_options)
            await msg.edit(embed=embeds[int(res.selected_options[0])-1])






def setup(bot: commands.Bot):
    bot.add_cog(help(bot))