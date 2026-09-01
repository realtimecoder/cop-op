# Co-opSeva — Cooperative Labour Service Marketplace

A working Django + HTML/CSS/JS implementation of the Co-opSeva SRS (v2.0,
Simplified Pricing Model), covering the MVP scope defined in Section 14 of
the specification.

## Tech stack
- **Backend:** Django 6.1 (Python), SQLite (swap `DATABASES` in
  `coopseva/settings.py` for PostgreSQL/MySQL in production)
- **Frontend:** Server-rendered HTML5 + hand-written CSS (no framework) +
  vanilla JS. All icons are inline SVG — no emoji, no external icon fonts.
- **Auth:** Session-based mobile OTP login (`django.contrib.sessions`), not
  token/JWT based, per your requirement.
- **i18n:** Django's built-in translation framework. English + Hindi are
  fully wired (Hindi strings translated in `locale/hi/`); Bengali, Tamil,
  Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi and Urdu are
  registered as selectable languages and will fall back to English until
  their `.po` files are translated — the framework and language switcher
  are already fully functional for all eleven.

## Quick start

```bash
cd coopseva
python3 -m venv venv && source venv/bin/activate     # optional but recommended
pip install -r requirements.txt

python3 manage.py migrate
python3 manage.py seed_demo          # loads categories, services, 5 verified workers
python3 manage.py createsuperuser    # or use the seeded one below
python3 manage.py runserver
```

Visit **http://127.0.0.1:8000/**

### Demo credentials
| Role | How to log in |
|---|---|
| Any customer | Go to **Log in**, enter any 10-digit number starting 6-9 (e.g. `9123456789`). The OTP is shown on-screen as a flash message (no real SMS gateway is wired up — plug in MSG91/Twilio in `accounts/views.py::login_request`). |
| Demo verified workers | Phones `9810000001`–`9810000010` — ten workers, one per major category (Ramesh/Electrician, Suresh/Plumber, Anita/Domestic Helper, Vikram/Carpenter, Geeta/Painting, Pooja/Salon, Imran/AC Repair, Manoj/Cleaning, Rekha/Caregiver, Sanjay/Driver) — already verified by the seed script. |
| Demo society operator (approves/rejects new workers into their society) | Phone `9800000001` — operates "Delhi-NCR Workers Cooperative Society" (the 10 demo workers above already belong to it). Log in via normal OTP flow, then visit `/dashboard/workers/verification/` or `/bookings/bulk/queue/`. |
| Demo institution (for testing bulk/multi-worker requests) | Phone `9700000099` ("Skyline Builders Pvt Ltd", role=builder). Log in via OTP, then visit `/bookings/bulk/new/`. |
| Federation administrator (full pricing + admin access, including creating societies) | Django admin: username `admin`, password `Admin@12345`. This account has `role=federation` **and** `is_superuser=True`, so it can also log in through the normal OTP flow once you set its phone number, or via `/admin/`. Manage societies at `/dashboard/societies/`. |

Change the admin password immediately in any non-demo environment.

## App structure
```
accounts/    Custom User model, roles, OTP login/registration, profile
catalog/     Service categories & services, fixed/hourly pricing fields
workers/     Worker profiles, verification, documents, availability,
             category-change requests, society model, geo-matching
bookings/    Booking lifecycle, availability checks, status flow, complaints
payments/    Simulated digital payment + invoice generation
reviews/     Ratings/reviews (customer→worker) and worker→customer feedback
dashboard/   Role-gated federation/society/support back-office screens,
             pricing config, category-change approvals, customer/worker history
core/        Public homepage, static pages, language-switch plumbing
templates/   All HTML templates (base.html + one folder per app)
static/      style.css (design system), app.js, SVG icon sprite
```

## Cross-check against the SRS

**Section 3 — Simplified Pricing Model**
- Fixed visit charge lives on `ServiceCategory.fixed_visit_charge`, editable
  only from `/dashboard/pricing/` by users with `role=federation` (FR-017,
  FR-019, BR-015 — enforced by `dashboard.views.is_federation_admin`).
- Fixed labour charge lives on `Service.fixed_labour_charge`, same
  restriction (FR-018).
