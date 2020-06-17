#!/usr/bin/env python

import sys
from datetime import datetime
from typing import Optional

import click
import dateparser
import sqlalchemy as sql
from termcolor import colored

from bojo.config import should_use_verbose
from bojo.db import (
    get_session,
    Item,
    ItemState,
    ItemStateDict,
    ItemSignifier,
    ItemSignifierDict,
)

NONE_STR = 'none'

if should_use_verbose():
    STATE_OPTS = ', '.join([f'[{k}] {v.value}' for k, v in ItemStateDict.items()])
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


@cli.command(help='Provides information about annotation')
def info() -> None:
    click.echo(Item.info())


@cli.command(help='Lists relevant items')
@click.argument('num-items', type=int, default=5)
def list(num_items: int) -> None:
    session = get_session()

    def _title(s: str) -> None:
        click.echo(colored(s, attrs=['underline']) + ':')

    # Shows the last N items.
    items = session.query(Item) \
        .order_by(Item.time_updated.desc()) \
        .limit(num_items)
    if items.count():
        _title(f'Last {items.count()} updated item(s)')
        for item in items:
            click.echo(item)

    # Lists upcoming items.
    items = session.query(Item) \
        .filter(Item.time > datetime.now()) \
        .filter(Item.state == ItemState.EVENT) \
        .order_by(Item.time) \
        .limit(num_items)
    if items.count():
        _title(f'\nUpcoming {items.count()} event(s)')
        for item in items:
            click.echo(item)

    # Lists priority items.
    items = session.query(Item) \
        .filter(Item.signifier == ItemSignifier.PRIORITY) \
        .order_by(Item.time)
    if items.count():
        _title(f'\nPriority item(s)')
        for item in items:
            click.echo(item)


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


@cli.group()
def mark():
    """Update item states."""

    pass


def _mark(id: int, state: ItemState) -> None:
    session = get_session()
    item = session.query(Item).get(id)
    if item is None:
        raise RuntimeError(f'Item {id} not found')

    item.state = state
    session.commit()
    click.echo(item)
    click.echo(f'Marked item {id} as {state.value}')


@mark.command(help='Mark an item as complete')
@click.argument('id', type=int)
def complete(id: int) -> None:
    _mark(id, ItemState.COMPLETE)


@mark.command(help='Mark an item as incomplete')
@click.argument('id', type=int)
def incomplete(id: int) -> None:
    _mark(id, ItemState.INCOMPLETE)


@mark.command(help='Mark an item as migrated')
@click.argument('id', type=int)
def migrate(id: int) -> None:
    _mark(id, ItemState.MIGRATED)


@mark.command(help='Mark an item as scheduled')
@click.argument('id', type=int)
def schedule(id: int) -> None:
    _mark(id, ItemState.SCHEDULED)


@mark.command(help='Mark an item as irrelevant')
@click.argument('id', type=int)
def irrelevant(id: int) -> None:
    _mark(id, ItemState.IRRELEVANT)


@mark.command(help='Mark an item as a note')
@click.argument('id', type=int)
def note(id: int) -> None:
    _mark(id, ItemState.NOTE)


@mark.command(help='Mark an item as an event')
@click.argument('id', type=int)
def event(id: int) -> None:
    _mark(id, ItemState.EVENT)


@cli.group()
def sig():
    """Changes the significance of items."""

    pass


def _sig(id: int, sig: Optional[ItemSignifier]) -> None:
    session = get_session()
    item = session.query(Item).get(id)
    if item is None:
        raise RuntimeError(f'Item {id} not found')

    item.signifier = sig
    session.commit()
    click.echo(item)
    click.echo(f'Marked item {id} as {sig.value}')


@sig.command(help='Signify an item as priority')
@click.argument('id', type=int)
def pri(id: int) -> None:
    _sig(id, ItemSignifier.PRIORITY)


@sig.command(help='Signify an item as inspirational')
@click.argument('id', type=int)
def insp(id: int) -> None:
    _sig(id, ItemSignifier.INSPIRATION)


@sig.command(help='Remove signifier from an item')
@click.argument('id', type=int)
def off(id: int) -> None:
    _sig(id, None)


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

    # Parses the state.
    state = state.strip().replace('\n', ' ')
    if state not in ItemStateDict:
        opts = ''.join([f'\n  {k}: {v}' for k, v in ItemStateDict.items()])
        raise RuntimeError(f'Invalid state {state}. Options are:{opts}')
    else:
        state = ItemStateDict[state]

    # Parses the signifier.
    signifier = signifier.strip().replace('\n', ' ')
    if signifier != NONE_STR:
        if signifier not in ItemSignifierDict:
            opts = ''.join(
                [f'\n  {k}: {v}' for k, v in ItemSignifierDict.items()])
            raise RuntimeError(
                f'Invalid signifier {signifier}. Options are:{opts}')
        else:
            signifier = ItemSignifierDict[signifier]
    else:
        signifier = None

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
