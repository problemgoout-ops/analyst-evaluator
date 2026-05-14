#!/usr/bin/env python3
"""
Расчёт грейдов на основе сохранённых данных.
Можно менять интерпретацию без переписывания всего.
"""

import json
import os
from collections import Counter

# Load configuration
CONFIG = {
    "threshold_percent": 70,
    "hard_skills_only": True,
    "grades_order": ["Сеньор", "Мидл+", "Мидл", "Джун+", "Стажер"],
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), 'r') as f:
        return json.load(f)

def calculate_grade(assessment, matrix, config=None):
    """Calculate grade based on assessment and matrix"""
    if config is None:
        config = CONFIG
    
    threshold = config.get("threshold_percent", 70)
    hard_only = config.get("hard_skills_only", True)
    grades_order = config.get("grades_order", ["Сеньор", "Мидл+", "Мидл", "Джун+", "Стажер"])
    
    # Filter competencies
    if hard_only:
        comps = [c for c in matrix if c.get('type') == 'Hard']
    else:
        comps = matrix
    
    grade_scores = {}
    for grade in grades_order:
        matching = 0
        total = 0
        for comp in comps:
            req = comp.get('requirements', {}).get(grade)
            if req is None:
                continue
            actual = assessment.get(comp.get('name'))
            if actual is None:
                continue
            total += 1
            if actual >= req:
                matching += 1
        
        pct = (matching / total * 100) if total > 0 else 0
        grade_scores[grade] = round(pct, 1)
    
    # Find highest grade meeting threshold
    final_grade = "Ниже Стажера"
    for grade in grades_order:
        if grade_scores.get(grade, 0) >= threshold:
            final_grade = grade
            break
    
    return final_grade, grade_scores

def main():
    # Load data
    matrix_web = load_json('matrix_web.json')
    matrix_1c = load_json('matrix_1c.json')
    web_self = load_json('web_self_assessment.json')
    web_mgr = load_json('web_manager_assessment.json')
    _1c_self = load_json('1c_self_assessment.json')
    _1c_mgr = load_json('1c_manager_assessment.json')
    
    # Calculate all grades
    results = []
    
    # 1C
    for name, assessment in _1c_self.items():
        self_grade, self_scores = calculate_grade(assessment, matrix_1c)
        mgr_assessment = _1c_mgr.get(name, {})
        mgr_grade, mgr_scores = calculate_grade(mgr_assessment, matrix_1c) if mgr_assessment else ("—", {})
        results.append({
            'name': name,
            'dept': '1C',
            'self_grade': self_grade,
            'mgr_grade': mgr_grade,
            'self_scores': self_scores,
            'mgr_scores': mgr_scores
        })
    
    # WEB
    for name, assessment in web_self.items():
        self_grade, self_scores = calculate_grade(assessment, matrix_web)
        mgr_assessment = web_mgr.get(name, {})
        mgr_grade, mgr_scores = calculate_grade(mgr_assessment, matrix_web) if mgr_assessment else ("—", {})
        results.append({
            'name': name,
            'dept': 'WEB',
            'self_grade': self_grade,
            'mgr_grade': mgr_grade,
            'self_scores': self_scores,
            'mgr_scores': mgr_scores
        })
    
    # Print results
    print("=" * 120)
    print("РЕЗУЛЬТАТЫ РАСЧЁТА ГРЕЙДОВ")
    print(f"Порог: {CONFIG['threshold_percent']}%, Только Hard: {CONFIG['hard_skills_only']}")
    print("=" * 120)
    
    for dept in ['1C', 'WEB']:
        dept_results = [r for r in results if r['dept'] == dept]
        print(f"\n{'─' * 120}")
        print(f"ГРУППА: {dept}")
        print(f"{'─' * 120}")
        print(f"{'ФИО':<30} │ {'Само':<7} │ {'Рук':<7} │ Δ │ {'Сн/М+/М/Дж+':<20}")
        print("─" * 80)
        
        for r in dept_results:
            name_short = ' '.join(r['name'].split()[:2])
            sg = r['self_scores']
            mg = r['mgr_scores']
            sp = f"{sg.get('Сеньор', 0):.0f}/{sg.get('Мидл+', 0):.0f}/{sg.get('Мидл', 0):.0f}/{sg.get('Джун+', 0):.0f}"
            mp = f"{mg.get('Сеньор', 0):.0f}/{mg.get('Мидл+', 0):.0f}/{mg.get('Мидл', 0):.0f}/{mg.get('Джун+', 0):.0f}" if mg else '—'
            
            if r['self_grade'] != r['mgr_grade']:
                delta = '↑' if r['mgr_grade'] in ['Сеньор', 'Мидл+'] and r['self_grade'] in ['Мидл', 'Джун+', 'Стажер'] else '↓'
            else:
                delta = '='
            
            print(f"{name_short:<30} │ {r['self_grade']:<7} │ {r['mgr_grade']:<7} │ {delta} │ {sp}/{mp}")
    
    # Summary
    print("\n" + "=" * 120)
    print("СВОДКА")
    print("=" * 120)
    
    self_counts = Counter(r['self_grade'] for r in results)
    mgr_counts = Counter(r['mgr_grade'] for r in results)
    
    for grade in ['Сеньор', 'Мидл+', 'Мидл', 'Джун+', 'Стажер']:
        s = self_counts.get(grade, 0)
        m = mgr_counts.get(grade, 0)
        if s > 0 or m > 0:
            print(f"  {grade:<10} │ Само: {s:<3} │ Рук: {m:<3}")
    
    same = sum(1 for r in results if r['self_grade'] == r['mgr_grade'])
    print(f"\n  Совпадают: {same}/{len(results)}")
    
    print("\n  Расхождения:")
    for r in results:
        if r['self_grade'] != r['mgr_grade']:
            print(f"    {r['name']}: {r['self_grade']} → {r['mgr_grade']}")

if __name__ == '__main__':
    main()
