# npe2 - napari plugin engine version 2

[![CI](https://github.com/napari/npe2/actions/workflows/ci.yml/badge.svg)](https://github.com/napari/npe2/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/napari/npe2/branch/main/graph/badge.svg?token=FTH635x542)](https://codecov.io/gh/napari/npe2)

## Project description

The **napari plugin engine version 2**, **npe2** extends the functionality of
[napari's core](https://github.com/napari/napari).
The plugin ecosystem offers user additional functionality for napari as well
as specific support for different scientific domains.

This repo contains source code and documentation about the napari plugin engine.

## Getting started

The [napari plugin docs landing page](https://napari.org/stable/plugins/index.html)
offers comprehensive information for **plugin users** and for **plugin developers**.

### Plugin users

For plugin users, the docs include information about:
- [Starting to use plugins](https://napari.org/stable/plugins/start_using_plugins/index.html#plugins-getting-started)
- [Finding and installing plugins](https://napari.org/stable/plugins/start_using_plugins/finding_and_installing_plugins.html#find-and-install-plugins)

### Plugin developers

For plugin developers, the docs cover topics like:
- [Building a plugin](https://napari.org/stable/plugins/building_a_plugin/index.html)
- [Contributing a plugin](https://napari.org/stable/plugins/building_a_plugin/guides.html)
- [Technical references such as the plugin manifest](https://napari.org/stable/plugins/technical_references/manifest.html)

## Usage information

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

## License

npe2 uses the [BSD License](./LICENSE).

## History

This repo replaces the initial napari plugin engine v1.
See also https://github.com/napari/napari/issues/3115 for
motivation and technical discussion about the creation of v2.

## Contact us

Visit [our community documentation](https://napari.org/stable/community/index.html)
or [open a new issue on this repo](https://github.com/napari/npe2/issues/new).
