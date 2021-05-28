#!/usr/bin/env python3

import os
import sys

realpath = os.path.realpath(__file__)
dir_realpath = os.path.dirname(os.path.dirname(realpath))
sys.path.append(dir_realpath)

from modelkit.cli import modelkit_cli  # NOQA

if __name__ == "__main__":
    modelkit_cli()
