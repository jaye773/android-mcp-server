#!/usr/bin/env python3
"""Simple test runner for Android MCP Server."""

import sys
import subprocess
import os
from pathlib import Path


def main():
    """Run the test suite with basic validation."""
    project_root = Path(__file__).parent
    os.chdir(project_root)

    print("🧪 Android MCP Server Test Suite")
    print("=" * 50)

    # Check if pytest is available
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__} available")
    except ImportError:
        print("❌ pytest not available. Install with: pip install pytest pytest-asyncio")
        sys.exit(1)

    # Check test directory structure
    tests_dir = project_root / "tests"
    if not tests_dir.exists():
        print("❌ tests/ directory not found")
        sys.exit(1)

    test_files = list(tests_dir.glob("test_*.py"))
    print(f"✅ Found {len(test_files)} test files:")
    for test_file in sorted(test_files):
        print(f"   • {test_file.name}")

    # Check mock infrastructure
    mocks_dir = tests_dir / "mocks"
    if mocks_dir.exists():
        print(f"✅ Mock infrastructure available")
    else:
        print("⚠️  Mock infrastructure not found")

    # Run syntax validation
    print("\n🔍 Validating test file syntax...")
    syntax_errors = 0

    for test_file in test_files:
        try:
            with open(test_file, 'r') as f:
                compile(f.read(), test_file, 'exec')
            print(f"   ✅ {test_file.name}")
        except SyntaxError as e:
            print(f"   ❌ {test_file.name}: {e}")
            syntax_errors += 1

    if syntax_errors > 0:
        print(f"\n❌ {syntax_errors} files have syntax errors")
        return False

    print(f"\n✅ All {len(test_files)} test files have valid syntax")

    # Check conftest.py
    conftest_file = tests_dir / "conftest.py"
    if conftest_file.exists():
        try:
            with open(conftest_file, 'r') as f:
                compile(f.read(), conftest_file, 'exec')
            print("✅ conftest.py syntax valid")
        except SyntaxError as e:
            print(f"❌ conftest.py syntax error: {e}")
            return False
    else:
        print("⚠️  conftest.py not found")

    # Basic import validation
    print("\n📦 Validating imports...")
    sys.path.insert(0, str(project_root))

    try:
        from tests.mocks import MockADBCommand
        print("✅ Mock infrastructure imports successfully")
    except ImportError as e:
        print(f"⚠️  Mock infrastructure import issue: {e}")

    # Test discovery
    print(f"\n🔍 Testing pytest discovery...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "--collect-only", "-q", "tests/"
        ], capture_output=True, text=True, cwd=project_root)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            collected = [line for line in lines if 'collected' in line]
            if collected:
                print(f"✅ {collected[-1]}")
            else:
                print("✅ Test discovery completed")
        else:
            print(f"⚠️  Test discovery issues:")
            print(result.stderr)
    except Exception as e:
        print(f"⚠️  Could not run test discovery: {e}")

    print("\n📊 Test Infrastructure Summary:")
    print(f"   • Test files: {len(test_files)}")
    print(f"   • Mock infrastructure: {'✅' if mocks_dir.exists() else '❌'}")
    print(f"   • Configuration: {'✅' if (project_root / 'pytest.ini').exists() else '❌'}")
    print(f"   • CI/CD pipeline: {'✅' if (project_root / '.github' / 'workflows').exists() else '❌'}")

    print(f"\n🎉 Test infrastructure validation complete!")
    print(f"💡 To run tests: python -m pytest tests/ -v")
    print(f"💡 For coverage: python -m pytest tests/ --cov=src --cov-report=term-missing")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)