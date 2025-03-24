#!/bin/bash

# Set script to exit immediately if a command exits with a non-zero status
set -e

echo "🧪 Running tests with verbose output and timing information..."

# Run Django tests with verbose output and time-tracking
python manage.py test --verbosity=2 --timing --parallel=4

# Check if tests ran successfully
if [ $? -eq 0 ]; then
    echo "✅ All tests passed successfully!"
else
    echo "❌ Some tests failed."
    exit 1
fi
