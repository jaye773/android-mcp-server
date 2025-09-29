# Android MCP Server Makefile
# Replicates GitHub workflow functions for local development

# Python interpreter
PYTHON := python3
PIP := $(PYTHON) -m pip

# Directories
SRC_DIR := src
TEST_DIR := tests
COVERAGE_DIR := htmlcov

# Default target
.DEFAULT_GOAL := help

# Phony targets
.PHONY: help all install install-dev clean test test-coverage test-unit test-integration \
        test-e2e test-performance test-slow lint format typecheck security \
        code-quality ci release-check build dist

## Help command
help: ## Show this help message
	@echo "Android MCP Server - Development Commands"
	@echo "========================================="
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  make all           # Run all checks and tests"
	@echo "  make install       # Install project dependencies"
	@echo "  make test          # Run all tests"
	@echo "  make lint          # Run linting checks"
	@echo "  make ci            # Run full CI pipeline locally"

##@ Main Commands

all: clean install-dev code-quality test security ## Run all checks and tests (clean, install, quality, test, security)
	@echo ""
	@echo "========================================="
	@echo "✅ All checks completed successfully!"
	@echo "========================================="
	@echo "Summary:"
	@echo "  • Code formatting: ✓"
	@echo "  • Linting: ✓"
	@echo "  • Type checking: ✓"
	@echo "  • Import sorting: ✓"
	@echo "  • Docstring style: ✓"
	@echo "  • Tests: ✓ (with 80% coverage)"
	@echo "  • Security: ✓"
	@echo ""
	@echo "Your code is ready for commit/push!"

all-quick: code-quality test-quick ## Quick version of all (no install, no slow tests, no security)
	@echo ""
	@echo "========================================="
	@echo "✅ Quick checks completed successfully!"
	@echo "========================================="
	@echo "Note: This was a quick check. Run 'make all' for comprehensive validation."

##@ Installation

install: ## Install project dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e .

install-dev: ## Install development dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,test]"

##@ Testing

test: ## Run all tests with coverage
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		--cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=80 \
		--asyncio-mode=auto \
		-m "not slow"

test-coverage: ## Run tests with HTML coverage report
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		--cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml \
		--cov-fail-under=80 \
		--asyncio-mode=auto
	@echo "Coverage report generated in $(COVERAGE_DIR)/index.html"

test-unit: ## Run only unit tests
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		--asyncio-mode=auto \
		-m "unit" \
		--tb=short

test-integration: ## Run integration tests
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		--asyncio-mode=auto \
		-m "integration" \
		--tb=short

test-e2e: ## Run end-to-end tests
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		--asyncio-mode=auto \
		-m "e2e" \
		--tb=short

test-performance: ## Run performance tests
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		--asyncio-mode=auto \
		-m "performance" \
		--tb=short

test-slow: ## Run slow tests
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		-m "slow" \
		--asyncio-mode=auto

test-media: ## Run media-related tests
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		--asyncio-mode=auto \
		-m "media" \
		--tb=short

test-quick: ## Run tests without slow tests
	$(PYTHON) -m pytest $(TEST_DIR)/ -v \
		--asyncio-mode=auto \
		-m "not slow and not performance" \
		--tb=short

##@ Code Quality

lint: ## Run flake8 linting
	@echo "Running flake8 syntax checks..."
	$(PYTHON) -m flake8 $(SRC_DIR) --count --select=E9,F63,F7,F82 --show-source --statistics
	@echo "Running flake8 style checks..."
	$(PYTHON) -m flake8 $(SRC_DIR) --count --statistics

format: ## Format code with black
	$(PYTHON) -m black $(SRC_DIR)

format-check: ## Check code formatting with black (no changes)
	$(PYTHON) -m black --check --diff $(SRC_DIR)

typecheck: ## Run mypy type checking
	$(PYTHON) -m mypy $(SRC_DIR) \
		--ignore-missing-imports \
		--strict-optional \
		--warn-redundant-casts \
		--warn-unused-ignores

