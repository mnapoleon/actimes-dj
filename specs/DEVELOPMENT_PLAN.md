# Django Racing Lap Times Application - Development Plan

Based on analysis of the existing codebase, here's a comprehensive plan to build this application from scratch:

## Phase 1: Project Setup & Foundation (Week 1)

### 1.1 Environment Setup
- Create Python virtual environment
- Install Django 5.x
- Initialize Django project `actimes_project`
- Create Django app `laptimes`
- Configure SQLite database
- Set up static files handling

### 1.2 Basic Project Structure
- Configure `settings.py` with app registration
- Set up URL routing (`urls.py`)
- Create basic HTML templates with Bootstrap 5
- Implement base template with navigation

## Phase 2: Data Models & Database (Week 1-2)

### 2.1 Model Design
- **Session Model**: track, car, session_type, upload_date, file_name, players_data, session_name
- **Lap Model**: session (FK), lap_number, driver_name, car_index, total_time, sectors (JSONField), tyre_compound, cuts
- Add proper relationships and constraints
- Create model methods for data processing

### 2.2 Database Implementation
- Create initial migrations
- Set up Django admin interface
- Add model string representations
- Implement helper methods (get_fastest_lap, get_drivers)

## Phase 3: JSON Processing & File Upload (Week 2)

### 3.1 Form Development
- Create `JSONUploadForm` with file validation
- Implement JSON structure validation
- Add proper error handling for malformed files
- Create `SessionEditForm` for metadata editing

### 3.2 Data Processing Logic
- Parse Assetto Corsa JSON format
- Extract session type from `__quickDrive` field
- Convert time values from milliseconds to seconds
- Map car indices to driver names
- Handle sector time arrays

## Phase 4: Core Views & Templates (Week 2-3)

### 4.1 Home View
- File upload functionality
- Recent sessions display
- Session list with track grouping
- Success/error message handling

### 4.2 Session Detail View
- Lap times table with pagination
- Driver filtering and sorting
- Fastest/slowest/personal best highlighting
- Session metadata display

### 4.3 CRUD Operations
- Session edit functionality
- Session deletion with confirmation
- Driver deletion from sessions

## Phase 5: Data Visualization (Week 3)

### 5.1 Chart.js Integration
- Line chart for lap time progression
- Multi-driver comparison
- Dynamic color assignment
- Responsive chart configuration

### 5.2 Performance Highlighting
- Purple highlighting for fastest times
- Green highlighting for personal bests
- Red highlighting for slowest times
- Sector-by-sector analysis

## Phase 6: Frontend Enhancement (Week 3-4)

### 6.1 Custom Styling
- Brand color scheme (Assetto Corsa red: #DB0E15)
- Custom CSS for table highlighting
- Rounded corners and modern design
- Responsive layout improvements

### 6.2 Template Tags & Filters
- Custom template filters for data access
- Driver color assignment
- Dictionary and list indexing helpers

### 6.3 Interactive Features
- JavaScript for filtering and sorting
- Dynamic URL parameter handling
- Driver management interface

## Phase 7: API & Advanced Features (Week 4)

### 7.1 REST API
- JSON API endpoint for session data
- Proper data serialization
- Error handling and status codes

### 7.2 Enhanced Functionality
- Bulk operations
- Export capabilities
- Session comparison features
- Advanced filtering options

## Phase 8: Testing & Optimization (Week 4-5)

### 8.1 Testing Suite
- Model tests for data validation
- View tests for CRUD operations
- Form tests for file upload
- Template tests for rendering

### 8.2 Performance Optimization
- Database query optimization
- Pagination implementation
- Caching strategies
- Static file optimization

## Phase 9: Production Preparation (Week 5)

### 9.1 Security & Configuration
- Environment variables for sensitive data
- CSRF protection verification
- File upload security
- Production settings separation

### 9.2 Documentation
- README with setup instructions
- CLAUDE.md for AI assistance
- Code documentation
- Deployment guidelines

## Technical Stack

- **Backend**: Django 5.x, SQLite
- **Frontend**: Bootstrap 5, Chart.js, Vanilla JavaScript
- **Data**: JSON file processing, JSONField for flexible storage
- **Styling**: Custom CSS with Assetto Corsa branding

## Key Features Implemented

1. **File Upload & Processing**: JSON race data parsing with validation
2. **Data Management**: Session and lap CRUD operations
3. **Visualization**: Interactive lap time charts
4. **Performance Analysis**: Fastest/slowest/PB highlighting
5. **Filtering**: Driver and lap filtering with sorting
6. **Responsive Design**: Mobile-friendly interface
7. **Driver Management**: Remove drivers from sessions

## Implementation Details

### JSON Data Structure Expected
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

### Database Schema
- **Session**: Primary entity for race sessions
- **Lap**: Detailed lap data with foreign key to Session
- Time conversion: milliseconds (JSON) → seconds (database)
- Flexible sector storage using JSONField

### Highlighting Logic
- **Purple**: Overall fastest time/sector
- **Green**: Personal best for driver
- **Red**: Overall slowest time/sector

This plan provides a structured approach to building the racing lap times application, progressing from basic setup to advanced features while maintaining code quality and user experience.