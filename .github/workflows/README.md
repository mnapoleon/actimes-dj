# GitHub Actions Workflows

This directory contains automated CI/CD workflows for the Assetto Corsa Lap Times Django application.

## Workflows

### 1. PR Tests (`pr-tests.yml`)
**Triggers:** Pull requests to `main` branch  
**Purpose:** Fast feedback for pull requests

**Steps:**
- ✅ Checkout code
- ✅ Set up Python 3.11 environment  
- ✅ Install dependencies from `requirements.txt`
- ✅ Run Django system checks
- ✅ Verify no pending migrations
- ✅ Apply database migrations
- ✅ Run all tests (currently 52 tests)
- ✅ Verify test count meets minimum threshold (50+ tests)
- ✅ Run duplicate file prevention tests specifically

### 2. Django Tests (`django-tests.yml`)
**Triggers:** Pull requests and pushes to `main` branch  
**Purpose:** Comprehensive testing across multiple Python versions

**Features:**
- **Multi-Python Testing:** Tests against Python 3.9, 3.10, 3.11, 3.12
- **Caching:** Pip dependency caching for faster builds
- **Coverage:** Code coverage reporting (Python 3.11 only)
- **Linting:** Code quality checks with flake8, black, isort
- **Security:** Vulnerability scanning with safety and bandit

## Test Requirements

For PRs to pass CI, they must:
- ✅ Pass all existing tests (52+ tests)
- ✅ Have no Django system check issues
- ✅ Have no pending migrations
- ✅ Pass duplicate file prevention specific tests
- ✅ Maintain or increase test coverage

## Local Testing

To run the same checks locally before pushing:

```bash
# System checks
python manage.py check

# Migration checks  
python manage.py makemigrations --check --dry-run

# Run all tests
python manage.py test --verbosity=2

# Run specific test suites
python manage.py test laptimes.tests.DuplicateFileTests
python manage.py test laptimes.tests.AdminInterfaceTests

# Count tests
python manage.py test --verbosity=0 2>&1 | grep "Ran.*test"
```

## Workflow Status

Both workflows will show status badges in pull requests, providing immediate feedback on:
- ✅ All tests passing
- ❌ Test failures with detailed logs
- ⚠️ Warnings for low test coverage or code quality issues

This ensures code quality and prevents regressions before merging to the main branch.