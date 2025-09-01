# Data Transformation Optimization Plan

## Executive Summary

This specification outlines a performance optimization strategy to move data transformations from page load to ingestion time. Currently, expensive calculations are performed on every session detail page load, leading to poor performance as data grows. By pre-computing and caching these values during file upload, we can achieve significant performance improvements.

## Current Performance Bottlenecks

### 1. Session Model Calculations (models.py:42-136)

**Expensive Operations Called on Every Page Load:**
- `get_driver_statistics()` - Lines 78-136
  - Iterates through all laps for each driver
  - Calculates best lap, average, consistency (standard deviation)
  - Filters out laps (lap_number > 0) multiple times
  - Called in `SessionDetailView.get_context_data()` line 329
- `get_optimal_lap_time()` - Lines 50-76
  - Called for each driver within `get_driver_statistics()`
  - Iterates through all driver laps to find best sector times
- `get_fastest_lap()` - Lines 42-44
  - Simple but still a database query on every load

### 2. SessionDetailView Calculations (views.py:307-486)

**Complex Operations Performed on Every Page Load:**
- **Chart Data Generation** (lines 363-373)
  - Creates data structure for all drivers and lap numbers
  - Nested loops through drivers and lap numbers
- **Row-Level Highlighting** (lines 390-421)
  - Finds fastest/slowest lap times across all laps
  - Calculates personal best per driver
  - Filters out laps multiple times
- **Sector Highlighting** (lines 422-486)
  - Most expensive operation
  - Processes all laps multiple times to find fastest/slowest sectors
  - Calculates personal best sectors per driver
  - Creates complex nested data structures

### 3. Performance Impact

**Time Complexity:** O(n*m*s) where:
- n = number of laps
- m = number of drivers  
- s = number of sectors

**Database Queries:** Multiple queries and in-memory filtering on every page load

## Proposed Solution

### Phase 1: Add Pre-computed Fields to Database

#### 1.1 Session Model Enhancements

Add new fields to store pre-computed session-level statistics:

```python
class Session(models.Model):
    # Existing fields...
    
    # Pre-computed session statistics
    fastest_lap_time = models.FloatField(null=True, blank=True)
    fastest_lap_driver = models.CharField(max_length=200, blank=True)
    total_laps = models.IntegerField(default=0)
    total_drivers = models.IntegerField(default=0)
    session_statistics = models.JSONField(default=dict)  # Store complex stats
    chart_data = models.JSONField(default=dict)  # Pre-computed chart data
    sector_statistics = models.JSONField(default=dict)  # Sector highlights
    last_calculated = models.DateTimeField(auto_now=True)
```

#### 1.2 Driver Statistics Structure

Store driver statistics in `session_statistics` JSONField:

```json
{
  "driver_name": {
    "best_lap_time": 123.456,
    "optimal_lap_time": 122.987,
    "lap_count": 25,
    "racing_lap_count": 24,
    "avg_lap_time": 125.234,
    "consistency": 0.876,
    "visible": true
  }
}
```

#### 1.3 Chart Data Structure

Store chart data in `chart_data` JSONField:

```json
{
  "driver_name": {
    "1": 125.456,
    "2": 123.789,
    "3": null
  }
}
```

#### 1.4 Sector Statistics Structure

Store sector highlights in `sector_statistics` JSONField:

```json
{
  "sector_highlights": {
    "0": {"fastest": 41.123, "slowest": 43.567},
    "1": {"fastest": 42.234, "slowest": 44.892},
    "2": {"fastest": 39.876, "slowest": 42.123}
  },
  "driver_pb_sectors": {
    "driver_name": {
      "0": 41.456,
      "1": 42.567,
      "2": 40.123
    }
  },
  "lap_highlights": {
    "fastest_total": 123.456,
    "slowest_total": 128.789,
    "driver_pb_total": {
      "driver_name": 123.789
    }
  }
}
```

### Phase 2: Modify Ingestion Process

#### 2.1 Enhanced _process_upload Method

Update `HomeView._process_upload()` to calculate statistics during ingestion:

```python
def _process_upload(self, form):
    # ... existing code for session creation ...
    
    # Create all lap objects first
    for lap_data in session_data["laps"]:
        # ... existing lap creation code ...
    
    # Calculate and store pre-computed statistics
    self._calculate_session_statistics(session)
    
    return redirect("home")

def _calculate_session_statistics(self, session):
    """Calculate and store all session statistics"""
    # Calculate driver statistics
    session.session_statistics = self._calculate_driver_statistics(session)
    
    # Calculate chart data
    session.chart_data = self._calculate_chart_data(session)
    
    # Calculate sector statistics  
    session.sector_statistics = self._calculate_sector_statistics(session)
    
    # Calculate session-level stats
    fastest_lap = session.laps.filter(lap_number__gt=0).order_by('total_time').first()
    if fastest_lap:
        session.fastest_lap_time = fastest_lap.total_time
        session.fastest_lap_driver = fastest_lap.driver_name
    
    session.total_laps = session.laps.count()
    session.total_drivers = session.laps.values_list('driver_name', flat=True).distinct().count()
    
    session.save()
```

