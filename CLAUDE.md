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
- **Lap**: Individual lap with foreign key to Session, containing lap number, driver, times, sectors, and tyre data

### Key Views (`laptimes/views.py`)
- **HomeView**: File upload form and recent sessions list with JSON parsing logic
- **SessionDetailView**: Detailed lap analysis with chart data, fastest/slowest highlighting, and filtering
- **SessionEditView/SessionDeleteView**: CRUD operations for sessions

### Data Processing
- JSON files parsed in `HomeView.form_valid()` method
- Session type extraction from `__quickDrive` field or fallback to type mapping
- Time conversion from milliseconds to seconds
- Sector times stored as JSON arrays

### Frontend Features
- Bootstrap 5 for responsive UI
- Chart.js integration for lap time visualization
- Dynamic highlighting: purple for fastest, red for slowest
- Driver filtering and sorting capabilities

### URL Structure
- `/` - Home page with upload and session list
- `/session/<id>/` - Session detail with lap times
- `/session/<id>/edit/` - Edit session metadata
- `/session/<id>/delete/` - Delete session
- `/api/session/<id>/` - JSON API endpoint

## Code Conventions

Follow Django best practices as outlined in the Copilot instructions:
- Use Django ORM for database operations
- Implement proper error handling and validation
- Use Django forms for file uploads
- Follow PEP 8 style guidelines
- Bootstrap for responsive UI design

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