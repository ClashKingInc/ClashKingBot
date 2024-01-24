
import disnake
import coc

from disnake.ext import commands
from classes.server import DatabaseServer
from classes.bot import CustomClient
from background.logs.event_websockets import clan_ee
from Link_and_Eval.eval_logic import eval_logic


class AutoEval(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("member_join", self.auto_eval)
        self.clan_ee.on("member_leave", self.auto_eval)


    async def auto_eval(self, event):
        clan = coc.Clan(data=event["clan"], client=self.bot.coc_client)
        member = coc.ClanMember(data=event["member"], client=self.bot.coc_client, clan=clan)

        pipeline = [
            {"$match": {"tag": clan.tag}},
            {"$lookup": {"from": "server", "localField": "server", "foreignField": "server", "as": "server_data"}},
            {"$set": {"server_data": {"$first": "$server_data"}}}
        ]
        for data in await self.bot.clan_db.aggregate(pipeline=pipeline).to_list(length=None):
            if data.get("server") not in self.bot.OUR_GUILDS:
                continue

            if not data.get("server_data", {}).get("autoeval", False):
                continue

            db_server = DatabaseServer(bot=self.bot, data=data.get("server_data", {}))
            link = await self.bot.link_client.get_link(member.tag)
            if link is not None:
                server = await self.bot.getch_guild(data.get("server"))
                if server is None:
                    continue
                discord_member = await server.getch_member(link)
                if discord_member is None:
                    continue

                for role in discord_member.roles:
                    if role.id in db_server.blacklisted_roles:
                        return
                change_nick = db_server.auto_nickname
                if not db_server.auto_eval_nickname:
                    change_nick = "Off"

                embed = await eval_logic(bot=self.bot, guild=server, members_to_eval=[discord_member],
                                         role_or_user=discord_member, test=False, change_nick=change_nick, auto_eval=True,
                                         auto_eval_tag=member.tag, return_embed=True, role_treatment=db_server.role_treatment)
                if data.get("server_data", {}).get("autoeval_log") is not None:
                    try:
                        channel = await self.bot.getch_channel(data.get("server_data", {}).get("autoeval_log"))
                        await channel.send(embed=embed)
                    except (disnake.NotFound, disnake.Forbidden):
                        await self.bot.server_db.update_one({"server": data.get("server")}, {'$set': {"autoeval_log": None}})



def setup(bot: CustomClient):
    bot.add_cog(AutoEval(bot))




