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


def _parse_state(state: str) -> ItemState:
    state = state.strip().lower().replace('\n', ' ')
    if state in ItemStateDict:
        return ItemStateDict[state]
    elif state in {v.value for v in ItemStateDict.values()}:
        return ItemState(state)
    else:
        opts = ''.join([f'\n  {k}: {v.value}' for k,
                        v in ItemStateDict.items()])
        raise RuntimeError(f'Invalid state {state}. Options are:{opts}')


def _parse_signifier(signifier: str) -> Optional[ItemSignifier]:
    signifier = signifier.strip().lower().replace('\n', ' ')
    if signifier != NONE_STR:
        if signifier not in ItemSignifierDict:
            return ItemSignifierDict[signifier]
        elif signifier in {v.value for v in ItemSignifierDict.values()}:
            return ItemSignifier(signifier)
        else:
            opts = ''.join(
                [f'\n  {k}: {v.value}' for k, v in ItemSignifierDict.items()])
            raise RuntimeError(
                f'Invalid signifier {signifier}. Options are:{opts}')
    else:
        return None


@cli.command(help='Update item state')
@click.argument('state')
@click.argument('id', type=int)
def mark(state: str, id: int) -> None:
    state = _parse_state(state)

    session = get_session()
    item = session.query(Item).get(id)
    if item is None:
        raise RuntimeError(f'Item {id} not found')

    item.state = state
    session.commit()
    click.echo(item)
    click.echo(f'Marked item {id} as {state.value}')


@cli.command(help='Update item signifier')
@click.argument('signifier', default=NONE_STR)
@click.argument('id', type=int)
def sig(signifier: str, id: int) -> None:
    signifier = _parse_signifier(signifier)

    session = get_session()
    item = session.query(Item).get(id)
    if item is None:
        raise RuntimeError(f'Item {id} not found')

    item.signifier = signifier
    session.commit()
    click.echo(item)
    click.echo(f'Marked item {id} as {sig.value}')


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

    state = _parse_state(state)
    signifier = _parse_signifier(signifier)

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