- Material cost has **no model field anywhere in the payment/invoice
  chain** — it cannot be collected or invoiced even by accident (FR-046 to
  FR-050).
- `Booking.total_amount` = visit charge + labour charge only (Section 3.5,
  12.1); builder/team bookings multiply labour charge × workers × days
  (Section 12.4, FR-033).
- `Payment.compute_settlement()` implements the worker payout / cooperative
  fee split from `WorkerProfile.payout_percentage` (Section 3.6, 12.3).

**Section 4 — Scope.** Quotation, bidding, and variable/worker-set/
customer-set pricing are structurally impossible: there is no price input
anywhere in the customer- or worker-facing UI, only read-only price tickets
sourced from the two admin-configured fields above.

**Section 5 — Functional requirements**
- FR-001–005 registration/OTP/roles/profile → `accounts` app.
- FR-006–012 worker verification/documents/skill grade → `workers` app +
  `/dashboard/workers/verification/` (society-operator role).
- FR-013–016 service catalogue/search → `catalog` app.
- FR-017–021 fixed pricing configuration → `dashboard.views.pricing_config`.
- FR-022–027 worker comparison & recommended ranking → `workers.views.
  worker_list_for_service`; `WorkerProfile.recommended_score()` implements
  the FR-025 weighted formula (0.35 rating + 0.25 skill + 0.20 availability
  + 0.15 distance + 0.05 reliability).
- FR-028–033 booking creation, status flow, recurring/emergency/builder
  bookings → `bookings` app; `Booking.STATUS_FLOW` encodes the exact
  Requested→…→Rated sequence from Section 5.6.
- FR-034–038 geo/matching — location fields exist on `User`/`WorkerProfile`
  (lat/lng, service radius); a real matching/geocoding service (Google Maps,
  Mapbox, or PostGIS) should replace the placeholder distance value used in
  `recommended_score()` before production use.
- FR-039–045 work execution — `Booking.before_photo/after_photo/
  completion_notes`, warranty on `Service.warranty_days`.
- FR-046–050 material handling — intentionally absent from `payments`/
  `bookings` billing fields, as required.
- FR-051–056 payments/invoicing → `payments` app; gateway calls are
  simulated (`Payment` is marked `SUCCESS` immediately) — swap in Razorpay/
  PayU/UPI intent flow in `bookings.views.make_payment`.
- FR-057–061 ratings/reviews, verified-only → `reviews` app; a `Review` can
  only be created against a `Booking` the customer owns.

**Section 9/10 — Business rules & roles.** `accounts.models.User.Role`
enumerates every role from the SRS role table; `dashboard.views` gates
every admin screen by role.

**Section 12 — Financial settlement.** See `Payment.compute_settlement()`
and the worked examples reproduced in `seed_demo` / pricing policy page.

**Section 14 — MVP.** Every checkbox in Section 14 is implemented:
customer/worker registration, society verification (dashboard queue),
service categories, fixed visit/labour charge configuration, worker
comparison, fixed-price booking, digital payment (simulated), invoice,
rating, complaint, society dashboard, Hindi-English interface, and worker
records (`WorkerProfile`) that can hold welfare/insurance document types.
Quotation and bidding modules are, as required, absent.

## What is intentionally simplified for this reference build
- **OTP delivery** is shown on-screen, not sent via SMS — wire up a real
  gateway before going live.
- **Payments** are simulated (`Payment.status = SUCCESS` on submit) — wire
  up a real gateway (Razorpay/UPI) before going live.
- **Geo-matching / "nearest worker"** now uses the real Google Maps
  Distance Matrix API (see the "Nearest worker matching" section below) —
  you just need to supply an API key.
- **AI demand forecasting / anomaly detection (Section 13)** are out of
  scope for this build (SRS marks them as post-MVP / "should" not "shall"
  in several places) — the data model (bookings, categories, localities) is
  already shaped to support adding this later, e.g. as a scheduled job that
  reads `Booking` aggregates.
- **9 of the 11 configured languages** (all but English/Hindi) need their
  `.po` files translated (`locale/<code>/LC_MESSAGES/django.po`) — the
  switcher, cookie persistence, and RTL handling for Urdu are already wired
  up and tested.

## Recent updates (this revision — v6, Phase 1 of the governance overhaul)

