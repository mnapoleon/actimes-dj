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
# Run all tests (38 tests total)
python manage.py test

# Run with detailed output
python manage.py test --verbosity=2

# Run only laptimes app tests
python manage.py test laptimes

# Run specific test class
python manage.py test laptimes.tests.SessionModelTests

# Run specific test method
python manage.py test laptimes.tests.SessionModelTests.test_session_creation

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
- 38 comprehensive tests covering models, views, forms, and integration
- Model tests: Session and Lap creation, validation, methods
- View tests: All major views including upload, detail, edit, delete
- Form tests: JSON upload validation and session editing
- Integration tests: Complete workflow from upload to viewing
- API tests: JSON endpoint functionality
- Driver management: Deletion and filtering features

### Admin Access
- URL: http://127.0.0.1:8000/admin/
- Username: admin
- Password: *******

### Environment Setup
- Python virtual environment is in `.venv/`
- Dependencies are managed via `requirements.txt` (Django 5.x only)
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