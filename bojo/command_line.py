#!/usr/bin/env python

import sys
from datetime import datetime
from typing import List, Optional

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


def _title(s: str) -> None:
    click.echo(colored(s, attrs=['underline']) + ':')


def _render_items(items: List[Item], title: str, empty_str: Optional[str]) -> None:
    num_items = items.count()
    if num_items:
        _title(title)
        for item in items:
            click.echo(item)
    else:
        if empty_str is not None:
            click.echo(empty_str)


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
        if signifier in ItemSignifierDict:
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


@click.group()
def cli():
    """A command-line bullet journal."""

    pass


@cli.command(help='Provides information about annotation')
def info() -> None:
    click.echo(Item.info())


@cli.command(help='Lists relevant items')
@click.option('-n', '--num-items', type=int, default=5)
@click.option('-s', '--state', multiple=True)
@click.option('-g', '--signifier', multiple=True)
def list(num_items: int, state: List[str], signifier: List[str]) -> None:
    session = get_session()

    # Parses state and signifier queries.
    if state:
        state = [_parse_state(s) for s in state]
    else:
        state = [s for s in ItemState]
    filt = Item.state.in_(state)

    if signifier:
        signifier = [_parse_signifier(s) for s in signifier]
        signifier_query = Item.signifier.in_(
            [s for s in signifier if s is not None])
        if any(s is None for s in signifier):
            signifier_query = sql.or_(
                Item.signifier.is_(None), signifier_query)
        filt = sql.or_(filt, signifier_query)

    # Shows the last N items.
    items = session.query(Item) \
        .order_by(Item.id.desc()) \
        .filter(filt) \
        .limit(num_items)
    if items.count():
        _title(f'Last {items.count()} updated item(s)')
        for item in items:
            click.echo(item.render(show_children=False))

    # Lists upcoming items.
    items = session.query(Item) \
        .filter(sql.and_(filt, Item.time > datetime.now())) \
        .order_by(Item.time) \
        .limit(num_items)
    if items.count():
        _title(f'\nUpcoming {items.count()} event(s)')
        for item in items:
            click.echo(item.render())

    # Lists priority items.
    items = session.query(Item) \
        .filter(sql.and_(filt, Item.signifier == ItemSignifier.PRIORITY)) \
        .order_by(Item.time)
    if items.count():
        _title(f'\nPriority item(s)')
        for item in items:
            click.echo(item.render(show_complete_children=False))


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


@cli.command(help='Mark past items as complete')
@click.option('-l', '--list', is_flag=True, help='If set, list completed items instead')
def complete(list: bool) -> None:
    session = get_session()

    if list:
        items = session.query(Item) \
            .filter(Item.state == ItemState.COMPLETE) \
            .order_by(Item.time_updated.desc())
        _render_items(items, 'Completed Items', 'All past items are completed')
    else:
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
    _render_items(items, 'Matching Items', 'No matching items found')


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
