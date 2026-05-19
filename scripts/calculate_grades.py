#!/usr/bin/env python3
"""
Расчёт грейдов аналитиков v3.1.

Методология:
- Матрицы: Титов (канонические)
- Пороги: S/J+/M = 70%, M+/Sr = 80%
- Hard + Soft вместе
- Проверка сверху вниз (Сеньор → Мидл+ → Мидл → Джун+ → Стажер)
- Fallback: Джун+
"""

import json
import os
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# v3.1 thresholds
THRESHOLDS = {
    'Стажер': 70,
    'Джун+': 70,
    'Мидл': 70,
    'Мидл+': 80,
    'Сеньор': 80,
}

GRADES_ORDER = ['Сеньор', 'Мидл+', 'Мидл', 'Джун+', 'Стажер']
FALLBACK = 'Джун+'
GRADE_SHORT = {'Сеньор':'Sr','Мидл+':'M+','Мидл':'M','Джун+':'J+','Стажер':'S'}
GRADE_INDEX = {'Сеньор':5,'Мидл+':4,'Мидл':3,'Джун+':2,'Стажер':1}


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_grade(assessment, matrix):
    """Calculate grade and percentage scores for each level."""
    grade_scores = {}
    for grade_key in GRADES_ORDER:
        threshold = THRESHOLDS[grade_key]
        matching = 0
        total = 0
        for comp in matrix:
            req = comp.get('requirements', {}).get(grade_key)
            if req is None:
                continue
            actual = assessment.get(comp.get('name'))
            total += 1
            if actual is not None and actual >= req:
                matching += 1
        pct = round(matching / total * 100, 1) if total > 0 else 0
        grade_scores[grade_key] = pct

    # Determine grade: check from top, use specific thresholds
    for grade_key in GRADES_ORDER:
        if grade_scores.get(grade_key, 0) >= THRESHOLDS[grade_key]:
            return grade_key, grade_scores

    return FALLBACK, grade_scores


def main():
    matrix_web = load_json('matrix_web.json')
    matrix_1c = load_json('matrix_1c.json')
    web_self = load_json('web_self_assessment.json')
    web_mgr = load_json('web_manager_assessment.json')
    _1c_self = load_json('1c_self_assessment.json')
    _1c_mgr = load_json('1c_manager_assessment.json')

    results = []

    for name, assessment in sorted(_1c_self.items()):
        sg, ss = calculate_grade(assessment, matrix_1c)
        ma = _1c_mgr.get(name, {})
        mg, ms = calculate_grade(ma, matrix_1c) if ma else ('—', {})
        results.append({'name': name, 'dept': '1C', 'self_grade': sg, 'mgr_grade': mg, 'self_scores': ss, 'mgr_scores': ms})

    for name, assessment in sorted(web_self.items()):
        sg, ss = calculate_grade(assessment, matrix_web)
        ma = web_mgr.get(name, {})
        mg, ms = calculate_grade(ma, matrix_web) if ma else ('—', {})
        results.append({'name': name, 'dept': 'WEB', 'self_grade': sg, 'mgr_grade': mg, 'self_scores': ss, 'mgr_scores': ms})

    print("=" * 110)
    print("РЕЗУЛЬТАТЫ РАСЧЁТА ГРЕЙДОВ v3.1")
    print(f"Пороги: S/J+/M=70%, M+/Sr=80% | Hard+Soft | Матрицы: Титов")
    print("=" * 110)

    for dept in ['1C', 'WEB']:
        dept_results = [r for r in results if r['dept'] == dept]
        print(f"\n{'─' * 110}")
        print(f"ГРУППА: {dept}")
        print(f"{'─' * 110}")
        print(f"{'ФИО':<35} │ {'САМ':<7} │ {'РУК':<7} │ Δ │ {'M%':>5} │ {'M+%':>5} │ {'Sr%':>5}")
        print("─" * 85)

        for r in dept_results:
            short = ' '.join(r['name'].split()[:2])
            sg = r['self_grade']
            mg = r['mgr_grade']
            si = GRADE_INDEX.get(sg, 0)
            mi = GRADE_INDEX.get(mg, 0)
            diff = mi - si
            delta = f'↑{diff}' if diff > 0 else f'↓{abs(diff)}' if diff < 0 else '='
            sp = f"{r['self_scores'].get('Мидл',0):>5.1f} │ {r['self_scores'].get('Мидл+',0):>5.1f} │ {r['self_scores'].get('Сеньор',0):>5.1f}"
            print(f"{short:<35} │ {sg:<7} │ {mg:<7} │ {delta:>2} │ {sp}")

    # Summary
    print("\n" + "=" * 110)
    print("СВОДКА")
    print("=" * 110)

    for dept in ['1C', 'WEB']:
        dept_results = [r for r in results if r['dept'] == dept]
        self_counts = Counter(r['self_grade'] for r in dept_results)
        mgr_counts = Counter(r['mgr_grade'] for r in dept_results)
        same = sum(1 for r in dept_results if r['self_grade'] == r['mgr_grade'])
        print(f"\n{dept}: {len(dept_results)} аналитиков, совпадают {same}/{len(dept_results)}")
        for grade in GRADES_ORDER:
            s = self_counts.get(grade, 0)
            m = mgr_counts.get(grade, 0)
            if s > 0 or m > 0:
                print(f"  {grade:<10} │ САМ: {s:<3} │ РУК: {m:<3}")

        diffs = [r for r in dept_results if r['self_grade'] != r['mgr_grade']]
        if diffs:
            print(f"  Расхождения:")
            for r in diffs:
                si = GRADE_INDEX.get(r['self_grade'], 0)
                mi = GRADE_INDEX.get(r['mgr_grade'], 0)
                d = mi - si
                delta = f'↑{d}' if d > 0 else f'↓{abs(d)}'
                print(f"    {r['name']}: САМ={r['self_grade']} РУК={r['mgr_grade']} ({delta})")


if __name__ == '__main__':
    main()