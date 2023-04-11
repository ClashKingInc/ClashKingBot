@commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        time = datetime.now().timestamp()
        if "linked_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            # initializing player link list
            clan_member_tags = []
            for player in clan.members:
                clan_member_tags.append(player.tag)
            player_links = await self.bot.link_client.get_links(*clan_member_tags)

            linked_players_embed = clan_responder.linked_players(
                ctx.guild.members, clan, player_links)
            unlinked_players_embed = clan_responder.unlinked_players(
                clan, player_links)

            unlinked_players_embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey, custom_id=f"linked_{clan.tag}"))

            await ctx.edit_original_message(
                embeds=[linked_players_embed, unlinked_players_embed],
                components=buttons)

        elif "trophies_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embed = clan_responder.player_trophy_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"trophies_{clan.tag}"))

            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "clansort-" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("-"))[1]
            sort_by = (str(ctx.data.custom_id).split("-"))[-1]
            clan = await self.bot.getClan(clan)

            players: list[coc.Player] = await self.bot.get_players(tags=[member.tag for member in clan.members], custom=False)
            embed = await self.clan_sort(players=players, clan=clan, sort_by=sort_by)
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "waropt_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embeds = await clan_responder.opt_status(self.bot, clan)
            embeds[-1].description += f"Last Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            await ctx.edit_original_message(embeds=embeds)

        elif "warlog_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            warlog = await self.bot.coc_client.get_warlog(clan.tag, limit=25)

            embed = clan_responder.war_log(clan, warlog)
            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "stroops_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embed: disnake.Embed = await clan_responder.super_troop_list(clan)

            values = (
                f"{embed.fields[0].value}\n"
                f"Last Refreshed: <t:{int(datetime.now().timestamp())}:R>")
            embed.set_field_at(
                0, name="**Not Boosting:**",
                value=values, inline=False)

            await ctx.edit_original_message(embed=embed)

        elif "clanboard_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            db_clan = await self.bot.clan_db.find_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]})

            clan_legend_ranking = await self.bot.clan_leaderboard_db.find_one(
                {"tag": clan.tag})

            embed = await clan_responder.clan_overview(
                clan=clan, db_clan=db_clan,
                clan_legend_ranking=clan_legend_ranking, previous_season=self.bot.gen_previous_season_date(),
                season=self.bot.gen_season_date(), bot=self.bot)

            values = (
                f"{embed.fields[-1].value}"
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            embed.set_field_at(len(
                embed.fields) - 1, name="**Boosted Super Troops:**",
                               value=values, inline=False)

            try:
                embed.set_image(url=ctx.message.embeds[0].image.url)
            except:
                pass

            await ctx.edit_original_message(embed=embed)

        elif "townhall_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embed = await clan_responder.player_townhall_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            await ctx.edit_original_message(embed=embed)

        elif "lo_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            member_tags = [member.tag for member in clan.members]
            members = await self.bot.get_players(
                tags=member_tags, custom=True)

            embed = clan_responder.create_last_online(
                clan=clan, clan_members=members)
            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "clangames_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            season_date = self.bot.gen_games_season()

            member_tags = [member.tag for member in clan.members]

            tags = await self.bot.player_stats.distinct(
                "tag", filter={f"clan_games.{season_date}.clan": clan.tag})
            all_tags = list(set(member_tags + tags))

            tasks = []
            for tag in all_tags:
                results = await self.bot.player_stats.find_one(
                    {"tag": tag})

                task = asyncio.ensure_future(
                    self.bot.coc_client.get_player(
                        player_tag=tag, cls=MyCustomPlayer,
                        bot=self.bot, results=results))

                tasks.append(task)

            player_responses = await asyncio.gather(*tasks)

            embed = clan_responder.create_clan_games(
                clan=clan, player_list=player_responses,
                member_tags=member_tags,
                season_date=season_date)

            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "donated_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]

            else:
                season_date = clan_utils.gen_season_date()

            tasks = []
            for member in clan.members:
                results = await self.bot.player_stats.find_one({"tag": member.tag})
                task = asyncio.ensure_future(
                    self.bot.coc_client.get_player(
                        player_tag=member.tag, cls=MyCustomPlayer, bot=self.bot,
                        results=results))
                tasks.append(task)
            player_responses = await asyncio.gather(*tasks)

            embed = clan_responder.clan_donations(
                clan=clan, type="donated",
                season_date=season_date,
                player_list=player_responses)

            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "received_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]

            else:
                season_date = clan_utils.gen_season_date()

            tasks = []
            for member in clan.members:
                results = await self.bot.player_stats.find_one({"tag": member.tag})
                task = asyncio.ensure_future(
                    self.bot.coc_client.get_player(
                        player_tag=member.tag, cls=MyCustomPlayer, bot=self.bot,
                        results=results))
                tasks.append(task)
            player_responses = await asyncio.gather(*tasks)

            embed = clan_responder.clan_donations(
                clan=clan, type="received",
                season_date=season_date,
                player_list=player_responses)

            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "ratio_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]

            else:
                season_date = clan_utils.gen_season_date()

            tasks = []
            for member in clan.members:
                results = await self.bot.player_stats.find_one({"tag": member.tag})
                task = asyncio.ensure_future(
                    self.bot.coc_client.get_player(
                        player_tag=member.tag, cls=MyCustomPlayer, bot=self.bot,
                        results=results))
                tasks.append(task)
            player_responses = await asyncio.gather(*tasks)

            embed = clan_responder.clan_donations(
                clan=clan, type="ratio",
                season_date=season_date,
                player_list=player_responses)

            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "act_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]
            else:
                season_date = clan_utils.gen_season_date()

            member_tags = [member.tag for member in clan.members]
            members = await self.bot.get_players(
                tags=member_tags, custom=True)

            embed = clan_responder.create_activities(
                clan=clan, clan_members=members, season=season_date, bot=self.bot)

            embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            await ctx.edit_original_message(embed=embed)