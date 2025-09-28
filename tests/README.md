# Android MCP Server Test Suite

Comprehensive testing infrastructure for the Android MCP Server project.

## Overview

This test suite provides comprehensive coverage of all major components without requiring physical Android devices. All tests use mock infrastructure to simulate Android device interactions.

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_adb_manager.py      # ADB device management tests
├── test_server.py           # MCP server functionality tests
├── test_validation.py       # Input validation system tests
├── test_error_handler.py    # Error handling system tests
├── test_ui_inspector.py     # UI layout extraction tests
├── test_integration.py      # Integration and E2E tests
├── mocks/                   # Mock infrastructure
│   ├── __init__.py
│   └── adb_mock.py         # Mock ADB commands and responses
├── data/                    # Test data and fixtures
│   └── sample_ui_dumps.py   # Sample UI XML dumps
└── README.md               # This file
```

## Test Categories

### Unit Tests
- **test_adb_manager.py**: Device discovery, command execution, error handling
- **test_validation.py**: Input sanitization, security validation, parameter checking
- **test_error_handler.py**: Error categorization, recovery suggestions, statistics
- **test_ui_inspector.py**: UI layout parsing, element finding, hierarchy extraction

### Integration Tests
- **test_integration.py**: Component interaction, workflow validation, error propagation
- **test_server.py**: MCP tool functions, parameter validation, component coordination

### End-to-End Tests
- Complete automation workflows (login, navigation, form filling)
- Error recovery scenarios
- Performance integration tests

## Mock Infrastructure

### ADB Mock System
- **MockADBCommand**: Simulates realistic ADB command execution
- **MockDeviceScenarios**: Predefined device states (healthy, offline, slow)
- **MockUIScenarios**: Sample UI dumps from different screen types
- **MockErrorScenarios**: Common error conditions and edge cases

### Test Fixtures
- Pre-configured mock components for all major classes
- Realistic test data based on actual Android device responses
- Temporary directories for file operations
- Sample UI dumps from real applications

## Running Tests

### Basic Test Execution
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_adb_manager.py -v

# Run tests by category
python -m pytest tests/ -v -m unit
python -m pytest tests/ -v -m integration
python -m pytest tests/ -v -m e2e
```

### With Coverage
```bash
# Generate coverage report
python -m pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML coverage report
python -m pytest tests/ --cov=src --cov-report=html:htmlcov

# Fail if coverage below 80%
python -m pytest tests/ --cov=src --cov-fail-under=80
```

### Performance Tests
```bash
# Run performance tests
python -m pytest tests/ -v -m performance

# Skip slow tests for faster feedback
python -m pytest tests/ -v -m "not slow"
```

### Parallel Execution
```bash
# Run tests in parallel (requires pytest-xdist)
python -m pytest tests/ -n auto

# Run on specific number of cores
python -m pytest tests/ -n 4
```

## Test Markers

Tests are categorized with pytest markers:

- `unit`: Unit tests that don't require external dependencies
- `integration`: Integration tests with mocked external services
- `e2e`: End-to-end tests requiring full system
- `slow`: Tests that take significant time to run
- `device`: Tests that would require actual Android device (mocked in CI)
- `adb`: Tests involving ADB operations
- `ui`: Tests for UI interaction functionality
- `media`: Tests for media capture functionality
- `validation`: Tests for input validation system
- `error_handling`: Tests for error handling system
- `performance`: Performance-related tests

## Dependencies

Required test dependencies (automatically installed with `pip install -e ".[test]"`):

- **pytest>=8.0.0**: Test framework
- **pytest-asyncio>=0.23.0**: Async test support
- **pytest-cov>=4.1.0**: Coverage reporting
- **pytest-mock>=3.12.0**: Enhanced mocking capabilities
- **pytest-xdist>=3.5.0**: Parallel test execution
- **coverage>=7.4.0**: Coverage measurement

## Configuration

### pytest.ini
- Test discovery patterns
- Coverage configuration
- Async mode settings
- Test markers definition
- Coverage exclusion rules

### Async Testing
All async functions are automatically handled with `--asyncio-mode=auto` configuration.

## Mock Infrastructure Details

### Device Simulation
```python
# Healthy device scenario
device = MockDeviceScenarios.healthy_device()
# Returns: battery=85%, storage=2GB, responsive

# Offline device scenario
device = MockDeviceScenarios.offline_device()
# Returns: status="offline", error message
```

