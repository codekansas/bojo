#!/usr/bin/env python

import pathlib

import click

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
    ALL_CHOICES,
    NONE_STR,
)


@click.command('serve', help='Serves bullet journal through Flask')
@click.option('-p', '--port', type=int, default=8000)
def serve_command(port: int) -> None:
    from flask import Flask, render_template

    cur_folder = str(pathlib.Path(__file__).parent.absolute())
    app = Flask(__name__, template_folder=cur_folder)

    @app.route('/favicon.ico')
    def favicon() -> str:
        return ''

    @app.route('/')
    @app.route('/<state>')
    def index(state: str = NONE_STR) -> str:
        session = get_session()
        items = session.query(Item).order_by(Item.id.desc())
        state = parse_choice(state)
        if isinstance(state, ItemState):
            items = items.filter(Item.state == state)
            strs = (f'All {state.value.capitalize()}',
                    f'No {state.value.capitalize()}')
        elif isinstance(state, ItemSignifier):
            items = items.filter(Item.signifier == state)
            strs = (f'All {state.value.capitalize()}',
                    f'No {state.value.capitalize()}')
        else:
            strs = ('All Items', 'No Items')
        title = strs[0] if items.count() else strs[1]
        links = [l for l in ALL_CHOICES if len(l) > 3]
        session.close()

        return render_template('index.html', items=items, title=title, links=links)

    app.run(port=port)