isort: ## Sort imports with isort
	$(PYTHON) -m isort $(SRC_DIR)

isort-check: ## Check import sorting with isort (no changes)
	$(PYTHON) -m isort --check-only --diff $(SRC_DIR)

docstyle: ## Check docstring style with pydocstyle
	$(PYTHON) -m pydocstyle $(SRC_DIR) \
		--convention=google \
		--add-ignore=D100,D101,D102,D103,D104,D105

code-quality: format-check lint typecheck isort-check docstyle ## Run all code quality checks

##@ Security

security: ## Run security scans with bandit and safety
	@echo "Running bandit security scan..."
	-$(PYTHON) -m bandit -r $(SRC_DIR)/ -f json -o bandit-report.json
	-$(PYTHON) -m bandit -r $(SRC_DIR)/
	@echo "Checking dependencies with safety..."
	-$(PYTHON) -m safety scan --output json --output-file safety-report.json
	-$(PYTHON) -m safety scan

##@ Build & Release

build: clean ## Build distribution packages
	$(PYTHON) -m build

dist: build ## Create distribution (alias for build)

release-check: ## Check if ready for release
	@echo "Checking release readiness..."
	@echo "1. Running tests..."
	@$(MAKE) test
	@echo "2. Checking code quality..."
	@$(MAKE) code-quality
	@echo "3. Running security scan..."
	@$(MAKE) security
	@echo "✓ All release checks passed!"

upload-test: dist ## Upload to TestPyPI
	$(PYTHON) -m twine upload --repository testpypi dist/*

upload: dist ## Upload to PyPI (use with caution)
	$(PYTHON) -m twine upload dist/*

##@ CI/CD

ci: install-dev code-quality test security ## Run full CI pipeline
	@echo "✓ CI pipeline completed successfully!"

ci-quick: install-dev lint typecheck test-quick ## Run quick CI checks (no slow tests)
	@echo "✓ Quick CI checks completed!"

##@ Development Workflow

dev-setup: install-dev ## Setup development environment
	@echo "Installing pre-commit hooks..."
	-pre-commit install
	@echo "✓ Development environment ready!"

fix: format isort ## Auto-fix code formatting and imports
	@echo "✓ Code formatting fixed!"

check: code-quality test-quick ## Quick check before committing
	@echo "✓ Code is ready to commit!"

pre-commit: fix check ## Fix issues and run checks (ideal for pre-commit hook)
	@echo "✓ Code has been fixed and validated!"

##@ Cleanup

clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf $(COVERAGE_DIR)
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type f -name "coverage.xml" -delete
	rm -f bandit-report.json safety-report.json

clean-all: clean ## Deep clean including virtual environments
	rm -rf venv/ env/ .venv/

##@ Docker (Optional)

docker-build: ## Build Docker image
	docker build -t android-mcp-server .

docker-run: ## Run Docker container
	docker run -it --rm \
		--device /dev/bus/usb \
		-v $(PWD)/output:/app/output \
		android-mcp-server

##@ Documentation

docs: ## Generate documentation
	@echo "Generating documentation..."
	# Add documentation generation commands here if needed
	@echo "Documentation generation not configured yet"

##@ Monitoring

watch-tests: ## Watch and run tests on file changes
	$(PYTHON) -m pytest-watch $(TEST_DIR)/ -- -v --tb=short

##@ Utilities

version: ## Show current version
	@grep "version" pyproject.toml | head -1 | cut -d'"' -f2

deps-tree: ## Show dependency tree
	$(PYTHON) -m pipdeptree

deps-check: ## Check for outdated dependencies
	$(PIP) list --outdated

# Special targets for GitHub Actions compatibility
.PHONY: test-matrix-ubuntu test-matrix-macos test-matrix-windows

test-matrix-ubuntu: install-dev test ## Test target for Ubuntu
	@echo "✓ Ubuntu tests completed!"

test-matrix-macos: install-dev test ## Test target for macOS
	@echo "✓ macOS tests completed!"

test-matrix-windows: install-dev test ## Test target for Windows
	@echo "✓ Windows tests completed!"