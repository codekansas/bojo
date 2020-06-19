#!/usr/bin/env python

import os
from pathlib import Path


def get_bojo_root() -> Path:
    """Returns the root directory for logging data."""

    root_dir = Path.home() / '.bojo'

    # Can set this environment variable to override.
    if 'BOJO_ROOT' in os.environ:
        root_dir = Path(os.environ['BOJO_ROOT'])
    
    # Makes environment if it doesn't exist yet.
    if not os.path.exists(root_dir):
        os.makedirs(root_dir, mode=0o700, exist_ok=True)
    
    return root_dir


def should_use_verbose() -> bool:
    return 'BOJO_VERBOSE' in os.environ
