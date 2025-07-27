# Session List Advanced Filtering - Phase 3

## Overview
Add advanced filtering and search capabilities to the session list to improve user experience when working with large numbers of racing sessions. This builds on the pagination foundation established in Phase 1 and Phase 2.

## Current State
- ✅ Pagination with configurable page sizes (10, 20, 50, 100)
- ✅ Ordering by upload date (newest first)
- ✅ Optimized queries with lap count annotations
- ✅ Database indexes for performance (upload_date, track, car)

## Proposed Features

### 1. Session Filtering
**Track Filter:**
- Dropdown with all available tracks
- "All Tracks" option
- Alphabetically sorted

**Car Filter:**
- Dropdown with all available cars
- "All Cars" option
- Alphabetically sorted

**Session Type Filter:**
- Practice, Qualifying, Race options
- "All Types" option

**Date Range Filter:**
- Date picker for "From" and "To" dates
- Quick presets: Today, Last 7 days, Last 30 days, All time
- Clear date range option

### 2. Search Functionality
**Session Name Search:**
- Text input for searching session names
- Fuzzy matching support
- Search-as-you-type with debouncing

**Driver Search:**
- Search for sessions containing specific drivers
- Autocomplete based on existing driver names

**Combined Search:**
- Global search across session names, tracks, cars, and drivers
- Highlight matching results

### 3. Advanced Sorting
**Multi-column Sorting:**
- Upload date (default)
- Track name (alphabetical)
- Car name (alphabetical)
- Lap count (highest/lowest first)
- Session type
- Fastest lap time

**Sort Direction:**
- Ascending/Descending toggle
- Visual indicators for current sort

### 4. Filter State Management
**URL Parameters:**
- All filters preserved in URL
- Shareable filtered views
- Browser back/forward support

**Filter Persistence:**
- Remember user's last filter preferences
- Local storage for session state
- Reset to defaults option

## Technical Implementation

### 1. Backend Changes

**View Enhancements (HomeView):**
```python
def get_queryset(self):
    queryset = Session.objects.annotate(lap_count=Count('laps'))
    
    # Apply filters
    track = self.request.GET.get('track')
    if track and track != 'all':
        queryset = queryset.filter(track=track)
    
    car = self.request.GET.get('car')
    if car and car != 'all':
        queryset = queryset.filter(car=car)
    
    session_type = self.request.GET.get('session_type')
    if session_type and session_type != 'all':
        queryset = queryset.filter(session_type=session_type)
    
    # Date range filtering
    date_from = self.request.GET.get('date_from')
    date_to = self.request.GET.get('date_to')
    if date_from:
        queryset = queryset.filter(upload_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(upload_date__lte=date_to)
    
    # Search functionality
    search = self.request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(session_name__icontains=search) |
            Q(track__icontains=search) |
            Q(car__icontains=search) |
            Q(laps__driver_name__icontains=search)
        ).distinct()
    
    # Sorting
    sort_by = self.request.GET.get('sort', '-upload_date')
    queryset = queryset.order_by(sort_by)
    
    return queryset

def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Add filter options
    context['tracks'] = Session.objects.values_list('track', flat=True).distinct().order_by('track')
    context['cars'] = Session.objects.values_list('car', flat=True).distinct().order_by('car')
    context['session_types'] = Session.objects.values_list('session_type', flat=True).distinct().order_by('session_type')
    
    # Current filter values
    context['current_filters'] = {
        'track': self.request.GET.get('track', 'all'),
        'car': self.request.GET.get('car', 'all'),
        'session_type': self.request.GET.get('session_type', 'all'),
        'date_from': self.request.GET.get('date_from', ''),
        'date_to': self.request.GET.get('date_to', ''),
        'search': self.request.GET.get('search', ''),
        'sort': self.request.GET.get('sort', '-upload_date'),
    }
    
    return context
```

**New API Endpoints:**
```python
# For autocomplete functionality
def driver_autocomplete(request):
    term = request.GET.get('term', '')
    drivers = Lap.objects.filter(
        driver_name__icontains=term
    ).values_list('driver_name', flat=True).distinct()[:10]
    return JsonResponse(list(drivers), safe=False)
```

### 2. Frontend Implementation

