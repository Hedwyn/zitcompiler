"""
Demonstrates zetaify: compile a native class directly from a JSON schema.
"""

from __future__ import annotations

import json
from pathlib import Path

from zitcompiler.jsonschemas import zetaify

schema = json.loads((Path(__file__).parent / "person.json").read_text())

Person = zetaify(schema, stub_path=Path(__file__).parent / "person.pyi")

# Optional fields (height, active) are not included in the native struct —
# zetaclass only supports concrete types (int, float, str); None-unions are dropped.
alice = Person(name="Alice", age=30)
bob = Person(name="Bob", age=25)

print(alice)
print(bob)
print(f"Equal: {alice == bob}")
