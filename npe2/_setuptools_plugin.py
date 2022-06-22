from __future__ import annotations
from typing import Any, Callable

from setuptools.command.sdist import sdist
from setuptools import Command, Distribution
print("IMPORT")

class compile_npe2(sdist):
    def run(self) -> None:
        breakpoint()
        return super().run()

def npe2_keyword(
    dist: Distribution,
    keyword: str,
    value: bool | dict[str, Any] | Callable[[], dict[str, Any]],
) -> None:
    print(locals())
    breakpoint()