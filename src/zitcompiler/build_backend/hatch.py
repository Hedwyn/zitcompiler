"""
Build hook hatchling backend.

@date: 09.08.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import importlib
import sys
from functools import cached_property
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

from zitcompiler import get_all_compiled_symbols

from .config import HatchConfig, load_config


def log(message: str) -> None:
    print(message, file=sys.stderr)  # noqa: T201


class HatchlingBuildHook(BuildHookInterface):
    PLUGIN_NAME = "zitcompiler"

    @cached_property
    def _config(self) -> HatchConfig:
        return load_config(self.config)

    @cached_property
    def is_debug(self) -> bool:
        if not self._config["debug"]:
            return False
        log("zitcompiler: debug mode enabled")
        return True

    def debug_log(self, message: str) -> None:
        if not self.is_debug:
            return
        log(message)

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        if self.target_name != "wheel":
            return

        module_name = self._config["module"]
        if not module_name:
            return

        root = Path(self.root)
        src_dir = root / "src"
        path_entry = str(src_dir) if src_dir.is_dir() else str(root)
        sys.path.insert(0, path_entry)

        importlib.import_module(module_name)

        missing: list[str] = []
        symbols = get_all_compiled_symbols()
        for record in symbols:
            self.debug_log(
                f"zitcompiler: collected {record.module_path} -> {record.symbol_names} @ {record.output_path}",
            )
            if not record.output_path.exists():
                missing.append(str(record.output_path))

        if missing:
            paths = ", ".join(missing)
            raise RuntimeError(f"zitcompiler: compilation failed, missing artifacts: {paths}")

        artifacts = build_data.get("artifacts")
        if not isinstance(artifacts, list):
            artifacts = []
            build_data["artifacts"] = artifacts
        for record in symbols:
            try:
                rel_path = str(record.output_path.relative_to(root))
            except ValueError:
                rel_path = str(record.output_path)
            artifacts.append(rel_path)


@hookimpl
def hatch_register_build_hook() -> type[BuildHookInterface]:
    """
    Registers Smelt's build hook as a hatch plugin
    """
    return HatchlingBuildHook
