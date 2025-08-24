.PHONY: help setup install migrate test run clean lint format

help:
	@echo "Available commands:"
	@echo "  setup     - Create virtual environment and install dependencies"
	@echo "  install   - Install dependencies"
	@echo "  migrate   - Run database migrations"
	@echo "  test      - Run tests"
	@echo "  run       - Start development server"
	@echo "  celery    - Start Celery worker"
	@echo "  clean     - Clean up generated files"
	@echo "  lint      - Run linting"
	@echo "  format    - Format code"

setup:
	python -m venv venv
	./venv/bin/pip install -r requirements.txt

install:
	pip install -r requirements.txt

migrate:
	python manage.py makemigrations
	python manage.py migrate

test:
	python manage.py test

run:
	python manage.py runserver

celery:
	celery -A caseforge worker --loglevel=info

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf staticfiles

lint:
	flake8 .
	black --check .
	isort --check-only .

format:
	black .
	isort .