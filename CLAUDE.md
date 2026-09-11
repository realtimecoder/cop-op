# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment
- **Python Executable**: `.\myvenv\Scripts\python.exe`
- **Run Server**: `.\myvenv\Scripts\python.exe manage.py runserver`
- **Migrations**:
  - Create: `.\myvenv\Scripts\python.exe manage.py makemigrations`
  - Apply: `.\myvenv\Scripts\python.exe manage.py migrate`
- **Env Vars**: Use a `.env` file for `GOOGLE_MAPS_API_KEY`, `RAZORPAY_KEY_ID`, and `RAZORPAY_KEY_SECRET`.

### Testing
- **Run All Tests**: `.\myvenv\Scripts\python.exe manage.py test`
- **Run Specific App Tests**: `.\myvenv\Scripts\python.exe manage.py test <app_name>`
- **Run Single Test**: `.\myvenv\Scripts\python.exe manage.py test <app_name>.tests.<TestClass>.<test_method>`

### Custom Management Commands
- **Seed Demo Data**: `.\myvenv\Scripts\python.exe manage.py seed_demo`
- **Backfill Geocoding**: `.\myvenv\Scripts\python.exe manage.py backfill_geocoding`
- **Verify Maps API Key**: `.\myvenv\Scripts\python.exe manage.py check_maps_key`
- **Check Worker Status**: `.\myvenv\Scripts\python.exe manage.py check_worker_status`
- **Debug Locations**: `.\myvenv\Scripts\python.exe manage.py debug_locations`
- **Fix Service Offerings**: `.\myvenv\Scripts\python.exe manage.py fix_offerings`

## Architecture Overview
Co-opSeva is a Django-based marketplace for verified cooperative labour services. It employs a role-based access control (RBAC) system to provide distinct experiences for different user personas.

### Core Apps
- `accounts`: Custom `User` model, OTP-based login, and role management. Handles the "Smart Onboarding" flow: `login_request` $\rightarrow$ `verify_otp` $\rightarrow$ `select_role` $\rightarrow$ `complete_profile`.
- `catalog`: Service taxonomy (`ServiceCategory` $\rightarrow$ `Service`).
- `bookings`: Booking lifecycle. Manages individual `Booking` records and institutional `BulkServiceRequest` $\rightarrow$ `BulkAssignment` flows (including "Rapid Booking" via the matching engine).
- `workers`: Manages the cooperative hierarchy (`Federation` $\rightarrow$ `Society` $\rightarrow$ `WorkerProfile`). Tracks worker skill grades, certificates, and `WorkerServiceOffering` (linking workers to services).
- `dashboard`: Role-specific administrative and moderation interfaces (e.g., Worker Verification Queue, Federation Pricing).
- `payments`: Digital wallet, payout splits, and platform commissions via Razorpay.
- `reviews`: Worker ratings and feedback.
- `core`: General site pages and site-wide context processors.

### Shared Services & Utilities
- **Matching Engine** (`bookings/services.py`): Logic to find best workers based on road distance (Google Maps), ratings, and fairness (work distribution). Requires `WorkerServiceOffering` for eligibility.
- **Geo-Service** (`workers/geo.py`): Centralized logic for address geocoding and road-distance calculations via Google Maps APIs.

### Key Integrations & Config
- **Payments**: Razorpay gateway. High precision is maintained using the `decimal` module for all financial calculations.
- **Geocoding**: Google Maps Distance Matrix and Geocoding APIs for location-aware matching.
- **Internationalisation**: Multi-language support for major Indian languages + English; Timezone set to `Asia/Kolkata`.
- **Auth**: Session-based authentication. Public browsing is allowed, but booking, profiles, and dashboards require authentication.

### Key Design Patterns
- **Role-Based Theming**: CSS variables are overridden in `base.html` based on `user.role`.
- **Status-Driven State Machine**: `Booking` and `BulkServiceRequest` models implement strict status flows to ensure valid transitions.
- **Fixed-Price Ledger**: Uses a snapshot pricing model (capturing `visit_charge` and `labour_charge` at booking) to prevent price fluctuations during a job.
- **Fairness-Aware Ranking**: The `recommended_score` explicitly penalizes recently active workers to ensure equitable work distribution.
- **Graceful Degradation**: High-dependency features (Maps, Payments) have built-in fallbacks (e.g., rating-based sorting or simulated payments) if API keys are missing.
- **File Uploads**: Custom limits (10MB) to accommodate phone-camera photos.