#### 2.2 Extract Calculation Methods

Move existing calculation logic from views and models to new helper methods:

```python
def _calculate_driver_statistics(self, session):
    """Extract from Session.get_driver_statistics()"""
    # Move logic from models.py:78-136

def _calculate_chart_data(self, session):
    """Extract from SessionDetailView chart data logic"""  
    # Move logic from views.py:363-373

def _calculate_sector_statistics(self, session):
    """Extract from SessionDetailView sector highlighting logic"""
    # Move logic from views.py:422-486
```

### Phase 3: Optimize Views for Pre-computed Data

#### 3.1 Simplified SessionDetailView

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context["session"] = self.session
    
    # Use pre-computed data instead of calculating on-demand
    context["driver_statistics"] = self.session.session_statistics
    context["chart_data"] = self.session.chart_data
    context["sector_highlights"] = self.session.sector_statistics.get("sector_highlights", {})
    context["fastest_lap_time"] = self.session.fastest_lap_time
    
    # ... rest of context setup using pre-computed values ...
    
    return context
```

#### 3.2 Remove Expensive Model Methods

Deprecate or remove:
- `Session.get_driver_statistics()`
- `Session.get_optimal_lap_time()`  
- Complex view calculations

### Phase 4: Data Migration and Consistency

#### 4.1 Migration Strategy

1. **Database Migration**: Add new fields with default values
2. **Data Backfill**: Calculate statistics for existing sessions
3. **Validation**: Ensure pre-computed values match old calculations
4. **Cutover**: Update views to use pre-computed data

#### 4.2 Consistency Mechanisms

**Recalculation Triggers:**
- Lap deletion (driver removal)
- Session editing that affects lap data
- Manual recalculation command

**Management Command:**
```python
# management/commands/recalculate_session_stats.py
def handle(self, *args, **options):
    for session in Session.objects.all():
        self._calculate_session_statistics(session)
```

## Implementation Plan

### Sprint 1: Database Schema (1 week)
- [ ] Add new fields to Session model
- [ ] Create and run migration  
- [ ] Add model validation for new fields
- [ ] Create management command for recalculation

### Sprint 2: Ingestion Enhancement (2 weeks)  
- [ ] Extract calculation methods from existing code
- [ ] Implement calculation during upload
- [ ] Add unit tests for calculation accuracy
- [ ] Backfill existing sessions

### Sprint 3: View Optimization (1 week)
- [ ] Update SessionDetailView to use pre-computed data
- [ ] Remove deprecated model methods
- [ ] Update templates if needed
- [ ] Performance testing and validation

### Sprint 4: Edge Cases & Polish (1 week)
- [ ] Handle lap deletion/driver removal
- [ ] Add recalculation for session editing
- [ ] Documentation updates
- [ ] Load testing with large datasets

## Expected Performance Improvements

### Current Performance:
- **SessionDetailView**: O(n*m*s) calculation complexity
- **Database Queries**: Multiple queries + complex in-memory operations
- **Page Load Time**: Increases linearly with lap count

### Optimized Performance:
- **SessionDetailView**: O(1) - simple field access
- **Database Queries**: Single session fetch
- **Page Load Time**: Constant regardless of lap count

### Estimated Improvements:
- **50+ lap sessions**: 80-90% reduction in page load time
- **100+ lap sessions**: 90-95% reduction in page load time
- **Database Load**: 70-80% reduction in query complexity

## Risk Mitigation

### Data Consistency
- **Risk**: Pre-computed data becoming stale
- **Mitigation**: Recalculation triggers, management commands, validation

### Storage Overhead  
- **Risk**: Increased database size from JSON fields
- **Mitigation**: Compress JSON data, archive old sessions

### Migration Complexity
- **Risk**: Complex migration for existing data
- **Mitigation**: Phased rollout, validation scripts, rollback plan

### Code Complexity
- **Risk**: Dual maintenance of calculation logic
- **Mitigation**: Single source of truth, comprehensive tests

## Testing Strategy

### Unit Tests
- Calculation accuracy (old vs new methods)
- Edge cases (empty sessions, single laps)
- Data validation and consistency

### Integration Tests  
- End-to-end upload with calculation
- View rendering with pre-computed data
- Recalculation triggers

### Performance Tests
- Load testing with varying session sizes
- Memory usage profiling
- Database query analysis

## Success Metrics

### Performance Metrics
- Page load time reduction: Target 80%+ for large sessions  
- Database query count reduction: Target 70%+
- Memory usage reduction: Target 60%+

### Quality Metrics
- Zero calculation discrepancies between old/new methods
- All existing functionality preserved
- Test coverage maintained at 95%+

## Conclusion

This optimization will transform the application from calculating expensive statistics on every page load to pre-computing them once during ingestion. The result will be dramatically improved performance, especially for large racing sessions, while maintaining all existing functionality and adding better data consistency.