# npe2

[![CI](https://github.com/napari/npe2/actions/workflows/ci.yml/badge.svg)](https://github.com/napari/npe2/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/napari/npe2/branch/main/graph/badge.svg?token=FTH635x542)](https://codecov.io/gh/napari/npe2)

## napari plugin engine version 2

The **napari plugin engine version 2**, **npe2** extends the functionality of napari's core.
The plugin ecosystem offers user additional functionality for napari as well as specific support
for different scientific domains.

This repo contains source code and documentation about the napari plugin engine.

## Documentation

See the: [napari plugin docs](https://napari.org/stable/plugins/index.html) for information about
creating plugins for the napari plugin engine (npe2).  These docs include:
- the [plugin manifest reference](https://napari.org/stable/plugins/technical_references/manifest.html)
- the [plugin contribution guide](https://napari.org/stable/plugins/building_a_plugin/guides.html)

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

## History

This repo replaces the initial napari plugin engine v1.
See also https://github.com/napari/napari/issues/3115 for
motivation and technical discussion about the creation of v2.
