# npe2

[![CI](https://github.com/napari/npe2/actions/workflows/ci.yml/badge.svg)](https://github.com/napari/npe2/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/napari/npe2/branch/main/graph/badge.svg?token=FTH635x542)](https://codecov.io/gh/napari/npe2)

napari plugin refactor

see also https://github.com/napari/napari/issues/3115

## Documentation

For documentation on authoring npe2 plugins, see the [napari plugin docs](https://napari.org/plugins/index.html).  These include:
- the [manifest reference](https://napari.org/plugins/manifest.html)
- the [contribution guide](https://napari.org/plugins/contributions.html)

## Command line tool

Includes a command line tool `npe2` with the following commands:
```bash
Commands:
  cache     Cache utils
  convert   Convert first generation napari plugin to new (manifest) format.
  parse     Show parsed manifest as yaml
  validate  Validate manifest for a distribution name or manifest filepath.
```

examples:

```bash
# convert current directory to an npe2-ready plugin
# (note: the repo must also be installed and importable in the current environment)
npe2 convert .
```

```bash
npe2 validate your-plugin-package
```

```bash
npe2 parse your-plugin-package
```
