"""
Notion Today To-do 데이터베이스에서 이번 주/다음 주 항목을 가져와
프로젝트별로 묶어 weekly_input.txt로 저장합니다.
"""

import os
import sys
import requests
from datetime import date, timedelta

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        print("ERROR: .env 파일이 없습니다.")
        sys.exit(1)
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "17f3a29d85cf83a4931781dd2554fb09")

if not NOTION_TOKEN:
    print("ERROR: .env 파일에 NOTION_TOKEN을 입력하세요.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def get_week_range(base: date):
    """base 날짜가 속한 주의 월~일 반환"""
    monday = base - timedelta(days=base.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def query_date_range(start: date, end: date) -> list:
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "and": [
                {"property": "날짜", "date": {"on_or_after": start.isoformat()}},
                {"property": "날짜", "date": {"on_or_before": end.isoformat()}},
            ]
        },
        "sorts": [{"property": "날짜", "direction": "ascending"}],
    }
    res = requests.post(url, headers=HEADERS, json=payload)
    if res.status_code != 200:
        print(f"ERROR: Notion API 오류 {res.status_code} - {res.text}")
        sys.exit(1)
    return res.json().get("results", [])


def get_text(prop: dict) -> str:
    if not prop:
        return ""
    ptype = prop.get("type", "")
    if ptype == "title":
        return "".join(t["plain_text"] for t in prop.get("title", []))
    if ptype == "rich_text":
        return "".join(t["plain_text"] for t in prop.get("rich_text", []))
    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    if ptype == "multi_select":
        return ", ".join(s["name"] for s in prop.get("multi_select", []))
    if ptype == "status":
        st = prop.get("status")
        return st["name"] if st else ""
    if ptype == "date":
        d = prop.get("date")
        return d["start"] if d else ""
    return ""


def parse_items(items: list) -> list:
    result = []
    for item in items:
        props = item.get("properties", {})
        result.append({
            "title":    get_text(props.get("할일", {})),
            "project":  get_text(props.get("프로젝트", {})) or "기타",
            "category": get_text(props.get("업무구분", {})),
            "status":   get_text(props.get("상태", {})),
            "note":     get_text(props.get("비고", {})),
        })
    return result


def group_by_project(items: list) -> dict:
    groups = {}
    for item in items:
        proj = item["project"]
        groups.setdefault(proj, []).append(item)
    return groups


def build_weekly(this_week: list, next_week: list, week_start: date, week_end: date) -> str:
    lines = [
        f"주간 업무보고 ({week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')})",
        "작성자:",
        "",
    ]

    this_week = [t for t in this_week if "주간보고" not in t["title"]]
    next_week  = [t for t in next_week  if "주간보고" not in t["title"]]

    this_week_by_proj = group_by_project(this_week)
    next_week_by_proj = group_by_project(next_week)

    all_projects = list(dict.fromkeys(
        list(this_week_by_proj.keys()) + list(next_week_by_proj.keys())
    ))

    # 금주 진행사항
    lines.append("─" * 50)
    lines.append("[금주 진행사항]")
    lines.append("")
    if not this_week:
        lines.append("  (이번 주 등록된 업무 없음)")
    else:
        for proj in [p for p in all_projects if p in this_week_by_proj]:
            lines.append(f"  [{proj}]")
            for i, t in enumerate(this_week_by_proj[proj], 1):
                status_tag = f" ({t['status']})" if t["status"] else ""
                lines.append(f"  {i}. {t['title']}{status_tag}")
                if t["note"]:
                    lines.append(f"     → {t['note']}")
            lines.append("")

    # 차주 예정사항
    lines.append("─" * 50)
    lines.append("[차주 예정사항]")
    lines.append("")
    if not next_week:
        lines.append("  (다음 주 등록된 업무 없음)")
        lines.append("")
    else:
        for proj in [p for p in all_projects if p in next_week_by_proj]:
            lines.append(f"  [{proj}]")
            for t in next_week_by_proj[proj]:
                lines.append(f"  - {t['title']}")
            lines.append("")

    # 주요 이슈사항
    lines.append("─" * 50)
    lines.append("[주요 이슈사항]")
    lines.append("")
    issues = [t for t in this_week if t["note"]]
    if issues:
        for t in issues:
            lines.append(f"  - [{t['project']}] {t['note']}")
    else:
        lines.append("  - 없음")
    lines.append("")
    lines.append("─" * 50)

    return "\n".join(lines)


if __name__ == "__main__":
    today = date.today()
    week_start, week_end = get_week_range(today)
    next_start = week_end + timedelta(days=1)
    next_end = next_start + timedelta(days=6)

    print(f"이번 주 ({week_start} ~ {week_end}) 데이터를 가져오는 중...")
    this_week_items = parse_items(query_date_range(week_start, week_end))
    next_week_items = parse_items(query_date_range(next_start, next_end))

    print(f"  이번 주 항목: {len(this_week_items)}개, 다음 주 항목: {len(next_week_items)}개")

    content = build_weekly(this_week_items, next_week_items, week_start, week_end)

    out_path = os.path.join(os.path.dirname(__file__), "weekly_input.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  weekly_input.txt 저장 완료")
    print()
    print(content)
