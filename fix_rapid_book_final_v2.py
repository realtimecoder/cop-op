import sys

with open('bookings/bulk_views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'def rapid_bulk_book(request, request_id):' in line:
        new_lines.append(line)
        new_lines.append('    """Algo-driven Rapid Book for Bulk Requests."""\n')
        new_lines.append('    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)\n')
        new_lines.append('    if bulk.status != BulkServiceRequest.Status.REQUESTED:\n')
        new_lines.append('        messages.error(request, "Rapid booking is only available for new requests.")\n')
        new_lines.append('        return redirect(\'bookings:bulk_request_detail\', request_id=request_id)\n')
        new_lines.append('\n')
        new_lines.append('    # Use Site Address for distance calculation\n')
        new_lines.append('    site_coords = geocode_address(bulk.address, bulk.city, bulk.pincode)\n')
        new_lines.append('    if site_coords:\n')
        new_lines.append('        lat, lng = site_coords\n')
        new_lines.append('    else:\n')
        new_lines.append('        lat, lng = request.user.latitude, request.user.longitude\n')
        new_lines.append('        messages.warning(request, "Could not geocode site address. Using institution office location for worker matching.")\n\n')
        new_lines.append('    # 1. Find best candidates using the matching engine\n')
        new_lines.append('    best_candidates = find_best_workers(\n')
        new_lines.append('        bulk.service,\n')
        new_lines.append('        lat,\n')
        new_lines.append('        lng,\n')
        new_lines.append('        limit=bulk.workers_required\n')
        new_lines.append('    )\n\n')
        new_lines.append('    if not best_candidates:\n')
        new_lines.append('        messages.error(request, "No available workers found for this service.")\n')
        new_lines.append('        return redirect(\'bookings:bulk_request_detail\', request_id=request_id)\n\n')
        new_lines.append('    # CRITICAL FIX: Explicitly sort candidates by score descending to ensure top rank is picked\n')
        new_lines.append('    best_candidates.sort(key=lambda x: x[1], reverse=True)\n\n')
        new_lines.append('    found_workers = [c[0] for c in best_candidates]\n')
        new_lines.append('    count = len(found_workers)\n\n')
        new_lines.append('    if count < bulk.workers_required:\n')
        new_lines.append('        for worker in found_workers:\n')
        new_lines.append('            BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)\n\n')
        new_lines.append('        if found_workers:\n')
        new_lines.append('            bulk.assigned_society = found_workers[0].society\n')
        new_lines.append('            bulk.save(update_fields=[\'assigned_society\'])\n\n')
        new_lines.append('        bulk.status = BulkServiceRequest.Status.AWAITING_APPROVAL\n')
        new_lines.append('        bulk.save(update_fields=[\'status\'])\n\n')
        new_lines.append('        messages.warning(request, f"Only {count} of {bulk.workers_required} workers were found. " \n')
        new_lines.append('                                f"Updated total: ₹{bulk.total_amount}. Please review and accept/reject.")\n')
        new_lines.append('        return redirect(\'bookings:bulk_request_detail\', request_id=request_id)\n\n')
        new_lines.append('    # Full Fulfillment\n')
        new_lines.append('    for worker in found_workers:\n')
        new_lines.append('        BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)\n\n')
        new_lines.append('    if found_workers:\n')
        new_lines.append('        bulk.assigned_society = found_workers[0].society\n')
        new_//S_S_T_B_T
        new_lines.append('        bulk.save(update_fields=[\'assigned_society\'])\n\n')
        new_lines.append('    bulk.status = BulkServiceRequest.Status.ASSIGNED\n')
        new_lines.append('    _notify_bulk_workers(bulk)\n')
        new_lines.append('    bulk.save(update_fields=[\'status\'])\n')
        new_lines.append('    messages.success(request, f"Rapid Book successful! {count} workers have been assigned. They will be notified to accept.")\n')
        new_lines.append('    return redirect(\'bookings:bulk_request_detail\', request_id=request_id)\n')
        
        while i < len(lines):
            i += 1
            if i < len(lines) and (lines[i].strip().startswith('def ') or lines[i].strip().startswith('class ')):
                i -= 1
                break
    else:
        new_lines.append(line)
    i += 1

with open('bookings/bulk_views.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
