.PHONY: setup clean lint test run install

PYTHON ?= python

setup:
	$(PYTHON) -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"

install:
	$(PYTHON) -m pip install -e .

clean:
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(pathlib.Path(p), ignore_errors=True) for p in ('build','dist','.pytest_cache','.ruff_cache')]"

lint:
	$(PYTHON) -m ruff check main.py tests scripts

test:
	$(PYTHON) -m pytest -q

run:
	$(PYTHON) main.py
