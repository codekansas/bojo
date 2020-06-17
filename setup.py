#!/usr/bin/env python
"""Instructions for uploading to pypi:

1) python setup.py sdist bdist_wheel
2) python -m twine upload dist/*
"""

from setuptools import find_packages, setup

with open('README.md') as f:
    readme = f.read()

setup(name='BoJo',
      version='0.1.1',
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
