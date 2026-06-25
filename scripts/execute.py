#!/usr/bin/env python3
"""
하네스 오케스트레이터 (Track A).

phases/phase-<name>.json 에 정의된 단계(step)를 순서대로 실행한다.
각 단계마다:
  1) 컨텍스트(프리앰블)를 조립하고            <- build_preamble()  [☐ 실습]
  2) Claude 를 헤드리스로 호출해 코딩을 시키고  <- invoke_claude()   [★ 제공]
  3) 실패하면 직전 에러를 붙여 재시도하고       <- execute_step()    [☐ 실습]
  4) 성공하면 (git repo 면) 커밋한다.          <- commit_message()  [☐ 실습]

사용:
  python3 scripts/execute.py --phase mvp --dry-run     # Claude 호출 없이 프리앰블만 출력
  python3 scripts/execute.py --phase mvp                # 실제 실행 (claude CLI 필요)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# 저장소 루트 = 이 파일의 부모의 부모
ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
PHASES_DIR = ROOT / "phases"
CLAUDE_MD = ROOT / "CLAUDE.md"
DEFAULT_MAX_RETRIES = 3


# ──────────────────────────────────────────────────────────────────────────────
# ★ 제공: 작은 도우미들
# ──────────────────────────────────────────────────────────────────────────────
def read_text(path: Path) -> str:
    """파일을 읽되 없으면 빈 문자열."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def list_docs() -> list[Path]:
    """docs/ 의 .md 를 '알파벳 정렬' 로 반환 — 로딩 순서를 결정적으로 고정한다."""
    if not DOCS_DIR.exists():
        return []
    return sorted(DOCS_DIR.glob("*.md"), key=lambda p: p.name)