### UI Simulation
```python
# Login screen with username/password fields
ui_dump = MockUIScenarios.login_screen()

# Scrollable list with multiple items
ui_dump = MockUIScenarios.scrollable_list()

# Complex nested UI hierarchy
ui_dump = MockUIScenarios.complex_nested()
```

### Command Simulation
```python
# Execute mock ADB command
result = await MockADBCommand.execute_command(
    "adb shell input tap 100 200",
    timeout=10,
    device_id="emulator-5554"
)
# Returns realistic response with proper timing simulation
```

## CI/CD Integration

### GitHub Actions Workflows

#### Test Suite (`.github/workflows/test.yml`)
- Multi-platform testing (Ubuntu, macOS, Windows)
- Multiple Python versions (3.11, 3.12)
- Code quality checks (flake8, mypy)
- Coverage reporting to Codecov
- Integration and E2E test suites
- Security scanning (bandit, safety)
- Performance benchmarks

#### Code Quality (`.github/workflows/code-quality.yml`)
- Code formatting (black)
- Import sorting (isort)
- Linting (flake8)
- Type checking (mypy)
- Documentation style (pydocstyle)

#### Release Pipeline (`.github/workflows/release.yml`)
- Full test suite validation
- Package building and validation
- Automated GitHub releases
- PyPI publishing

### Test Execution Strategy
1. **Fast feedback**: Unit tests run on every push/PR
2. **Comprehensive validation**: Integration tests on main branch
3. **Performance monitoring**: Performance tests on releases
4. **Security validation**: Security scans on all changes

## Coverage Goals

- **Overall Coverage**: ≥80% (enforced by CI)
- **Unit Test Coverage**: ≥85% for core modules
- **Integration Coverage**: ≥75% for workflows
- **Mock Coverage**: 100% (all mocks should be tested)

### Coverage Exclusions
- Test files themselves
- Development utilities
- Third-party integrations
- Abstract base classes
- Debug/development code

## Best Practices

### Writing Tests
1. **Use descriptive test names**: `test_device_selection_with_invalid_device_id`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Mock external dependencies**: Never rely on actual Android devices
4. **Test edge cases**: Include error conditions and boundary values
5. **Use fixtures**: Reuse common test setups via conftest.py

### Mock Usage
1. **Realistic responses**: Mock data should match real device behavior
2. **Proper timing**: Include realistic delays in async operations
3. **Error scenarios**: Test both success and failure paths
4. **State simulation**: Mock stateful interactions appropriately

### Async Testing
1. **Use pytest.mark.asyncio**: Mark async tests properly
2. **Await all async calls**: Don't forget await keywords
3. **Mock async functions**: Use AsyncMock for async dependencies
4. **Handle timeouts**: Test timeout scenarios appropriately

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# If you see import errors, ensure the project is installed
pip install -e ".[test]"

# Or add the project root to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/android-mcp-server"
```

#### Async Test Issues
```bash
# Make sure pytest-asyncio is installed and configured
pip install pytest-asyncio

# Check pytest.ini has asyncio_mode = auto
```

#### Coverage Issues
```bash
# Generate detailed coverage report
python -m pytest tests/ --cov=src --cov-report=html:htmlcov
open htmlcov/index.html  # View detailed report
```

#### Performance Test Failures
```bash
# Skip performance tests during development
python -m pytest tests/ -v -m "not performance"

# Run performance tests with verbose output
python -m pytest tests/ -v -m performance -s
```

### Debug Mode
```bash
# Run tests with debug output
python -m pytest tests/ -v -s --tb=long

# Run specific test with debugging
python -m pytest tests/test_adb_manager.py::TestADBManager::test_list_devices_success -v -s
```

## Contributing

### Adding New Tests
1. Follow existing naming conventions
2. Add appropriate test markers
3. Include both success and failure cases
4. Update fixtures if needed
5. Maintain test documentation

### Updating Mocks
1. Keep mocks synchronized with real device behavior
2. Add new scenarios for edge cases
3. Validate mock responses match actual device output
4. Update documentation when adding new mock capabilities

### Performance Considerations
1. Use `@pytest.mark.performance` for slow tests
2. Consider using `pytest-benchmark` for precise timing
3. Mock expensive operations appropriately
4. Profile test execution for bottlenecks

---

For questions or issues with the test infrastructure, please check the project's issue tracker or contribute improvements via pull requests.