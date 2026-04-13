SHELL := /bin/sh

MYST_PROJECT_DIR := manuscript
MYST := myst

.PHONY: help check-myst check-scaffold build-html start clean
.PHONY: build-figures build-tables build-phase2 check-phase2

help:
	@printf '%s\n' \
		'Available targets:' \
		'  check-scaffold  Validate required repo scaffold paths' \
		'  build-figures   Build example Phase 2 figures and source-data exports' \
		'  build-tables    Build example Phase 2 table outputs' \
		'  build-phase2    Build figures and tables, then validate generated artifacts' \
		'  check-phase2    Validate generated figure and table artifacts' \
		'  build-html      Build static MyST HTML in manuscript/_build/html' \
		'  start           Start the MyST local preview server' \
		'  clean           Remove MyST build artifacts'

check-myst:
	@command -v $(MYST) >/dev/null 2>&1 || { \
		echo "myst is not installed. Install with: python3 -m pip install -r env/requirements-myst.txt"; \
		exit 1; \
	}

check-scaffold:
	@python3 scripts/check_scaffold.py

build-figures: check-scaffold
	python3 figures/src/build_example_figure.py

build-tables: check-scaffold
	python3 tables/src/build_main_table.py

check-phase2:
	@python3 scripts/check_generated_artifacts.py

build-phase2: build-figures build-tables check-phase2

build-html: check-myst check-scaffold
	cd $(MYST_PROJECT_DIR) && $(MYST) build --html

start: check-myst check-scaffold
	cd $(MYST_PROJECT_DIR) && $(MYST) start

clean: check-myst
	rm -rf $(MYST_PROJECT_DIR)/_build