def load_phase(name: str) -> dict:
    """phases/phase-<name>.json 로드."""
    path = PHASES_DIR / f"phase-{name}.json"
    if not path.exists():
        sys.exit(f"[오류] 단계 정의가 없습니다: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_outputs(name: str, phase: dict) -> None:
    """진행 상태를 phase-<name>-output.json 으로 저장(.gitignore 됨)."""
    out = ROOT / f"phase-{name}-output.json"
    out.write_text(json.dumps(phase, ensure_ascii=False, indent=2), encoding="utf-8")


def git_available() -> bool:
    """현재 폴더가 git 저장소이고 git 이 설치돼 있으면 True."""
    if shutil.which("git") is None:
        return False
    r = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return r.returncode == 0 and r.stdout.strip() == "true"


def git_commit(message: str) -> bool:
    """변경분을 스테이징 후 커밋. git repo 가 아니면 조용히 건너뛴다."""
    if not git_available():
        print("  · git 저장소가 아니라 커밋을 건너뜁니다.")
        return False
    subprocess.run(["git", "add", "-A"], cwd=ROOT, capture_output=True, text=True)
    r = subprocess.run(["git", "commit", "-m", message], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  · 커밋할 변경이 없거나 실패: {r.stdout.strip() or r.stderr.strip()}")
        return False
    print(f"  · 커밋: {message}")
    return True


def invoke_claude(prompt: str, dry_run: bool) -> dict:
    """
    Claude 를 헤드리스로 호출한다. 반환 계약: {"ok": bool, "summary": str, "error": str}

    --dry-run 이면 호출하지 않고 프리앰블만 출력한 뒤 성공으로 간주한다(컨텍스트 확인용).
    """
    if dry_run:
        print("\n" + "═" * 70)
        print("DRY-RUN 프리앰블 (실제 Claude 호출 없음)")
        print("═" * 70)
        print(prompt)
        print("═" * 70 + "\n")
        return {"ok": True, "summary": "(dry-run)", "error": ""}

    if shutil.which("claude") is None:
        return {"ok": False, "summary": "", "error": "claude CLI 를 찾을 수 없습니다(--dry-run 으로 연습하세요)."}

    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return {"ok": False, "summary": "", "error": proc.stderr.strip() or "claude 비정상 종료"}
    try:
        data = json.loads(proc.stdout)
        text = data.get("result", "") if isinstance(data, dict) else str(data)
        return {"ok": True, "summary": text[:280], "error": ""}
    except json.JSONDecodeError:
        # JSON 이 아니어도 출력이 있으면 성공으로 본다.
        return {"ok": True, "summary": proc.stdout.strip()[:280], "error": ""}


# ──────────────────────────────────────────────────────────────────────────────
# ☐ 실습 1 — 컨텍스트 계층화 (이 함수가 하네스 엔지니어링의 핵심)
# ──────────────────────────────────────────────────────────────────────────────
def build_preamble(phase: dict, step: dict, previous_error: str = "") -> str:
    """
    한 단계(step)를 실행하기 직전에 Claude 에게 줄 '프리앰블'을 조립한다.

    좋은 프리앰블은 다음을 '순서대로' 계층화한다:
      (1) 가드레일      — CLAUDE.md 전문
      (2) 설계 컨텍스트 — list_docs() 의 문서들을 알파벳 순서로
      (3) 진행 맥락     — 이미 completed 된 step 들의 title/summary (무엇이 끝났는지)
      (4) 직전 에러     — previous_error 가 있으면, "같은 실수를 반복하지 말 것" 과 함께
      (5) 이번 지시     — step["prompt"]

    왜 순서가 중요한가: 규칙 → 구조 → 한 일 → 고칠 것 → 할 일 순으로 줘야
    모델이 "맥락 위에서" 결정한다. 순서가 섞이면 가드레일이 묻힌다.

    return: Claude 에게 보낼 하나의 문자열 프리앰블.
    """
    # TODO 실습: 위 (1)~(5) 를 읽기 좋은 문자열로 합쳐서 return 하세요.
    #   힌트: read_text(CLAUDE_MD), list_docs(), [s for s in phase["steps"] if s["status"]=="completed"]
    #   힌트: previous_error 가 비어있지 않을 때만 (4) 를 넣으세요.
    raise NotImplementedError(
        "실습 1: build_preamble() 를 구현하세요. "
        "README 의 '실습 순서' 4번을 참고하고, 완성 후 --dry-run 으로 계층을 확인하세요."
    )


# ──────────────────────────────────────────────────────────────────────────────
# ☐ 실습 3 — 커밋 메시지 규약
# ──────────────────────────────────────────────────────────────────────────────
def commit_message(phase: dict, step: dict) -> str:
    """
    성공한 단계를 커밋할 때 쓸 메시지를 만든다.

    규약(권장): "feat(<scope>): <step 제목>"
      - <scope>  : phase.get("commit_scope") (예: "mvp")
      - <step 제목>: step["title"]
    """
    # TODO 실습: 위 규약대로 한 줄 메시지를 만들어 return 하세요.
    raise NotImplementedError("실습 3: commit_message() 를 구현하세요.")


# ──────────────────────────────────────────────────────────────────────────────
# ☐ 실습 2 — 재시도 / 에러 피드백 루프 (일부 빈칸)
# ──────────────────────────────────────────────────────────────────────────────
def execute_step(phase: dict, step: dict, dry_run: bool, max_retries: int) -> bool:
    """
    한 단계를 최대 max_retries 회까지 시도한다.
    실패하면 그 에러를 다음 시도의 프리앰블에 넣어(누적) 모델이 교정하도록 한다.

    상태 전이: pending → in_progress → completed | blocked
    return: 성공(True) / 막힘(False)
    """
    print(f"\n▶ {step['id']} — {step['title']}")
    step["status"] = "in_progress"
    previous_error = ""  # 직전 시도의 에러 — 다음 프리앰블에 실어 같은 실수를 피하게 한다

    for attempt in range(1, max_retries + 1):
        # ★ 제공: 프리앰블을 조립해 Claude 를 호출한다. (build_preamble 를 채우면 여기서 동작)
        preamble = build_preamble(phase, step, previous_error)
        result = invoke_claude(preamble, dry_run)

        if result["ok"]:
            step["status"] = "completed"
            step["summary"] = result["summary"]
            print(f"  ✓ 성공 (시도 {attempt}/{max_retries})")
            if not dry_run:
                git_commit(commit_message(phase, step))  # commit_message() ☐ 실습 3
            return True

        # 실패 → 재시도. 핵심: 이 에러를 '다음 시도'가 보게 만들어야 같은 실수를 피한다.
        print(f"  ✗ 실패 (시도 {attempt}/{max_retries}): {result['error'][:120]}")
        # TODO 실습 2: 아래 한 줄을 고치세요 — 다음 루프의 build_preamble 에 에러가 실리도록.
        #   비워두면(=""): previous_error 가 빈 채라 '같은 프리앰블'로 재시도 → 같은 실패 반복.
        previous_error = ""  # ← result["error"] 로 바꾸세요

    step["status"] = "blocked"
    print(f"  ⛔ {max_retries}회 시도 후 막힘 → blocked")
    return False


def run(phase_name: str, dry_run: bool, max_retries: int) -> int:
    phase = load_phase(phase_name)
    print(f"=== 하네스 실행: phase '{phase_name}' (단계 {len(phase['steps'])}개) ===")

    blocked = 0
    for step in phase["steps"]:
        if step.get("status") == "completed":
            print(f"\n▷ {step['id']} — 이미 완료, 건너뜀")
            continue
        ok = execute_step(phase, step, dry_run, max_retries)
        save_outputs(phase_name, phase)
        if not ok:
            blocked += 1
            if phase.get("stop_on_block", True):
                print("\n중단: 막힌 단계가 있어 이후 단계를 멈춥니다(--no-stop 으로 계속 가능).")
                break

    done = sum(1 for s in phase["steps"] if s["status"] == "completed")
    print(f"\n=== 완료: {done}/{len(phase['steps'])} 성공, 막힘 {blocked} ===")
    return 1 if blocked else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="하네스 오케스트레이터 (Track A)")
    ap.add_argument("--phase", default="mvp", help="실행할 단계 이름 (phases/phase-<name>.json)")
    ap.add_argument("--dry-run", action="store_true", help="Claude 호출 없이 프리앰블만 출력")
    ap.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    ap.add_argument("--no-stop", dest="stop", action="store_false", help="막혀도 다음 단계 계속")
    args = ap.parse_args()

    try:
        phase_path = PHASES_DIR / f"phase-{args.phase}.json"
        if args.stop is False and phase_path.exists():
            pass  # stop 플래그는 phase JSON 의 stop_on_block 보다 우선하지 않음(단순화)
        return run(args.phase, args.dry_run, args.max_retries)
    except NotImplementedError as e:
        print(f"\n[실습 미완성] {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