This is Phase 1 of a much larger requested redesign (full CRUD/RBAC
matrix, cross-federation worker matching, financial/wallet system,
graphs, real Razorpay live mode). Phase 1 builds the **foundation**
everything else depends on — a real Admin → Federation → Society →
Worker governance hierarchy with proper role-based CRUD permissions.
Later phases (matching engine, dashboards/graphs, wallets, commission
engine, live payments) are documented but not yet built — see the
roadmap at the bottom of this section.

### CRUD authority matrix (industry-standard RBAC)

| Entity | Create | Read | Update | Delete |
|---|---|---|---|---|
| Federation | **Admin only** | Admin: all. Federation-admin: own. Public: name only | Admin: rename/ban/commission. Federation-admin: own settings | Admin only |
| Society | Federation (under itself) **or** Admin (independent) | Admin: all. Federation: its own. Society-head: own | Federation: its societies (fieldwork toggle). Society-head: own profile. Admin: rename/ban/delete/promote | Admin only |
| Worker skill/certificate verification | Worker (self-signup) | Admin: all + documents. Society-head: claimed workers | **Admin only** | Admin only |
| Worker → Society membership | Society-head (from admin-verified pool only) | Admin, Federation (its societies), Society-head (own) | Society-head (own society) | — |
| Customer | Self (signup) | Admin: all + KYC docs. Self: own | Self: own | Admin (ban) |
| Pricing | Federation (own) / Independent Society (own) — **Phase 4** | Everyone, scoped | Federation-admin / independent-society-head | — |

### What Phase 1 actually changed

1. **`Federation` is now a real model**, not just a role label. Only
   Admin (`is_platform_admin` — superuser or `role=platform_admin`) can
   create one, at `/dashboard/federations/`, and appoint who administers
   it (by phone number — the account is created/promoted automatically).
2. **`Society.federation` is now a real, nullable foreign key.** A
   society is either governed by a federation, or **independent**
   (`federation=None`) — an independent society is meant to run its own
   pricing/queries/work (pricing part lands in Phase 4).
3. **Federation creates its own societies; Admin creates independent
   ones.** `/dashboard/societies/` now branches on who's asking:
   a federation's own admin can only create/manage societies under
   itself; Admin can create an independent society or attach one to any
   federation.
4. **Join/invite flow, both directions, receiver must accept**
   (`FederationJoinRequest`). A federation can invite an independent
   society (`/dashboard/independent-societies/`); an independent
   society's head can request to join a federation
   (`/dashboard/federation-directory/`). Either way, only the
   **receiving** side can accept/reject
   (`/dashboard/join-requests/`) — verified with a test that a society
   cannot self-accept its own outgoing request, and vice versa. Once
   accepted, `society.federation` is set — the society is now expected
   to follow that federation's pricing and policies (enforcement lands
   in Phase 4 once federation-scoped pricing exists).
5. **Skill/certificate verification is now Admin-only, structurally
   separate from society membership.** Previously a society operator
   verified AND claimed a worker in one action. Now:
   - `/dashboard/workers/verification/` (Admin only) — identity/skill
     check, sets `verification_status`. Confirmed with a test that a
     society head gets redirected away from this page (403/302).
   - `/dashboard/workers/claim-queue/` (society-head only) — lists
     admin-verified, still-unclaimed workers; claiming one sets
     `worker.society` to the head's own society. Confirmed a
     newly-verified worker has `society=None` until explicitly claimed.
6. **Society-head "does own fieldwork" toggle** (`head_performs_
   fieldwork`) — only the society's own federation can flip it; not
   meaningful for an independent society (its head always works,
   handles pricing, and resolves queries by definition, per the
   governance model).
7. **Admin governance actions** (Section 9): rename, ban-for-a-period
   (`ban_until`), accept resignation, hard-delete, and
   promote-independent-society-to-federation — all Admin-only, all on
   `/dashboard/societies/` and `/dashboard/federations/`.

### What's NOT done yet (honest — deferred to later phases)

- **Phase 2** — cross-federation/cross-society "best worker" matching
  (nearest + rest-day fairness + rating + completions, with federation
  name/rating shown), emergency-booking auto-pick-and-book, and
  federation being invisible to the customer until acceptance (worker
  phone number reveal on accept).
