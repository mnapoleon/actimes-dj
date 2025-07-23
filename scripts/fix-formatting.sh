#!/bin/bash

# Auto-fix formatting issues
# Run this to automatically fix most linting issues

echo "🔧 Auto-fixing code formatting..."

echo "📝 Running black formatter..."
black .

echo "📦 Fixing import sorting..."
isort .

echo "✅ Formatting fixes applied!"
echo "Run './scripts/run-checks.sh' to verify all issues are resolved."