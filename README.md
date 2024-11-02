# npe2 - napari plugin engine version 2

[![CI](https://github.com/napari/npe2/actions/workflows/ci.yml/badge.svg)](https://github.com/napari/npe2/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/napari/npe2/branch/main/graph/badge.svg?token=FTH635x542)](https://codecov.io/gh/napari/npe2)

## Project description

The **napari plugin engine version 2**, **npe2** extends the functionality of
[napari's core](https://github.com/napari/napari).
The plugin ecosystem offers user additional functionality for napari as well
as specific support for different scientific domains.

This repo contains source code and documentation about the napari plugin engine.

## Getting started documentation

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

## Installation

To install the `npe2` command line tool.

1. Create and activate a virtual environment.

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2. Install npe2.

    ```bash
    pip install npe2
    ```

3. Test your installation.

    ```bash
    npe2 --help
    ```

## Usage

The command line tool `npe2` offers the following commands:

```bash
cache      Cache utils
compile    Compile @npe2.implements contributions to generate a manifest.                        
convert    Convert first generation napari plugin to new (manifest) format.                                                  
fetch      Fetch manifest from remote package.
list       List currently installed plugins.                       
parse      Show parsed manifest as yaml.
validate   Validate manifest for a distribution name or manifest filepath.   
```

### Examples

List currently installed plugins:

```bash
npe2 list
```

Convert current directory to an npe2-ready plugin. 
(Note: the repo must also be installed and importable in the current environment.)

```bash
npe2 convert .
```

Validate a plugin package. For example, a plugin named `your-plugin-package`:

```bash
npe2 validate your-plugin-package
```

Show a parsed manifest of your plugin:

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
