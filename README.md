# npe2

[![CI](https://github.com/napari/npe2/actions/workflows/ci.yml/badge.svg)](https://github.com/napari/npe2/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/napari/npe2/branch/main/graph/badge.svg?token=FTH635x542)](https://codecov.io/gh/napari/npe2)

napari plugin refactor

see also https://github.com/napari/napari/issues/3115

Includes a command line tool `npe2` with the following commands:
```bash
Commands:
  convert   Convert existing plugin to new manifest.
  parse     Show parsed manifest as yaml
  validate  Validate manifest for a distribution name or manifest filepath.
```

examples:

```bash
# create npe2 manifest from first-generation napari plugin
npe2 convert your-plugin-package --out napari.yaml
```

```bash
npe2 validate your-plugin-package
```

```bash
npe2 parse your-plugin-package
```
