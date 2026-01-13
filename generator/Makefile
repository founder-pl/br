.PHONY: install dev test lint format clean build docker run help

# Default target
help:
	@echo "BR Documentation Generator - Available commands:"
	@echo ""
	@echo "  make install    - Install package"
	@echo "  make dev        - Install with dev dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make build      - Build package"
	@echo "  make docker     - Build Docker image"
	@echo "  make run        - Run CLI help"
	@echo ""

# Install package
install:
	pip install -e .

# Install with dev dependencies
dev:
	pip install -e ".[dev]"

# Run tests
test:
	pytest tests/ -v --cov=br_doc_generator --cov-report=term-missing

# Run tests with coverage report
test-cov:
	pytest tests/ -v --cov=br_doc_generator --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

# Lint code
lint:
	ruff check src/ tests/
	mypy src/

# Format code
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build package
build: clean
	python -m build

# Build Docker image
docker:
	docker build -t br-doc-generator:latest .

# Run Docker with compose
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Run CLI
run:
	br-doc --help

# Generate example form
form:
	br-doc form --output projekt.yaml --name "Mój Projekt B+R"

# Validate example
validate:
	br-doc validate --input output/dokumentacja.md --levels all
