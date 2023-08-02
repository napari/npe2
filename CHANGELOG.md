# Changelog

## [v0.7.1](https://github.com/napari/npe2/tree/v0.7.1) (2023-07-16)

[Full Changelog](https://github.com/napari/npe2/compare/v0.7.0...v0.7.1)

**Implemented enhancements:**

- feat: support python3.11 [\#293](https://github.com/napari/npe2/pull/293) ([tlambert03](https://github.com/tlambert03))
- add graph layer  [\#292](https://github.com/napari/npe2/pull/292) ([JoOkuma](https://github.com/JoOkuma))

**Fixed bugs:**

- fix: use constraints in napari tests [\#298](https://github.com/napari/npe2/pull/298) ([Czaki](https://github.com/Czaki))
- Use full `plugin_name` when finding chosen `reader` rather than `startswith` [\#297](https://github.com/napari/npe2/pull/297) ([DragaDoncila](https://github.com/DragaDoncila))
- Change ArrayLike type to use read only properties [\#289](https://github.com/napari/npe2/pull/289) ([andy-sweet](https://github.com/andy-sweet))
- Bugfix: use .lower\(\) to make paths & pattern fnmatch case  insensitive [\#275](https://github.com/napari/npe2/pull/275) ([psobolewskiPhD](https://github.com/psobolewskiPhD))

**Documentation:**

- Fix typo in `DynamicPlugin` [\#304](https://github.com/napari/npe2/pull/304) ([lucyleeow](https://github.com/lucyleeow))
- DOCS: Widget guide should consistently use parent=None kwarg in examples [\#302](https://github.com/napari/npe2/pull/302) ([GenevieveBuckley](https://github.com/GenevieveBuckley))

**Merged pull requests:**

- remove tomlpp [\#294](https://github.com/napari/npe2/pull/294) ([tlambert03](https://github.com/tlambert03))
- Use hatchling as build backend [\#282](https://github.com/napari/npe2/pull/282) ([tlambert03](https://github.com/tlambert03))

## [v0.7.0](https://github.com/napari/npe2/tree/v0.7.0) (2023-04-14)

[Full Changelog](https://github.com/napari/npe2/compare/v0.6.2...v0.7.0)

**Fixed bugs:**

- fix: pass command registry to rdr.exec in io\_utils.\_read [\#285](https://github.com/napari/npe2/pull/285) ([tlambert03](https://github.com/tlambert03))
- fix: use logger instead of warning for TestPluginManager.discover [\#283](https://github.com/napari/npe2/pull/283) ([tlambert03](https://github.com/tlambert03))
- Add specific error when reader plugin was chosen but failed [\#276](https://github.com/napari/npe2/pull/276) ([DragaDoncila](https://github.com/DragaDoncila))

**Tests & CI:**

- Fix tests: use npe1 version \(0.1.2\) of napari-ndtiffs [\#277](https://github.com/napari/npe2/pull/277) ([psobolewskiPhD](https://github.com/psobolewskiPhD))
- ci: update pre-commit, use ruff and fix mypy [\#273](https://github.com/napari/npe2/pull/273) ([tlambert03](https://github.com/tlambert03))
- Switch from GabrielBB/xvfb-action to aganders3/headless-gui [\#269](https://github.com/napari/npe2/pull/269) ([Czaki](https://github.com/Czaki))

**Refactors:**

- refactor: use src layout and pyproject.toml [\#281](https://github.com/napari/npe2/pull/281) ([tlambert03](https://github.com/tlambert03))

**Documentation:**

- Fix link to magicgui objects.inv in intersphinx [\#270](https://github.com/napari/npe2/pull/270) ([melissawm](https://github.com/melissawm))

**Merged pull requests:**

- chore: changelog v0.7.0 [\#286](https://github.com/napari/npe2/pull/286) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump peter-evans/create-pull-request from 4 to 5 [\#284](https://github.com/napari/npe2/pull/284) ([dependabot[bot]](https://github.com/apps/dependabot))
- Pin pydantic bellow 2.0 [\#279](https://github.com/napari/npe2/pull/279) ([Czaki](https://github.com/Czaki))

## [v0.6.2](https://github.com/napari/npe2/tree/v0.6.2) (2023-01-12)

[Full Changelog](https://github.com/napari/npe2/compare/v0.6.1...v0.6.2)

**Implemented enhancements:**

- Expose `syntax_style` [\#261](https://github.com/napari/npe2/pull/261) ([brisvag](https://github.com/brisvag))
- enable keybinding contribution [\#254](https://github.com/napari/npe2/pull/254) ([kne42](https://github.com/kne42))
- Add count of discovered plugins [\#248](https://github.com/napari/npe2/pull/248) ([Czaki](https://github.com/Czaki))
- fix: relax display name validation [\#242](https://github.com/napari/npe2/pull/242) ([tlambert03](https://github.com/tlambert03))
- feat: add more fetch sources [\#240](https://github.com/napari/npe2/pull/240) ([tlambert03](https://github.com/tlambert03))
- feat: add category [\#239](https://github.com/napari/npe2/pull/239) ([tlambert03](https://github.com/tlambert03))
- bug: ignore extra fields on manifest [\#237](https://github.com/napari/npe2/pull/237) ([tlambert03](https://github.com/tlambert03))
- feat: add icon to manifest [\#235](https://github.com/napari/npe2/pull/235) ([tlambert03](https://github.com/tlambert03))
- add visibility field [\#234](https://github.com/napari/npe2/pull/234) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- Fix PackageMetadata validation error with extra provided field [\#256](https://github.com/napari/npe2/pull/256) ([aganders3](https://github.com/aganders3))
- fix: alternate fix for dotted plugin\_name [\#238](https://github.com/napari/npe2/pull/238) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- fix flaky fetch tests [\#255](https://github.com/napari/npe2/pull/255) ([nclack](https://github.com/nclack))

**Documentation:**

- Move to sphinx-design tabs [\#259](https://github.com/napari/npe2/pull/259) ([melissawm](https://github.com/melissawm))
- Fix a few broken links [\#258](https://github.com/napari/npe2/pull/258) ([melissawm](https://github.com/melissawm))

**Merged pull requests:**

- changelog v0.6.2 [\#268](https://github.com/napari/npe2/pull/268) ([github-actions[bot]](https://github.com/apps/github-actions))
- ci\(dependabot\): bump styfle/cancel-workflow-action from 0.10.1 to 0.11.0 [\#252](https://github.com/napari/npe2/pull/252) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump styfle/cancel-workflow-action from 0.10.0 to 0.10.1 [\#246](https://github.com/napari/npe2/pull/246) ([dependabot[bot]](https://github.com/apps/dependabot))
- Add setuptools plugin to compile manifest at build [\#194](https://github.com/napari/npe2/pull/194) ([tlambert03](https://github.com/tlambert03))

## [v0.6.1](https://github.com/napari/npe2/tree/v0.6.1) (2022-08-08)

[Full Changelog](https://github.com/napari/npe2/compare/v0.6.0...v0.6.1)

**Fixed bugs:**

- fix command id validation when dot in package name [\#230](https://github.com/napari/npe2/pull/230) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- changelog v0.6.1 [\#231](https://github.com/napari/npe2/pull/231) ([tlambert03](https://github.com/tlambert03))

## [v0.6.0](https://github.com/napari/npe2/tree/v0.6.0) (2022-08-07)

[Full Changelog](https://github.com/napari/npe2/compare/v0.5.2...v0.6.0)

**Implemented enhancements:**

- Add \(refactor\) configuration contribution, allowing plugins to declare a schema for their configurables [\#219](https://github.com/napari/npe2/pull/219) ([tlambert03](https://github.com/tlambert03))
- npe1 module ast visitor \(for faster fetch without install\) [\#217](https://github.com/napari/npe2/pull/217) ([tlambert03](https://github.com/tlambert03))
- Compile plugins using `npe2.implements` [\#186](https://github.com/napari/npe2/pull/186) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- fix name validator to allow periods [\#227](https://github.com/napari/npe2/pull/227) ([tlambert03](https://github.com/tlambert03))
- fix: delay inspection of command params [\#223](https://github.com/napari/npe2/pull/223) ([tlambert03](https://github.com/tlambert03))
- Improve error message on schema validation [\#220](https://github.com/napari/npe2/pull/220) ([Czaki](https://github.com/Czaki))

**Tests & CI:**

- ci: remove fetch\_manifests [\#224](https://github.com/napari/npe2/pull/224) ([tlambert03](https://github.com/tlambert03))
- run io\_utils tests first [\#222](https://github.com/napari/npe2/pull/222) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- v0.6.0 changelog [\#229](https://github.com/napari/npe2/pull/229) ([github-actions[bot]](https://github.com/apps/github-actions))
- build: remove magicgui dependency [\#218](https://github.com/napari/npe2/pull/218) ([tlambert03](https://github.com/tlambert03))

## [v0.5.2](https://github.com/napari/npe2/tree/v0.5.2) (2022-07-24)

[Full Changelog](https://github.com/napari/npe2/compare/v0.5.1...v0.5.2)

**Implemented enhancements:**

- feat: deactivate on disable [\#212](https://github.com/napari/npe2/pull/212) ([tlambert03](https://github.com/tlambert03))
- feat: add register\_disposable [\#211](https://github.com/napari/npe2/pull/211) ([tlambert03](https://github.com/tlambert03))
- add back command enablement, category, short\_title, and icon [\#210](https://github.com/napari/npe2/pull/210) ([tlambert03](https://github.com/tlambert03))
- add version to cli [\#205](https://github.com/napari/npe2/pull/205) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- Fix `npe2 list` when a dotted field key is empty [\#203](https://github.com/napari/npe2/pull/203) ([tlambert03](https://github.com/tlambert03))

**Refactors:**

- Split out `from_npe1` setuptools package inspection into new module [\#206](https://github.com/napari/npe2/pull/206) ([tlambert03](https://github.com/tlambert03))

**Documentation:**

- Fix documentation links [\#208](https://github.com/napari/npe2/pull/208) ([melissawm](https://github.com/melissawm))

**Merged pull requests:**

- changelog v0.5.2 [\#213](https://github.com/napari/npe2/pull/213) ([tlambert03](https://github.com/tlambert03))

## [v0.5.1](https://github.com/napari/npe2/tree/v0.5.1) (2022-06-27)

[Full Changelog](https://github.com/napari/npe2/compare/v0.5.0...v0.5.1)

**Implemented enhancements:**

- Add PluginManager `dict()` method to export state of manager [\#197](https://github.com/napari/npe2/pull/197) ([tlambert03](https://github.com/tlambert03))
- Add `npe2 list` command to discover/display all currently installed plugins [\#192](https://github.com/napari/npe2/pull/192) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- index npe1 stuff on `npe2 list` [\#198](https://github.com/napari/npe2/pull/198) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- Always mock cache in tests [\#199](https://github.com/napari/npe2/pull/199) ([tlambert03](https://github.com/tlambert03))

**Documentation:**

- Add mised theme type in description [\#200](https://github.com/napari/npe2/pull/200) ([Czaki](https://github.com/Czaki))
- Add docs clarifying menus `when` and `group` [\#195](https://github.com/napari/npe2/pull/195) ([tlambert03](https://github.com/tlambert03))
- Add docs about length requirements to display name [\#191](https://github.com/napari/npe2/pull/191) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- changelog v0.5.1 [\#201](https://github.com/napari/npe2/pull/201) ([tlambert03](https://github.com/tlambert03))
- Remove typing-extensions imports [\#193](https://github.com/napari/npe2/pull/193) ([tlambert03](https://github.com/tlambert03))

## [v0.5.0](https://github.com/napari/npe2/tree/v0.5.0) (2022-06-21)

[Full Changelog](https://github.com/napari/npe2/compare/v0.4.1...v0.5.0)

**Implemented enhancements:**

- Prevent runtime-arg checking on npe2.implements decorators by default [\#188](https://github.com/napari/npe2/pull/188) ([tlambert03](https://github.com/tlambert03))
- Add `npe2 fetch` command to cli to fetch remote manifests [\#185](https://github.com/napari/npe2/pull/185) ([tlambert03](https://github.com/tlambert03))
- allow `npe2 parse` to output to file, add format option [\#183](https://github.com/napari/npe2/pull/183) ([tlambert03](https://github.com/tlambert03))
- Add `npe1_shim` field to schema [\#182](https://github.com/napari/npe2/pull/182) ([tlambert03](https://github.com/tlambert03))
- allow `npe2.write` to take layer instances [\#181](https://github.com/napari/npe2/pull/181) ([tlambert03](https://github.com/tlambert03))
- Add `npe2pm` `TestPluginManager` fixture [\#180](https://github.com/napari/npe2/pull/180) ([tlambert03](https://github.com/tlambert03))
- Add `@npe.implements` decorators, for opt-in manifest validation and/or AST-based-generation [\#75](https://github.com/napari/npe2/pull/75) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- Fail silently when caching throws `OSError` [\#184](https://github.com/napari/npe2/pull/184) ([DragaDoncila](https://github.com/DragaDoncila))

## [v0.4.1](https://github.com/napari/npe2/tree/v0.4.1) (2022-06-13)

[Full Changelog](https://github.com/napari/npe2/compare/v0.4.0...v0.4.1)

**Fixed bugs:**

- hide docs again in napari menus \(Fix napari docs build\) [\#178](https://github.com/napari/npe2/pull/178) ([tlambert03](https://github.com/tlambert03))

## [v0.4.0](https://github.com/napari/npe2/tree/v0.4.0) (2022-06-13)

[Full Changelog](https://github.com/napari/npe2/compare/v0.3.0.rc0...v0.4.0)

**Implemented enhancements:**

- Turn menus contributions into dict of arbitrary key to list of MenuItems [\#175](https://github.com/napari/npe2/pull/175) ([tlambert03](https://github.com/tlambert03))
- Add minor conveniences for DynamicPlugin [\#173](https://github.com/napari/npe2/pull/173) ([tlambert03](https://github.com/tlambert03))
- Add `plugin_manager` module for global singleton convenience  [\#164](https://github.com/napari/npe2/pull/164) ([tlambert03](https://github.com/tlambert03))
- Allow arbitrary menu locations in npe2 [\#160](https://github.com/napari/npe2/pull/160) ([sofroniewn](https://github.com/sofroniewn))

**Fixed bugs:**

- Fix writer order preference [\#172](https://github.com/napari/npe2/pull/172) ([tlambert03](https://github.com/tlambert03))
- Fix potential error with `npe2 cache --list` with uninstalled plugin [\#165](https://github.com/napari/npe2/pull/165) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- Pre commit, flake8, and mypy updates [\#171](https://github.com/napari/npe2/pull/171) ([tlambert03](https://github.com/tlambert03))
- add dependabot [\#167](https://github.com/napari/npe2/pull/167) ([tlambert03](https://github.com/tlambert03))
- Auto update changelog workflow [\#151](https://github.com/napari/npe2/pull/151) ([Carreau](https://github.com/Carreau))

**Refactors:**

- Revert menu restriction \(\#160\) [\#174](https://github.com/napari/npe2/pull/174) ([tlambert03](https://github.com/tlambert03))
- Push stack=... through all the reader internal API, take II [\#142](https://github.com/napari/npe2/pull/142) ([Carreau](https://github.com/Carreau))

**Documentation:**

- Add doc links to README [\#158](https://github.com/napari/npe2/pull/158) ([nclack](https://github.com/nclack))
- Fix codeblock directive in docstring [\#156](https://github.com/napari/npe2/pull/156) ([melissawm](https://github.com/melissawm))

## [v0.3.0.rc0](https://github.com/napari/npe2/tree/v0.3.0.rc0) (2022-04-05)

[Full Changelog](https://github.com/napari/npe2/compare/v0.3.0...v0.3.0.rc0)

## [v0.3.0](https://github.com/napari/npe2/tree/v0.3.0) (2022-04-05)

[Full Changelog](https://github.com/napari/npe2/compare/v0.2.2...v0.3.0)

**Implemented enhancements:**

- NPE1Adapter Part 3 - caching of adapter manifests [\#126](https://github.com/napari/npe2/pull/126) ([tlambert03](https://github.com/tlambert03))
- NPE1Adapter Part 2 - adding the NPE1Adapter object. [\#125](https://github.com/napari/npe2/pull/125) ([tlambert03](https://github.com/tlambert03))
- NPE1Adapter Part 1 - updated \_from\_npe1 conversion logic to prepare for locally defined objects [\#124](https://github.com/napari/npe2/pull/124) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- Avoid use of inspect.signature on CommandContribution class [\#146](https://github.com/napari/npe2/pull/146) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- Fix black problem on pre-commit CI [\#147](https://github.com/napari/npe2/pull/147) ([Czaki](https://github.com/Czaki))
- Fix ci for testing all plugins [\#134](https://github.com/napari/npe2/pull/134) ([tlambert03](https://github.com/tlambert03))
- Add ci to test all plugins on PR label part1 [\#133](https://github.com/napari/npe2/pull/133) ([tlambert03](https://github.com/tlambert03))

**Refactors:**

- Turn off npe1 discovery by default [\#145](https://github.com/napari/npe2/pull/145) ([tlambert03](https://github.com/tlambert03))
- Reorganize contributions into submodule [\#130](https://github.com/napari/npe2/pull/130) ([tlambert03](https://github.com/tlambert03))
- drop py3.7 & misc small reformats [\#123](https://github.com/napari/npe2/pull/123) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- add v0.3.0 changelog [\#150](https://github.com/napari/npe2/pull/150) ([tlambert03](https://github.com/tlambert03))

## [v0.2.2](https://github.com/napari/npe2/tree/v0.2.2) (2022-03-14)

[Full Changelog](https://github.com/napari/npe2/compare/v0.2.1...v0.2.2)

**Implemented enhancements:**

- Add DynamicPlugin object/context for ease of testing & dynamic plugin creation [\#128](https://github.com/napari/npe2/pull/128) ([tlambert03](https://github.com/tlambert03))

**Refactors:**

- Disallow mutation on plugin manifest name [\#127](https://github.com/napari/npe2/pull/127) ([tlambert03](https://github.com/tlambert03))
- Clarify Typing. [\#105](https://github.com/napari/npe2/pull/105) ([Carreau](https://github.com/Carreau))

## [v0.2.1](https://github.com/napari/npe2/tree/v0.2.1) (2022-03-11)

[Full Changelog](https://github.com/napari/npe2/compare/v0.2.0...v0.2.1)

**Fixed bugs:**

- Fix auto-discovery of plugins for napari \<= 0.4.15 [\#120](https://github.com/napari/npe2/pull/120) ([tlambert03](https://github.com/tlambert03))

## [v0.2.0](https://github.com/napari/npe2/tree/v0.2.0) (2022-03-10)

[Full Changelog](https://github.com/napari/npe2/compare/v0.1.2...v0.2.0)

**Implemented enhancements:**

- add py.typed [\#115](https://github.com/napari/npe2/pull/115) ([tlambert03](https://github.com/tlambert03))
- Suggest to run npe2 validate when errors present. [\#104](https://github.com/napari/npe2/pull/104) ([Carreau](https://github.com/Carreau))
- Add enable disable [\#101](https://github.com/napari/npe2/pull/101) ([tlambert03](https://github.com/tlambert03))
- make package meta hashable [\#97](https://github.com/napari/npe2/pull/97) ([tlambert03](https://github.com/tlambert03))
- add min\_ver to PackageMetadata [\#96](https://github.com/napari/npe2/pull/96) ([tlambert03](https://github.com/tlambert03))
- set display\_name to plugin name when empty [\#92](https://github.com/napari/npe2/pull/92) ([nclack](https://github.com/nclack))

**Fixed bugs:**

- add back deprecated \_samples on contributions index [\#116](https://github.com/napari/npe2/pull/116) ([tlambert03](https://github.com/tlambert03))
- Make conversion robust to entry\_point string entries [\#94](https://github.com/napari/npe2/pull/94) ([nclack](https://github.com/nclack))

**Tests & CI:**

- Fix test warning [\#118](https://github.com/napari/npe2/pull/118) ([tlambert03](https://github.com/tlambert03))
- Test napari during CI [\#117](https://github.com/napari/npe2/pull/117) ([tlambert03](https://github.com/tlambert03))
- Separate dev test from integration test. [\#114](https://github.com/napari/npe2/pull/114) ([Carreau](https://github.com/Carreau))

**Refactors:**

- Simplify Reader/writer internal logic. [\#107](https://github.com/napari/npe2/pull/107) ([Carreau](https://github.com/Carreau))

**Documentation:**

- Update reader plugin contribution doc to mention `[(None,)]`  sentinel [\#113](https://github.com/napari/npe2/pull/113) ([tlambert03](https://github.com/tlambert03))
- DOC: typo missing backtick [\#102](https://github.com/napari/npe2/pull/102) ([Carreau](https://github.com/Carreau))
- Fix some typos and dead links [\#99](https://github.com/napari/npe2/pull/99) ([andy-sweet](https://github.com/andy-sweet))

## [v0.1.2](https://github.com/napari/npe2/tree/v0.1.2) (2022-01-28)

[Full Changelog](https://github.com/napari/npe2/compare/v0.1.1...v0.1.2)

**Fixed bugs:**

- add include\_package\_data to setup.cfg in npe2 convert [\#89](https://github.com/napari/npe2/pull/89) ([tlambert03](https://github.com/tlambert03))
- Handle list of paths in iter\_compatible\_reader [\#87](https://github.com/napari/npe2/pull/87) ([ppwadhwa](https://github.com/ppwadhwa))

**Tests & CI:**

- update gh release action to include schema [\#90](https://github.com/napari/npe2/pull/90) ([tlambert03](https://github.com/tlambert03))

**Documentation:**

- use latest release schema for docs [\#85](https://github.com/napari/npe2/pull/85) ([tlambert03](https://github.com/tlambert03))
- Better way to find templates folder when building docs [\#84](https://github.com/napari/npe2/pull/84) ([tlambert03](https://github.com/tlambert03))
- Move some \_docs files [\#78](https://github.com/napari/npe2/pull/78) ([tlambert03](https://github.com/tlambert03))

## [v0.1.1](https://github.com/napari/npe2/tree/v0.1.1) (2022-01-07)

[Full Changelog](https://github.com/napari/npe2/compare/v0.1.0...v0.1.1)

**Implemented enhancements:**

- Add option to validate python\_name imports [\#76](https://github.com/napari/npe2/pull/76) ([tlambert03](https://github.com/tlambert03))
- Extract out ImportExport logic from PluginManifest, don't sort yaml fields alphabetically [\#72](https://github.com/napari/npe2/pull/72) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- Bring test coverage to 100%, reorganize tests [\#70](https://github.com/napari/npe2/pull/70) ([tlambert03](https://github.com/tlambert03))

**Refactors:**

- change sample plugin name from `my_plugin` to `my-plugin` [\#74](https://github.com/napari/npe2/pull/74) ([tlambert03](https://github.com/tlambert03))
- split contributions/io into readers and writers [\#73](https://github.com/napari/npe2/pull/73) ([tlambert03](https://github.com/tlambert03))
- remove SPDX licenses [\#71](https://github.com/napari/npe2/pull/71) ([tlambert03](https://github.com/tlambert03))
- change engine to schema\_version [\#69](https://github.com/napari/npe2/pull/69) ([tlambert03](https://github.com/tlambert03))
- Replace entry\_point with activate/deactive function [\#68](https://github.com/napari/npe2/pull/68) ([tlambert03](https://github.com/tlambert03))

**Documentation:**

- Autogen docs [\#77](https://github.com/napari/npe2/pull/77) ([tlambert03](https://github.com/tlambert03))

## [v0.1.0](https://github.com/napari/npe2/tree/v0.1.0) (2021-12-15)

[Full Changelog](https://github.com/napari/npe2/compare/v0.1.0rc1...v0.1.0)

**Implemented enhancements:**

- Remove semver dependency, vendor small portion [\#62](https://github.com/napari/npe2/pull/62) ([tlambert03](https://github.com/tlambert03))
- Make `npe2 convert` modify a repository [\#60](https://github.com/napari/npe2/pull/60) ([tlambert03](https://github.com/tlambert03))
- Delay import of `cmd.python_name` until needed [\#55](https://github.com/napari/npe2/pull/55) ([tlambert03](https://github.com/tlambert03))
- Add autogenerate\_from\_command field to Widget contribution [\#51](https://github.com/napari/npe2/pull/51) ([tlambert03](https://github.com/tlambert03))
- Update error messages [\#46](https://github.com/napari/npe2/pull/46) ([ppwadhwa](https://github.com/ppwadhwa))
- PackageMetadata field [\#44](https://github.com/napari/npe2/pull/44) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- add changelog generator config [\#65](https://github.com/napari/npe2/pull/65) ([tlambert03](https://github.com/tlambert03))
- Test conversion for all plugins [\#52](https://github.com/napari/npe2/pull/52) ([tlambert03](https://github.com/tlambert03))

**Refactors:**

- Start to make command APIs clearer [\#61](https://github.com/napari/npe2/pull/61) ([tlambert03](https://github.com/tlambert03))
- rename autogenerate field \(\#53\) [\#58](https://github.com/napari/npe2/pull/58) ([nclack](https://github.com/nclack))
- Schema review [\#49](https://github.com/napari/npe2/pull/49) ([nclack](https://github.com/nclack))

## [v0.1.0rc1](https://github.com/napari/npe2/tree/v0.1.0rc1) (2021-12-03)

[Full Changelog](https://github.com/napari/npe2/compare/v0.0.1rc1...v0.1.0rc1)

**Implemented enhancements:**

- add `get_callable` to Executable mixin [\#34](https://github.com/napari/npe2/pull/34) ([tlambert03](https://github.com/tlambert03))
- Sample data [\#31](https://github.com/napari/npe2/pull/31) ([tlambert03](https://github.com/tlambert03))
- support for Dock Widgets [\#26](https://github.com/napari/npe2/pull/26) ([tlambert03](https://github.com/tlambert03))
- Manifest cli [\#20](https://github.com/napari/npe2/pull/20) ([ppwadhwa](https://github.com/ppwadhwa))

**Tests & CI:**

- use pytomlpp, and test toml/json round trips [\#43](https://github.com/napari/npe2/pull/43) ([tlambert03](https://github.com/tlambert03))
- prep for release [\#42](https://github.com/napari/npe2/pull/42) ([tlambert03](https://github.com/tlambert03))

**Refactors:**

- Change 'publisher' to 'author' \(\#39\) [\#40](https://github.com/napari/npe2/pull/40) ([nclack](https://github.com/nclack))
- Cleanup manifest [\#38](https://github.com/napari/npe2/pull/38) ([nclack](https://github.com/nclack))

## [v0.0.1rc1](https://github.com/napari/npe2/tree/v0.0.1rc1) (2021-11-17)

[Full Changelog](https://github.com/napari/npe2/compare/cdbe96c3f0ea8c0e3ad050e91c24b40029cc0387...v0.0.1rc1)

**Implemented enhancements:**

- Small updates for napari [\#25](https://github.com/napari/npe2/pull/25) ([tlambert03](https://github.com/tlambert03))
- Add display\_name validation [\#23](https://github.com/napari/npe2/pull/23) ([nclack](https://github.com/nclack))
- Prevent extra fields in Commands. [\#15](https://github.com/napari/npe2/pull/15) ([Carreau](https://github.com/Carreau))
- More Validation. [\#14](https://github.com/napari/npe2/pull/14) ([Carreau](https://github.com/Carreau))
- Add debug to help diagnosing non-validation errors. [\#12](https://github.com/napari/npe2/pull/12) ([Carreau](https://github.com/Carreau))
- Add support for writer plugins [\#3](https://github.com/napari/npe2/pull/3) ([nclack](https://github.com/nclack))
- Some extra validation and allow to execute module with -m [\#1](https://github.com/napari/npe2/pull/1) ([Carreau](https://github.com/Carreau))

**Tests & CI:**

- Better pytest error on invalid schema. [\#11](https://github.com/napari/npe2/pull/11) ([Carreau](https://github.com/Carreau))
- Misc validation and testing. [\#5](https://github.com/napari/npe2/pull/5) ([Carreau](https://github.com/Carreau))
- Implement linting, CI, add basic tests [\#4](https://github.com/napari/npe2/pull/4) ([tlambert03](https://github.com/tlambert03))

**Refactors:**

- General refactor, Exectuable mixin, io\_utils APIs, remove some globals [\#18](https://github.com/napari/npe2/pull/18) ([tlambert03](https://github.com/tlambert03))
- Rename command command field to id. [\#10](https://github.com/napari/npe2/pull/10) ([Carreau](https://github.com/Carreau))
- Rename contributes to contributions ? [\#8](https://github.com/napari/npe2/pull/8) ([Carreau](https://github.com/Carreau))



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
