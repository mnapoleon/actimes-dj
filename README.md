# Assetto Corsa Lap Times - Django Application

A Django web application for analyzing racing lap times from Assetto Corsa JSON files. This application stores session data in a SQLite database and provides a web interface for uploading and analyzing lap times.

## Features

### **Core Functionality**
- **Smart JSON Upload**: Comprehensive validation and parsing of Assetto Corsa race data
- **Intelligent Session Detection**: Automatic session type extraction from `__quickDrive` fields
- **Database Storage**: SQLite with optimized relationships and indexing
- **Time Conversion**: Automatic milliseconds to seconds conversion with precision formatting

### **Advanced Data Visualization**
- **Interactive Charts**: Multi-driver lap progression visualization using Chart.js
- **Performance Highlighting System**:
  - 🟣 **Purple**: Overall fastest lap/sector times
  - 🟢 **Green**: Personal best times per driver  
  - 🔴 **Red**: Overall slowest lap/sector times
- **Dynamic Sector Analysis**: Automatic detection of sector count (3+ sectors supported)
- **Real-time Chart Updates**: Color-coded driver comparison with 10 distinct colors

### **Comprehensive Session Management**
- **Session CRUD Operations**: Create, view, edit, and delete sessions
- **Driver Management**: Individual driver deletion with confirmation
- **Session Editing**: Dual-input system (dropdown + custom text) for tracks and cars
- **Metadata Management**: Optional session naming and date/time editing

### **Advanced Filtering & Analysis**
- **Multi-criteria Sorting**: By driver, lap number, total time, or individual sector times
- **Driver Filtering**: Real-time filtering with URL state management
- **Pagination**: Optimized display with 50 laps per page
- **Performance Analytics**: Fastest lap detection and personal best tracking

### **Professional Interface**
- **Responsive Design**: Bootstrap 5 with mobile optimization
- **Assetto Corsa Branding**: Official logo and brand colors
- **Breadcrumb Navigation**: Context-aware navigation paths
- **Message System**: Success/error notifications with Django messages
- **Admin Interface**: Comprehensive Django admin with search and filtering

## Database Schema

### Session Model

- **session_name**: Optional custom session identifier
- **track**: Track name (with dropdown suggestions from existing data)
- **car**: Car model (with dropdown suggestions from existing data)
- **session_type**: Practice, Qualifying, Race (auto-detected from JSON)
- **upload_date**: Timestamp with editing capability
- **file_name**: Original JSON filename for reference
- **players_data**: Complete player information (JSON field)
- **Methods**: `get_fastest_lap()`, `get_drivers()`, custom string representation

### Lap Model

- **session**: Foreign key relationship with cascade delete
- **lap_number**: Lap sequence number (0 = out lap)
- **driver_name**: Driver identifier extracted from players data
- **car_index**: Player array index for data mapping
- **total_time**: Lap time in seconds (converted from milliseconds)
- **sectors**: Dynamic sector times array (JSON field, supports 3+ sectors)
- **tyre_compound**: Tire type (S, M, H, etc.)
- **cuts**: Track limit violations count
- **Methods**: `format_time()` (MM:SS.mmm), `get_sector_times()`
- **Constraints**: Unique combination of session + lap_number + car_index

## Installation & Setup

1. **Clone and navigate to project directory**

   ```bash
   cd actimes-dj
   ```

2. **Virtual environment is already configured**

   - Python virtual environment is located in `.venv/`
   - Django is already installed

3. **Database is already migrated**

   - SQLite database with all tables created
   - Admin user created (username: admin, password: admin123)

4. **Run the development server**

   ```bash
   python manage.py runserver
   ```

5. **Access the application**
   - Main app: http://127.0.0.1:8000/
   - Admin interface: http://127.0.0.1:8000/admin/

## Usage

### 1. **Upload Race Data**
- Navigate to the home page (`/`)
- Upload JSON file with comprehensive validation
- Automatic parsing and data conversion (milliseconds → seconds)
- Session type auto-detection from `__quickDrive` or numeric type fields
- Success/error feedback with detailed messaging

### 2. **Session Management**
- **Home Page**: View recent sessions (latest 10, sorted by track)
- **Session Details**: Complete lap analysis with interactive charts
- **Edit Sessions**: Modify track, car, session name, and upload date
- **Delete Sessions**: Confirmation dialog with session summary

### 3. **Advanced Lap Analysis**
- **Performance Highlighting**: 
  - Purple badges for overall fastest times
  - Green badges for personal best times
  - Red badges for overall slowest times
- **Interactive Charts**: Multi-driver lap progression visualization
- **Dynamic Filtering**: Filter by specific drivers with URL state persistence
- **Multi-column Sorting**: By driver, lap number, total time, or individual sectors
- **Sector Analysis**: Dynamic sector count detection (supports 3+ sectors)