- **Phase 3** — Federation and Society dashboards with the two
  requested graphs each (workers deployed over time, income earned over
  time) and the live booked/working-status filter, filterable by society.
- **Phase 4** — society rating computed from its workers' ratings,
  **federation/independent-society-owned pricing** (currently pricing
  is still platform-global — this is the biggest remaining structural
  change), commission engine + monthly admin payout tracking, and
  promote-to-federation's pricing implications.
- **Phase 5** — wallet + withdrawal for every party, and documentation
  for going from Razorpay test keys to live keys (the integration code
  itself already supports this — see the Razorpay section below — this
  phase is really just verification + wallet-specific payout wiring).

### Demo accounts for this hierarchy
| Role | Phone | Notes |
|---|---|---|
| Federation admin | `9900000001` | Administers "Delhi-NCR Labour Federation" |
| Society head (federated) | `9800000001` | Heads "Delhi-NCR Workers Cooperative Society" — under the federation above, all 10 demo workers |
| Society head (independent) | `9800000002` | Heads "Gurgaon Independent Workers Society" — no federation, for testing the join/invite flow |

## Recent updates (this revision — v5)

**Fixed: "Federation" and "Society" were labels, not a real structure.**
Previously any worker could self-register and start working immediately
— there was no actual Federation → Society → Worker hierarchy, just role
names on the User model. This revision makes it real:

1. **Society is now a real cooperative unit with an operator.**
   `Society.operator` is a dedicated account (role=society) appointed by
   a federation administrator. Only that operator can claim/verify
   workers into their own society — workers can no longer pick or be
   auto-assigned a society themselves. Confirmed with a test: Operator A
   cannot see or claim a worker already claimed by Operator B's society;
   an unclaimed worker is visible to any operator until one of them
   approves (claims) them.
2. **Federation administration now manages societies.**
   `/dashboard/societies/` (federation-admin only) lets you create a new
   cooperative society and appoint its operator by phone number — the
   operator's account is created automatically (role promoted to
   `society`) if it doesn't already exist, since self-registering with
   the society role is deliberately not exposed in public sign-up.
3. **The "Institution" flow (bulk/multi-worker requests) is now real,
   not just a price multiplier.** Previously, `workers_required` on a
   single `Booking` only multiplied the price — it never created actual
   separate worker assignments. Now:
   - Institutions (`role=builder`) submit a `BulkServiceRequest`
     (`/bookings/bulk/new/`) specifying a service, how many workers, for
     how many days.
   - Any society operator can **claim** it for their own cooperative
     (`/bookings/bulk/queue/`), then hand-pick that many of their *own*
     verified workers to fulfil it (`/bookings/bulk/<id>/assign/`) — a
     `BulkAssignment` row is created per worker, each with its own
     completion status and payout.
   - The institution confirms completion once done, which splits the
     total payment across every assigned worker individually (Section
     12 "Track wages") rather than a single lump sum.
   - Verified end to end with a real test: 2 workers in one cooperative
     society assigned to a 2-worker, 3-day request — correct total
     (₹5,550), correct per-worker payout split (₹2,164.50 each) after
     completion.

This is the real Federation → Society → Worker structure the SRS
describes, and the real Institution → Bulk request → Cooperative
assignment → Completion flow — not the earlier price-multiplier
approximation.

## Recent updates (this revision)

This revision fixes a critical booking bug and adds several features
requested after the initial build:

1. **Booking creation bug — fixed.** Every non-builder booking was
   silently failing: `workers_required`/`duration_days` were required
   model fields that the template only rendered for builder-type
   services, so Django's form validation failed for everything else and
   the booking was never created (the page just reloaded with no visible
   error). These fields are now optional at the form layer with sane
   defaults applied in the view — confirmed fixed for both fixed-price
   and hourly bookings, which now correctly appear in **My bookings**
   and on the worker's dashboard.
2. **Full Urban-Company-style catalogue.** `Browse services` now lists 16
   categories and 63 services/sub-services — Salon for Women, Spa for
   Women, Salon & Massage for Men, AC & Appliance Repair, Electrician,
   Plumber, Carpenter, Painting & Waterproofing, Cleaning, Pest Control,
   Home Renovation, Domestic Helper, Caregiver, Driver, Gardener, and
   Construction Labourer — each with several realistic sub-services.
