from __future__ import annotations
from typing import Any, Callable

from setuptools.command.sdist import sdist
import setuptools


class compile_npe2(sdist):
    def run(self) -> None:
        breakpoint()
        return super().run()


def npe2_compile(
    dist: setuptools.Distribution,
) -> None:
    print(locals())
    breakpoint()
