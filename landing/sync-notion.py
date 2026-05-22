#!/usr/bin/env python3
"""
Синхронизация данных из Notion → data.json для analysts.html + analyst.html

Источник: база "Состав ЦК" (35e88ad72e8880058a25f6b2ebb15dc5)

Маппинг полей (каталог):
  Аккордеон отдела   ← Отдел
  ФИО + аватар       ← Фамилия Имя
  Бейдж грейда       ← Самооценка
  Бейдж продукта     ← Продукт
  Бейдж интегральной ← Интегральная оценка
  Бейдж нахождения   ← Нахождение

Маппинг полей (профиль):
  Шапка: Фамилия Имя, Отдел, Стек, Продукт, Нахождение, Самооценка, Руководитель ФР
  Оценка: Интегральная оценка, Потенциал (ПИФ), Руководитель ФР, Самооценка, ППД статус, PlayBook статус, Провайдер
  GAP: из базы "GAP по специалистам"
  Превышает: из базы "Превышение ожиданий"
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone


def translit(name):
    pairs = [
        ('а','a'),('б','b'),('в','v'),('г','g'),('д','d'),('е','e'),('ё','yo'),('ж','zh'),('з','z'),('и','i'),('й','y'),('к','k'),('л','l'),('м','m'),('н','n'),('о','o'),('п','p'),('р','r'),('с','s'),('т','t'),('у','u'),('ф','f'),('х','kh'),('ц','ts'),('ч','ch'),('ш','sh'),('щ','shch'),('ъ',''),('ы','y'),('ь',''),('э','e'),('ю','yu'),('я','ya'),
        ('А','A'),('Б','B'),('В','V'),('Г','G'),('Д','D'),('Е','E'),('Ё','Yo'),('Ж','Zh'),('З','Z'),('И','I'),('Й','Y'),('К','K'),('Л','L'),('М','M'),('Н','N'),('О','O'),('П','P'),('Р','R'),('С','S'),('Т','T'),('У','U'),('Ф','F'),('Х','Kh'),('Ц','Ts'),('Ч','Ch'),('Ш','Sh'),('Щ','Shch'),('Ъ',''),('Ы','Y'),('Ь',''),('Э','E'),('Ю','Yu'),('Я','Ya')
    ]
    s = name
    for ru, en in pairs:
        s = s.replace(ru, en)
    s = re.sub(r'[^a-zA-Z0-9]', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "${NOTION_API_KEY}")
NOTION_VERSION = "2022-06-28"

# Composite DB "Состав ЦК"
COMPOSITE_DB_ID = "35e88ad72e8880058a25f6b2ebb15dc5"
# GAP DB
GAP_DB_ID = "36188ad72e8881fd8871f3023575f8f1"
# Exceeds DB
EXCEEDS_DB_ID = "36188ad72e88813ea419c1728f47fc72"

OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/home/ClawdTitov/.openclaw/workspace/data.json")
REMOTE_PATH = "/var/www/u3520972/data/www/titovtech.ru/data.json"
REMOTE_HOST = "u3520972@31.31.198.55"


def notion_request(path, body=None):
    url = f"https://api.notion.com/v1/{path}"
    data = json.dumps(body).encode() if body else b""
    req = urllib.request.Request(url, data=data, method="POST" if body else "GET")
    req.add_header("Authorization", f"Bearer {NOTION_API_KEY}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Notion API error: {e.code} {e.reason}", file=sys.stderr)
        return None


def get_prop(prop):
    if not prop:
        return ""
    t = prop.get("type", "")
    if t == "title" and prop.get("title"):
        return prop["title"][0]["plain_text"]
    if t == "select" and prop.get("select"):
        return prop["select"]["name"]
    if t == "rich_text" and prop.get("rich_text"):
        return prop["rich_text"][0]["plain_text"]
    if t == "number" and prop.get("number") is not None:
        return prop["number"]
    if t == "status" and prop.get("status"):
        return prop["status"]["name"]
    return ""


def fetch_composite_db():
    """Fetch all pages from Состав ЦК via search"""
    all_pages = []
    has_more = True
    start_cursor = None
    while has_more:
        body = {"query": " ", "filter": {"property": "object", "value": "page"}, "page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        data = notion_request("search", body)
        if not data:
            break
        target_nodash = COMPOSITE_DB_ID.replace("-", "")
        for page in data.get("results", []):
            parent = page.get("parent", {})
            pid = parent.get("database_id", "").replace("-", "")
            if pid == target_nodash:
                all_pages.append(page)
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
    return all_pages


def fetch_gap_db():
    """Fetch all records from GAP по специалистам"""
    results = []
    has_more = True
    start_cursor = None
    while has_more:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        data = notion_request(f"databases/{GAP_DB_ID}/query", body)
        if not data:
            break
        results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
    return results


def fetch_exceeds_db():
    """Fetch all records from Превышение ожиданий"""
    results = []
    has_more = True
    start_cursor = None
    while has_more:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        data = notion_request(f"databases/{EXCEEDS_DB_ID}/query", body)
        if not data:
            break
        results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
    return results


def main():
    print("Fetching Состав ЦК...")
    ck_pages = fetch_composite_db()
    print(f"  Got {len(ck_pages)} pages")

    print("Fetching GAP по специалистам...")
    gap_pages = fetch_gap_db()
    print(f"  Got {len(gap_pages)} records")

    print("Fetching Превышение ожиданий...")
    exceeds_pages = fetch_exceeds_db()
    print(f"  Got {len(exceeds_pages)} records")

    # Build employees from Состав ЦК
    employees = []
    for page in ck_pages:
        p = page.get("properties", {})
        name = get_prop(p.get("Фамилия Имя", {}))
        if not name:
            continue
        emp = {
            "name": name,
            "slug": translit(name),
            "dept": get_prop(p.get("Отдел", {})),
            "grade": get_prop(p.get("Самооценка", {})),
            "location": get_prop(p.get("Нахождение", {})),
            "integral": get_prop(p.get("Интегральная оценка", {})),
            "product": get_prop(p.get("Продукт", {})),
            "stack": get_prop(p.get("Стек", {})),
            "pif": get_prop(p.get("Потенциал (ПИФ)", {})),
            "managerGrade": get_prop(p.get("Руководитель", {})),
            "managerFR": get_prop(p.get("Руководитель ФР", {})),
            "ppdStatus": get_prop(p.get("ППД статус", {})),
            "playbookStatus": get_prop(p.get("PlayBook статус", {})),
            "ppdResult": get_prop(p.get("ППД", {})),
            "playbookResult": get_prop(p.get("PlayBook результат", {})),
            "provider": get_prop(p.get("Провайдер", {})),
            "evalDiff": get_prop(p.get("Разница в оценке", {})),
        }
        employees.append(emp)

    employees.sort(key=lambda e: (e["dept"], e["name"]))

    # Build GAP data per person
    gap_data = {}
    for page in gap_pages:
        p = page.get("properties", {})
        name = get_prop(p.get("ФИО", {}))
        if not name:
            continue
        if name not in gap_data:
            gap_data[name] = {"gap_blocks": 0, "gap_skills": 0, "exceeds_blocks": 0, "exceeds_skills": 0, "gap_detail": "", "exceeds_detail": ""}
        gap_data[name]["gap_blocks"] = p.get("GAP блоков", {}).get("number") or 0
        gap_data[name]["gap_skills"] = p.get("GAP навыков", {}).get("number") or 0
        gap_data[name]["exceeds_blocks"] = p.get("Превышает блоков", {}).get("number") or 0
        gap_data[name]["exceeds_skills"] = p.get("Превышает навыков", {}).get("number") or 0
        gap_data[name]["gap_detail"] = get_prop(p.get("GAP (блоки → навыки)", {}))
        gap_data[name]["exceeds_detail"] = get_prop(p.get("Превышает (блоки → навыки)", {}))

    # Build exceeds data per person (skills)
    exceeds_data = {}
    for page in exceeds_pages:
        p = page.get("properties", {})
        name = get_prop(p.get("ФИО", {}))
        if not name:
            continue
        if name not in exceeds_data:
            exceeds_data[name] = []
        block = get_prop(p.get("Блок", {}))
        skill = get_prop(p.get("Навык", {}))
        self_eval = get_prop(p.get("Самооценка", {}))
        requirement = p.get("Требование M", {}).get("number")
        exceeds_val = p.get("Превышение", {}).get("number")
        level = get_prop(p.get("Уровень", {}))
        target_grade = get_prop(p.get("Целевой грейд", {}))
        skill_type = get_prop(p.get("Тип", {}))
        exceeds_data[name].append({
            "block": block,
            "skill": skill,
            "selfEval": self_eval,
            "requirement": requirement,
            "exceeds": exceeds_val,
            "level": level,
            "targetGrade": target_grade,
            "type": skill_type,
        })

    # Merge gap + exceeds data into employees
    for emp in employees:
        gd = gap_data.get(emp["name"], {})
        emp["gap_blocks"] = gd.get("gap_blocks", 0)
        emp["gap_skills"] = gd.get("gap_skills", 0)
        emp["exceeds_blocks"] = gd.get("exceeds_blocks", 0)
        emp["exceeds_skills"] = gd.get("exceeds_skills", 0)
        emp["gap_detail"] = gd.get("gap_detail", "")
        emp["exceeds_detail"] = gd.get("exceeds_detail", "")
        emp["skills"] = exceeds_data.get(emp["name"], [])

    output = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Notion API - Состав ЦК + GAP + Превышение",
        "mapping": {
            "dept": "Отдел",
            "name": "Фамилия Имя",
            "grade": "Самооценка",
            "location": "Нахождение",
            "integral": "Интегральная оценка",
            "product": "Продукт",
            "stack": "Стек",
            "pif": "Потенциал (ПИФ)",
            "managerGrade": "Руководитель",
            "managerFR": "Руководитель ФР",
            "ppdStatus": "ППД статус",
            "playbookStatus": "PlayBook статус",
            "ppdResult": "ППД",
            "playbookResult": "PlayBook результат",
            "provider": "Провайдер",
            "gap_blocks": "GAP блоков",
            "gap_skills": "GAP навыков",
            "exceeds_blocks": "Превышает блоков",
            "exceeds_skills": "Превышает навыков",
            "gap_detail": "GAP (блоки → навыки)",
            "exceeds_detail": "Превышает (блоки → навыки)",
        },
        "employees": employees,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Written {len(employees)} employees to {OUTPUT_PATH}")

    # Deploy to titovtech.ru
    import subprocess
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", REMOTE_HOST, f"cat > {REMOTE_PATH}"],
            input=json.dumps(output, ensure_ascii=False).encode(),
            timeout=15,
        )
        if result.returncode == 0:
            print(f"Deployed to https://titovtech.ru/data.json")
        else:
            print(f"SSH deploy failed: {result.returncode}", file=sys.stderr)
    except Exception as e:
        print(f"SSH deploy error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()