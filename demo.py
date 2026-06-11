"""
Tiny demo for this project.
"""

from dataclasses import dataclass
from pathlib import Path

from zitcompiler import ZigModuleDef, zitcompiled

examples_folder = Path("examples")

say_hello = zitcompiled(examples_folder / "hello_world_ext_no_mod.zig", "hello_world")
say_hello()


@dataclass
class TopLevel:
    _placeholder: int = 0


@dataclass
class Person:
    age: int
    height: int
    weight: int


person_instance = Person(age=30, height=180, weight=75)
person_module = ZigModuleDef(
    top_level=TopLevel,
    structs=[Person],
    module_name="person",
)

print("\n=== Person Module Demo ===", flush=True)
print_person_fields, format_person_values = zitcompiled(
    examples_folder / "person_printer.zig",
    ["print_person_fields", "format_person_values"],
    module_def=person_module,
)

print("\nStruct field information from Zig (via compile-time reflection):", flush=True)
print_person_fields()

print("\nFormatted person instance values:", flush=True)
format_person_values(person_instance.age, person_instance.height, person_instance.weight)
