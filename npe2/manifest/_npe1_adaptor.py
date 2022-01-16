import inspect
from pathlib import Path

from appdirs import user_cache_dir

from npe2.manifest.utils import Executable

from . import contributions
from .schema import PluginManifest

COMMAND_PARAMS = inspect.signature(contributions.CommandContribution).parameters
HOOKIMPL_DECO = "napari_plugin_engine.napari_hook_implementation"


CACHE = Path(user_cache_dir("npe1", "napari"))


def deep_update(dct: dict, merge_dct: dict, copy=True) -> dict:
    """Merge possibly nested dicts"""
    _dct = dct.copy() if copy else dct
    for k, v in merge_dct.items():
        if k in _dct and isinstance(dct[k], dict) and isinstance(v, dict):
            deep_update(_dct[k], v, copy=False)
        elif isinstance(v, list):
            if k not in _dct:
                _dct[k] = []
            _dct[k].extend(v)
        else:
            _dct[k] = v
    return _dct


def merge_contributions(*contribs: contributions.ContributionPoints) -> dict:
    if not contribs:
        return {}

    out = contribs[0].dict(exclude_unset=True)
    if len(contribs) > 1:
        for n, c in enumerate(contribs[1:]):
            print("n", n)
            for cmd in c.commands or ():
                cmd.id += f"_{n + 2}"
            for name, val in c:
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, Executable):
                            item.command += f"_{n + 2}"
            print(c.dict(exclude_unset=True))
            deep_update(out, c.dict(exclude_unset=True))
    return out


class NPE1Adaptor(PluginManifest):
    def get_manifest(self):
        cached = CACHE / self._cache_key()
        if cached.exists():
            pm = PluginManifest.from_file(cached)
            pm.package_metadata = self.package_metadata
            return pm

        from .._from_npe1 import manifest_from_npe1

        mfs = [manifest_from_npe1(ep.name) for ep in self._npe1_entry_points]
        info = mfs[0].dict(exclude={"contributions", "package_metadata"})
        info["display_name"] = self.name
        info["package_metadata"] = self.package_metadata
        info["contributions"] = merge_contributions(*(m.contributions for m in mfs))

        pm = PluginManifest(**info)
        yaml = pm.yaml(exclude={"package_metadata"})
        cached.parent.mkdir(exist_ok=True, parents=True)
        cached.write_text(yaml)
        return pm

    def _cache_key(self, ext=".yaml"):
        return f"{self.name}_{self.package_metadata.version}{ext}"
