"""
Notion 데이터베이스에서 오늘/내일 업무 항목을 가져와 today_input.txt로 저장합니다.
"""

import os
import sys
import requests
from datetime import date, timedelta

# .env 파일 로드 (python-dotenv가 없으면 수동으로 읽기)
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        print("ERROR: .env 파일이 없습니다. .env.example을 복사하고 토큰을 입력하세요.")
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

if not NOTION_TOKEN or NOTION_TOKEN == "secret_여기에_토큰_입력":
    print("ERROR: .env 파일에 NOTION_TOKEN을 입력하세요.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def query_by_date(date_str: str) -> list:
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "날짜",
            "date": {"equals": date_str},
        }
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


def get_page_body(page_id: str) -> str:
    """페이지 본문(blocks) 텍스트 추출"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return ""

    lines = []
    for block in res.json().get("results", []):
        btype = block.get("type", "")
        content = block.get(btype, {})
        rich_text = content.get("rich_text", [])
        text = "".join(t["plain_text"] for t in rich_text).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def parse_items(items: list) -> list:
    result = []
    for item in items:
        props = item.get("properties", {})
        page_id = item.get("id", "")
        result.append({
            "title":    get_text(props.get("할일", {})),
            "project":  get_text(props.get("프로젝트", {})),
            "category": get_text(props.get("업무구분", {})),
            "status":   get_text(props.get("상태", {})),
            "note":     get_text(props.get("비고", {})),
            "body":     get_page_body(page_id),
        })
    return result


def build_input(today_items: list, tomorrow_items: list) -> str:
    lines = ["# 금일업무"]

    if not today_items:
        lines.append("\n## 업무1")
        lines.append("제목: (오늘 등록된 업무 없음)")
        lines.append("내용:")
        lines.append("액션:")
    else:
        for i, task in enumerate(today_items, 1):
            lines.append(f"\n## 업무{i}")
            lines.append(f"제목: {task['title']}")
            lines.append(f"프로젝트: {task['project']}")
            lines.append("내용:")
            if task["body"]:
                for body_line in task["body"].split("\n"):
                    if body_line.strip():
                        lines.append(f"  - {body_line.strip()}")
            if task["note"]:
                lines.append(f"액션: {task['note']}")
            else:
                lines.append("액션:")

    def is_weekly_meeting(title: str) -> bool:
        return "주간보고" in title

    lines.append("\n# 내일계획")
    if tomorrow_items:
        for task in tomorrow_items:
            if is_weekly_meeting(task["title"]):
                continue
            label = f"  - {task['title']}"
            if task["project"]:
                label += f" ({task['project']})"
            lines.append(label)
    else:
        # 오늘 미완료 항목을 내일 계획으로
        pending = [t for t in today_items if t["status"] != "완료" and not is_weekly_meeting(t["title"])]
        if pending:
            for task in pending:
                lines.append(f"  - {task['title']} 이어서 진행")
        else:
            lines.append("  - (없음)")

    lines.append("\n# 특이사항")
    return "\n".join(lines)


if __name__ == "__main__":
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    print(f"노션에서 {today} 데이터를 가져오는 중...")
    today_items = parse_items(query_by_date(today))
    tomorrow_items = parse_items(query_by_date(tomorrow))

    print(f"  오늘 항목: {len(today_items)}개, 내일 항목: {len(tomorrow_items)}개")

    content = build_input(today_items, tomorrow_items)

    out_path = os.path.join(os.path.dirname(__file__), "today_input.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  today_input.txt 저장 완료")