**Filter Form:**
```html
<div class="card mb-4">
    <div class="card-header">
        <div class="d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
                <i class="bi bi-funnel"></i> Filter Sessions
            </h6>
            <div>
                <button type="button" class="btn btn-sm btn-outline-secondary" id="clearFilters">
                    Clear All
                </button>
                <button type="button" class="btn btn-sm btn-primary" data-bs-toggle="collapse" data-bs-target="#filterCollapse">
                    <i class="bi bi-chevron-down"></i>
                </button>
            </div>
        </div>
    </div>
    
    <div class="collapse" id="filterCollapse">
        <div class="card-body">
            <form method="get" id="filterForm">
                <div class="row g-3">
                    <!-- Search -->
                    <div class="col-md-6">
                        <label class="form-label">Search</label>
                        <input type="text" name="search" class="form-control" 
                               placeholder="Search sessions, tracks, cars, drivers..." 
                               value="{{ current_filters.search }}">
                    </div>
                    
                    <!-- Track Filter -->
                    <div class="col-md-3">
                        <label class="form-label">Track</label>
                        <select name="track" class="form-select">
                            <option value="all">All Tracks</option>
                            {% for track in tracks %}
                                <option value="{{ track }}" {% if track == current_filters.track %}selected{% endif %}>
                                    {{ track }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <!-- Car Filter -->
                    <div class="col-md-3">
                        <label class="form-label">Car</label>
                        <select name="car" class="form-select">
                            <option value="all">All Cars</option>
                            {% for car in cars %}
                                <option value="{{ car }}" {% if car == current_filters.car %}selected{% endif %}>
                                    {{ car }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <!-- Session Type Filter -->
                    <div class="col-md-3">
                        <label class="form-label">Session Type</label>
                        <select name="session_type" class="form-select">
                            <option value="all">All Types</option>
                            {% for type in session_types %}
                                <option value="{{ type }}" {% if type == current_filters.session_type %}selected{% endif %}>
                                    {{ type }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <!-- Date Range -->
                    <div class="col-md-4">
                        <label class="form-label">From Date</label>
                        <input type="date" name="date_from" class="form-control" 
                               value="{{ current_filters.date_from }}">
                    </div>
                    
                    <div class="col-md-4">
                        <label class="form-label">To Date</label>
                        <input type="date" name="date_to" class="form-control" 
                               value="{{ current_filters.date_to }}">
                    </div>
                    
                    <!-- Sort Options -->
                    <div class="col-md-4">
                        <label class="form-label">Sort By</label>
                        <select name="sort" class="form-select">
                            <option value="-upload_date">Newest First</option>
                            <option value="upload_date">Oldest First</option>
                            <option value="track">Track (A-Z)</option>
                            <option value="-track">Track (Z-A)</option>
                            <option value="car">Car (A-Z)</option>
                            <option value="-car">Car (Z-A)</option>
                            <option value="-lap_count">Most Laps</option>
                            <option value="lap_count">Fewest Laps</option>
                        </select>
                    </div>
                </div>
                
                <div class="row mt-3">
                    <div class="col-12">
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-search"></i> Apply Filters
                        </button>
                        <button type="button" class="btn btn-outline-secondary" id="resetFilters">
                            <i class="bi bi-arrow-clockwise"></i> Reset
                        </button>
                    </div>
                </div>
                
                <!-- Hidden field to preserve per_page -->
                <input type="hidden" name="per_page" value="{{ current_per_page }}">
            </form>
        </div>
    </div>
</div>
```

**JavaScript Enhancements:**
```javascript
// Auto-submit filters with debouncing
let filterTimeout;
document.getElementById('filterForm').addEventListener('input', function(e) {
    if (e.target.name === 'search') {
        clearTimeout(filterTimeout);
        filterTimeout = setTimeout(() => {
            this.submit();
        }, 500);
    } else {
        this.submit();
    }
});

// Clear all filters
document.getElementById('clearFilters').addEventListener('click', function() {
    const form = document.getElementById('filterForm');
    form.reset();
    // Clear URL parameters except per_page
    const url = new URL(window.location);
    const perPage = url.searchParams.get('per_page');
    url.search = '';
    if (perPage) url.searchParams.set('per_page', perPage);
    window.location.href = url.toString();
});

// Reset filters to defaults
document.getElementById('resetFilters').addEventListener('click', function() {
    const form = document.getElementById('filterForm');
    form.reset();
    form.submit();
});

// Update pagination links to preserve filters
function updatePaginationLinks() {
    const form = document.getElementById('filterForm');
    const formData = new FormData(form);
    const params = new URLSearchParams(formData);
    
    document.querySelectorAll('.pagination a').forEach(link => {
        const url = new URL(link.href);
        for (const [key, value] of params.entries()) {
            if (key !== 'page') {
                url.searchParams.set(key, value);
            }
        }
        link.href = url.toString();
    });
}
```

