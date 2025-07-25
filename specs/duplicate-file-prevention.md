# Duplicate File Upload Prevention Feature

## Overview

This feature will prevent users from uploading the same Assetto Corsa JSON file multiple times, avoiding duplicate session data in the database and improving data integrity.

## Problem Statement

Currently, users can upload the same JSON file repeatedly, creating duplicate sessions with identical data. This leads to:
- Data redundancy and confusion
- Increased database size
- Difficulty in session management
- Poor user experience

## Solution Approach

### 1. File Hash-Based Detection

**Primary Method**: Generate a hash of the uploaded file content to create a unique fingerprint.

- Use SHA-256 hash of the entire JSON file content
- Store hash in Session model for future comparison
- Check hash before processing upload

### 2. Content-Based Detection (Secondary)

**Fallback Method**: Compare key session metadata for additional validation.

- Track + Car + Session Type + Lap Count combination
- First/last lap times comparison
- Upload timestamp proximity (within minutes)

## Technical Implementation

### Database Changes

#### 1. Add File Hash Field to Session Model

```python
# In laptimes/models.py
class Session(models.Model):
    # ... existing fields ...
    file_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-upload_date']
        indexes = [
            models.Index(fields=['file_hash']),
        ]
```

#### 2. Migration Required

```bash
python manage.py makemigrations
python manage.py migrate
```

### Form Validation Enhancement

#### 1. Update JSONUploadForm

```python
# In laptimes/forms.py
import hashlib

class JSONUploadForm(forms.Form):
    # ... existing fields ...
    
    def clean_json_file(self):
        file = self.cleaned_data['json_file']
        
        # ... existing validations ...
        
        # Generate file hash
        file.seek(0)
        content = file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check for duplicate hash
        if Session.objects.filter(file_hash=file_hash).exists():
            existing_session = Session.objects.get(file_hash=file_hash)
            raise ValidationError(
                f'This file has already been uploaded. '
                f'Existing session: "{existing_session}" '
                f'(uploaded on {existing_session.upload_date.strftime("%Y-%m-%d %H:%M")})'
            )
        
        # Store hash for later use
        file._file_hash = file_hash
        file.seek(0)
        
        return file
```

### View Updates

#### 1. Update HomeView.form_valid()

```python
# In laptimes/views.py
def form_valid(self, form):
    json_file = form.cleaned_data['json_file']
    try:
        # ... existing parsing logic ...
        
        # Create Session object with file hash
        session = Session.objects.create(
            track=data['track'],
            car=car_model,
            session_type=session_type,
            file_name=json_file.name,
            players_data=data['players'],
            upload_date=upload_date,
            file_hash=getattr(json_file, '_file_hash', None)
        )
        
        # ... rest of existing logic ...
```

### User Interface Enhancements

#### 1. Enhanced Error Messages

- Clear indication when duplicate file is detected
- Show details of existing session
- Provide link to existing session for review

#### 2. Admin Interface Updates

```python
# In laptimes/admin.py
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['track', 'car', 'session_type', 'upload_date', 'lap_count', 'file_hash_short']
    list_filter = ['session_type', 'track', 'car', 'upload_date']
    search_fields = ['track', 'car', 'file_name', 'file_hash']
    readonly_fields = ['upload_date', 'file_hash']
    
    def file_hash_short(self, obj):
        return obj.file_hash[:8] if obj.file_hash else 'N/A'
    file_hash_short.short_description = 'Hash (short)'
```

## Advanced Features (Future Enhancements)

### 1. Duplicate Detection with Variations

- Detect files with minor modifications (different session names, etc.)
- Content-based similarity matching
- Threshold-based duplicate detection

### 2. Merge Options

- Allow merging laps from similar sessions
- Combine sessions with identical metadata
- User choice to replace or merge

### 3. Bulk Upload Protection

