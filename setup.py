#!/usr/bin/env python

from setuptools import setup

setup(name='BoJo',
      version='1.0',
      description='Command-line tool for bullet journaling',
      author='Benjamin Bolte',
      author_email='ben@bolte.cc',
      url='https://www.github.com/codekansas/bojo',
      entry_points={
          'console_scripts': ['bojo=bojo.command_line:cli'],
      },
      install_requires=[
          'click',
          'dateparser',
          'sqlalchemy',
          'termcolor',
      ])