3. **Hourly pricing.** Services can now be priced **Fixed** or **Per
   hour** (`Service.pricing_type`), configurable only by the federation
   administrator from `/dashboard/pricing/`. Hourly services collect the
   number of hours at booking time and bill visit charge + (rate × hours).
4. **Worker availability / no double-booking.** Booking a worker checks
   both (a) any date they're already committed to an active booking, and
   (b) dates the worker has manually blocked from their own dashboard
   (`/workers/dashboard/availability/`). Blocked/occupied dates are
   greyed out with an inline message on the booking date picker, and the
   server rejects the booking even if the picker is bypassed.
5. **Worker dashboard is now work-only.** No service browsing or booking
   UI lives there. It shows: full signup profile (name, phone, address,
   categories, skill grade, experience, languages, bio), every assigned
   booking with the **income earned** and **customer review** for that
   specific job, and a **total lifetime income** card.
6. **Category changes require federation-admin approval.** A worker can
   request new/changed categories from their dashboard
   (`/workers/dashboard/request-category-change/`); their current
   categories stay active and unaffected until a federation admin
   approves the request from `/dashboard/workers/category-changes/`,
   at which point the new categories (and matching service offerings)
   apply automatically.
7. **Full admin history.** `/dashboard/customers/` and `/dashboard/workers/`
   list every customer/worker with drill-down detail pages showing their
   complete booking history, total spend or earnings, reviews, documents,
   and (for workers) category-change history.
8. **Image upload display bug — fixed.** Uploads always worked on the
   backend, but nothing displayed them back to the user. Added: a header
   avatar, a profile-photo preview on the profile page, and image
   thumbnails (with a "View file" fallback for non-image documents) on
   both the worker's own documents page and the admin worker-detail page.
9. **Pricing-policy page clarified.** The public `/pricing-policy/` page
   is intentionally **read-only** — anyone (including anonymous visitors)
   can see it. Only `/dashboard/pricing/` (federation-admin only) can
   actually edit prices; a direct "Edit pricing" link now appears on the
   public page for logged-in federation admins to avoid the confusion of
   looking for an edit form on the wrong page.

## Recent updates (this revision — v4)

**Root cause of "same address, no worker found" — two real bugs fixed:**

1. **Addresses were never geocoded.** Typing an address into the profile
   form only stored it as text — it never became latitude/longitude.
   Only the "Find nearest to me" GPS button (browser location) produced
   coordinates. So two accounts with an identical typed address still
   had *no* coordinates to compare, and nearest-worker matching had
   nothing to work with. **Fixed**: saving a profile (customer or
   worker — they share the same `User.address` field) now automatically
   calls Google's **Geocoding API** and stores the resulting
   latitude/longitude, with no extra UI needed. The worker-comparison
   page also now falls back to a logged-in customer's saved (geocoded)
   address automatically when they haven't clicked the GPS button —
   confirmed with a same-address test showing a ~0km match.
2. **Worker onboarding never created service offerings.** Selecting
   categories during onboarding saved the categories, but never created
   the `WorkerServiceOffering` rows that the worker-comparison page
   actually queries — so a newly onboarded worker could never appear
   for *any* service, regardless of address. **Fixed**: onboarding now
   auto-creates an offering for every active service in each selected
   category, the same way category-change approval already did.

**New tools:**
- `python3 manage.py backfill_geocoding` — geocodes every existing
  user's address who doesn't have coordinates yet (for accounts created
  before a Maps key was configured, or before this fix), without
  needing them to re-save their profile.
- `scripts/check_google_maps.py` — standalone (no Django needed) script
  that runs 5 real Distance Matrix test cases against fixed Delhi
  landmarks and tells you plainly whether your key works, or exactly
  which of 4 common misconfigurations is blocking it.

**Note on required Google APIs**: the nearest-worker feature now needs
**two** APIs enabled on the same Google Cloud project — **Distance
Matrix API** (for worker-to-customer travel distance) and **Geocoding
API** (for turning typed addresses into coordinates). Enable both at
https://console.cloud.google.com/google/maps-apis/api-list — the same
`GOOGLE_MAPS_API_KEY` covers both.

