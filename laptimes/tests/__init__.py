"""
Test suite for the laptimes application.

This package organizes tests into logical modules:
- test_models.py: Model functionality and business logic
- test_forms.py: Form validation and processing
- test_views.py: View logic and HTTP responses
- test_api.py: API endpoints and JSON responses
- test_admin.py: Django admin interface
- test_integration.py: End-to-end workflows
- test_file_management.py: File upload and duplicate detection
"""

# Import all test classes for test discovery
from .test_admin import *
from .test_api import *
from .test_file_management import *
from .test_forms import *
from .test_integration import *
from .test_models import *
from .test_views import *
