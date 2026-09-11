"""
Co-opSeva development seed data
Creates:
  1 platform admin
  2 federations
  4 societies
  50 workers
  200 customers

Run from the project root:
    python manage.py shell < seed_test_data.py

This script uses the project's actual User, Federation, Society,
WorkerProfile, ServiceCategory, Service and WorkerServiceOffering models.
It is intended for development/testing only.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.db import transaction

from workers.models import (
    Federation,
    Society,
    FederationPricing,
    SocietyPricing,
    PlatformConfig,
    WorkerProfile,
    WorkerServiceOffering,
)
from catalog.models import ServiceCategory, Service

User = get_user_model()

# Delhi test locations. Workers/customers are distributed around these areas.
AREAS = [
    ("Connaught Place", 28.6315, 77.2167, "110001"),
    ("Karol Bagh", 28.6519, 77.1909, "110005"),
    ("Lajpat Nagar", 28.5677, 77.2433, "110024"),
    ("Saket", 28.5244, 77.2066, "110017"),
    ("Dwarka", 28.5921, 77.0460, "110075"),
    ("Rohini", 28.7495, 77.0565, "110085"),
    ("Pitampura", 28.7033, 77.1322, "110034"),
    ("Mayur Vihar", 28.6080, 77.2946, "110091"),
    ("Janakpuri", 28.6219, 77.0878, "110058"),
    ("Vasant Kunj", 28.5206, 77.1588, "110070"),
    ("Preet Vihar", 28.6415, 77.2955, "110092"),
    ("Greater Kailash", 28.5494, 77.2420, "110048"),
]

FIRST_NAMES = [
    "Aarav", "Arjun", "Kabir", "Rohan", "Aditya", "Vikram", "Karan",
    "Rahul", "Aman", "Dev", "Nikhil", "Yash", "Kunal", "Varun",
    "Raj", "Ankit", "Manish", "Sahil", "Mohit", "Ravi", "Neeraj",
    "Sameer", "Akash", "Harsh", "Vivek", "Aisha", "Maya", "Emma",
    "Olivia", "Liam", "Noah", "Ethan", "Ryan", "Alex", "Daniel",
    "Jack", "Leo", "Lucas", "Sam", "Ben", "Mia", "Sara", "Nina",
    "Anaya", "Isha", "Riya", "Priya", "Tara", "Zara", "Meera",
]

LAST_NAMES = [
    "Sharma", "Verma", "Singh", "Gupta", "Khan", "Mehta", "Kapoor",
    "Malhotra", "Bansal", "Arora", "Saxena", "Chopra", "Joshi",
    "Agarwal", "Mishra", "Sethi", "Khanna", "Jain", "Rao", "Das",
]

SERVICE_DATA = [
    ("Plumbing", "Plumbing and water-system services", "plumbing",
     "Tap repair", 60, 250, 450),
    ("Electrical", "Electrical installation and repair", "bolt",
     "Electrical repair", 60, 250, 500),
    ("Carpentry", "Furniture and woodwork services", "hammer",
     "Furniture repair", 90, 300, 600),
    ("Cleaning", "Home and commercial cleaning", "sparkles",
     "Home cleaning", 120, 200, 450),
    ("Driving", "Driver and local transport services", "car",
     "Local driver service", 240, 300, 900),
    ("Gardening", "Garden maintenance and landscaping", "leaf",
     "Garden maintenance", 120, 250, 500),
    ("Domestic Help", "Household assistance services", "home",
     "Domestic assistance", 180, 250, 650),
    ("Caregiving", "Elder and patient assistance", "heart",
     "Caregiving support", 240, 350, 900),
    ("Technician", "Appliance and equipment repair", "wrench",
     "Appliance repair", 90, 300, 700),
]

WORKER_JOBS = [
    ("Plumber", 0, 0),
    ("Electrician", 1, 1),
    ("Carpenter", 2, 2),
    ("Cleaner", 3, 3),
    ("Driver", 4, 4),
    ("Gardener", 5, 5),
    ("Domestic Helper", 6, 6),
    ("Caregiver", 7, 7),
    ("Technician", 8, 8),
]

WORKER_RATINGS = [
    Decimal("5.00"), Decimal("4.90"), Decimal("4.80"), Decimal("4.70"),
    Decimal("4.60"), Decimal("4.50"), Decimal("4.40"), Decimal("4.20"),
    Decimal("4.00"), Decimal("3.80"), Decimal("3.50"), Decimal("3.20"),
    Decimal("2.80"), Decimal("0.00"),
]

SKILLS = [
    WorkerProfile.SkillGrade.BASIC,
    WorkerProfile.SkillGrade.SKILLED,
    WorkerProfile.SkillGrade.ADVANCED,
    WorkerProfile.SkillGrade.EXPERT,
    WorkerProfile.SkillGrade.CERTIFIED,
]

VERIFY = [
    WorkerProfile.VerificationStatus.VERIFIED,
    WorkerProfile.VerificationStatus.VERIFIED,
    WorkerProfile.VerificationStatus.VERIFIED,
    WorkerProfile.VerificationStatus.VERIFIED,
    WorkerProfile.VerificationStatus.PENDING,
]

def user_data(username, first, last, role, phone, area):
    area_name, lat, lng, pin = area
    return dict(
        username=username,
        first_name=first,
        last_name=last,
        email=f"{username}@test.coopseva.local",
        phone_number=phone,
        role=role,
        address=f"{((first + ' ' + last))} House, {area_name}, New Delhi",
        city="Delhi",
        state="Delhi",
        country="India",
        pincode=pin,
        latitude=lat,
        longitude=lng,
        is_phone_verified=True,
        has_completed_tour=True,
    )

@transaction.atomic
def seed():
    print("Starting Co-opSeva test-data seed...")

    # Global platform setting
    PlatformConfig.objects.update_or_create(
        key="DEFAULT_COMMISSION",
        defaults={"value": "10.0"},
    )

    # ------------------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------------------
    admin, created = User.objects.get_or_create(
        username="test_platform_admin",
        defaults={
            "first_name": "Platform",
            "last_name": "Admin",
            "email": "admin@test.coopseva.local",
            "role": User.Role.PLATFORM_ADMIN,
            "phone_number": "9000000001",
            "city": "Delhi",
            "state": "Delhi",
            "country": "India",
            "pincode": "110001",
            "latitude": 28.6315,
            "longitude": 77.2167,
            "is_phone_verified": True,
            "has_completed_tour": True,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    admin.role = User.Role.PLATFORM_ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()

    # ------------------------------------------------------------------
    # FEDERATIONS
    # ------------------------------------------------------------------
    federations = []
    federation_specs = [
        ("Delhi Urban Labour Federation", "DL-ULF-2026-001", Decimal("8.00")),
        ("Delhi Cooperative Service Federation", "DL-CSF-2026-002", Decimal("12.00")),
    ]

    for i, (name, reg, commission) in enumerate(federation_specs, start=1):
        username = f"test_federation_{i}"
        phone = f"90000000{10+i:02d}"
        u, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Federation",
                "last_name": f"Admin {i}",
                "email": f"{username}@test.coopseva.local",
                "role": User.Role.FEDERATION,
                "phone_number": phone,
                "address": "Federation Office, Delhi",
                "city": "Delhi",
                "state": "Delhi",
                "country": "India",
                "pincode": "110001",
                "latitude": 28.6315,
                "longitude": 77.2167,
                "is_phone_verified": True,
                "has_completed_tour": True,
            },
        )
        u.role = User.Role.FEDERATION
        u.save()

        f, _ = Federation.objects.update_or_create(
            name=name,
            defaults={
                "city": "Delhi",
                "registration_number": reg,
                "admin_user": u,
                "commission_percent": commission,
                "is_active": True,
                "is_banned": False,
            },
        )
        federations.append(f)

        # Example federation pricing overrides
        cats = list(ServiceCategory.objects.all()[:3])
        overrides = {str(c.id): 200 + (i * 25) for c in cats}
        FederationPricing.objects.update_or_create(
            federation=f,
            defaults={
                "category_overrides": overrides,
                "service_overrides": {},
            },
        )

    # ------------------------------------------------------------------
    # SOCIETIES
    # ------------------------------------------------------------------
    societies = []
    society_specs = [
        ("Central Delhi Skilled Workers Society", federations[0], "110001"),
        ("South Delhi Home Services Society", federations[0], "110017"),
        ("West Delhi Cooperative Workers Society", federations[1], "110058"),
        ("East Delhi Community Services Society", federations[1], "110091"),
    ]

    for i, (name, federation, pin) in enumerate(society_specs, start=1):
        area = AREAS[(i - 1) % len(AREAS)]
        username = f"test_society_{i}"
        phone = f"90000000{30+i:02d}"

        u, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Society",
                "last_name": f"Operator {i}",
                "email": f"{username}@test.coopseva.local",
                "role": User.Role.SOCIETY,
                "phone_number": phone,
                "address": f"Society Office, {area[0]}, Delhi",
                "city": "Delhi",
                "state": "Delhi",
                "country": "India",
                "pincode": pin,
                "latitude": area[1],
                "longitude": area[2],
                "is_phone_verified": True,
                "has_completed_tour": True,
            },
        )
        u.role = User.Role.SOCIETY
        u.save()

        s, _ = Society.objects.update_or_create(
            name=name,
            defaults={
                "city": "Delhi",
                "registration_number": f"DL-SOC-2026-{i:03d}",
                "description": f"Cooperative society providing verified local services across Delhi. Society {i}.",
                "federation": federation,
                "operator": u,
                "head_performs_fieldwork": True,
                "is_active": True,
                "is_banned": False,
            },
        )
        societies.append(s)

        SocietyPricing.objects.update_or_create(
            society=s,
            defaults={
                "category_overrides": {},
                "service_overrides": {},
            },
        )

    # ------------------------------------------------------------------
    # CATALOG SERVICES
    # ------------------------------------------------------------------
    catalog = []
    for name, description, icon, service_name, duration, visit, labour in SERVICE_DATA:
        category, _ = ServiceCategory.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
                "icon": icon,
                "is_active": True,
                "fixed_visit_charge": visit,
            },
        )
        category.description = description
        category.is_active = True
        category.save(update_fields=["description", "is_active"])

        service, _ = Service.objects.get_or_create(
            category=category,
            name=service_name,
            defaults={
                "description": description,
                "required_skill": "Skilled",
                "estimated_duration_minutes": duration,
                "tools_required": "Standard service tools",
                "fixed_labour_charge": labour,
                "hourly_rate": labour,
                "min_hours": 1,
                "warranty_days": 7,
                "service_area": "Delhi-NCR",
                "is_active": True,
            },
        )
        service.is_active = True
        service.save(update_fields=["is_active"])
        catalog.append((category, service))

    # ------------------------------------------------------------------
    # WORKERS — EXACTLY 50
    # ------------------------------------------------------------------
    worker_profiles = []

    for i in range(50):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 3) % len(LAST_NAMES)]
        job_name, service_index, _ = WORKER_JOBS[i % len(WORKER_JOBS)]

        # Spread workers around Delhi; tiny deterministic offsets create
        # several very-near matches while still keeping broad coverage.
        area_index = (i * 3 + (i // 9)) % len(AREAS)
        area_name, base_lat, base_lng, pin = AREAS[area_index]
        lat_offset = ((i % 5) - 2) * 0.004
        lng_offset = (((i * 2) % 5) - 2) * 0.004

        lat = round(base_lat + lat_offset, 6)
        lng = round(base_lng + lng_offset, 6)

        username = f"test_worker_{i+1:03d}"
        phone = f"900001{i+1:04d}"
        role = User.Role.WORKER

        u, _ = User.objects.get_or_create(
            username=username,
            defaults=user_data(
                username,
                first,
                last,
                role,
                phone,
                (area_name, lat, lng, pin),
            ),
        )

        u.first_name = first
        u.last_name = last
        u.email = f"{username}@test.coopseva.local"
        u.role = role
        u.phone_number = phone
        u.address = f"{first} {last} House, {area_name}, New Delhi"
        u.city = "Delhi"
        u.state = "Delhi"
        u.country = "India"
        u.pincode = pin
        u.latitude = lat
        u.longitude = lng
        u.is_phone_verified = True
        u.has_completed_tour = True
        u.save()

        rating = WORKER_RATINGS[i % len(WORKER_RATINGS)]
        reliability = Decimal(str(round(0.50 + ((i * 7) % 51) / 100, 2)))
        skill = SKILLS[i % len(SKILLS)]
        verified = VERIFY[i % len(VERIFY)]

        # Explicit edge cases
        if i == 0:
            rating, reliability, skill = Decimal("5.00"), Decimal("1.00"), WorkerProfile.SkillGrade.CERTIFIED
        elif i == 1:
            rating, reliability, skill = Decimal("4.90"), Decimal("0.98"), WorkerProfile.SkillGrade.EXPERT
        elif i == 2:
            rating, reliability, skill = Decimal("3.20"), Decimal("0.55"), WorkerProfile.SkillGrade.BASIC
        elif i == 3:
            rating, reliability, skill = Decimal("0.00"), Decimal("0.70"), WorkerProfile.SkillGrade.SKILLED
        elif i == 4:
            rating, reliability, skill = Decimal("2.80"), Decimal("0.50"), WorkerProfile.SkillGrade.BASIC

        radius = [3, 5, 7, 10][i % 4]
        available = i not in {12, 27, 41}

        wp, _ = WorkerProfile.objects.update_or_create(
            user=u,
            defaults={
                "society": societies[i % len(societies)],
                "membership_number": f"CSV-W-{i+1:04d}",
                "membership_date": date(2026, 1, 1) + timedelta(days=i),
                "verification_status": verified,
                "verification_officer": "Test Verification Officer" if verified == WorkerProfile.VerificationStatus.VERIFIED else "",
                "verification_date": date.today() if verified == WorkerProfile.VerificationStatus.VERIFIED else None,
                "skill_grade": skill,
                "years_experience": 1 + (i % 15),
                "bio": f"Experienced {job_name.lower()} serving customers across Delhi.",
                "languages_spoken": "Hindi, English",
                "service_radius_km": radius,
                "is_available_now": available,
                "average_rating": rating,
                "completed_jobs": 0 if rating == 0 else 5 + (i * 3),
                "reliability_score": reliability,
                "last_worked_date": date.today() - timedelta(days=i % 20) if rating != 0 else None,
                "payout_percentage": Decimal("78.00") + Decimal(str((i % 5) - 2)),
            },
        )

        category, service = catalog[service_index]
        wp.categories.set([category])
        WorkerServiceOffering.objects.update_or_create(
            worker=wp,
            service=service,
            defaults={"typical_arrival_minutes": 20 + ((i * 7) % 50)},
        )
        worker_profiles.append(wp)

    # ------------------------------------------------------------------
    # CUSTOMERS — EXACTLY 200
    # ------------------------------------------------------------------
    for i in range(200):
        first = FIRST_NAMES[(i * 7) % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 11 + 2) % len(LAST_NAMES)]
        area_index = (i * 5 + i // 12) % len(AREAS)
        area_name, base_lat, base_lng, pin = AREAS[area_index]

        # More variation around each area for distance/radius testing.
        lat = round(base_lat + (((i * 13) % 17) - 8) * 0.0012, 6)
        lng = round(base_lng + (((i * 17) % 17) - 8) * 0.0012, 6)

        username = f"test_customer_{i+1:03d}"
        phone = f"900002{i+1:04d}"

        u, _ = User.objects.get_or_create(
            username=username,
            defaults=user_data(
                username,
                first,
                last,
                User.Role.CUSTOMER,
                phone,
                (area_name, lat, lng, pin),
            ),
        )

        u.first_name = first
        u.last_name = last
        u.email = f"{username}@test.coopseva.local"
        u.role = User.Role.CUSTOMER
        u.phone_number = phone
        u.address = f"{first} {last} Residence, {area_name}, New Delhi"
        u.city = "Delhi"
        u.state = "Delhi"
        u.country = "India"
        u.pincode = pin
        u.latitude = lat
        u.longitude = lng
        u.is_phone_verified = True
        u.has_completed_tour = True
        u.save()

    print("")
    print("SEED COMPLETE")
    print(f"Admin:       {User.objects.filter(username='test_platform_admin').count()}")
    print(f"Federations: {Federation.objects.filter(name__startswith='Delhi ').count()}")
    print(f"Societies:   {Society.objects.filter(name__contains='Delhi').count()}")
    print(f"Workers:     {WorkerProfile.objects.filter(user__username__startswith='test_worker_').count()}")
    print(f"Customers:   {User.objects.filter(username__startswith='test_customer_').count()}")
    print("")
    print("Generated accounts use usernames test_worker_XXX and test_customer_XXX.")
    print("Existing non-test users are not deleted or modified.")

seed()
