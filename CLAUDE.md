# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Server & Database
- Start server: `python manage.py runserver`
- Apply migrations: `python manage.py migrate`
- Load demo data: `python manage.py seed_demo`
- Create admin user: `python manage.py createsuperuser`

### Testing
- Run all tests: `python manage.py test`
- Run tests for a specific app: `python manage.py test <app_name>`
- Run a single test: `python manage.py test <app_name>.tests.<TestClass>.<test_method>`

### Specialized Tools
- Geocode existing users: `python manage.py backfill_geocoding`
- Verify Google Maps API key: `python manage.py check_maps_key`
- Standalone Maps check: `python scripts/check_google_maps.py`

### Environment Configuration
- **Google Maps API**: Requires `GOOGLE_MAPS_API_KEY` env var. Must enable both **Distance Matrix API** and **Geocoding API**.
- **Razorpay**: Requires `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` (test keys `rzp_test_...`) for real payment flow; otherwise falls back to simulation.

### Demo Access
- **Customer**: Any 10-digit number starting with 6-9. OTP is displayed as a flash message on-screen.
- **Verified Workers**: `9810000001`–`9810000010` (one per major category).
- **Society Operator**: `9800000001` (Delhi-NCR Workers Cooperative Society).
- **Institution (Builder)**: `9700000099` (Skyline Builders Pvt Ltd).
- **Federation Admin**: Django admin (`admin` / `Admin@12345`).

## Code Architecture

### Tech Stack
- **Backend**: Django 6.1, SQLite (dev).
- **Frontend**: Server-rendered HTML5, hand-written CSS, vanilla JS. Icons are inline SVG.
- **Auth**: Session-based mobile OTP login.
- **i18n**: Django translation framework. English and Hindi are fully implemented.

### High-Level Structure
The project is a Django application following a modular app-based architecture:
- `accounts/`: Custom User model, role management, and OTP-based authentication.
- `catalog/`: Service categories and individual services with pricing definitions.
- `workers/`: Worker profiles, verification workflows, availability, and geo-matching.
- `bookings/`: Booking lifecycle, status transitions, bulk requests, and complaints.
- `payments/`: Payment processing (simulated or Razorpay) and invoice generation.
- `reviews/`: Two-way rating system (Customer $\leftrightarrow$ Worker).
- `dashboard/`: Role-gated administrative interfaces for Federation and Society levels.
- `core/`: Public-facing pages, home, about, and i18n plumbing.
- `templates/`: Global template directory with app-specific subfolders.
- `static/`: Design system (CSS), vanilla JS, and SVG icon sprites.

### Key Mechanisms
- **Role Hierarchy & RBAC:** 
  - **Federation Admin** $\to$ Manages societies, appoints operators, and configures global pricing.
  - **Society Operator** $\to$ Approves/verifies workers into their society and claims bulk requests.
  - **Worker** $\to$ Fulfils bookings and manages availability.
  - **Customer/Institution** $\to$ Requests services. Institutions (`role=builder`) can create bulk requests.
- **Pricing Model:** Implements a "Simplified Pricing Model": `Total = Visit Charge + Labour Charge`. Labour can be **Fixed** or **Per-hour**. Material costs are strictly excluded from the data model and billing chain.
- **Bulk Booking Flow:** Institutions submit a `BulkServiceRequest` $\to$ a Society Operator claims it $\to$ the Operator assigns specific verified workers via `BulkAssignment`.
- **Geo-Matching:** Uses Google Maps Geocoding to turn typed addresses into coordinates and the Distance Matrix API to calculate real-road distance/ETA for "nearest worker" sorting.
- **Status Flow:** `Booking` follows a strict `STATUS_FLOW` (Requested $\to$ Assigned $\to$ Accepted $\to$ Arriving $\to$ Arrived $\to$ Started $\to$ Completed $\to$ Confirmed $\to$ Paid $\to$ Rated).
- **i18n:** Integrated Django translation framework. English and Hindi are fully implemented; others are registered and fall back to English.

### Governance & Permissions (CRUD Matrix)
| Entity | Create | Read | Update | Delete |
|---|---|---|---|---|
| Federation | Admin only | Admin: all. Federation-admin: own. Public: name only | Admin: rename/ban/commission. Federation-admin: own settings | Admin only |
| Society | Federation (under itself) or Admin (independent) | Admin: all. Federation: its own. Society-head: own | Federation: its societies (fieldwork toggle). Society-head: own profile. Admin: rename/ban/delete/promote | Admin only |
| Worker Verification | Worker (self-signup) | Admin: all + documents. Society-head: claimed workers | Admin only | Admin only |
| Society Membership | Society-head (from admin-verified pool only) | Admin, Federation (its societies), Society-head (own) | Society-head (own society) | — |
| Customer | Self (signup) | Admin: all + KYC docs. Self: own | Self: own | Admin (ban) |
| Pricing | Federation (own) / Independent Society (own) — **Phase 4** | Everyone, scoped | Federation-admin / independent-society-head | — |

### Project Roadmap
- **Phase 1 (Completed)**: Foundation (Governance hierarchy, RBAC, Admin $\to$ Federation $\to$ Society $\to$ Worker structure).
- **Phase 2**: Cross-federation matching engine, emergency auto-pick, privacy (hidden phone until acceptance).
- **Phase 3**: Federation/Society dashboards with income and deployment graphs, live status filters.
- **Phase 4**: Society ratings, federation/independent-society-owned pricing, commission engine.
- **Phase 5**: Wallet system (withdrawals), Razorpay live mode verification.