### 3. URL Structure
**Filter Parameters:**
- `?track=silverstone&car=ferrari&session_type=race`
- `?search=monaco&date_from=2024-01-01&date_to=2024-12-31`
- `?sort=track&per_page=50&page=2`

**Combined Example:**
`/sessions/?track=spa&car=ferrari&search=rain&sort=-upload_date&per_page=20&page=1`

## Implementation Phases

### Phase 3.1: Basic Filtering
1. **Track and Car Dropdowns**
   - Simple select dropdowns
   - Auto-submit on change
   - URL parameter preservation

2. **Search Functionality**
   - Session name search
   - Basic text matching
   - Debounced input

### Phase 3.2: Advanced Features
3. **Date Range Filtering**
   - Date pickers
   - Quick preset buttons
   - Validation

4. **Enhanced Search**
   - Multi-field search
   - Driver name search
   - Fuzzy matching

### Phase 3.3: Polish & UX
5. **Filter State Management**
   - Collapsible filter panel
   - Filter count indicators
   - Local storage persistence

6. **Performance Optimization**
   - Search result caching
   - Autocomplete optimization
   - Query optimization

## Database Considerations

**Additional Indexes Needed:**
```python
# In Session model Meta class
indexes = [
    # ... existing indexes ...
    models.Index(fields=['session_type']),  # For session type filtering
    models.Index(fields=['track', '-upload_date']),  # Compound index for track + date
    models.Index(fields=['car', '-upload_date']),    # Compound index for car + date
]
```

**Search Optimization:**
- Consider full-text search for larger datasets
- PostgreSQL GIN indexes for complex searches
- Elasticsearch integration for advanced search (future consideration)

## Testing Strategy

### Unit Tests
- Filter parameter validation
- Query optimization verification
- Edge case handling (empty results, invalid dates)

### Integration Tests
- Complete filter workflow
- URL parameter preservation
- Pagination with filters

### Performance Tests
- Filter query performance with large datasets
- Search responsiveness
- Memory usage with complex filters

## Success Metrics

### User Experience
- **Findability**: Users can quickly locate specific sessions
- **Performance**: Filter results return in < 1 second
- **Intuitiveness**: Clear filter interface with helpful defaults

### Technical Metrics
- **Query Performance**: Complex filters execute in < 200ms
- **Database Efficiency**: Proper index utilization
- **Scalability**: Filters work efficiently with 10,000+ sessions

## Future Enhancements

### Advanced Features
- **Saved Filters**: Allow users to save and recall filter combinations
- **Filter Suggestions**: Smart suggestions based on usage patterns
- **Bulk Operations**: Select multiple filtered sessions for batch actions
- **Export Filtered Results**: CSV/JSON export of filtered session data

### Analytics Integration
- **Filter Usage Analytics**: Track popular filter combinations
- **Performance Monitoring**: Monitor filter query performance
- **User Behavior**: Understand how users navigate large session lists

## Files to Modify

### Core Implementation
- `laptimes/views.py` - Add filtering logic to HomeView
- `laptimes/templates/laptimes/home.html` - Add filter form UI
- `laptimes/models.py` - Add additional database indexes
- `laptimes/urls.py` - Add autocomplete endpoints

### Supporting Files
- `laptimes/static/laptimes/css/style.css` - Filter form styling
- `laptimes/tests.py` - Comprehensive filter testing
- `actimes_project/settings.py` - Performance-related settings

## Risk Assessment

### Low Risk
- Non-breaking additive features
- Optional filtering (doesn't affect existing users)
- Well-established Django filtering patterns

### Medium Risk
- Complex query performance with large datasets
- URL parameter management complexity
- Browser compatibility for advanced date pickers

### Mitigation Strategies
- Comprehensive performance testing
- Progressive enhancement approach
- Fallback options for complex features
- Query optimization and monitoring

## Conclusion

The advanced filtering features will transform the session list from a simple paginated view into a powerful session management tool. Users will be able to quickly find specific sessions, analyze patterns across their racing data, and efficiently manage large collections of race sessions.

The implementation leverages Django's robust ORM capabilities while maintaining excellent performance through proper indexing and query optimization. The modular approach allows for incremental implementation and future enhancements.