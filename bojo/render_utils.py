#!/usr/bin/env python

from typing import List, Optional, Union

import click
from termcolor import colored

from bojo.db import (
    get_session,
    Item,
    ItemState,
    ItemStateDict,
    ItemSignifier,
    ItemSignifierDict,
)

NONE_STR = 'none'
ALL_STR = 'all'

ALL_CHOICES = [s for s in ItemStateDict.keys()] + \
              [s for s in ItemSignifierDict.keys()] + \
              [s.value for s in ItemState] + \
              [s.value for s in ItemSignifier] + \
              [NONE_STR]


def render_title(s: str) -> None:
    click.echo(colored(s, attrs=['underline']) + ':')


def render_items(items: List[Item], title: str, empty_str: Optional[str], **kwargs) -> None:
    num_items = items.count()
    if num_items:
        render_title(title)
        for item in items:
            click.echo(item.render(**kwargs))
    else:
        if empty_str is not None:
            click.echo(empty_str)


def parse_state(state: str) -> ItemState:
    state = state.strip().lower().replace('\n', ' ')
    if state in ItemStateDict:
        return ItemStateDict[state]
    elif state in {v.value for v in ItemStateDict.values()}:
        return ItemState(state)
    else:
        opts = ''.join([f'\n  {k}: {v.value}' for k,
                        v in ItemStateDict.items()])
        raise RuntimeError(f'Invalid state {state}. Options are:{opts}')


def parse_signifier(signifier: str) -> Optional[ItemSignifier]:
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


def parse_choice(s: str) -> Optional[Union[ItemState, ItemSignifier]]:
    if s == NONE_STR or s == ALL_STR:
        return None
    if s in ItemStateDict:
        return ItemStateDict[s]
    if s in ItemSignifierDict:
        return ItemSignifierDict[s]

    # Checks if it is a direct string match.
    try:
        return ItemState(s)
    except ValueError:
        pass
    try:
        return ItemSignifier(s)
    except ValueError:
        pass

    # Checks substring match.
    if len(s) >= 3:
        for t in ItemState:
            if t.value.startswith(s):
                return t
        for t in ItemSignifier:
            if t.value.startswith(s):
                return t

    opts = ', '.join(ALL_CHOICES)
    raise ValueError(f'Invalid choice: {s}. Options are {opts}')
