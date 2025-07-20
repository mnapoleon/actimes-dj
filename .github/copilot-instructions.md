# Copilot Instructions

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview

This is a Django web application for analyzing racing lap times from Assetto Corsa JSON files. The application features:

- SQLite database with Sessions and Laps tables
- File upload functionality for JSON race data
- Data visualization with fastest/slowest lap highlighting
- Driver filtering and sorting capabilities
- Session management with track and car information

## Code Style Guidelines

- Follow Django best practices and conventions
- Use Django's ORM for database operations
- Implement proper error handling and validation
- Use Django forms for file uploads
- Follow PEP 8 style guidelines
- Use Bootstrap for responsive UI design

## Key Components

- **Models**: Session and Lap models with foreign key relationships
- **Views**: Class-based views for upload and display functionality
- **Templates**: Bootstrap-based responsive templates
- **Forms**: Django forms for file upload and filtering
- **Static Files**: CSS, JS, and Bootstrap assets

## Database Schema

- **Session**: Track, car, session type, upload timestamp
- **Lap**: Lap number, total time, sector times, driver, tyre, cuts (foreign key to Session)

When generating code, prioritize clean, maintainable Django patterns and ensure proper database relationships.
