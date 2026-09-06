#!/usr/bin/env python3
"""Start executable entry to the mycallyplus GUI (no python -m required)."""

import importlib 
import os 
import sys 
from pathlib import Path 


def main ()->int :
    repo_root =Path (__file__ ).resolve ().parent 
    sys .path .insert (0 ,str (repo_root .parent ))
    package =importlib .import_module (repo_root .name )
    return package .main (["gui"])


if __name__ =="__main__":
    sys .exit (main ())
