.PHONY: setup clean lint test run install diagnostics package package-smoke

PYTHON ?= python

setup:
	$(PYTHON) -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"

install:
	$(PYTHON) -m pip install -e .

clean:
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(pathlib.Path(p), ignore_errors=True) for p in ('build','dist','release','.pytest_cache','.ruff_cache')]"

lint:
	$(PYTHON) -m ruff check main.py tests scripts src/core/camera.py src/core/runtime.py src/core/paths.py

test:
	$(PYTHON) -m pytest -q

diagnostics:
	$(PYTHON) main.py --diagnostics

package:
	$(PYTHON) -m PyInstaller --clean --noconfirm face_attendance.spec

package-smoke: package
	$(PYTHON) scripts/smoke_package.py

run:
	$(PYTHON) main.py
