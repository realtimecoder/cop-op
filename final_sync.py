import sys

# Path to the models file
models_path = 'bookings/models.py'

with open(models_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_bulk_request = False
for line in lines:
    if 'class BulkServiceRequest(models.Model):' in line:
        in_bulk_request = True
    
    if in_bulk_request and 'status = models.CharField(max_length=25, choices=Status.choices, default=Status.REQUESTED)' in line:
        new_lines.append(line)
        new_lines.append('    is_auto_booked = models.BooleanField(default=False, help_text="True if the request was fulfilled via Rapid Book.")\n')
    else:
        new_lines.append(line)
    
    # Basic check to see if we've left the class definition (roughly)
    if in_bulk_request and line.startswith('class ') and 'BulkServiceRequest' not in line:
        in_bulk_request = False

with open(models_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# Now fix bulk_views.py
views_path = 'bookings/bulk_views.py'
with open(views_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update rapid_bulk_book to set is_auto_booked and status=IN_PROGRESS
# Look for the block that sets status to ASSIGNED in rapid_bulk_book
import re
pattern = r"(bulk\.status\s*=\s*BulkServiceRequest\.Status\.ASSIGNED)\n\s*_notify_bulk_workers\(bulk\)\n\s*bulk\.save\(update_fields=\[\'status\'\]\)"
replacement = r"bulk.status = BulkServiceRequest.Status.IN_PROGRESS\nbulk.is_auto_booked = True\n    _notify_bulk_workers(bulk)\n    bulk.save(update_fields=['status', 'is_auto_booked'])"
# This is getting complex. I'll just use a simple string replace if I know the exact text.

# Let's use a simpler method for views.py
with open(views_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

final_views = []
in_rapid_book = False
for line in lines:
    if 'def rapid_bulk_book' in line:
        in_rapid_book = True
    
    if in_rapid_book and 'bulk.status = BulkServiceRequest.Status.ASSIGNED' in line:
        final_views.append('    bulk.status = BulkServiceRequest.Status.IN_PROGRESS\n')
        final_views.append('    bulk.is_auto_booked = True\n')
    elif in_rapid_book and 'bulk.save(update_fields=[\'status\'])' in line:
        final_views.append('    bulk.save(update_fields=[\'status\', \'is_auto_booked\'])\n')
    elif in_rapid_book and (line.startswith('def ') or line.startswith('class ')) and 'rapid_bulk_book' not in line:
        in_rapid_book = False
        final_views.append(line)
    else:
        final_views.append(line)

# 2. Update mark_bulk_assignment_complete to handle is_auto_booked
# We'll do this in a second pass or together
content_final = "".join(final_views)
content_final = content_final.replace(
    'if bulk.status != BulkServiceRequest.Status.IN_PROGRESS:',
    'if bulk.status not in (BulkServiceRequest.Status.ASSIGNED, BulkServiceRequest.Status.IN_PROGRESS, BulkServiceRequest.Status.AWAITING_APPROVAL):'
)

# Add the auto-advance logic to mark_bulk_assignment_complete
# Look for the part where it just says "Your part of the work has been marked as complete."
target = '    messages.success(request, "Your part of the work has been marked as complete.")'
replacement_complete = """    if bulk.is_auto_booked and not bulk.assignments.filter(is_completed=False).exists():
        bulk.status = BulkServiceRequest.Status.WORK_COMPLETED
        bulk.save(update_fields=['status'])

        Notification.objects.create(
            user=bulk.institution,
            message=f"Bulk Request #{bulk.id} for {bulk.service.name} has been completed. Please verify and confirm the work.",
            link=f"/bookings/bulk/{bulk.id}/"
        )
        messages.info(request, "You were the last worker to finish! The request has been marked as completed for the customer.")
    else:
        messages.success(request, "Your part of the work has been marked as complete.")"""

content_final = content_final.replace(target, replacement_complete)

with open(views_path, 'w', encoding='utf-8') as f:
    f.write(content_final)
