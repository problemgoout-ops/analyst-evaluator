#!/usr/bin/env python3
"""Upload remaining GAP and EXCEEDS rows to Notion."""
import json, requests, os, time

API_KEY = os.environ.get('NOTION_API_KEY')
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

DB_GAP = "36188ad72e8881d99e9ad94b88637219"
DB_EXCEEDS = "36188ad72e88813ea419c1728f47fc72"

gap_data = json.load(open('data/gap_analysis.json'))

# Get existing ФИО in GAP db to skip already-uploaded people
def get_existing_people(db_id):
    people = set()
    start = None
    while True:
        body = {"page_size": 100}
        if start:
            body["start_cursor"] = start
        resp = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=HEADERS, json=body)
        data = resp.json()
        for r in data.get("results", []):
            for k, v in r.get("properties", {}).items():
                if v["type"] == "title":
                    people.add("".join(t["plain_text"] for t in v.get("title", [])))
        if not data.get("has_more"):
            break
        start = data.get("next_cursor")
    return people

existing_gap = get_existing_people(DB_GAP)
existing_exc = get_existing_people(DB_EXCEEDS)
print(f"Already in GAP: {len(existing_gap)} people")
print(f"Already in EXCEEDS: {len(existing_exc)} people")

def dept_notion(dept):
    return "1С" if dept in ("1C", "1С") else "WEB/R&D"

def notion_create(page_data, retries=3):
    for attempt in range(retries):
        resp = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=page_data)
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

# Upload remaining GAP rows
print("\n=== Uploading remaining GAP ===")
count = 0
for key in sorted(gap_data.keys()):
    r = gap_data[key]
    name = r['name']
    if name in existing_gap:
        continue
    
    dept = dept_notion(r['dept'])
    target = r['target_grade']
    
    for g in r['self_gaps']:
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
            if count % 10 == 0:
                print(f"  GAP: {count} uploaded", flush=True)
        else:
            print(f"  GAP FAILED: {name} - {g['skill'][:30]}")
        time.sleep(0.35)
    
    print(f"  ✅ {name}: GAP uploaded")

print(f"  GAP remaining: {count} rows DONE")

# Upload remaining EXCEEDS rows
print("\n=== Uploading remaining EXCEEDS ===")
count = 0
for key in sorted(gap_data.keys()):
    r = gap_data[key]
    name = r['name']
    if name in existing_exc:
        continue
    
    dept = dept_notion(r['dept'])
    target = r['target_grade']
    
    for e in r['self_exceeds']:
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
            if count % 10 == 0:
                print(f"  Exceeds: {count} uploaded", flush=True)
        else:
            print(f"  EXCEEDS FAILED: {name} - {e['skill'][:30]}")
        time.sleep(0.35)
    
    print(f"  ✅ {name}: Exceeds uploaded")

print(f"  Exceeds remaining: {count} rows DONE")
print("\n✅ ALL REMAINING DONE")