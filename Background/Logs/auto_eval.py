try:
    s_data = await self.bot.server_db.find_one({"server": server})
    if s_data.get("autololeval", False) is False:
        raise Exception
    link = await self.bot.link_client.get_link(member.tag)
    if link is not None:
        evalua = self.bot.get_cog("Eval")
        user = await cache_server.getch_member(link)
        embed = await evalua.eval_logic(guild=cache_server, members_to_eval=[user], role_or_user=user,
                                        test=False,
                                        change_nick="Off", return_embed=True)
        log_channel = s_data.get("autoeval_log")
        if log_channel is not None:
            try:
                log_channel = await self.bot.getch_channel(log_channel)
                await log_channel.send(embed=embed)
            except:
                pass
except:
    pass

try:
    s_data = await self.bot.server_db.find_one({"server": server})
    if s_data.get("autololeval", False) is False:
        raise Exception
    link = await self.bot.link_client.get_link(member.tag)
    if link is not None:
        evalua = self.bot.get_cog("Eval")
        user = await cache_server.getch_member(link)
        embed = await evalua.eval_logic(guild=cache_server, members_to_eval=[user], role_or_user=user,
                                        test=False,
                                        change_nick="Off", return_embed=True)
        log_channel = s_data.get("autoeval_log")
        if log_channel is not None:
            try:
                log_channel = await self.bot.getch_channel(log_channel)
                await log_channel.send(embed=embed)
            except:
                pass
except:
    pass
