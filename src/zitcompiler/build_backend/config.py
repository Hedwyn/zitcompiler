"""
Config schema and loader for the zitcompiler hatchling build hook.

@date: 11.06.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

from typing import TypedDict


class HatchConfig(TypedDict):
    module: str | None
    debug: bool


def load_config(data: dict[str, object]) -> HatchConfig:
    module = data.get("module")
    debug = data.get("debug", False)

    if module is not None and not isinstance(module, str):
        raise TypeError(f"zitcompiler: 'module' must be a string, got {type(module).__name__!r}")
    if not isinstance(debug, bool):
        raise TypeError(f"zitcompiler: 'debug' must be a bool, got {type(debug).__name__!r}")

    return {"module": module, "debug": debug}
