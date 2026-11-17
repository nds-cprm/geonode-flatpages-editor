#!/usr/bin/env python
"""Roda os testes do app: python runtests.py [opções do "manage.py test"] [rótulos]"""
import os
import sys

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
    args = sys.argv[1:]
    if not any(not a.startswith("-") for a in args):
        args.append("tests")
    execute_from_command_line([sys.argv[0], "test", *args])
