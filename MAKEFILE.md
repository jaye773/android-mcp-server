# Makefile Usage Guide

The Android MCP Server includes a comprehensive Makefile that exactly replicates GitHub Actions CI workflows for local development.

## Quick Start

```bash
# Show all available commands
make help

# Run EXACT same checks as GitHub CI (on push to main/develop)
make push-checks

# Run all checks with clean (same as push-checks but cleans first)
make all

# Quick validation (basic checks only)
make all-quick

# Auto-fix code issues and run CI checks
make pre-commit

# Run tests only (with 80% coverage requirement)
make test

# Fix code formatting
make fix
```

## Main Commands

### `make push-checks` (IMPORTANT: Matches GitHub CI)
Runs the EXACT same checks that GitHub Actions runs when you push to main/develop:
1. Installs dependencies (with pip upgrade)
2. Runs flake8 syntax checks (E9,F63,F7,F82)
3. Runs flake8 style checks (all rules)
4. Runs pydocstyle with Google convention
5. Runs pytest with 80% coverage requirement

**This is what you should run before pushing to ensure CI will pass.**

### `make all`
Same as `push-checks` but cleans build artifacts first. Use this for a completely fresh validation.

### `make all-quick`
A faster version for iterative development:
- Basic flake8 checks (errors only)
- Documentation style checks
- Quick tests (no slow/performance tests)
- No installation step

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
make push-checks   # EXACT GitHub Actions CI checks (use before push!)
make ci            # Alias for push-checks
make ci-quick      # Quick CI checks (no install)
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

### Before Push/Pull Request
```bash
make push-checks  # Run exact GitHub CI checks
# or
make all          # Same with clean first
git push
```

### Debugging Test Failures
```bash
make test-unit -v    # Verbose unit tests
make test-coverage   # Check coverage gaps
open htmlcov/index.html
```