## Previous updates (v3)

Fixes and features added after the previous revision's feedback:

1. **"Worker not showing" investigated — not a bug.** New worker
   signups start with `verification_status = pending`. Until a society
   operator approves them from `/dashboard/workers/verification/`, they
   correctly don't appear in customer-facing worker lists — only
   already-verified workers do. Confirmed with a reproduction test that
   the recommendation/matching engine itself has no bug: once verified,
   a new worker appears and ranks exactly like any other. Added a clear
   on-dashboard notice so workers understand why they're not visible yet.
2. **Real-time status — no more "simulate advance" button.** Every status
   change is now caused by a real action taken by the right person:
   the assigned **worker** clicks Accept / Reject / "I'm heading there" /
   "I have arrived" / Start work / Mark completed (each transition is
   validated server-side — a worker can't skip steps, and a customer
   posting to a worker-only endpoint gets an HTTP 403, confirmed by test).
   The **customer** then clicks "Confirm work is done" before paying.
   The booking-detail page polls a small JSON endpoint every 8 seconds
   and reloads automatically the moment the status actually changes —
   genuinely live, not a timer or a fake progression.
3. **Dot-step progress tracker** replaces the old percentage bar —
   a horizontal row of dots/labels (Requested → Assigned → Accepted →
   Arriving → Arrived → Started → Completed → Confirmed → Paid → Rated),
   with a pulsing highlight on the current step and a filled marigold
   check on completed steps. Cancelled/rejected bookings show a plain
   status message instead of the stepper.
4. **Razorpay integration, test mode.** `payments/razorpay_client.py`
   wraps the official `razorpay` SDK. When `RAZORPAY_KEY_ID` /
   `RAZORPAY_KEY_SECRET` (test keys, starting `rzp_test_`) are set, real
   Razorpay Checkout opens for payment and the signature is verified
   server-side in `razorpay_callback()` before the booking is marked
   paid. Without keys configured, payments fall back to a clearly
   labelled simulation (`Payment.is_simulated = True`, shown as a badge
   on the invoice) so the flow never breaks. See the dedicated Razorpay
   section below for setup steps.
5. **Pricing policy is now federation-admin-only.** `/pricing-policy/`
   requires `role=federation` (or superuser) and redirects everyone
   else; the link was removed from the public nav and footer entirely.
   Customers still see live pricing on every service and worker card at
   booking time — this only restricts the single dedicated rate-card page.
6. **All 11 languages now have real translations**, not just English and
   Hindi. Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam,
   Punjabi and Urdu each have ~90 of the highest-visibility strings
   translated (navigation, homepage, login/OTP, booking flow, worker
   dashboard) — confirmed rendering correctly per language, including
   Urdu's right-to-left layout. Less-common strings on deeper admin
   pages still fall back to English; extend `locale/<code>/LC_MESSAGES/
   django.po` for full coverage.
7. **"Book again" feature.** A completed, paid, and rated booking shows
   a **Book again with this worker** button that takes the customer
   straight back to the booking form for that exact service + worker.
8. **Profile / document image upload — root cause found and fixed.**
   Uploads were being silently rejected with no visible error whenever
   the browser sent something Django's `ImageField` validator couldn't
   parse — most commonly an iPhone photo saved in **HEIC** format, which
   Pillow can't read without an extra plugin. The form now: (a) shows
   every field's validation errors directly under the upload control,
   (b) explicitly checks content-type and gives a plain-language message
   telling the person to switch their camera to "Most Compatible" mode
   or share the photo via WhatsApp first (which auto-converts it), and
   (c) enforces a clear, visible file-size limit (5MB for profile
   photos, 8MB for worker documents) instead of an opaque failure.
   `DATA_UPLOAD_MAX_MEMORY_SIZE`/`FILE_UPLOAD_MAX_MEMORY_SIZE` were also
   raised to 10MB so a normal phone photo never gets cut off before
   reaching that validation. Verified with real (not fake) oversized and
   correctly-typed images.
