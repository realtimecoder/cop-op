import sys

with open('workers/models.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'def recommended_score(self, distance_km=2.0):' in line:
        new_lines.append(line)
        new_lines.append('        """FR-025 Recommended Ranking formula (Optimized for Nearest & Fair):\n')
        new_lines.append('        Score = 0.10*Rating + 0.10*SkillMatch + 0.05*Availability + 0.45*Distance + 0.25*Fairness + 0.05*Reliability\n')
        new_lines.append('        Fairness ensures work distribution without completely blocking nearby workers."""\n')
        new_lines.append('        rating_component = float(self.average_rating) / 5.0\n')
        new_lines.append('        skill_map = {\'basic\': .5, \'skilled\': .65, \'advanced\': .8, \'expert\': .9, \'certified\': 1.0}\n')
        new_lines.append('        skill_component = skill_map.get(self.skill_grade, .5)\n')
        new_lines.append('        availability_component = 1.0 if self.is_available_now else 0.3\n')
        new_lines.append('        distance_component = max(0.0, 1 - (distance_km / max(self.service_radius_km, 1)))\n')
        new_lines.append('        reliability_component = float(self.reliability_score)\n\n')
        new_lines.append('        # Softened Fairness component: penalize but dont kill the score\n')
        new_lines.append('        fairness_component = 1.0\n')
        new_lines.append('        if self.last_worked_date:\n')
        new_lines.append('            days_since_work = (timezone.localdate() - self.last_worked_date).days\n')
        new_lines.append('            if days_since_work == 0:\n')
        new_lines.append('                fairness_component = 0.5\n')
        new_lines.append('            elif days_since_work == 1:\n')
        new_lines.append('                fairness_component = 0.7\n')
        new_lines.append('            elif days_since_work == 2:\n')
        new_lines.append('                fairness_component = 0.9\n\n')
        new_lines.append('        score = (0.10 * rating_component + 0.10 * skill_component + 0.05 * availability_component\n')
        new_lines.append('                 + 0.45 * distance_component + 0.25 * fairness_component + 0.05 * reliability_component)\n')
        new_//S_S_T_B_T
        new_lines.append('        return round(score * 100, 1)\n')
        
        # Find the end of the old method to skip it
        while i < len(lines) and (not lines[i].strip().startswith('def ') and not lines[i].strip().startswith('class ')):
            i += 1
        i -= 1 
        # This skip logic is slightly flawed, I'll use a more robust string replacement
        continue
    else:
        new_lines.append(line)
    i += 1
