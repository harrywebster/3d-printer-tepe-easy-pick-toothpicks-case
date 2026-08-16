# One command per revision:
#
#     make v14
#
# builds src/geom14.py and ships it. Everything shipped is produced by
# src/build.py; this file only creates the venv, runs that one script, and
# hands its output to src/ship.py to copy. Nothing here generates a
# deliverable, so the pictures and the printable files cannot come from
# different models.

PYTHON ?= python3
VENV   := .venv
PY     := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip
BUILD  := build

.DEFAULT_GOAL := help

help:
	@echo "make v14         build geom14, ship to revisions/v14 and the root aliases"
	@echo "make build-v14   build into $(BUILD)/v14 only, ship nothing"
	@echo "make deps        create $(VENV) and install the pinned requirements"
	@echo "make verify      rebuild the current revision and diff it against what is shipped"
	@echo "make clean       remove $(BUILD)/"
	@echo ""
	@echo "Shipping refuses to overwrite an existing revisions/vNN."
	@echo "Pass FORCE=1 only if you really mean to replace a released revision."

$(VENV)/bin/python:
	$(PYTHON) -m venv $(VENV)

deps: $(VENV)/bin/python requirements.txt
	@$(PIP) install --quiet --upgrade pip
	@$(PIP) install --quiet -r requirements.txt
	@echo "dependencies installed into $(VENV)"

# Build only — leaves revisions/ and the root aliases untouched.
build-v%: deps
	@echo "$*" | grep -qE '^[0-9]+$$' || { \
	  echo "usage: make vNN  (e.g. make v14)"; exit 1; }
	@test -f src/geom$*.py || { \
	  echo "src/geom$*.py does not exist."; \
	  echo "CLAUDE.md step 1: copy the previous geometry module to it and change"; \
	  echo "the parameters there. Never edit a released revision in place."; \
	  exit 1; }
	EASYPICK_OUT=$(BUILD)/v$* $(PY) src/build.py geom$* v$*

# Build, then copy into revisions/vNN and refresh the root aliases.
v%: build-v%
	@$(PY) src/ship.py v$* $(if $(FORCE),--force,)

# Rebuild whatever the root currently ships and diff it, without shipping
# anything. Use this to confirm a checkout still reproduces its own output.
verify: deps
	@$(PY) src/verify.py

clean:
	rm -rf $(BUILD)

.PHONY: help deps verify clean