9. **Google Maps key verification command.** Run
   `python3 manage.py check_maps_key` after setting `GOOGLE_MAPS_API_KEY`
   — it makes one real Distance Matrix call (Connaught Place → India
   Gate, Delhi) and tells you plainly whether the key works, or exactly
   which of the four common misconfigurations (API not enabled, billing
   not enabled, key restrictions, wrong key) is blocking it. The nearest-
   worker sorting logic itself was re-verified correct with a mocked
   multi-worker response — distances are matched to the right worker,
   not shuffled.

## Razorpay test-mode setup

1. Sign up / log in at https://dashboard.razorpay.com
2. Toggle **Test Mode** (top-left switch in the dashboard) — this is
   critical, live keys will actually attempt to charge real cards.
3. Go to **Settings → API Keys → Generate Test Key**. Copy the Key ID
   (starts `rzp_test_`) and Key Secret.
4. Set them as environment variables before running the server:
   ```bash
   export RAZORPAY_KEY_ID="rzp_test_xxxxxxxxxxxx"
   export RAZORPAY_KEY_SECRET="xxxxxxxxxxxxxxxxxxxx"
   python3 manage.py runserver
   ```
5. On the payment page, use Razorpay's published test instruments —
   card `4111 1111 1111 1111` with any future expiry and any CVV, or any
   test UPI ID — Razorpay's test mode never contacts a real bank.
6. Without these two variables set, the **Pay now** button still works
   end to end, just via the simulated fallback (clearly labelled as such
   on the invoice) so local development/demos never get stuck.

## Nearest worker matching (Google Maps Distance Matrix)

The worker-comparison page (`/workers/for-service/<id>/`) has a
**"Find nearest to me"** button and a **Nearest** sort option that use real
road distance and travel time from Google's Distance Matrix API — not a
straight-line estimate.

### How it works
1. Customer clicks **Find nearest to me** → the browser's own Geolocation
   permission prompt appears → on approval, the coordinates are appended
   to the URL (`?lat=..&lng=..&sort=nearest`) and, if logged in, saved to
   their profile via `POST /accounts/update-location/` for reuse later.
2. `workers/geo.py::annotate_workers_with_distance()` sends one Distance
   Matrix request (one origin, many destinations) to Google and attaches
   `distance_km` / `duration_min` / `duration_text` to each `WorkerProfile`
   in the list.
3. Workers are then sorted nearest-first. Workers without a saved location
   (see below) are pushed to the end rather than the top.
4. Workers also get a **"Use my current location"** button on their
   onboarding page (`/workers/onboarding/`) so their base location is on
   file for this to work at all — without it, a worker simply won't have
   a distance shown.

### Enabling it
1. Get a key: https://console.cloud.google.com/google/maps-apis →
   enable **both** the **Distance Matrix API** and the **Geocoding
   API** on the same project (and enable billing — Google requires a
   billing account even within the free monthly quota). Distance Matrix
   computes worker-to-customer travel time; Geocoding turns a typed
   address into coordinates in the first place — both are needed for
   the full "nearest worker" flow to work end to end.
2. Set it as an environment variable before running the server:
   ```bash
   export GOOGLE_MAPS_API_KEY="your-key-here"
   python3 manage.py runserver
   ```
   (On Windows: `set GOOGLE_MAPS_API_KEY=your-key-here`, or add it to a
   `.env` file loaded by your process manager in production.)
3. That's it — no code changes needed. Until a key is set, the page shows
   an inline notice explaining that live distance isn't available yet, and
   sorting quietly falls back to the existing rating/experience/
   availability options, so nothing breaks.
4. **Verify the key actually works** before relying on it — two options:
   - **Standalone script (no Django needed)**, good for testing a key on
     any machine before it's even deployed:
     ```bash
     export GOOGLE_MAPS_API_KEY="your-key-here"
     python3 scripts/check_google_maps.py
     ```
     This has one dependency (`requests`/standard library only, actually
     no extra install needed) and runs 5 real Distance Matrix calls
     against fixed Delhi landmarks (short/medium/long distances, plus a
     multi-destination call mirroring the real worker-comparison
     request), printing a clear PASS/FAIL with the actual distance/time
     for each. On failure it tells you plainly which of the 4 usual
     causes is likely: API not enabled, billing not enabled, key
     restrictions, or a bad/mistyped key.
   - **Django management command**, if you'd rather check from inside
     the running project:
     ```bash
     python3 manage.py check_maps_key
     ```

