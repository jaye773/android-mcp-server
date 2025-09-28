# Contributing

Thanks for your interest in contributing to Android MCP Server! This guide will help you get set up and make effective contributions.

## Development Setup

- Requirements:
  - Python 3.11+
  - ADB (Android SDK Platform Tools)
  - An Android device or emulator with USB debugging enabled (optional for unit tests)

### Using uv (recommended)

```
uv sync --dev
```

### Using pip

```
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .[dev,test]
```

## Running Checks

```
pytest -v --asyncio-mode=auto
flake8 src tests
mypy src --ignore-missing-imports
black --check src tests
isort --check-only src tests
```

## Project Conventions

- Keep changes focused; avoid unrelated refactors in the same PR.
- Follow existing code style; prefer small, readable functions.
- Add or update tests when fixing bugs or adding features.
- Update documentation (README/docs) if behavior or interfaces change.

## Pull Requests

1. Fork and create a feature branch.
2. Make your changes with tests and docs updates.
3. Ensure CI checks pass locally.
4. Open a PR with a concise description, context, and screenshots/logs where helpful.

## Security

Do not include secrets in issues or PRs. If you believe you’ve found a security vulnerability, please open a minimal, anonymized issue describing the class of vulnerability and how to contact you privately.

## Releasing

Tags starting with `v*` trigger the release workflow. Coordinate with maintainers before tagging.

