from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import ServiceCategory, Service
from accounts.models import User
from workers.models import Society, WorkerProfile, WorkerServiceOffering, Federation


class Command(BaseCommand):
    help = "Seed Co-opSeva with a full Urban-Company-style category catalogue, a society, and verified workers."

    def handle(self, *args, **options):
        self.stdout.write("Seeding Co-opSeva demo data...")

        FIXED = Service.PricingType.FIXED
        HOURLY = Service.PricingType.HOURLY

        # ---------------------------------------------------------------
        # Full category + sub-service catalogue (Urban-Company-style
        # structure, adapted to the cooperative fixed/hourly pricing model).
        # Each tuple: (category, icon, visit_charge, [ (service, pricing_type, rate, skill), ... ])
        # For FIXED services `rate` = fixed_labour_charge.
        # For HOURLY services `rate` = hourly_rate (min_hours defaults to 1
        # unless overridden with a 5th tuple element).
        # ---------------------------------------------------------------
        data = [
            ("Salon for Women", "scissors", 100, [
                ("Haircut & styling", FIXED, 500, "salon"),
                ("Facial & cleanup", FIXED, 900, "salon"),
                ("Waxing (full body)", FIXED, 1200, "salon"),
                ("Manicure & pedicure", FIXED, 700, "salon"),
                ("Bridal makeup", FIXED, 4500, "salon"),
            ]),
            ("Spa for Women", "heart", 100, [
                ("Full body massage", HOURLY, 800, "spa"),
                ("Head & shoulder massage", HOURLY, 500, "spa"),
            ]),
            ("Salon & Massage for Men", "scissors", 100, [
                ("Haircut & beard styling", FIXED, 350, "salon"),
                ("Head massage", HOURLY, 400, "spa"),
                ("Full body massage (men)", HOURLY, 700, "spa"),
            ]),
            ("AC & Appliance Repair", "wind", 150, [
                ("AC service & gas top-up", FIXED, 900, "ac repair"),
                ("AC installation / uninstallation", FIXED, 1100, "ac repair"),
                ("Washing machine repair", FIXED, 700, "appliance repair"),
                ("Refrigerator repair", FIXED, 800, "appliance repair"),
                ("Microwave repair", FIXED, 600, "appliance repair"),
                ("Water purifier (RO) service", FIXED, 650, "appliance repair"),
                ("Chimney repair & cleaning", FIXED, 750, "appliance repair"),
            ]),
            ("Electrician", "bolt", 150, [
                ("Fan installation", FIXED, 1000, "electrical"),
                ("Switch & socket replacement", FIXED, 700, "electrical"),
                ("Light / fixture installation", FIXED, 800, "electrical"),
                ("MCB / fuse box repair", FIXED, 1000, "electrical"),
                ("General electrical wiring (per hour)", HOURLY, 350, "electrical"),
            ]),
            ("Plumber", "droplet", 150, [
                ("Tap repair / replacement", FIXED, 700, "plumbing"),
                ("Pipe leakage fix", FIXED, 1200, "plumbing"),
                ("Toilet / commode repair", FIXED, 900, "plumbing"),
                ("Water tank cleaning", FIXED, 1300, "plumbing"),
                ("General plumbing (per hour)", HOURLY, 300, "plumbing"),
            ]),
            ("Carpenter", "hammer", 150, [
                ("Furniture repair", FIXED, 900, "carpentry"),
                ("Door / window fitting", FIXED, 1100, "carpentry"),
                ("Furniture assembly (flat-pack)", FIXED, 800, "carpentry"),
                ("General carpentry (per hour)", HOURLY, 300, "carpentry"),
            ]),
            ("Painting & Waterproofing", "brush", 150, [
                ("Interior wall painting (per room)", FIXED, 3500, "painting"),
                ("Exterior painting (per day)", HOURLY, 900, "painting"),
                ("Waterproofing treatment", FIXED, 4000, "painting"),
                ("Wall putty & touch-up", FIXED, 1500, "painting"),
            ]),
            ("Cleaning", "sparkle", 100, [
                ("Full home deep cleaning", FIXED, 1800, "cleaning"),
                ("Bathroom deep cleaning", FIXED, 700, "cleaning"),
                ("Kitchen deep cleaning", FIXED, 900, "cleaning"),
                ("Sofa & carpet shampooing", FIXED, 1100, "cleaning"),
                ("General cleaning (per hour)", HOURLY, 250, "cleaning"),
            ]),
            ("Pest Control", "spray", 100, [
                ("General pest control", FIXED, 1200, "pest control"),
                ("Termite control", FIXED, 2200, "pest control"),
                ("Cockroach & ant control", FIXED, 900, "pest control"),
                ("Mosquito control (fogging)", FIXED, 1000, "pest control"),
                ("Bed bug treatment", FIXED, 1600, "pest control"),
            ]),
            ("Home Renovation", "box", 150, [
                ("False ceiling (per sq. ft.)", HOURLY, 60, "renovation", 20),
                ("Modular kitchen consultation", FIXED, 500, "renovation"),
                ("Tile & flooring work (per hour)", HOURLY, 350, "renovation"),
            ]),
            ("Domestic Helper", "home", 100, [
                ("Daily household help (per hour)", HOURLY, 150, "housekeeping"),
                ("Cooking help (per hour)", HOURLY, 200, "housekeeping"),
                ("Full-day household help", HOURLY, 150, "housekeeping", 8),
            ]),
            ("Caregiver", "heart", 100, [
                ("Elderly care (per hour)", HOURLY, 180, "caregiving"),
                ("Baby / infant care (per hour)", HOURLY, 200, "caregiving"),
                ("Post-surgery patient care (per hour)", HOURLY, 220, "caregiving"),
            ]),
            ("Driver", "truck", 100, [
                ("Daily driver (8 hours)", HOURLY, 150, "driving", 8),
                ("Outstation driver (per day)", HOURLY, 1400, "driving", 1),
                ("Hourly driver on-call", HOURLY, 180, "driving"),
            ]),
            ("Gardener", "leaf", 100, [
                ("Garden maintenance (per visit)", FIXED, 800, "gardening"),
                ("Lawn mowing", FIXED, 600, "gardening"),
                ("Plant care (per hour)", HOURLY, 200, "gardening"),
            ]),
            ("Construction Labourer", "wrench", 150, [
                ("General mason work (per day)", HOURLY, 900, "masonry", 8),
                ("Helper / labourer (per day)", HOURLY, 600, "construction labour", 8),
                ("Tiling & flooring (per day)", HOURLY, 1000, "construction labour", 8),
            ]),
        ]

        for cat_name, icon, visit_charge, services in data:
            category, _ = ServiceCategory.objects.get_or_create(
                name=cat_name,
                defaults={'icon': icon, 'fixed_visit_charge': visit_charge,
                          'description': f"Verified {cat_name.lower()} professionals with transparent, fixed pricing."}
            )
            for entry in services:
                svc_name, ptype, rate, skill = entry[0], entry[1], entry[2], entry[3]
                min_hours = entry[4] if len(entry) > 4 else 1
                defaults = {
                    'required_skill': skill,
                    'description': f"{svc_name} performed by a verified cooperative worker.",
                    'warranty_days': 7,
                    'pricing_type': ptype,
                }
                if ptype == FIXED:
                    defaults['fixed_labour_charge'] = rate
                else:
                    defaults['hourly_rate'] = rate
                    defaults['min_hours'] = min_hours
                Service.objects.get_or_create(category=category, name=svc_name, defaults=defaults)

        self.stdout.write(self.style.SUCCESS(
            f"  {ServiceCategory.objects.count()} categories, {Service.objects.count()} services ready."))

        # ---- Demo Federation + its Admin (Admin creates Federation; ----
        # Federation creates Society under itself — the real hierarchy).
        federation_admin, _ = User.objects.get_or_create(
            phone_number='9900000001',
            defaults={'username': '9900000001', 'first_name': 'Delhi-NCR', 'last_name': 'Federation-Admin',
                      'role': User.Role.FEDERATION, 'is_phone_verified': True, 'city': 'Delhi'}
        )
        federation, _ = Federation.objects.get_or_create(
            name="Delhi-NCR Labour Federation",
            defaults={'city': 'Delhi', 'registration_number': 'DL-FED-0001',
                      'admin_user': federation_admin, 'commission_percent': 10}
        )
        if federation.admin_user_id != federation_admin.id:
            federation.admin_user = federation_admin
            federation.save(update_fields=['admin_user'])

        # ---- Society Head (approves/claims workers into their society) ----
        operator, _ = User.objects.get_or_create(
            phone_number='9800000001',
            defaults={'username': '9800000001', 'first_name': 'Suman', 'last_name': 'Society-Head',
                      'role': User.Role.SOCIETY, 'is_phone_verified': True, 'city': 'Delhi'}
        )

        # ---- Society ---- (created under the demo Federation, matching
        # the real Federation -> Society -> Worker hierarchy the
        # platform now enforces. A second, independent society is also
        # seeded to demonstrate the join/invite flow.)
        society, _ = Society.objects.get_or_create(
            name="Delhi-NCR Workers Cooperative Society",
            defaults={'city': 'Delhi', 'registration_number': 'DL-COOP-0001',
                      'operator': operator, 'federation': federation}
        )
        if society.operator_id != operator.id:
            society.operator = operator
            society.save(update_fields=['operator'])
        if society.federation_id != federation.id:
            society.federation = federation
            society.save(update_fields=['federation'])

        # ---- A second, INDEPENDENT society (no federation) — sets its
        # own pricing/policy and can be invited to join a federation. ----
        indep_head, _ = User.objects.get_or_create(
            phone_number='9800000002',
            defaults={'username': '9800000002', 'first_name': 'Farida', 'last_name': 'Independent-Head',
                      'role': User.Role.SOCIETY, 'is_phone_verified': True, 'city': 'Gurgaon'}
        )
        indep_society, _ = Society.objects.get_or_create(
            name="Gurgaon Independent Workers Society",
            defaults={'city': 'Gurgaon', 'registration_number': 'GGN-IND-0001', 'operator': indep_head}
        )
        if indep_society.operator_id != indep_head.id:
            indep_society.operator = indep_head
            indep_society.save(update_fields=['operator'])

        # ---- Demo verified workers, one per major category ----
        demo_workers = [
            ("9810000001", "Ramesh", "Kumar", "Electrician", "advanced", 8),
            ("9810000002", "Suresh", "Yadav", "Plumber", "skilled", 5),
            ("9810000003", "Anita", "Devi", "Domestic Helper", "certified", 10),
            ("9810000004", "Vikram", "Singh", "Carpenter", "expert", 12),
            ("9810000005", "Geeta", "Sharma", "Painting & Waterproofing", "skilled", 4),
            ("9810000006", "Pooja", "Nair", "Salon for Women", "certified", 6),
            ("9810000007", "Imran", "Khan", "AC & Appliance Repair", "advanced", 7),
            ("9810000008", "Manoj", "Verma", "Cleaning", "skilled", 3),
            ("9810000009", "Rekha", "Joshi", "Caregiver", "certified", 9),
            ("9810000010", "Sanjay", "Rawat", "Driver", "advanced", 11),
        ]
        for phone, fn, ln, cat_name, grade, years in demo_workers:
            user, created = User.objects.get_or_create(
                phone_number=phone,
                defaults={'username': phone, 'first_name': fn, 'last_name': ln,
                          'role': User.Role.WORKER, 'is_phone_verified': True, 'city': 'Delhi',
                          'address': f'{fn} Nagar, Delhi', 'pincode': '110001',
                          'latitude': 28.60 + (hash(phone) % 20) / 100.0,
                          'longitude': 77.15 + (hash(phone) % 25) / 100.0}
            )
            profile, _ = WorkerProfile.objects.get_or_create(
                user=user,
                defaults={'society': society, 'verification_status': WorkerProfile.VerificationStatus.VERIFIED,
                          'skill_grade': grade, 'years_experience': years,
                          'average_rating': 4.5, 'completed_jobs': 25,
                          'bio': f"Experienced {cat_name.lower()} professional, cooperative-verified.",
                          'verification_officer': operator.get_full_name(), 'verification_date': timezone.now().date()}
            )
            category = ServiceCategory.objects.filter(name=cat_name).first()
            if category:
                profile.categories.add(category)
                for service in category.services.all():
                    WorkerServiceOffering.objects.get_or_create(worker=profile, service=service)

        self.stdout.write(self.style.SUCCESS(
            f"  {WorkerProfile.objects.filter(verification_status='verified').count()} verified demo workers ready."))

        # ---- Demo institution (for testing the bulk-request flow) ----
        User.objects.get_or_create(
            phone_number='9700000099',
            defaults={'username': '9700000099', 'first_name': 'Skyline', 'last_name': 'Builders Pvt Ltd',
                      'role': User.Role.BUILDER, 'is_phone_verified': True, 'city': 'Delhi',
                      'address': 'Sector 62, Site Office'}
        )

        self.stdout.write(self.style.SUCCESS(
            "  Federation admin: 9900000001 | Society head (federated): 9800000001 | "
            "Independent society head: 9800000002"))
        self.stdout.write(self.style.SUCCESS("Seed complete. Log in with any demo phone number via OTP (shown on screen)."))
