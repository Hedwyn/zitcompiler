"""
CLI frontend for zitcompiler.

@author: Baptiste Pestourie
@date: 28.05.2026
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import click

from ._compiler import BuildLibOptions, zig_build_lib


@click.group()
def zit() -> None:
    logging.basicConfig(level=logging.INFO)


@zit.command
@click.argument("module_path", type=Path)
def build_lib(*, module_path: Path) -> None:
    asyncio.run(zig_build_lib(BuildLibOptions(module_path=module_path)))
    click.echo("Library built !")
