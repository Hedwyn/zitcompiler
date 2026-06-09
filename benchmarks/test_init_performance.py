"""
Benchmarks for initialization performance.

@date: 08.06.2025
@author: Baptiste Pestourie
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from benchmarks.conftest import bench

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


class _Point:
    x: int
    y: int
    z: int


@bench(_Point)
def test_init_positional(
    benchmark: BenchmarkFixture,
    cls: type,
) -> None:
    def init_loop() -> None:
        for i in range(100):
            cls(i, i + 1, i + 2)

    benchmark(init_loop)


@bench(_Point, kw_only=True)
def test_init_kw_only(
    benchmark: BenchmarkFixture,
    cls: type,
) -> None:
    def init_loop() -> None:
        for i in range(100):
            cls(x=i, y=i + 1, z=i + 2)

    benchmark(init_loop)