### Notes / limits
- Google's free tier covers a generous number of Distance Matrix calls per
  month; each page load with location enabled costs one API call (one
  origin × up to 25 destinations per call). For very high traffic,
  consider caching worker-to-locality distances or bucketing by pincode
  instead of calling per page view.
- `mode=driving` is hardcoded in `workers/geo.py` — change to `walking` or
  `two_wheeler` (India-specific) if that fits your worker fleet better.
- If Google returns a non-OK status for a specific worker (e.g. it can't
  route to that lat/lng), that worker is simply excluded from distance
  sorting for that request rather than breaking the whole page.

## Manual QA performed before hand-over (this revision)
Every item below was executed via Django's test client on a freshly
migrated + seeded database and confirmed passing:
- All 16 category pages, all 63 service detail pages, and all 63
  worker-comparison pages return `200` — zero broken pages across the
  entire expanded catalogue.
- **Booking bug fix confirmed**: a fixed-price booking (Fan installation)
  and an hourly booking (Daily household help, 3 hours) both create
  successfully, compute the correct total (₹1,150 and ₹550 respectively),
  and appear in the customer's **My bookings** and the worker's dashboard.
- **Double-booking prevention confirmed**: booking the same worker again
  on a date they already have an active job blocked with a clear message;
  a manually-blocked (leave) date is blocked the same way; a date whose
  earlier booking already reached payment+review correctly frees up
  again (a completed job doesn't hold the calendar forever).
- **Category-change approval confirmed end-to-end**: a worker's
  categories are provably unchanged right up until a federation admin
  approves the request, at which point they flip over and matching
  service offerings are auto-created; a rejected request leaves the
  worker's categories untouched.
- **Hourly pricing config confirmed**: federation admin can switch a
  service between Fixed and Per-hour and back, and the change is
  reflected immediately in the public pricing policy page and the
  worker-comparison price ticket.
- **Image upload display confirmed**: profile photo appears in the header
  avatar and on the profile page immediately after upload; worker
  documents show a thumbnail (or a "View file" link for non-image types)
  both on the worker's own documents page and the admin worker-detail page.
- **Admin history confirmed**: `/dashboard/customers/<id>/` and
  `/dashboard/workers/<id>/` correctly aggregate total spend / total
  income and list every booking, review, complaint, and document for
  that person.
- Society-operator worker verification and complaint resolution retested
  and still passing after all of the above changes.

## Manual QA performed at initial hand-over
Every flow below was executed end-to-end via Django's test client during
development and returned the expected HTTP status / redirect:
- Anonymous browsing of home, category list, category detail, service
  detail, worker comparison, worker profile, how-it-works, about, contact,
  pricing policy — all `200`, all reachable **without** logging in.
- Booking a service while anonymous correctly redirects to `/accounts/
  login/`.
- Full OTP login → new-user registration → booking → status-advance
  simulation → payment → invoice → review → complaint, for a brand-new
  customer account.
- Worker onboarding → document upload → worker dashboard, for a brand-new
  worker account.
- Federation-admin pricing update (visit charge + labour charge) and
  confirmed the new price is what a customer subsequently sees.
- Nearest-worker sorting with a mocked Google Distance Matrix response:
  confirmed each worker is matched to the correct distance/ETA (not
  shuffled), sorted nearest-first, and that workers with no saved
  location degrade gracefully instead of breaking the page.
- Society-operator worker-verification queue and complaint-resolution
  screens.
- Role-based access control: a `customer`-role account is redirected away
  from `/dashboard/` and `/dashboard/pricing/`.
- Language switcher: posting to `/i18n/setlang/` sets the `django_language`
  cookie and subsequent pages render `lang="hi"` with translated strings.

## Production hardening checklist (not yet done — flagged deliberately)
- Replace `SECRET_KEY` and set `DEBUG = False`.
- Set `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`,
  `SECURE_HSTS_SECONDS` once served over HTTPS.
- Move `DATABASES` to PostgreSQL and `MEDIA_ROOT` to S3/GCS-backed storage.
- Add rate limiting to `/accounts/login/` and `/accounts/verify-otp/` to
  prevent OTP abuse.
- Add a Celery worker + broker if you want async SMS/email/notification
  sending instead of inline calls.
