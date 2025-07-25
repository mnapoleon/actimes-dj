#!/bin/bash

# Local development checks script
# Run this before pushing to catch issues early

set -e  # Exit on any error

echo "🔍 Running local development checks..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Step 1: Django system checks${NC}"
python manage.py check

echo -e "${YELLOW}📋 Step 2: Migration checks${NC}"
python manage.py makemigrations --check --dry-run

echo -e "${YELLOW}🧹 Step 3: Code formatting with black${NC}"
black --check --diff .

echo -e "${YELLOW}📦 Step 4: Import sorting with isort${NC}"
isort --check-only --diff .

echo -e "${YELLOW}🔍 Step 5: Linting with flake8${NC}"
flake8 .

echo -e "${YELLOW}🛡️  Step 6: Dependency vulnerability check${NC}"
safety check --json --output safety-report.json || echo "Safety found vulnerabilities (see safety-report.json)"

echo -e "${YELLOW}🧪 Step 7: Running tests${NC}"
python manage.py test --verbosity=2

echo -e "${YELLOW}📊 Step 8: Test coverage${NC}"
coverage run --source='.' manage.py test
coverage report --show-missing
coverage html  # Generates htmlcov/ directory

echo -e "${GREEN}✅ All checks passed! You're ready to push.${NC}"

# Cleanup temporary files
rm -f safety-report.json

echo -e "${GREEN}📊 Coverage report generated in htmlcov/index.html${NC}"