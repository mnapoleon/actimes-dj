# Assetto Corsa Lap Times - Django Application

A Django web application for analyzing racing lap times from Assetto Corsa JSON files. This application stores session data in a SQLite database and provides a web interface for uploading and analyzing lap times.

## Features

- **File Upload**: Upload JSON race data files through a web interface
- **Database Storage**: Sessions and laps stored in SQLite database with proper relationships
- **Data Visualization**:
  - Fastest lap highlighting in purple
  - Slowest lap highlighting in red
  - Fastest/slowest sector time badges
- **Filtering & Sorting**: Filter by driver and sort by various criteria
- **Session Management**: View multiple racing sessions
- **Admin Interface**: Django admin for managing data
- **Responsive Design**: Bootstrap-based UI that works on all devices

## Database Schema

### Session Model

- Track name
- Car model
- Session type (Practice, Qualifying, Race)
- Upload timestamp
- Original filename
- Player data (JSON field)

### Lap Model

- Foreign key to Session
- Lap number
- Driver name and car index
- Total lap time
- Individual sector times (1, 2, 3)
- Tyre compound
- Track cuts count

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

1. **Upload Race Data**:

   - Go to the home page
   - Upload a JSON file containing race session data
   - The app will parse and store the data in the database

2. **View Sessions**:

   - Recent sessions are displayed on the home page
   - Click on a session to view detailed lap times

3. **Analyze Lap Times**:

   - View all laps with highlighting for fastest/slowest times
   - Filter by specific drivers
   - Sort by lap number, total time, or sector times
   - Purple highlighting for fastest laps/sectors
   - Red highlighting for slowest laps/sectors

4. **Admin Interface**:
   - Access Django admin at `/admin/`
   - Manage sessions and laps directly
   - View database statistics

## Project Structure

```
actimes-dj/
├── actimes_project/          # Django project settings
│   ├── settings.py          # Main configuration
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI configuration
├── laptimes/                 # Main Django app
│   ├── models.py            # Session and Lap models
│   ├── views.py             # Upload and display views
│   ├── forms.py             # File upload forms
│   ├── admin.py             # Admin interface configuration
│   ├── urls.py              # App URL patterns
│   ├── templates/           # HTML templates
│   │   └── laptimes/
│   │       ├── base.html    # Base template
│   │       ├── home.html    # Upload and session list
│   │       └── session_detail.html  # Lap times display
│   └── static/              # CSS and static files
│       └── laptimes/css/style.css
├── manage.py                # Django management script
├── db.sqlite3              # SQLite database
└── .venv/                  # Python virtual environment
```

## API Endpoints

- `/` - Home page with upload form and session list
- `/session/<id>/` - Detailed lap times for a specific session
- `/api/session/<id>/` - JSON API endpoint for session data
- `/admin/` - Django admin interface

## Development

The application uses:

- **Django 5.x** - Web framework
- **SQLite** - Database (included with Django)
- **Bootstrap 5** - CSS framework
- **Bootstrap Icons** - Icon set

To extend the application:

1. Modify models in `laptimes/models.py`
2. Create migrations: `python manage.py makemigrations`
3. Apply migrations: `python manage.py migrate`
4. Update views and templates as needed

## Data Format

The application expects JSON files with this structure:

```json
{
  "track": "Track Name",
  "car": "Car Model",
  "players": [{ "name": "Driver Name" }],
  "laps": [
    {
      "lap": 0,
      "car": 0,
      "time": 123.456,
      "sectors": [41.123, 42.234, 40.099],
      "tyre": "M",
      "cuts": 0
    }
  ]
}
```
