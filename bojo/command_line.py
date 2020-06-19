#!/usr/bin/env python

import json
import sys
from datetime import datetime
from typing import List, Optional

import click
import dateparser
import sqlalchemy as sql

from bojo.config import should_use_verbose
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
    parse_state,
    parse_signifier,
    render_items,
    render_title,
    NONE_STR,
)
from bojo.subcommands.list import list_command

if should_use_verbose():
    STATE_OPTS = ', '.join(
        [f'[{k}] {v.value}' for k, v in ItemStateDict.items()])
    SIGNIFIER_OPTS = ', '.join(
        [f'[{k}] {v.value}' for k, v in ItemSignifierDict.items()])

    STATE_PROMPT = f'State ({STATE_OPTS})'
    SIGNIFIER_PROMPT = f'Signifier ({SIGNIFIER_OPTS})'
else:
    STATE_PROMPT = 'State'
    SIGNIFIER_PROMPT = 'Signifier'


@click.group()
def cli():
    """A command-line bullet journal."""

    pass


cli.add_command(list_command)


@cli.command(help='Provides information about annotation')
def info() -> None:
    click.echo(Item.info())


@cli.command(help='Delete an item forever')
@click.argument('id', type=int)
def delete(id: int) -> None:
    session = get_session()
    item = session.query(Item).get(id)
    if item is None:
        raise RuntimeError(f'Item {id} not found')
    click.echo(item)

    if click.confirm('Do you want to delete this item?', abort=True):
        session.delete(item)
        session.commit()
        click.echo('Deleted item')


@cli.command(help='Update item state')
@click.argument('state', type=str)
@click.argument('id', type=int)
def mark(state: str, id: int) -> None:
    session = get_session()
    item = session.query(Item).get(id)
    if item is None:
        raise RuntimeError(f'Item {id} not found')

    state = parse_choice(state)
    if isinstance(state, ItemState):
        item.state = state
        ostr = f'Marked item {id} as {state.value}'
    elif isinstance(state, ItemSignifier):
        item.signifier = state
        ostr = f'Marked item {id} as {state.value}'
    else:
        item.signifier = None
        ostr = f'Cleared signifier for item {id}'
    session.commit()
    click.echo(item)
    click.echo(ostr)


@cli.command(help='Mark past items as complete')
def complete() -> None:
    session = get_session()

    items = session.query(Item) \
        .filter(Item.time < datetime.now()) \
        .filter(Item.state != ItemState.COMPLETE)
    num_items = items.count()
    if num_items:
        if click.confirm(f'Mark {num_items} items as complete?', abort=True):
            items.update({'state': ItemState.COMPLETE})
            session.commit()
            click.echo(f'Completed {num_items} items')
    else:
        click.echo('All past items are complete')


@cli.command(help='Run a text query on all items')
@click.argument('substring')
@click.option('-s', '--show-complete', is_flag=True, help='If set, show completed items')
def query(substring: str, show_complete: bool) -> None:
    session = get_session()
    query = session.query(Item).filter(Item.description.contains(substring))
    if not show_complete:
        query = query.filter(Item.state != ItemState.COMPLETE)
    items = query.order_by(Item.time_updated.desc())
    render_items(items, 'Matching Items', 'No matching items found')


@cli.command('export', help='Exports events to JSON')
@click.argument('file', default='-')
def export_func(file: str) -> None:
    session = get_session()
    all_items = [item.as_dict() for item in session.query(Item)]
    with click.open_file(file, 'w') as f:
        json.dump(all_items, f, indent=2)


@cli.command('import', help='Imports events from JSON')
@click.argument('file', default='-')
def import_func(file: str) -> None:
    session = get_session()
    click.get_text_stream('stdin')
    all_items = []
    with click.open_file(file, 'r') as f:
        for item_str in json.load(f):
            all_items.append(Item.from_dict(item_str))
    session = get_session()
    session.add_all(all_items)
    session.commit()
    click.echo(f'Added {len(all_items)} items')


@cli.command(help='Adds a new item')
@click.option('-d', '--description', prompt=f'Description',
              help='The description of the item being added')
@click.option('-s', '--state', prompt=STATE_PROMPT,
              help='The state of the item being added')
@click.option('--signifier', prompt=SIGNIFIER_PROMPT,
              default=NONE_STR, help='The signifier of the item being added')
@click.option('-p', '--parent', prompt='Parent', default=NONE_STR,
              help='The parent ID of the item being added')
@click.option('-t', '--time', prompt='Time', default=NONE_STR,
              help='The time of the item being added')
def add(description: str, state: str, signifier: str, parent: str, time: str) -> None:
    # Parses the parent.
    if parent != NONE_STR:
        parent = int(parent)

    state = parse_state(state)
    signifier = parse_signifier(signifier)

    # Parses the time.
    if time != NONE_STR:
        time = dateparser.parse(time)
    else:
        time = None

    # Creates the item to insert.
    item = Item(description=description, state=state,
                signifier=signifier, time=time, parent_id=parent)

    click.echo(item)
    if click.confirm('Do you want to add this item?', abort=True):
        session = get_session()
        session.add(item)
        session.commit()
        click.echo('Added item')
