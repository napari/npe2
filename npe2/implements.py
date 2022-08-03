import contextlib
from inspect import Parameter, Signature
from pathlib import Path
from typing import Any, Callable, List, Sequence, Type, TypeVar, Union, cast

from pydantic import BaseModel

from ._inspection._visitors import find_npe2_module_contributions
from .manifest import PluginManifest, contributions

__all__ = [
    "compile",
    "on_activate",
    "on_deactivate",
    "reader",
    "sample_data_generator",
    "widget",
    "writer",
    "CHECK_ARGS_PARAM",
]


T = TypeVar("T", bound=Callable[..., Any])

CHECK_ARGS_PARAM = "ensure_args_valid"


def _build_decorator(contrib: Type[BaseModel]) -> Callable:
    """Create a decorator (e.g. `@implements.reader`) to mark an object as a contrib.

    Parameters
    ----------
    contrib : Type[BaseModel]
        The type of contribution this object implements.
    """
    # build a signature based on the fields in this contribution type, mixed with
    # the fields in the CommandContribution
    contribs: Sequence[Type[BaseModel]] = (contributions.CommandContribution, contrib)
    params: List[Parameter] = []
    for contrib in contribs:
        # iterate over the fields in the contribution types
        for field in contrib.__fields__.values():
            # we don't need python_name (since that will be gleaned from the function
            # we're decorating) ... and we don't need `command`, since that will just
            # be a string pointing to the contributions.commands entry that we are
            # creating here.
            if field.name not in {"python_name", "command"}:
                # ensure that required fields raise a TypeError if they are not provided
                default = Parameter.empty if field.required else field.get_default()
                # create the parameter and add it to the signature.
                param = Parameter(
                    field.name,
                    Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=field.outer_type_ or field.type_,
                )
                params.append(param)

    # add one more parameter to control whether the arguments in the decorator itself
    # are validated at runtime
    params.append(
        Parameter(
            CHECK_ARGS_PARAM,
            kind=Parameter.KEYWORD_ONLY,
            default=False,
            annotation=bool,
        )
    )

    signature = Signature(parameters=params, return_annotation=Callable[[T], T])

    # creates the actual `@npe2.implements.something` decorator
    # this just stores the parameters for the corresponding contribution type
    # as attributes on the function being decorated.
    def _deco(**kwargs) -> Callable[[T], T]:
        def _store_attrs(func: T) -> T:
            # If requested, assert that we've satisfied the signature when
            # the decorator is invoked at runtime.
            # TODO: improve error message to provide context
            if kwargs.pop(CHECK_ARGS_PARAM, False):
                signature.bind(**kwargs)

            # TODO: check if it's already there and assert the same id
            # store these attributes on the function
            with contextlib.suppress(AttributeError):
                setattr(func, f"_npe2_{contrib.__name__}", kwargs)

            # return the original decorated function
            return func

        return _store_attrs

    # set the signature and return the decorator
    setattr(_deco, "__signature__", signature)
    return _deco


# builds decorators for each of the contribution types that are essentially just
# pointers to some command.
reader = _build_decorator(contributions.ReaderContribution)
writer = _build_decorator(contributions.WriterContribution)
widget = _build_decorator(contributions.WidgetContribution)
sample_data_generator = _build_decorator(contributions.SampleDataGenerator)


def on_activate(func):
    """Mark a function to be called when a plugin is activated."""
    setattr(func, "npe2_on_activate", True)
    return func


def on_deactivate(func):
    """Mark a function to be called when a plugin is deactivated."""
    setattr(func, "npe2_on_deactivate", True)
    return func


def find_packages(where: Union[str, Path] = ".") -> List[Path]:
    return [p.parent for p in Path(where).resolve().rglob("**/__init__.py")]


def get_package_name(where: Union[str, Path] = ".") -> str:
    from ._inspection._setuputils import get_package_dir_info

    return get_package_dir_info(where).package_name


def compile(
    src_dir: Union[str, Path],
    dest: Union[str, Path, None] = None,
    packages: Sequence[str] = (),
    plugin_name: str = "",
) -> PluginManifest:
    """Compile plugin manifest from `src_dir`, where is a top-level repo.

    This will discover all the contribution points in the repo and output a manifest
    object

    Parameters
    ----------
    src_dir : Union[str, Path]
        Repo root. Should contain a pyproject or setup.cfg file.

    Returns
    -------
    PluginManifest
        Manifest including all discovered contribution points, combined with any
        existing contributions explicitly stated in the manifest.
    """
    import pkgutil

    from npe2.manifest.utils import merge_contributions

    src_path = Path(src_dir)
    assert src_path.exists(), f"src_dir {src_dir} does not exist"

    if dest is not None:
        pdest = Path(dest)
        suffix = pdest.suffix.lstrip(".")
        if suffix not in {"json", "yaml", "toml"}:
            raise ValueError(
                f"dest {dest!r} must have an extension of .json, .yaml, or .toml"
            )

    _packages = find_packages(src_path)
    if packages:
        _packages = [p for p in _packages if p.name in packages]

    if not plugin_name:
        plugin_name = get_package_name(src_path)

    contribs: List[contributions.ContributionPoints] = []
    for pkg_path in _packages:
        contribs.extend(
            find_npe2_module_contributions(
                module_info.module_finder.find_module(module_info.name).path,  # type: ignore  # noqa
                plugin_name=plugin_name,
                module_name=f"{pkg_path.name}.{module_info.name}",
            )
            for module_info in pkgutil.iter_modules([str(pkg_path)])
        )

    mf = PluginManifest(
        name=plugin_name,
        contributions=merge_contributions(contribs),
    )

    # if (manifest := info.get("manifest")) and Path(manifest).exists():
    #     original_manifest = PluginManifest.from_file(manifest)
    #     mf.display_name = original_manifest.display_name
    #     mf = merge_manifests([original_manifest, mf], overwrite=True)

    if dest is not None:
        manifest_string = getattr(mf, cast(str, suffix))(indent=2)
        pdest.write_text(manifest_string)

    return mf
