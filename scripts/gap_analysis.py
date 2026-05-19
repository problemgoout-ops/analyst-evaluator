#!/usr/bin/env python3
"""
GAP-анализ компетенций аналитиков v3.1.

Методология:
- Берём зафиксированный грейд из final_grades.json (НЕ пересчитываем)
- Сравниваем фактические навыки с требованиями СЛЕДУЮЩЕГО грейда
- GAP: факт < требование (навык не дотягивает)
- Превышение: факт > требование (навык уже на уровне выше)
- Для Сеньоров: сравниваем с Sr-требованиями (подтверждение уровня)

Пороги v3.1: S/J+/M = 70%, M+/Sr = 80%
Матрицы: Титов (10 троек на Sr для 1С, 10 для WEB)
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

GRADE_ORDER = ['Стажер', 'Джун+', 'Мидл', 'Мидл+', 'Сеньор']
GRADE_NEXT = {'Стажер': 'Джун+', 'Джун+': 'Мидл', 'Мидл': 'Мидл+', 'Мидл+': 'Сеньор'}
GRADE_SHORT = {'Сеньор': 'Sr', 'Мидл+': 'M+', 'Мидл': 'M', 'Джун+': 'J+', 'Стажер': 'S'}
LABELS = {0: '❌', 1: '📖', 2: '🛠', 3: '🦾'}


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


def gap_analysis(name, assessment, matrix, current_grade):
    """Compare actual scores against NEXT grade requirements."""
    if current_grade == 'Сеньор':
        next_g = 'Сеньор'
        is_senior = True
    else:
        next_g = GRADE_NEXT.get(current_grade, 'Мидл')
        is_senior = False

    gaps = []
    exceeds = []

    for item in matrix:
        skill_name = item['name']
        skill_type = item['type']
        skill_block = item['block']
        req = item['requirements'].get(next_g)
        if req is None:
            continue
        actual = assessment.get(skill_name)
        if actual is None:
            continue

        entry = {
            'skill': skill_name,
            'block': skill_block,
            'type': skill_type,
            'required': req,
            'actual': actual,
            'target_grade': next_g,
            'label': f"{LABELS.get(actual, '?')} {actual}/{req}"
        }

        if actual < req:
            entry['gap'] = req - actual
            gaps.append(entry)
        elif actual > req:
            entry['exceed'] = actual - req
            exceeds.append(entry)

    gaps.sort(key=lambda x: -x['gap'])
    exceeds.sort(key=lambda x: -x['exceed'])
    return gaps, exceeds, next_g, is_senior


def run_gap_analysis():
    """Run GAP analysis for all analysts and return results."""
    sa_1c = load_json('1c_self_assessment.json')
    mr_1c = load_json('1c_manager_assessment.json')
    sa_web = load_json('web_self_assessment.json')
    mr_web = load_json('web_manager_assessment.json')
    mat_1c = load_json('matrix_1c.json')
    mat_web = load_json('matrix_web.json')
    fg = load_json('final_grades.json')

    grade_en_ru = {'Sr': 'Сеньор', 'M+': 'Мидл+', 'M': 'Мидл', 'J+': 'Джун+', 'S': 'Стажер'}

    all_results = {}
    for dept, sa, mr, mat in [('1C', sa_1c, mr_1c, mat_1c), ('WEB', sa_web, mr_web, mat_web)]:
        sa_key = f'{dept}_self'
        mr_key = f'{dept}_manager'
        for name in sorted(sa.keys()):
            g_en = fg.get(sa_key, {}).get(name, 'J+')
            current_self = grade_en_ru.get(g_en, 'Джун+')
            g_en_mgr = fg.get(mr_key, {}).get(name, 'J+')
            current_mgr = grade_en_ru.get(g_en_mgr, 'Джун+')

            self_gaps, self_exceeds, target_g, is_sr = gap_analysis(name, sa[name], mat, current_self)
            mgr_gaps, mgr_exceeds, _, _ = gap_analysis(name, mr.get(name, {}), mat, current_mgr)

            all_results[f'{dept}_{name}'] = {
                'dept': dept,
                'name': name,
                'current_grade_self': current_self,
                'current_grade_mgr': current_mgr,
                'target_grade': target_g,
                'is_senior': is_sr,
                'self_gaps': self_gaps,
                'self_exceeds': self_exceeds,
                'mgr_gaps': mgr_gaps,
                'mgr_exceeds': mgr_exceeds,
                'gap_count_self': len(self_gaps),
                'exceed_count_self': len(self_exceeds),
                'gap_count_mgr': len(mgr_gaps),
                'exceed_count_mgr': len(mgr_exceeds),
            }

    return all_results


def print_summary(results):
    """Print summary table."""
    gr = {'Сеньор': 'Sr', 'Мидл+': 'M+', 'Мидл': 'M', 'Джун+': 'J+', 'Стажер': 'S'}
    print("GAP-АНАЛИЗ (сравнение с требованиями СЛЕДУЮЩЕГО грейда)")
    print("=" * 95)
    print(f"{'Аналитик':<30s} {'Отдел':<4s} {'САМ':>4s} {'→':>2s} {'Цель':>5s} {'GAP':>4s} {'EXC':>4s} | {'РУК':>4s} {'→':>2s} {'Цель':>5s} {'GAP':>4s} {'EXC':>4s}")
    print("-" * 95)
    for key, r in sorted(results.items()):
        sg = gr.get(r['current_grade_self'], '?')
        mg = gr.get(r['current_grade_mgr'], '?')
        tg = gr.get(r['target_grade'], '?')
        sr_mark = ' ★' if r['is_senior'] else ''
        print(f"{r['name'][:30]:<30s} {r['dept']:<4s} {sg:>4s}  → {tg:>5s} {r['gap_count_self']:>4d} {r['exceed_count_self']:>4d} | {mg:>4s}  → {tg:>5s} {r['gap_count_mgr']:>4d} {r['exceed_count_mgr']:>4d}{sr_mark}")
    print(f"\n★ = Сеньор, сравнение с Sr-требованиями")


def print_detail(name, dept, results, show='both'):
    """Print detailed GAP/Exceeds for one analyst."""
    key = f'{dept}_{name}'
    if key not in results:
        print(f"Аналитик {name} ({dept}) не найден")
        return

    r = results[key]
    gr = {'Сеньор': 'Sr', 'Мидл+': 'M+', 'Мидл': 'M', 'Джун+': 'J+', 'Стажер': 'S'}

    print(f"\n{'=' * 70}")
    print(f"  {name} ({dept})")
    print(f"  САМ: {gr.get(r['current_grade_self'], '?')} → целевой: {gr.get(r['target_grade'], '?')}")
    print(f"  РУК: {gr.get(r['current_grade_mgr'], '?')}")
    if r['is_senior']:
        print(f"  ★ Сеньор — подтверждение уровня")
    print(f"{'=' * 70}")

    if show in ('both', 'gaps'):
        print(f"\n  🔴 GAP (навыки ниже требований {r['target_grade']}):")
        print(f"  {'Навык':<40s} {'Блок':<20s} {'Факт':>4s} {'Треб':>4s} {'GAP':>4s}")
        for g in r['self_gaps']:
            print(f"  {g['skill'][:40]:<40s} {g['block'][:20]:<20s} {g['actual']:>4d} {g['required']:>4d} {g['gap']:>4d}")

    if show in ('both', 'exceeds'):
        print(f"\n  🟢 Превышение (навыки выше требований {r['target_grade']}):")
        print(f"  {'Навык':<40s} {'Блок':<20s} {'Факт':>4s} {'Треб':>4s} {'+':>4s}")
        for e in r['self_exceeds']:
            print(f"  {e['skill'][:40]:<40s} {e['block'][:20]:<20s} {e['actual']:>4d} {e['required']:>4d} {e['exceed']:>4d}")


if __name__ == '__main__':
    import sys

    results = run_gap_analysis()

    # Save
    with open(os.path.join(DATA_DIR, 'gap_analysis.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    if len(sys.argv) > 1:
        # Print detail for specific analyst
        name = ' '.join(sys.argv[1:])
        # Find by partial name match
        for key, r in results.items():
            if name in r['name']:
                print_detail(r['name'], r['dept'], results)
                break
        else:
            print(f"Аналитик '{name}' не найден")
    else:
        print_summary(results)
        print(f"\nИспользование: python3 gap_analysis.py [имя аналитика]")
        print(f"Для детального GAP-анализа конкретного сотрудника")