- Batch file upload with duplicate checking
- Preview mode showing which files would be duplicates
- Skip/replace options for bulk operations

## Testing Strategy

### 1. Unit Tests

```python
# In laptimes/tests.py
class DuplicateFileTests(TestCase):
    def test_duplicate_file_upload_prevention(self):
        """Test that uploading the same file twice is prevented"""
        
    def test_file_hash_generation(self):
        """Test that file hash is correctly generated and stored"""
        
    def test_different_files_same_content(self):
        """Test that files with identical content are detected as duplicates"""
        
    def test_error_message_for_duplicates(self):
        """Test that meaningful error messages are shown for duplicates"""
```

### 2. Integration Tests

- Complete upload workflow with duplicate detection
- Form validation with duplicate files
- Admin interface functionality

### 3. Performance Tests

- Hash generation performance with large files
- Database query performance with hash indexing
- Memory usage during file processing

## Implementation Steps

### Phase 1: Core Functionality ✅ COMPLETED
1. ✅ Add `file_hash` field to Session model
2. ✅ Create and run migration
3. ✅ Update JSONUploadForm validation
4. ✅ Update HomeView to store hash
5. ✅ Add basic unit tests

### Phase 2: Enhanced UX ✅ COMPLETED
1. ✅ Improve error messages with session details and clickable links
2. ✅ Update admin interface with hash display and search
3. ✅ Add comprehensive test coverage (10 new tests)
4. ✅ Update documentation

#### Phase 2 Implementation Details

**Enhanced Error Messages:**
- Clickable links to existing sessions when duplicates are detected
- Improved date/time formatting ("YYYY-MM-DD at HH:MM")
- User-friendly instructions to view existing session or upload different file
- Links open in new tab to preserve current form state
- **NEW**: Prominent red alert container for duplicate errors with Bootstrap styling
- Distinctive visual treatment separates duplicate errors from standard validation errors
- Enhanced with warning icon and "Duplicate File Detected" header

**Admin Interface Improvements:**
- Added `file_hash_short` column to list view (shows first 8 characters)
- Full hash display in detail view with copy functionality
- Enhanced search includes file hash field
- Organized fieldsets: Session Information, File Information, Player Data
- Collapsible Player Data section for cleaner interface
- Proper handling of legacy sessions without hashes

**Test Coverage Expansion:**
- Enhanced error message validation tests
- Clickable link functionality tests  
- Date/time formatting verification
- Admin interface integration tests
- Legacy session handling tests
- Search functionality validation

**Total Test Suite: 52 tests (38 original + 5 Phase 1 + 9 Phase 2)**

### Phase 3: Advanced Features (Optional)
1. Content-based similarity detection
2. Merge/replace options
3. Bulk upload protection
4. Performance optimizations

## Considerations

### 1. Backward Compatibility

- Existing sessions without hashes will have `null` values
- Migration should handle existing data gracefully
- Form validation should handle sessions without hashes

### 2. Edge Cases

- Very large files (memory usage during hashing)
- Network interruptions during upload
- Identical content with different filenames
- Manual database modifications

### 3. Performance Impact

- Hash generation adds processing time
- Database query overhead for duplicate checking
- Memory usage for large file processing

### 4. Security Considerations

- Hash collisions (extremely rare with SHA-256)
- File content validation before hashing
- Proper error handling to prevent information leakage

## Success Criteria

1. **Functional**: No duplicate sessions can be created from identical files
2. **User Experience**: Clear error messages when duplicates are detected
3. **Performance**: Upload process remains responsive
4. **Reliability**: 100% accuracy in duplicate detection
5. **Maintainability**: Clean, well-tested code that integrates seamlessly

## Estimated Timeline

- **Phase 1**: 2-3 days (core functionality)
- **Phase 2**: 1-2 days (enhanced UX)
- **Phase 3**: 3-4 days (advanced features, optional)

**Total**: 3-5 days for full implementation (Phases 1-2)