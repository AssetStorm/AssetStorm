SHELL := /bin/bash
export PYTHONUNBUFFERED := 1
export BASE := .
export PATH := $(shell echo $$PATH):$(BASE)/bin
export TZ := UTC

PYTHON_GLOBAL := $(shell /usr/bin/which python3.6)

PY_VERSION := 3.6

VENV_DIRNAME := ../env
VENV := $(BASE)/$(VENV_DIRNAME)

# The venv `python` executable.
PYTHON := $(VENV)/bin/python$(PY_VERSION)

# This is the command we use as `pip`. As this guy explains nicely, we don't use
# the `pip` binary directly:
# https://snarky.ca/why-you-should-use-python-m-pip/
PIP_COMMAND := $(PYTHON) -m pip
# This is the `pip` executable, which we need for `make` to see if it exists.
PIP := $(VENV)/bin/pip$(PY_VERSION)

PSERVE := $(VENV)/bin/pserve
PG_CONNECTION_PARAMS := --host=127.0.0.1 --port=5432 --dbname=assetstorm
PSQL := psql -P pager=off $(PG_CONNECTION_PARAMS)

.DEFAULT_GOAL := build


$(PIP): var
	@# as per `pyramid-cookiecutter-alchemy`: `$(PIP_COMMAND) install --upgrade`
	[ -f $(PIP) ] || \
	( \
		$(PYTHON_GLOBAL) -m venv $(VENV); \
		$(PIP_COMMAND) install --upgrade pip setuptools; \
	)


.PHONY: build
build: $(PIP) requirements.txt
	# for `brew` installed libxml2 to be found, we need some env vars
	LDFLAGS="-L/usr/local/opt/libxml2/lib" \
	CPPFLAGS="-I/usr/local/opt/libxml2/include" \
	PKG_CONFIG_PATH="/usr/local/opt/libxml2/lib/pkgconfig" \
		$(PIP_COMMAND) \
			--isolated \
			--disable-pip-version-check \
			install -r requirements.txt
	cd $(VENV)/bin/ && ln -sfn python$(PY_VERSION) python


.PHONY: dev.build
dev.build: build requirements.development.txt
	$(PIP_COMMAND) \
		--isolated \
		--disable-pip-version-check \
		install -r requirements.development.txt


.PHONY: dev.psql
dev.psql:
	PGPASSWORD=bar PGUSER=foo $(PSQL)


.PHONY: test
test:
    DEBUG=True $(VENV)/bin/python manage.py test AssetStorm
	# $(VENV)/bin/python AssetStorm/manage.py test AssetStorm



bin:
	mkdir -p "$(BASE)/bin"

var:
	mkdir -p "$(BASE)/var"

.PHONY: clean
clean: pyc-clean
	rm -rf \
		"$(VENV)"
