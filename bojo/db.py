#!/usr/bin/env python

import enum
from datetime import datetime

import sqlalchemy as sql
from sqlalchemy.ext.declarative import declarative_base
from termcolor import colored

from bojo.config import get_bojo_root, should_use_verbose


Base = declarative_base()


class ItemState(enum.Enum):
    INCOMPLETE = 'incomplete'
    COMPLETE = 'complete'
    MIGRATED = 'migrated'
    SCHEDULED = 'scheduled'
    IRRELEVANT = 'irrelevant'
    NOTE = 'note'
    EVENT = 'event'


ItemStates = [
    ('.', ItemState.INCOMPLETE, 'red'),
    ('x', ItemState.COMPLETE, 'green'),
    ('<', ItemState.MIGRATED, 'blue'),
    ('>', ItemState.SCHEDULED, 'cyan'),
    ('i', ItemState.IRRELEVANT, 'white'),
    ('-', ItemState.NOTE, 'magenta'),
    ('o', ItemState.EVENT, 'yellow'),
]
ItemStateColor = {x[1]: x[2] for x in ItemStates}
ItemStateDict = {x[0]: x[1] for x in ItemStates}
ItemStateDictInv = {v: k for k, v in ItemStateDict.items()}


class ItemSignifier(enum.Enum):
    PRIORITY = 'priority'
    INSPIRATION = 'inspiration'


ItemSignifierDict = {
    '*': ItemSignifier.PRIORITY,
    '!': ItemSignifier.INSPIRATION,
}
ItemSignifierDictInv = {v: k for k, v in ItemSignifierDict.items()}


class Item(Base):
    __tablename__ = 'item'

    id = sql.Column(sql.Integer, primary_key=True)
    description = sql.Column(sql.Text, nullable=False)
    state = sql.Column(sql.Enum(ItemState), nullable=False)
    signifier = sql.Column(sql.Enum(ItemSignifier))
    time = sql.Column(sql.DateTime)
    time_created = sql.Column(sql.DateTime, server_default=sql.sql.func.now())
    time_updated = sql.Column(sql.DateTime, onupdate=sql.sql.func.now())

    parent_id = sql.Column(sql.Integer, sql.ForeignKey('item.id'))
    children = sql.orm.relationship('Item',
                                    single_parent=True,
                                    cascade='all, delete-orphan',
                                    backref=sql.orm.backref('parent', remote_side=[id]))

    @staticmethod
    def info() -> str:
        strs = []

        # Adds state info.
        strs.append(colored('States', attrs=['underline']))
        for sym, state, color in ItemStates:
            strs.append(f'{sym} {colored(state.value, color)}')

        # Adds signifier info.
        strs.append('')
        strs.append(colored('Signifiers', attrs=['underline']))
        for sym, sig in ItemSignifierDict.items():
            v = sig.value
            if sig == ItemSignifier.PRIORITY:
                v = colored(v, attrs=['bold'])
            strs.append(f'{sym} {v}')

        # Adds snippit about verbose mode.
        strs.append('')
        strs.append(colored('Verbose Mode', attrs=['underline']))
        verbose_mode = should_use_verbose()
        env_var = colored('BOJO_VERBOSE', 'green')
        if verbose_mode:
            strs.append(f'Verbose mode is {colored("ENABLED", "green")}.')
            strs.append(
                f'Disable it by unsetting the {env_var} environment variable:')
            strs.append('  unset BOJO_VERBOSE')
        else:
            strs.append(f'Verbose mode is {colored("DISABLED", "red")}.')
            strs.append(
                f'Enable it by setting the {env_var} environment variable')
            strs.append('  export BOJO_VERBOSE=1')
        
        # Adds snippit about autocomplete.
        strs.append('')
        strs.append(colored('Autocomplete', attrs=['underline']))
        strs.append('To enable autocomplete, add the right setting to your shell:')
        strs.append('  eval "$(_BOJO_COMPLETE=source_bash bojo)"')
        strs.append('  eval "$(_BOJO_COMPLETE=source_zsh bojo)"')
        strs.append('  eval "$(_BOJO_COMPLETE=source_fish bojo)"')

        return '\n'.join(strs)

    def __format_time(self, t: datetime) -> str:
        return t.strftime('%A, %B %-d, %Y at %-I:%M %p')

    def __repr__(self) -> str:
        verbose_mode = should_use_verbose()

        color = ItemStateColor[self.state]
        rep = colored(self.description, color)

        state_symbol = ItemStateDictInv[self.state]
        if verbose_mode:
            state_symbol = f'{state_symbol} ({self.state.value})'
        rep = f'{state_symbol} {rep}'

        signifier_symbol = ItemSignifierDictInv.get(self.signifier, None)
        if signifier_symbol is not None:
            if verbose_mode:
                signifier_symbol = f'{signifier_symbol} ({self.signifier.value})'

            rep = f'{signifier_symbol} {rep}'

            if self.signifier == ItemSignifier.PRIORITY:
                rep = colored(rep, attrs=['bold'])

        if self.time is not None:
            t = self.__format_time(self.time)
            t = colored(t, attrs=['dark'])
            rep = f'{rep} {t}'

        if self.id is not None:
            sid = colored(self.id, attrs=['underline'])
            rep = f'{sid} {rep}'

        # Adds sub-representations.
        reps = [rep]
        for child in self.children:
            sub_rep = repr(child)
            reps.append('\n'.join(['  ' + c for c in sub_rep.split('\n')]))

        return '\n'.join(reps)


# Creates the SQLite database.
engine_url = f'sqlite:///{get_bojo_root() / "db.sqlite"}'
engine = sql.create_engine(engine_url)
Base.metadata.create_all(engine)


def get_session() -> sql.orm.Session:
    DBSession = sql.orm.sessionmaker(bind=engine)
    return DBSession()
