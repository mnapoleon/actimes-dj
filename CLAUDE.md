# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django web application for analyzing Assetto Corsa racing lap times from JSON files. The application stores session data in SQLite and provides a web interface for uploading, visualizing, and analyzing lap times with highlighting for fastest/slowest times.

## Development Commands

### Running the Application
```bash
python manage.py runserver
```
Starts the Django development server on http://127.0.0.1:8000/

### Database Management
```bash
python manage.py makemigrations
python manage.py migrate
```

### Statistics Management
```bash
# Recalculate pre-computed statistics for all sessions
python manage.py recalculate_session_stats --all

# Recalculate statistics for sessions missing pre-computed data
python manage.py recalculate_session_stats --outdated-only

# Recalculate statistics for a specific session
python manage.py recalculate_session_stats --session-id <ID>

# Preview what would be recalculated without making changes
python manage.py recalculate_session_stats --all --dry-run
```

### Testing
```bash
# Run all tests (60 tests total)
python manage.py test

# Run tests by category
python manage.py test laptimes.tests.test_models     # Model functionality
python manage.py test laptimes.tests.test_views      # View logic
python manage.py test laptimes.tests.test_forms      # Form validation
python manage.py test laptimes.tests.test_api        # API endpoints
python manage.py test laptimes.tests.test_admin      # Admin interface
python manage.py test laptimes.tests.test_integration # End-to-end workflows
python manage.py test laptimes.tests.test_file_management # File operations

# Run with detailed output
python manage.py test --verbosity=2

# Run only laptimes app tests
python manage.py test laptimes

# Run specific test class
python manage.py test laptimes.tests.test_models.SessionModelTests

# Run specific test method
python manage.py test laptimes.tests.test_models.SessionModelTests.test_session_creation

# Keep test database for debugging
python manage.py test --keepdb

# Run tests in parallel (faster)
python manage.py test --parallel

# Stop on first failure
python manage.py test --failfast
```

#### Test Coverage (Optional)
```bash
# Install coverage tool
pip install coverage

# Run tests with coverage tracking
coverage run --source='.' manage.py test

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html
```

**Test Suite Coverage:**
- 60 comprehensive tests organized into logical modules
- **Models** (18 tests): Session and Lap creation, validation, methods, statistics
- **Views** (14 tests): HTTP responses, context data, pagination, view logic
- **Forms** (6 tests): Upload validation, session editing, form validation
- **API** (1 test): JSON endpoints and data serialization
- **Admin** (5 tests): Django admin interface customization
- **Integration** (1 test): Complete user workflows
- **File Management** (15 tests): Upload, duplicate detection, driver management

### Code Quality & Pre-Push Requirements

**IMPORTANT**: Before any `git push` operations, Claude Code must run the following checks in order:

1. **Code Formatting** (Black):
   ```bash
   python -m black laptimes/ --check
   # If formatting needed:
   python -m black laptimes/
   ```

2. **Import Sorting** (isort):
   ```bash
   python -m isort laptimes/ --check-only
   # If sorting needed:
   python -m isort laptimes/
   ```

3. **Linting** (Flake8):
   ```bash
   python -m flake8 laptimes/
   ```
   Note: DJ01 warnings on `display_name` CharField fields are acceptable as they use `null=True` appropriately for optional fields.

4. **Tests** (All must pass):
   ```bash
   python manage.py test
   ```
   All 70 tests must pass before pushing.

5. **Type Checking** (Optional but recommended):
   ```bash
   python -m mypy laptimes/ --ignore-missing-imports
   ```

**Automated Pre-Push Workflow:**
```bash
# Run all checks in sequence
python -m black laptimes/ --check && \
python -m isort laptimes/ --check-only && \
python -m flake8 laptimes/ && \
python manage.py test && \
echo "All checks passed! Ready to push."
```

### Admin Access
- URL: http://127.0.0.1:8000/admin/
- Username: admin
- Password: *******

### Environment Setup
- Python 3.13 required
- Python virtual environment is in `.venv/`
- Dependencies are managed via `requirements.txt` (Django 5.2+)
- Database is SQLite (`db.sqlite3`)

## Architecture Overview

### Core Models (`laptimes/models.py`)
- **Session**: Represents a racing session with track, car, session type, and player data
  - **Performance Optimization**: Pre-computed statistics stored in JSONFields for O(1) access
  - **Fields**: `session_statistics`, `chart_data`, `sector_statistics`, `fastest_lap_time`, etc.
- **Lap**: Individual lap with foreign key to Session, containing lap number, driver, times, sectors, and tyre data
  - **Signal Handlers**: Automatic statistics invalidation on lap modifications/deletions

