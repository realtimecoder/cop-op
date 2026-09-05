# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment
- **Python Executable**: `.\myvenv\Scripts\python.exe`
- **Run Server**: `.\myvenv\Scripts\python.exe manage.py runserver`
- **Migrations**:
  - Create: `.\myvenv\Scripts\python.exe manage.py makemigrations`
  - Apply: `.\myvenv\Scripts\python.exe manage.py migrate`

### Testing
- **Run All Tests**: `.\myvenv\Scripts\python.exe manage.py test`
- **Run Specific App Tests**: `.\myvenv\Scripts\python.exe manage.py test <app_name>`
- **Run Single Test**: `.\myvenv\Scripts\python.exe manage.py test <app_name>.tests.<TestClass>.<test_method>`

## Architecture Overview

Co-opSeva is a Django-based marketplace for verified cooperative labour services. It employs a role-based access control (RBAC) system to provide distinct experiences for different user personas.

### Core Apps
- `accounts`: Handles authentication, OTP-based login, user profiles, and role management (`User` model).
- `catalog`: Manages the service taxonomy, categories, and individual service offerings.
- `bookings`: Manages the booking lifecycle, including bulk requests and scheduling.
- `workers`: Handles worker profiles, verification, skills, and cooperative affiliations.
- `dashboard`: Provides role-specific administrative and moderation interfaces.
- `payments`: Implements the digital wallet and payment tracking.
- `reviews`: Manages worker ratings and feedback.
- `core`: General site pages (Home, About, Contact, Pricing).

### Key Design Patterns
- **Role-Based Theming**: CSS variables are overridden in `base.html` based on `user.role` to change the site's visual identity for different personas.
- **Fixed Pricing**: The platform avoids bidding/quotations, utilizing a fixed-price ledger system.
- **Geocoding**: Integration with Google Maps API for location-based worker discovery.
