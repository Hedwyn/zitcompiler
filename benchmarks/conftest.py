"""
Common fixtures and glue code for benchmarks.

@date: 08.06.2025
@author: Baptiste Pestourie
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING, TypedDict, Unpack

import pytest
from rich.console import Console
from rich.table import Table
from rich.text import Text

from zitcompiler.zetaclasses import zetaclass

if TYPE_CHECKING:
    from collections.abc import Generator


class _BenchKwargs(TypedDict, total=False):
    init: bool
    repr: bool
    eq: bool
    order: bool
    unsafe_hash: bool
    frozen: bool
    match_args: bool
    kw_only: bool
    slots: bool
    weakref_slot: bool


_benchmark_results: dict[str, dict[str, float]] = {}


@pytest.fixture(autouse=True)
def _collect_result(benchmark: object, request: pytest.FixtureRequest) -> Generator[None]:
    yield
    stats = getattr(benchmark, "stats", None)
    if stats is None:
        return
    mean: float = stats["mean"] * 1e6
    name: str = request.node.name
    bracket = name.find("[")
    if bracket == -1:
        return
    category = name[:bracket]
    impl = name[bracket + 1 : -1]
    _benchmark_results.setdefault(category, {})[impl] = mean


_VARIANTS = ["zetaclass", "zetaclass[validate]", "zetaclass[packed]"]


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter,
) -> None:
    if not _benchmark_results:
        return

    table = Table(title="relative performance (dataclass = 1.00x)", show_lines=False)
    table.add_column("category", style="bold")
    table.add_column("dataclass (µs)", justify="right")
    for v in _VARIANTS:
        table.add_column(f"{v} (µs)".replace("[", r"\["), justify="right")
        table.add_column("rel", justify="right")

    for category in sorted(_benchmark_results):
        impls = _benchmark_results[category]
        dc = impls.get("dataclass")
        dc_str = f"{dc:.1f}" if dc is not None else "N/A"
        row: list[str | Text] = [category, dc_str]
        for v in _VARIANTS:
            val = impls.get(v)
            val_str = f"{val:.1f}" if val is not None else "N/A"
            row.append(val_str)
            if dc is not None and val is not None:
                ratio = val / dc
                color = "green" if ratio < 1.0 else "red"
                row.append(Text(f"{ratio:.2f}x", style=color))
            else:
                row.append("N/A")
        table.add_row(*row)

    buf = StringIO()
    Console(file=buf, highlight=False, force_terminal=True).print(table)
    terminalreporter.write_sep("-", "benchmark summary")
    terminalreporter._tw.line(buf.getvalue())


def bench(base_cls: type, **kwargs: Unpack[_BenchKwargs]) -> pytest.MarkDecorator:
    def _fresh() -> type:
        annotations: dict[str, object] = dict(getattr(base_cls, "__annotations__", {}))
        return type(base_cls.__name__, base_cls.__bases__, {"__annotations__": annotations})

    dc_decorator = dataclass(
        init=kwargs.get("init", True),
        repr=kwargs.get("repr", True),
        eq=kwargs.get("eq", True),
        order=kwargs.get("order", False),
        unsafe_hash=kwargs.get("unsafe_hash", False),
        frozen=kwargs.get("frozen", False),
        match_args=kwargs.get("match_args", True),
        kw_only=kwargs.get("kw_only", False),
        slots=kwargs.get("slots", False),
        weakref_slot=kwargs.get("weakref_slot", False),
    )

    params = [
        pytest.param(dc_decorator(_fresh()), id="dataclass"),
        pytest.param(zetaclass(_fresh(), **kwargs), id="zetaclass"),
        pytest.param(zetaclass(_fresh(), **kwargs, validate=True), id="zetaclass[validate]"),
        pytest.param(zetaclass(_fresh(), **kwargs, packed=True), id="zetaclass[packed]"),
    ]

    return pytest.mark.parametrize("cls", params)