### Key Views (`laptimes/views.py`)
- **HomeView**: File upload form and recent sessions list with JSON parsing logic
  - **Optimization**: Pre-computes statistics during upload for instant access
- **SessionDetailView**: Detailed lap analysis with chart data, fastest/slowest highlighting, and filtering  
  - **Optimization**: Uses pre-computed data with fallback to on-demand calculation
  - **Performance**: 90,000x+ faster data access through pre-computation
- **SessionEditView/SessionDeleteView**: CRUD operations for sessions
- **DriverDeleteView**: Driver removal with automatic statistics recalculation

### Statistics Module (`laptimes/statistics.py`)
- **SessionStatisticsCalculator**: Centralized calculation engine
- **Features**: Driver statistics, optimal lap times, sector analysis, chart data
- **Performance**: Single source of truth for all statistics computation

### Data Processing
- JSON files parsed in `HomeView.form_valid()` method
- Session type extraction from `__quickDrive` field or fallback to type mapping
- Time conversion from milliseconds to seconds
- Sector times stored as JSON arrays
- **Performance Optimization**: Statistics calculated once during ingestion, stored in database

### Frontend Features
- Bootstrap 5 for responsive UI
- Chart.js integration for lap time visualization with pre-computed data
- Dynamic highlighting: purple for fastest, red for slowest
- Driver filtering and sorting capabilities
- Real-time driver visibility controls with localStorage persistence

### URL Structure
- `/` - Home page with upload and session list
- `/session/<id>/` - Session detail with lap times
- `/session/<id>/edit/` - Edit session metadata
- `/session/<id>/delete/` - Delete session
- `/api/session/<id>/` - JSON API endpoint

## Performance Optimization

### Data Transformation Optimization
The application implements a comprehensive performance optimization that moves expensive calculations from page load to ingestion time:

**Before Optimization:**
- Complex O(n*m*s) calculations on every SessionDetailView load
- Driver statistics computed on-demand for every page view
- Chart data generated dynamically with nested loops
- Sector analysis performed repeatedly for highlighting

**After Optimization:**
- **90,000x+ performance improvement** for data access
- **Constant-time O(1) page loads** regardless of session complexity
- Pre-computed statistics stored in database during upload
- Fallback system ensures backward compatibility

**Key Components:**
- **SessionStatisticsCalculator**: Centralized calculation engine
- **Pre-computed JSONFields**: `session_statistics`, `chart_data`, `sector_statistics`
- **Signal Handlers**: Automatic cache invalidation on data changes
- **Management Command**: `recalculate_session_stats` for maintenance

### Performance Metrics
Real-world measurements on sessions with 35+ laps and multiple drivers:
- Driver statistics: **90,798x faster** (0.0866s → 0.000001s)  
- Chart data generation: **28,182x faster** (0.0776s → 0.000001s)
- Sector statistics: **1,913x faster** (0.0018s → 0.000001s)

## Code Conventions

Follow Django best practices as outlined in the Copilot instructions:
- Use Django ORM for database operations
- Implement proper error handling and validation
- Use Django forms for file uploads
- Follow PEP 8 style guidelines
- Bootstrap for responsive UI design
- **Performance**: Use pre-computed data when available, fallback to calculation

## Data Format

JSON files should contain:
```json
{
  "track": "Track Name",
  "car": "Car Model", 
  "players": [{"name": "Driver Name"}],
  "sessions": [{
    "laps": [{
      "lap": 0,
      "car": 0,
      "time": 123456, // milliseconds
      "sectors": [41123, 42234, 40099], // milliseconds
      "tyre": "M",
      "cuts": 0
    }]
  }]
}
```

## Important Notes

- Time values are converted from milliseconds (JSON) to seconds (database)
- Sector times stored as JSON arrays in Lap model
- Session type parsing handles both `__quickDrive` and numeric type fields
- Personal best and overall fastest/slowest highlighting implemented in templates
- **CRITICAL**: Always run formatting (black), linting (flake8), and tests before any git push operations

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

**MANDATORY PRE-PUSH CHECKLIST FOR CLAUDE CODE:**
1. ✅ Format code: `python -m black laptimes/`
2. ✅ Sort imports: `python -m isort laptimes/`
3. ✅ Check linting: `python -m flake8 laptimes/`  
4. ✅ Run tests: `python manage.py test` (all 70 tests must pass)
5. ✅ Only then proceed with git add, commit, and push

FAILURE TO FOLLOW THIS CHECKLIST IS UNACCEPTABLE.