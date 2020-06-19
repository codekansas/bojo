#!/usr/bin/env python

from typing import Optional

import click
import sqlalchemy as sql
from datetime import datetime

from bojo.db import (
    get_session,
    Item,
    ItemState,
    ItemStateDict,
    ItemSignifier,
    ItemSignifierDict,
)
from bojo.render_utils import (
    parse_choice,
    render_items,
    NONE_STR,
)


@click.group('list', invoke_without_command=True)
@click.option('-n', '--num-items', envvar='BOJO_NUM_ITEMS',
              type=int, default=10, prompt='Number of items')
@click.pass_context
def list_command(ctx, num_items: int) -> None:
    """Lists items in the bullet journal."""

    ctx.ensure_object(dict)
    ctx.obj['NUM_ITEMS'] = num_items

    if ctx.invoked_subcommand is None:
        ctx.invoke(pri)


@list_command.command(help='Show all items, orderd by ID')
@click.argument('state', type=str, default=NONE_STR)
@click.pass_context
def all(ctx, state: str) -> None:
    session = get_session()
    num_items = ctx.obj['NUM_ITEMS']

    items = session.query(Item).order_by(Item.id.desc())
    state = parse_choice(state)
    if isinstance(state, ItemState):
        items = items.filter(Item.state == state)
        strs = (f'All {state.value}', f'No {state.value}')
    elif isinstance(state, ItemSignifier):
        items = items.filter(Item.signifier == state)
        strs = (f'All {state.value}', f'No {state.value}')
    else:
        strs = ('All items', 'No items')
    items = items.limit(num_items)

    render_items(items, *strs, show_children=False)


@list_command.command(help='Show upcoming items')
@click.argument('state', type=str, default=ItemState.EVENT.value)
@click.pass_context
def upcoming(ctx, state: str) -> None:
    session = get_session()
    num_items = ctx.obj['NUM_ITEMS']

    items = session.query(Item).filter(Item.time > datetime.now())
    state = parse_choice(state)
    if isinstance(state, ItemState):
        items = items.filter(Item.state == state)
        strs = (f'Upcoming {state.value}', f'No upcoming {state.value}')
    elif isinstance(state, ItemSignifier):
        items = items.filter(Item.signifier == state)
        strs = (f'Upcoming {state.value}', f'No upcoming {state.value}')
    else:
        strs = ('Upcoming items', 'No upcoming items')
    items = items.order_by(Item.time).limit(num_items)

    render_items(items, *strs)


@list_command.command(help='Show priority items')
@click.pass_context
def pri(ctx) -> None:
    session = get_session()
    num_items = ctx.obj['NUM_ITEMS']

    items = session.query(Item) \
        .filter(Item.signifier == ItemSignifier.PRIORITY) \
        .order_by(Item.time) \
        .limit(num_items)
    render_items(items, 'Priority items', 'No priority items',
                 show_complete_children=False)


@list_command.command(help='Show completed items')
@click.pass_context
def complete(ctx) -> None:
    session = get_session()
    num_items = ctx.obj['NUM_ITEMS']

    items = session.query(Item) \
        .filter(Item.state == ItemState.COMPLETE) \
        .order_by(Item.time_updated.desc()) \
        .limit(num_items)
    render_items(items, 'Completed Items', 'All past items are completed')