### 4. **Driver Management**
- **Individual Driver Deletion**: Remove specific drivers and all their laps
- **Driver Filtering**: Dropdown selection with "All Drivers" option
- **Performance Comparison**: Side-by-side driver analysis with color coding

### 5. **Data Export & API**
- **JSON API**: RESTful endpoint at `/api/session/<id>/` for external integrations
- **Structured Data**: Export session and lap data in JSON format

### 6. **Admin Interface**
- **Comprehensive Management**: Full CRUD operations on sessions and laps
- **Advanced Filtering**: By session type, track, car, upload date, driver, tire compound
- **Search Functionality**: Search across tracks, cars, drivers, and filenames
- **Performance Optimizations**: Optimized queries with select_related

## Project Structure

```
actimes-dj/
├── actimes_project/          # Django project settings
│   ├── settings.py          # Main configuration
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI configuration
├── laptimes/                 # Main Django app
│   ├── models.py            # Session and Lap models with methods
│   ├── views.py             # All views (Home, Detail, Edit, Delete, API)
│   ├── forms.py             # JSON upload and session edit forms
│   ├── admin.py             # Optimized admin interface
│   ├── urls.py              # Complete URL patterns
│   ├── templatetags/        # Custom template tags
│   │   └── laptimes_extras.py  # Array indexing and color utilities
│   ├── templates/           # Complete HTML templates
│   │   └── laptimes/
│   │       ├── base.html    # Base template with navigation
│   │       ├── home.html    # Upload form and session list
│   │       ├── session_detail.html  # Interactive analysis page
│   │       ├── session_edit.html    # Session editing form
│   │       └── session_confirm_delete.html  # Deletion confirmation
│   ├── static/              # Static assets
│   │   ├── laptimes/css/style.css  # Custom styling
│   │   └── imgs/assetto_corsa_logo.svg  # Branding
│   └── tests.py             # Comprehensive test suite (726 lines)
├── manage.py                # Django management script
├── db.sqlite3              # SQLite database
└── .venv/                  # Python virtual environment
```

## API Endpoints

### **Web Interface**
- `/` - Home page with upload form and recent sessions (latest 10)
- `/session/<int:pk>/` - Detailed session analysis with charts and lap data
- `/session/<int:pk>/edit/` - Edit session metadata (track, car, name, date)
- `/session/<int:pk>/delete/` - Delete session with confirmation dialog
- `/session/<int:session_pk>/delete-driver/<str:driver_name>/` - Remove specific driver

### **API Endpoints**
- `/api/session/<int:pk>/` - JSON API returning complete session and lap data

### **Admin Interface**
- `/admin/` - Django admin with advanced filtering and search capabilities
- `/admin/laptimes/session/` - Session management interface
- `/admin/laptimes/lap/` - Lap data management interface

## Development

The application uses:

- **Django 5.x** - Web framework with class-based views
- **SQLite** - Database with optimized indexing and constraints
- **Bootstrap 5** - Responsive CSS framework
- **Bootstrap Icons** - Complete icon library
- **Chart.js** - Interactive data visualization
- **Custom CSS** - Assetto Corsa branding and performance highlighting

### Database Management

```bash
# Create new migrations after model changes
python manage.py makemigrations

# Apply migrations to database
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

### Extending the Application

1. Modify models in `laptimes/models.py`
2. Create migrations: `python manage.py makemigrations`
3. Apply migrations: `python manage.py migrate`
4. Update views and templates as needed
5. Add tests for new functionality in `laptimes/tests.py`

## Data Format

The application expects Assetto Corsa JSON files with this structure:

```json
{
  "track": "Silverstone International",
  "car": "Ferrari SF70H",
  "__quickDrive": "{\"Mode\":\"/Pages/Drive/QuickDrive_Qualifying.xaml\"}",
  "players": [
    {
      "name": "Driver Name",
      "car": "Ferrari SF70H"
    }
  ],
  "sessions": [{
    "type": 2,
    "laps": [
      {
        "lap": 1,
        "car": 0,
        "time": 123456,
        "sectors": [41123, 42234, 40099],
        "tyre": "M",
        "cuts": 0
      }
    ]
  }]
}
```

### **Key Features of Data Processing:**
- **Time Conversion**: Milliseconds (JSON) → Seconds (database) with precision
- **Session Type Detection**: Extracts from `__quickDrive` field or numeric `type`
- **Multi-driver Support**: Handles multiple players with car index mapping
- **Flexible Sectors**: Supports 3+ sector configurations automatically
- **Validation**: Comprehensive JSON structure and data type validation
- **Error Handling**: Detailed error messages for malformed data
