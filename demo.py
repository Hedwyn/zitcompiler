"""
Tiny demo for this project.
"""

from pathlib import Path

from zitcompiler import zit_compiled
from zitcompiler._compiler import zig_build_lib

examples_folder = Path("examples")

say_hello = zit_compiled(examples_folder / "hello_world_ext_no_mod.zig", "hello_world")
say_hello()

GreeterType = zit_compiled(examples_folder / "greeter_ext.zig", "GreeterType", "class")

greeter = GreeterType()
greeter.hello_world()
