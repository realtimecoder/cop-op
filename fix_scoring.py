import sys

with open('workers/models.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'def recommended_score(self, distance_km=2.0):' in line:
        # Replace the whole method content until the return line
        new_lines.append(line)
        new_lines.append('        """FR-025 Recommended Ranking formula (Updated for Fairness):\n')
        new_lines.append('        Score = 0.10*Rating + 0.10*SkillMatch + 0.10*Availability + 0.35*Distance + 0.30*Fairness + 0.05*Reliability\n')
        new_lines.append('        Fairness penalizes workers who worked in the last 1-2 days to ensure equitable work distribution."""\n')
        new_lines.append('        rating_component = float(self.average_rating) / 5.0\n')
        new_lines.append('        skill_map = {\'basic\': .5, \'skilled\': .65, \'advanced\': .8, \'expert\': .9, \'certified\': 1.0}\n')
        new_lines.append('        skill_component = skill_map.get(self.skill_grade, .5)\n')
        new_lines.append('        availability_component = 1.0 if self.is_available_now else 0.3\n')
        new_lines.append('        distance_component = max(0.0, 1 - (distance_km / max(self.service_radius_km, 1)))\n')
        new_lines.append('        reliability_component = float(self.reliability_score)\n\n')
        new_lines.append('        # Fairness component: penalize very recent work (within 2 days)\n')
        new_lines.append('        fairness_component = 1.0\n')
        new_lines.append('        if self.last_worked_date:\n')
        new_lines.append('            days_since_work = (timezone.localdate() - self.last_worked_date).days\n')
        new_lines.append('            if days_since_work == 0:\n')
        new_lines.append('                fairness_component = 0.1\n')
        new_lines.append('            elif days_since_work == 1:\n')
        new_lines.append('                fairness_component = 0.4\n')
        new_lines.append('            elif days_since_work == 2:\n')
        new_lines.append('                fairness_component = 0.7\n\n')
        new_lines.append('        score = (0.10 * rating_component + 0.10 * skill_component + 0.10 * availability_component\n')
        new_lines.append('                 + 0.35 * distance_component + 0.30 * fairness_component + 0.05 * reliability_component)\n')
        new_lines.append('        return round(score * 100, 1)\n')
        
        # Skip the old method implementation
        while i < len(lines) and (not lines[i].strip().startswith('def ') and not lines[i].strip().startswith('class ')):
            i += 1
        i -= 1 # back one to let the outer loop handle it or move past
        # Actually we need to skip exactly until the end of this method.
        # Let's just find the return round(score * 100, 1) line.
        
        # Re-doing the loop to be simpler: find method start, skip until return.
        # Wait, the logic above is a bit messy. Let's use a simpler string replace in the script.
        i += 1
        continue
    else:
        new_lines.append(line)
    i += 1
