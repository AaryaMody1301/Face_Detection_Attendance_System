.PHONY: setup clean format lint test docs run install

setup:
	python -m venv venv
	venv\Scripts\pip install -e .

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

format:
	venv\Scripts\black src tests
	venv\Scripts\isort src tests

lint:
	venv\Scripts\flake8 src tests

test:
	venv\Scripts\pytest tests

docs:
	cd docs && venv\Scripts\sphinx-build -b html . _build

run:
	python main.py app

install:
	venv\Scripts\pip install -e .

app:
	python main.py app

train:
	python main.py train

take:
	python main.py take $(subject)

view:
	python main.py view

help:
	@echo "Available commands:"
	@echo "  setup      Create virtual environment and install dependencies"
	@echo "  clean      Remove build artifacts"
	@echo "  format     Format code with black and isort"
	@echo "  lint       Check code with flake8"
	@echo "  test       Run tests with pytest"
	@echo "  docs       Build documentation"
	@echo "  run        Run the application"
	@echo "  install    Install the package in development mode"
	@echo "  app        Run the GUI application"
	@echo "  train      Train the face recognition model"
	@echo "  take       Take attendance for a subject (use subject=SUBJECT_NAME)"
	@echo "  view       View attendance records" 