import lightbulb
from coc.utils import get


@lightbulb.hook(lightbulb.ExecutionSteps.CHECKS)
def store_db(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    if ctx.user.id != 215061635574792192:
        raise RuntimeError('only thomm.o can use this command')


@lightbulb.hook(lightbulb.ExecutionSteps.PRE_INVOKE)
async def auto_defer_command_response(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    await ctx.defer()


@lightbulb.hook(lightbulb.ExecutionSteps.POST_INVOKE)
async def store_recent_clan_search(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    print(ctx.options)
    return
    if ctx.options and (clan_option := get(ctx.options, name='clan')) and ():
        clan_option = ctx.options[0].name
        clan_filled = ctx.filled_options.get('clan')
        last_part = clan_filled.split('|')[-1]
        if coc.utils.is_valid_tag(last_part):
            await self.bot.ck_client.add_recent_search(
                tag=coc.utils.correct_tag(tag=last_part), type=1, user_id=ctx.user.id
            )
