# npe2

[![CI](https://github.com/napari/npe2/actions/workflows/ci.yml/badge.svg)](https://github.com/napari/npe2/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/napari/npe2/branch/main/graph/badge.svg?token=FTH635x542)](https://codecov.io/gh/napari/npe2)

napari plugin refactor

see also https://github.com/napari/napari/issues/3115

Includes a command line tool `npe2` with the following commands:
```bash
Commands:
  convert   Convert existing plugin repository to npe2 format (create manifest, update setup.cfg)
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
