import sys

with open('templates/bookings/bulk_request_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if '        <div class="flex gap-1 mt-3" style="flex-wrap:wrap;">' in line:
        new_lines.append(line)
        i += 1
        # Now we are inside the action bar. 
        # We want to insert the Auto Book button before the Cancel button.
        
        # Current lines might be:
        # {% if is_institution %}
        #   {% if bulk.status == 'requested' or bulk.status == 'claimed' %}
        #   ... cancel button ...
        
        # We want to add:
        #   {% if bulk.status == 'requested' %}
        #   <a href="{% url 'bookings:rapid_bulk_book' bulk.id %}" class="btn btn-accent btn-sm">{% trans "Auto Book (Fast Match)" %}</a>
        #   {% endif %}
        
        # Let's just rebuild the whole institution block for safety.
        # We'll look for the end of the institution block.
        
        # Simplified approach: find the line where is_institution starts and replace the whole block
        # until we hit the is_assigned_society_operator block.
        
        # I'll just read the whole file and do a string replace for the specific section.
        pass
    else:
        new_lines.append(line)
    i += 1
