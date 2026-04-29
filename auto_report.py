"""
업무보고/주간보고 자동 생성 스크립트
사용법:
  python auto_report.py --type daily
  python auto_report.py --type weekly
"""

import argparse
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

WORKDIR    = Path(r"C:\Yuna")
REPORT_DIR = WORKDIR / "업무보고"
CMD_DIR    = WORKDIR / ".claude" / "commands"
CLAUDE     = r"C:\Users\lenovo\AppData\Roaming\npm\claude.cmd"
WEEKDAYS   = ["월", "화", "수", "목", "금", "토", "일"]


def call_claude(prompt: str) -> str:
    result = subprocess.run(
        [CLAUDE, "-p", prompt, "--tools", ""],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(WORKDIR),
    )
    if result.returncode != 0:
        print(f"[ERROR] claude 호출 실패:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def extract_report(text: str, header: str) -> str:
    """Claude 출력에서 보고서 본문만 추출 (마크다운 코드블록·설명 제거)"""
    # 코드블록 안에 있으면 꺼냄
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            stripped = part.strip().lstrip("plaintext").lstrip("text").strip()
            if stripped.startswith(header):
                return stripped
    # 코드블록 없이 헤더로 시작하는 위치 탐색
    idx = text.find(header)
    if idx != -1:
        return text[idx:].strip()
    return text


def run_fetch(script_name: str) -> None:
    print(f"노션 데이터 가져오는 중 ({script_name})...")
    result = subprocess.run(
        [sys.executable, str(REPORT_DIR / script_name)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"[ERROR] {script_name} 실패:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("  완료")


def build_prompt(cmd_file: Path, input_file: Path) -> str:
    instructions = cmd_file.read_text(encoding="utf-8")
    input_text   = input_file.read_text(encoding="utf-8")
    return (
        f"{instructions}\n\n"
        "---\n"
        "노션 데이터 수집과 파일 저장은 외부에서 처리합니다. 당신은 보고서 텍스트만 생성하면 됩니다.\n"
        "규칙:\n"
        "- 보고서 본문만 출력할 것\n"
        "- 파일 저장, 승인 요청, 파싱 결과 설명 등 일절 출력 금지\n"
        "- 보고서 내용 외 어떤 안내문구도 출력 금지\n\n"
        f"[입력 데이터]\n{input_text}"
    )


def run_daily() -> None:
    run_fetch("fetch_notion.py")

    prompt  = build_prompt(CMD_DIR / "업무보고.md", REPORT_DIR / "today_input.txt")
    print("보고서 생성 중...")
    content = extract_report(call_claude(prompt), "일일 업무보고")

    today    = date.today()
    filename = f"{today.isoformat()}_업무보고.txt"
    out_path = REPORT_DIR / filename
    out_path.write_text(content, encoding="utf-8")
    print(f"저장 완료: {out_path}")


def run_weekly() -> None:
    run_fetch("fetch_notion_weekly.py")

    prompt  = build_prompt(CMD_DIR / "주간보고.md", REPORT_DIR / "weekly_input.txt")
    print("주간보고 생성 중...")
    content = extract_report(call_claude(prompt), "주간 업무보고")

    monday   = date.today() - timedelta(days=date.today().weekday())
    filename = f"{monday.isoformat()}_주간보고.txt"
    out_path = REPORT_DIR / filename
    out_path.write_text(content, encoding="utf-8")
    print(f"저장 완료: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["daily", "weekly"], required=True)
    args = parser.parse_args()

    if args.type == "daily":
        run_daily()
    else:
        run_weekly()


if __name__ == "__main__":
    main()
