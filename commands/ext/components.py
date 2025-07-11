import asyncio
import datetime
import functools
import inspect
from typing import Any, Callable, get_type_hints

import hikari.events
import lightbulb
import pendulum as pend
from hikari.events.interaction_events import ComponentInteractionCreateEvent

from classes.mongo import MongoClient
from utility.constants import RED_ACCENT

loader = lightbulb.Loader()

registered_functions: dict[str, tuple[Callable[..., None], bool, bool, bool, str | None]] = {}


def register_action(
    name: str,
    user_only: bool = False,
    no_return: bool = False,
    is_modal: bool = False,
    ephemeral: bool = False,
    group: str | None = None,
):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(func)
        hints = get_type_hints(func)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # bind the incoming args/kwargs to parameter names
            bound = sig.bind_partial(*args, **kwargs)

            # for each argument, if the hint is pendulum.DateTime
            # but the value is a stdlib datetime, convert it
            for param_name, value in bound.arguments.items():
                hint = hints.get(param_name)
                if (
                    hint is pend.DateTime
                    and isinstance(value, datetime.datetime)
                    and not isinstance(value, pend.DateTime)
                ):
                    bound.arguments[param_name] = pend.instance(value)

            # call the original, with converted values
            return await func(*bound.args, **bound.kwargs)

        nonlocal name, group
        if group:
            registered_functions[group] = (None, None, None, None, None, True)

        registered_functions[name] = (
            wrapper,
            user_only,
            no_return,
            is_modal,
            ephemeral,
            group,
        )

        return wrapper

    return decorator


def build_ctx(
    interaction: hikari.ComponentInteraction | hikari.ModalInteraction,
    client: lightbulb.Client,
    is_modal=False,
):
    if not is_modal:
        return lightbulb.components.MenuContext(client, None, interaction, None, None, None, asyncio.Event())
    else:
        return lightbulb.components.ModalContext(client, None, interaction, asyncio.Event())


@lightbulb.di.with_di
async def component_handler(
    ctx: lightbulb.components.MenuContext | lightbulb.components.ModalContext,
    mongo: MongoClient = lightbulb.di.INJECTED,
):
    command_name, action_id = ctx.interaction.custom_id.split(':')
    (
        function,
        owner_only,
        no_return,
        is_modal,
        ephemeral,
        group,
    ) = registered_functions.get(command_name)

    if group:
        if not ctx.interaction.values:
            return
        (
            function,
            owner_only,
            no_return,
            is_modal,
            ephemeral,
            group,
        ) = registered_functions.get(ctx.interaction.values[0])

    if not is_modal:
        await ctx.defer(edit=True)

    kw = await mongo.button_store.find_one({'_id': action_id}, {'_id': 0})
    kw = kw or {} | {'color': RED_ACCENT, 'action_id': action_id, 'ctx': ctx}
    if not kw:
        return
    components = await function(**kw)

    if not no_return:
        await ctx.respond(components=components, edit=True, ephemeral=ephemeral)


@loader.listener(hikari.events.ComponentInteractionCreateEvent)
async def component_interaction(
    event: ComponentInteractionCreateEvent,
    client: lightbulb.Client = lightbulb.di.INJECTED,
):
    ctx = build_ctx(event.interaction, client)
    await component_handler(ctx=ctx)


@loader.listener(hikari.events.ModalInteractionCreateEvent)
async def modal_interaction(
    event: hikari.events.ModalInteractionCreateEvent,
    client: lightbulb.Client = lightbulb.di.INJECTED,
):
    ctx = build_ctx(event.interaction, client, True)
    await component_handler(ctx=ctx)
