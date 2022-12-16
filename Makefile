.PHONY: docs

docs:
	rm -rf docs/plugins
	python _docs/render.py
	rm -rf ./napari
	git clone --depth 1 --filter=blob:none --sparse -b update-plugin-docs https://github.com/tlambert03/napari.git
	(cd napari && git sparse-checkout set docs/plugins)
	cp napari/docs/plugins/* docs/plugins
	rm -rf ./napari
	jb build docs

# by default this will make a minor version bump (e.g v0.4.16 -> v0.4.17)
LAST := $(shell git tag -l | grep "v[0-9]+*" |  awk '!/rc/' | sort -V | tail -1)
SINCE := $(shell git log -1 -s --format=%cd --date=format:'%Y-%m-%d' $(LAST))
NEXT := $(shell echo $(LAST) | awk -F. -v OFS=. '{$$NF += 1 ; print}')
changelog:
	github_changelog_generator --future-release=$(NEXT) --since-commit=$(SINCE)
