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
