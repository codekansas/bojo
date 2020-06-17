#!/usr/bin/env python

from setuptools import find_packages, setup

with open('README.md') as f:
    readme = f.read()

setup(name='BoJo',
      version='0.1',
      description='Command-line tool for bullet journaling',
      long_description=readme,
      long_description_content_type='text/markdown',
      setup_requires=['setuptools>=18.0'],
      author='Benjamin Bolte',
      author_email='ben@bolte.cc',
      packages=find_packages(),
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
