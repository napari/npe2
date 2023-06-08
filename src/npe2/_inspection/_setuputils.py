import ast
from configparser import ConfigParser
from dataclasses import dataclass, field
from functools import cached_property
from importlib.metadata import EntryPoint
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

NPE1_EP = "napari.plugin"
NPE2_EP = "napari.manifest"


@dataclass
class PackageInfo:
    src_root: Optional[Path] = None
    package_name: str = ""
    entry_points: List[EntryPoint] = field(default_factory=list)
    setup_cfg: Optional[Path] = None
    setup_py: Optional[Path] = None
    pyproject_toml: Optional[Path] = None

    # @property
    # def packages(self) -> Optional[List[Path]]:
    #     return Path(self.top_module)

    @cached_property
    def _ep1(self) -> Optional[EntryPoint]:
        return next((ep for ep in self.entry_points if ep.group == NPE1_EP), None)

    @cached_property
    def _ep2(self) -> Optional[EntryPoint]:
        return next((ep for ep in self.entry_points if ep.group == NPE2_EP), None)

    @property
    def ep_name(self):
        if ep := self._ep1:
            return ep.name

    @property
    def ep_value(self):
        if ep := self._ep1:
            return ep.value

    @property
    def top_module(self) -> str:
        if ep := (self._ep1 or self._ep2):
            return ep.value.split(".", 1)[0].split(":", 1)[0]
        return ""  # pragma: no cover


def get_package_dir_info(path: Union[Path, str]) -> PackageInfo:
    """Attempt to *statically* get plugin info from a package directory."""
    path = Path(path).resolve()
    if not path.is_dir():  # pragma: no cover
        raise ValueError(f"Provided path is not a directory: {path}")

    info = PackageInfo(src_root=path)
    p = None

    # check for setup.cfg
    setup_cfg = path / "setup.cfg"
    if setup_cfg.exists():
        info.setup_cfg = setup_cfg
        p = ConfigParser()
        p.read(setup_cfg)
        info.package_name = p.get("metadata", "name", fallback="")
        if p.has_section("options.entry_points"):
            for group, val in p.items("options.entry_points"):
                name, _, value = val.partition("=")
                info.entry_points.append(EntryPoint(name.strip(), value.strip(), group))

    # check for setup.py
    setup_py = path / "setup.py"
    if setup_py.exists():
        info.setup_py = setup_py
        node = ast.parse(setup_py.read_text())
        visitor = _SetupVisitor()
        visitor.visit(node)
        if not info.package_name:
            info.package_name = visitor.get("name")
        if not info.entry_points:
            for group, vals in visitor.get("entry_points", {}).items():
                for val in vals if isinstance(vals, list) else [vals]:
                    name, _, value = val.partition("=")
                    info.entry_points.append(
                        EntryPoint(name.strip(), value.strip(), group)
                    )

    return info


class _SetupVisitor(ast.NodeVisitor):
    """Visitor to statically determine metadata from setup.py"""

    def __init__(self) -> None:
        super().__init__()
        self._names: Dict[str, Any] = {}
        self._setup_kwargs: Dict[str, Any] = {}

    def visit_Assign(self, node: ast.Assign) -> Any:
        if len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store):
                self._names[target.id] = self._get_val(node.value)

    def visit_Call(self, node: ast.Call) -> Any:
        if getattr(node.func, "id", "") == "setup":
            for k in node.keywords:
                key = k.arg
                value = self._get_val(k.value)
                self._setup_kwargs[str(key)] = value

    def _get_val(self, node: Optional[ast.expr]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return (
                self._names.get(node.id) if isinstance(node.ctx, ast.Load) else node.id
            )
        if isinstance(node, ast.Dict):
            keys = [self._get_val(k) for k in node.keys]
            values = [self._get_val(k) for k in node.values]
            return dict(zip(keys, values))
        if isinstance(node, ast.List):
            return [self._get_val(k) for k in node.elts]
        if isinstance(node, ast.Tuple):  # pragma: no cover
            return tuple(self._get_val(k) for k in node.elts)
        return str(node)  # pragma: no cover

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self._setup_kwargs.get(key, default)
