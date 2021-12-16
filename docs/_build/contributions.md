# Contributions

**Contributions** are a set of static declarations that you make in the `contributions` field of the [Plugin Manifest](). Your extension registers **Contributions** to extend various functionalities within napari. Here is a list of all available **Contributions**:

- [`commands`](#contributions.commands)
- [`themes`](#contributions.themes)
- [`readers`](#contributions.readers)
- [`writers`](#contributions.writers)
- [`sample_data`](#contributions.sample_data)
- [`widgets`](#contributions.widgets)

## contributions.commands

Contribute a **command** (a python callable) consisting of a unique `id`,
a `title` and (optionally) a `python_path` that points to a fully qualified python
callable.  If a `python_path` is not included in the manifest, it *must* be
registered during activation with `register_command`.

```{admonition} Future Plans
Command contributions will eventually include an **icon**, **category**, and
**enabled** state. Enablement is expressed with when clauses, that capture a
conditional expression determining whether the command should be enabled or not,
based on the current state of the program.  (i.e. "*If the active layer is a
`Labels` layer*")
```

Commands will show in a the Command Palette (⇧⌘P) but they can also show in other
menus.


### Fields

- **`commands.id`** : A unique identifier used to reference this command. While this may look like a python fully qualified name this does *not* refer to a python object; this identifier is specific to napari.  It must begin with the name of the package, and include only alphanumeric characters, plus dashes and underscores.
- **`commands.title`** : User facing title representing the command. This might be used, for example, when searching in a command palette. Examples: 'Generate lily sample', 'Read tiff image', 'Open gaussian blur widget'.
- **`commands.python_name`** : *(Optional: default=None).* Fully qualified name to a callable python object implementing this command. This usually takes the form of `{obj.__module__}:{obj.__qualname__} (e.g. `my_package.a_module:some_function`)



### Commands example

```yaml
contributions:
  commands:
  - id: my-plugin.hello_world
    title: Hello World

```


## contributions.themes

Contribute a color theme to napari.

You must specify an **id**, **label**, and whether the theme is a dark theme or a
light theme (such that the rest of napari changes to match your theme). Any color
keys omitted from the theme contribution will use the default napari dark/light
theme
colors.


### Fields

- **`themes.id`** : Identifier of the color theme as used in the user settings.
- **`themes.label`** : Label of the color theme as shown in the UI.
- **`themes.type`** : Base theme type, used for icons and filling in unprovided colors. Must be either `'dark'` or
- **`themes.colors`** : Theme colors. Valid keys include: `canvas`, `console`, `background`, `foreground`, `primary`, `secondary`, `highlight`, `text`, `icon`, `warning`, `current`. All keys are optional. Color values can be defined via:
   - name: `"Black"`, `"azure"`
   - hexadecimal value: `"0x000"`, `"#FFFFFF"`, `"7fffd4"`
   - RGB/RGBA tuples: `(255, 255, 255)`, `(255, 255, 255, 0.5)`
   - RGB/RGBA strings: `"rgb(255, 255, 255)"`, `"rgba(255, 255, 255, 0.5)`"
   - HSL strings: "`hsl(270, 60%, 70%)"`, `"hsl(270, 60%, 70%, .5)`"




### Themes example

```yaml
contributions:
  themes:
  - colors:
      background: '#272822'
      canvas: black
      console: black
      current: '#66d9ef'
      foreground: '#75715e'
      highlight: '#e6db74'
      primary: '#cfcfc2'
      secondary: '#f8f8f2'
      text: '#a1ef34'
      warning: '#f92672'
    id: monokai
    label: Monokai
    type: dark

```


## contributions.readers

Contribute a file reader.

Readers may be associated with specific **filename_patterns** (e.g. "*.tif",
"*.zip") and are invoked whenever `viewer.open('some/path')` is used on the
command line, or when a user opens a file in the graphical user interface by
dropping a file into the canvas, or using `File -> Open...`

See the [Reader Guide]() on how to create a reader contribution.


### Fields

- **`readers.command`** : Identifier of the command providing the reader interface.
- **`readers.filename_patterns`** : List of [fnmatch](https://docs.python.org/3/library/fnmatch.html) filename patterns that this reader accepts. Reader will be tried only if `fnmatch(filename, pattern) == True`. Use `['*']` to match all filenames.
- **`readers.accepts_directories`** : *(Optional: default=False).* Whether this reader accepts directories.



### Readers example

```yaml
contributions:
  commands:
  - id: my-plugin.read_xyz
    python_name: my_plugin._some_module:get_xyz_reader
    title: Read ".xyz" files
  readers:
  - accepts_directories: false
    command: my-plugin.read_xyz
    filename_patterns:
    - '*.xyz'

```


## contributions.writers

Contribute a layer writer.

Writers accept data from one or more layers and write them to file. Writers declare
support for writing one or more **layer_types**, may be associated with specific
**filename_patterns** (e.g. "\*.tif", "\*.zip") and are invoked whenever
`viewer.layers.save('some/path.ext')` is used on the command line, or when a user
requests to save one or more layers in the graphical user interface with `File ->
Save Selected Layer(s)...` or `Save All Layers...`


See the [Writer Guide]() on how to create a writer contribution.


### Fields

- **`writers.command`** : Identifier of the command providing a writer.
- **`writers.layer_types`** : List of layer type constraints. These determine what layers (or combinations thereof) this writer handles.
- **`writers.filename_extensions`** : *(Optional: default=[]).* List of filename extensions compatible with this writer. The first entry is used as the default if necessary. Empty by default. When empty, any filename extension is accepted.
- **`writers.display_name`** : *(Optional: default=).* Brief text used to describe this writer when presented. Empty by default. When present, this string is presented in the save dialog along side the plugin name and may be used to distinguish the kind of writer for the user. E.g. “lossy” or “lossless”.



### Writers example

```yaml
contributions:
  commands:
  - id: my-plugin.write_points
    python_name: my_plugin._some_module:write_points
    title: Save points layer to csv
  writers:
  - command: my-plugin.write_points
    filename_extensions:
    - .csv
    layer_types:
    - points

```


## contributions.sample_data

Contribute sample data for use in napari.

Sample data can take the form of a **command** that returns layer data, or a simple
path or **uri** to a local or remote resource (assuming there is a reader plugin
capable of reading that path/URI).


### Common Fields

- **`sample_data.key`** : A unique key to identify this sample.
- **`sample_data.display_name`** : String to show in the UI when referring to this sample


### Union Fields

In addition to the common fields, `sample_data` should additional include one of the following interfaces:



<hr/>

Contribute a command that generates data.


- **`sample_data.command`** : Identifier of a command that returns layer data tuple.



<hr/>

Contribute a URI to static local or remote data. This can be data included in
the plugin package, or a URL to remote data.  The URI must be readable by either
napari's builtin reader, or by a plugin that is included/required.


- **`sample_data.uri`** : Path or URL to a data resource. This URI should be a valid input to `io_utils.read`
- **`sample_data.reader_plugin`** : *(Optional: default=None).* Name of plugin to use to open URI


<hr/>


### Sample_Data example

```yaml
contributions:
  commands:
  - id: my-plugin.data.fractal
    python_name: my_plugin._data:fractal
    title: Create fractal image
  sample_data:
  - command: my-plugin.data.fractal
    display_name: Fractal
    key: fractal
  - display_name: Tabueran Kiribati
    key: napari
    uri: https://en.wikipedia.org/wiki/Napari#/media/File:Tabuaeran_Kiribati.jpg

```


## contributions.widgets

Contribute a widget that can be added to the napari viewer.

Widget contributions point to a **command** that, when called, returns a widget
*instance*; this includes functions that return a widget instance, (e.g. those
decorated with `magicgui.magic_factory`) and subclasses of either
[`QtWidgets.QWidget`](https://doc.qt.io/qt-5/qwidget.html) or
[`magicgui.widgets.Widget`](https://napari.org/magicgui/api/_autosummary/magicgui.widgets._bases.Widget.html).

Optionally, **autogenerate** may be used to create a widget (using
[magicgui](https://napari.org/magicgui/)) from a command.  (In this case, the
command needn't return a widget instance; it can be any function suitable as an
argument to `magicgui.magicgui()`.)

See the [Widget Guide]() on how to create a widget contribution.


### Fields

- **`widgets.command`** : Identifier of a command that returns a widget instance.  Or, if `autogenerate` is `True`, any command suitable as an argument to `magicgui.magicgui()`.
- **`widgets.display_name`** : Name for the widget, as presented in the UI.
- **`widgets.autogenerate`** : *(Optional: default=False).* If true, a widget will be autogenerated from the signature of the associated command using [magicgui](https://napari.org/magicgui/).



### Widgets example

```yaml
contributions:
  commands:
  - id: my-plugin.animation_wizard
    python_name: my_plugin._some_module:AnimationWizard
    title: Open animation wizard
  - id: my-plugin.do_threshold
    python_name: my_plugin._some_module:threshold
    title: Perform threshold on image, return new image
  widgets:
  - command: my-plugin.animation_wizard
    display_name: Wizard
  - autogenerate: true
    command: my-plugin.do_threshold
    display_name: Threshold

```
