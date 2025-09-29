# Makefile Usage Guide

The Android MCP Server includes a comprehensive Makefile that replicates all GitHub workflow functions for local development.

## Quick Start

```bash
# Show all available commands
make help

# Run all checks and tests (comprehensive)
make all

# Quick validation (no installation or slow tests)
make all-quick

# Auto-fix code issues and validate
make pre-commit

# Run tests only
make test

# Fix code formatting
make fix
```

## Main Commands

### `make all`
Runs the complete validation suite:
1. Cleans build artifacts
2. Installs development dependencies
3. Runs all code quality checks (format, lint, typecheck, imports, docstrings)
4. Runs all tests with 80% coverage requirement
5. Runs security scans

Use this before pushing to ensure CI will pass.

### `make all-quick`
A faster version for iterative development:
- Skips installation
- Runs code quality checks
- Runs tests (excluding slow and performance tests)
- Skips security scans

## Testing Commands

```bash
make test              # All tests with coverage
make test-quick        # Fast tests only
make test-unit         # Unit tests only
make test-integration  # Integration tests
make test-e2e          # End-to-end tests
make test-performance  # Performance tests
make test-slow         # Slow tests only
make test-coverage     # Generate HTML coverage report
```

## Code Quality

```bash
make code-quality   # Run all quality checks
make lint          # Run flake8 linting
make format        # Format with black
make typecheck     # Run mypy type checking
make isort         # Sort imports
make docstyle      # Check docstring style
make fix           # Auto-fix formatting and imports
```

## Development Workflow

```bash
# Initial setup
make dev-setup

# Before committing
make check         # Quick validation
make pre-commit    # Fix and validate

# Full validation
make all

# Clean everything
make clean
```

## CI/CD Commands

```bash
make ci            # Run full CI pipeline
make ci-quick      # Quick CI checks
make release-check # Verify release readiness
make build         # Build distribution packages
```

## Security

```bash
make security      # Run bandit and safety scans
```

## Utilities

```bash
make version       # Show current version
make deps-check    # Check for outdated packages
make deps-tree     # Show dependency tree
make clean         # Clean build artifacts
make clean-all     # Deep clean (including venvs)
```

## GitHub Actions Compatibility

The Makefile includes targets that match the GitHub Actions matrix:
- `make test-matrix-ubuntu`
- `make test-matrix-macos`
- `make test-matrix-windows`

## Tips

1. **Pre-commit Hook**: Add `make pre-commit` to your git pre-commit hook
2. **Watch Mode**: Use `make watch-tests` for TDD development
3. **Coverage Report**: Run `make test-coverage` and open `htmlcov/index.html`
4. **Quick Iteration**: Use `make all-quick` during development, `make all` before pushing

## Common Workflows

### Starting Development
```bash
git clone <repo>
cd android-mcp-server
make dev-setup
make test
```

### Making Changes
```bash
# Edit files...
make fix          # Auto-fix formatting
make check        # Validate changes
git add .
git commit
```

### Before Pull Request
```bash
make all          # Full validation
git push
```

### Debugging Test Failures
```bash
make test-unit -v    # Verbose unit tests
make test-coverage   # Check coverage gaps
open htmlcov/index.html
```