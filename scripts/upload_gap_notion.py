#!/usr/bin/env python3
"""Upload GAP analysis v3.1 data to Notion databases."""
import json, requests, os, sys, time

API_KEY = os.environ.get('NOTION_API_KEY')
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

DB_GAP = "36188ad72e8881d99e9ad94b88637219"
DB_EXCEEDS = "36188ad72e88813ea419c1728f47fc72"
DB_SUMMARY = "36188ad72e8881fd8871f3023575f8f1"

# Load data
gap_data = json.load(open('data/gap_analysis.json'))

def notion_create(page_data, retries=3):
    for attempt in range(retries):
        resp = requests.post(
            "https://api.notion.com/v1/pages",
            headers=HEADERS,
            json=page_data
        )
        if resp.status_code == 200:
            return True
        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', 1))
            time.sleep(retry_after)
            continue
        if resp.status_code >= 500:
            time.sleep(2)
            continue
        print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
        return False
    return False

# Department mapping
def dept_notion(dept):
    return "1С" if dept in ("1C", "1С") else "WEB/R&D"

# ============================================
# 1. SUMMARY TABLE
# ============================================
print("=== Uploading SUMMARY ===")
count = 0
for key in sorted(gap_data.keys()):
    r = gap_data[key]
    name = r['name']
    dept = dept_notion(r['dept'])
    grade = r['current_grade_self']
    target = r['target_grade']
    gap_count = r['gap_count_self']
    exc_count = r['exceed_count_self']
    
    # Group gaps by block
    gap_blocks = {}
    for g in r['self_gaps']:
        block = g['block']
        skill = g['skill']
        if block not in gap_blocks:
            gap_blocks[block] = []
        gap_blocks[block].append(skill)
    
    gap_str = "; ".join(f"{b}: {', '.join(ss)}" for b, ss in gap_blocks.items())
    
    # Group exceeds by block
    exc_blocks = {}
    for e in r['self_exceeds']:
        block = e['block']
        skill = e['skill']
        if block not in exc_blocks:
            exc_blocks[block] = []
        exc_blocks[block].append(skill)
    
    exc_str = "; ".join(f"{b}: {', '.join(ss)}" for b, ss in exc_blocks.items())
    
    page = {
        "parent": {"database_id": DB_SUMMARY},
        "properties": {
            "ФИО": {"title": [{"text": {"content": name}}]},
            "Отдел": {"select": {"name": dept}},
            "Грейд": {"select": {"name": grade}},
            "Целевой грейд": {"select": {"name": target}},
            "GAP навыков": {"number": gap_count},
            "Превышает навыков": {"number": exc_count},
            "GAP блоков": {"number": len(gap_blocks)},
            "Превышает блоков": {"number": len(exc_blocks)},
            "GAP (блоки → навыки)": {"rich_text": [{"text": {"content": gap_str[:2000]}}]},
            "Превышает (блоки → навыки)": {"rich_text": [{"text": {"content": exc_str[:2000]}}]},
        }
    }
    
    if notion_create(page):
        count += 1
        if count % 5 == 0:
            print(f"  Summary: {count}/24", flush=True)
    else:
        print(f"  FAILED: {name}")
    time.sleep(0.35)

print(f"  Summary: {count}/24 DONE")

# ============================================
# 2. GAP TABLE
# ============================================
print("\n=== Uploading GAP ===")
count = 0
total_gaps = 0

for key in sorted(gap_data.keys()):
    r = gap_data[key]
    name = r['name']
    dept = dept_notion(r['dept'])
    target = r['target_grade']
    
    for g in r['self_gaps']:
        total_gaps += 1
        criticality = "🔴 Критический" if g['gap'] >= 2 else "🟡 Недостаточно"
        
        page = {
            "parent": {"database_id": DB_GAP},
            "properties": {
                "ФИО": {"title": [{"text": {"content": name}}]},
                "Отдел": {"select": {"name": dept}},
                "Блок": {"select": {"name": g['block']}},
                "Навык": {"rich_text": [{"text": {"content": g['skill'][:2000]}}]},
                "Тип": {"select": {"name": g['type']}},
                "Целевой грейд": {"select": {"name": target}},
                "Самооценка": {"number": g['actual']},
                "Требование M": {"number": g['required']},
                "Разрыв": {"number": g['gap']},
                "Критичность": {"select": {"name": criticality}},
            }
        }
        
        if notion_create(page):
            count += 1
            if count % 20 == 0:
                print(f"  GAP: {count} uploaded", flush=True)
        else:
            print(f"  GAP FAILED: {name} - {g['skill'][:30]}")
        time.sleep(0.35)

print(f"  GAP: {count} rows DONE (expected ~{total_gaps})")

# ============================================
# 3. EXCEEDS TABLE
# ============================================
print("\n=== Uploading EXCEEDS ===")
count = 0
total_exc = 0

for key in sorted(gap_data.keys()):
    r = gap_data[key]
    name = r['name']
    dept = dept_notion(r['dept'])
    target = r['target_grade']
    
    for e in r['self_exceeds']:
        total_exc += 1
        level = "🟡 Значительно превышает" if e['exceed'] >= 2 else "🟢 Превышает"
        
        page = {
            "parent": {"database_id": DB_EXCEEDS},
            "properties": {
                "ФИО": {"title": [{"text": {"content": name}}]},
                "Отдел": {"select": {"name": dept}},
                "Блок": {"select": {"name": e['block']}},
                "Навык": {"rich_text": [{"text": {"content": e['skill'][:2000]}}]},
                "Тип": {"select": {"name": e['type']}},
                "Целевой грейд": {"select": {"name": target}},
                "Самооценка": {"number": e['actual']},
                "Требование M": {"number": e['required']},
                "Превышение": {"number": e['exceed']},
                "Уровень": {"select": {"name": level}},
            }
        }
        
        if notion_create(page):
            count += 1
            if count % 20 == 0:
                print(f"  Exceeds: {count} uploaded", flush=True)
        else:
            print(f"  EXCEEDS FAILED: {name} - {e['skill'][:30]}")
        time.sleep(0.35)

print(f"  Exceeds: {count} rows DONE (expected ~{total_exc})")
print("\n✅ ALL DONE")