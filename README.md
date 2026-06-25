# 하네스 틀 (Harness Skeleton) — 실습용

증권사 사내 **바이브 코딩 / 하네스 엔지니어링** 강의의 손으로 채우는 실습 틀입니다.

이 틀의 핵심은 **Python 오케스트레이터** 하나입니다. `scripts/execute.py` 가
`phases/` 의 단계 정의를 읽어 **컨텍스트(프리앰블)** 를 조립하고, 단계별로 코딩 작업을
Claude 에게 굴리며, 실패하면 **에러를 붙여 재시도**하고, 성공하면 커밋합니다.

대상(예제) 프로젝트는 **고객 거래 정산 모듈**입니다. 즉, 하네스가 단계별로
`settlement.py`(정산 로직)와 테스트, 간단한 HTML 리포트를 만들어 가는 모습을 보게 됩니다.

> 이 틀은 공개 저장소(`jha0313/harness_framework`)의 **구조만** 참고해 처음부터 새로 작성한
> 원본입니다. 외부 코드/문구를 복사하지 않았습니다.

---

## 시작하기

```bash
git clone https://github.com/kwangtekNa/harness-practice.git
cd harness-practice
python3 scripts/execute.py --phase mvp --dry-run   # 빈칸 상태라 "실습 1을 구현하세요" 안내가 뜨면 정상
```

Python 3.11+ 만 있으면 시작할 수 있습니다 (`pytest`·`ruff` 는 선택). 이어서 아래 **실습 순서** 대로 빈칸(☐)을 채우세요.

---

## 기호

| 기호 | 의미 |
|---|---|
| ★ | 완성 제공 (골격·보일러플레이트, 손대지 않아도 됨) |
| ☐ | **빈칸 — 실습에서 채우는 부분** (`# TODO 실습:` 또는 `<!-- TODO 실습: -->`) |
| ◆ | 예제 데이터 |

---

## 디렉터리 한눈에 보기

```
하네스실습/
├── README.md                 ★ (이 파일)
├── CLAUDE.md                 ☐ 프로젝트 가드레일 — 하네스의 "헌법"
├── docs/                     공유 컨텍스트 (execute.py 가 프리앰블에 자동 주입)
│   ├── PRD.md                ☐ 무엇을·왜 만드는가
│   ├── ADR.md                ☐ 결정과 이유
│   ├── ARCHITECTURE.md       ☐ 구조·파일 배치
│   ├── UI_GUIDE.md           ☐ 리포트 표현 규칙
│   └── SPEC.md               ★ 정산 규칙 (제공·단일출처·고정)
├── .claude/
│   ├── settings.json         ★ 안전 훅 (Stop·PreToolUse), 훅 1개는 ☐
│   └── commands/harness.md   ★ /harness 슬래시 명령 (컨텍스트→단계설계→execute.py)
├── scripts/
│   ├── execute.py            ★ 엔진 + ☐ 핵심 3곳(프리앰블·에러피드백·커밋규약)
│   └── test_execute.py       ☐ 테스트
├── phases/phase-mvp.json     ◆ 단계 정의 (정산 모듈을 단계로 빌드)
└── data/                     ◆ 체결내역 CSV (입력 데이터)
```

---

## 하네스가 도는 방식 (한 장 요약)

```
phases/phase-mvp.json ──▶ execute.py
                            │  단계마다:
                            │   1) build_preamble()  CLAUDE.md + docs/ + 완료이력 + 직전에러 + 이번지시
                            │   2) Claude 호출 (claude -p ...)
                            │   3) 실패 → 에러 붙여 재시도 (최대 N회)
                            │   4) 성공 → git 커밋  feat(mvp): <단계 제목>
                            ▼
                  settlement.py · tests · report.html (대상 프로젝트 산출물)
```

---

## 실습 순서 (권장 — 위에서 아래로)

| # | 채울 파일 / 빈칸 | 무엇을 배우나 | 검증 |
|---|---|---|---|
| 1 | `docs/PRD.md` | 무엇을·왜 만드는지 먼저 못박기 | 동료가 읽고 범위를 말할 수 있나 |
| 2 | `CLAUDE.md` | 가드레일(모호하면 질문·전체 테스트·근본원인·금액 Decimal) | 규칙이 "행동"으로 적혔나 |
| 3 | `docs/ADR.md`·`ARCHITECTURE.md`·`UI_GUIDE.md` | 결정·구조·표현 규칙 | 서로 모순 없나 |
| 4 | `execute.py` 의 `build_preamble()` | **컨텍스트 계층화 (핵심)** | `--dry-run` 출력 확인 |
| 5 | `execute.py` 의 에러 피드백 한 줄(실습 2) · `commit_message()` | 실패→에러피드백→재시도, 커밋 규약 | `test_execute.py` |
| 6 | `scripts/test_execute.py` | 프리앰블·상태전이·커밋을 테스트로 고정 | 전부 통과 |

> 재시도 **루프 자체는 제공**되어 있고(읽고 이해), 실습은 그 안에서 "직전 에러를 다음 시도에
> 전달하는 한 줄"(실습 2)만 고치면 됩니다.

빈칸을 다 채우면, 실제로 하네스를 돌려 대상 프로젝트를 빌드해 봅니다(아래).

---

## 검증 / 실행 명령

```bash
# 1) 프리앰블만 출력 — Claude 호출 없이 컨텍스트 계층 확인 (실습 4 검증)
python3 scripts/execute.py --phase mvp --dry-run

# 2) 테스트 — 빈칸을 다 채우면 통과 (실습 5~6 검증)
python3 -m pytest -q scripts/test_execute.py

# 3) 실제 빌드 — claude CLI 가 있으면 단계별로 settlement.py 등을 만든다.
#    (대상 프로젝트를 git 으로 관리하려면 먼저  git init  )
python3 scripts/execute.py --phase mvp
```

또는 Claude Code 세션에서 슬래시 명령으로 전체 워크플로를 굴릴 수 있습니다:

```
/harness 고객 거래 정산 모듈 만들기
```

`/harness` 는 `CLAUDE.md`·`docs/` 를 읽고 → 단계를 설계해 `phases/phase-<name>.json` 에 쓰고
→ `scripts/execute.py` 로 드라이런·실행까지 안내합니다. (`.claude/commands/harness.md`)

---

## 막히면

- 빈칸은 모두 `☐`(`# TODO 실습:` 또는 `<!-- TODO 실습: -->`)로 표시돼 있습니다.
- `--dry-run` 출력으로 프리앰블이 **가드레일 → docs → 완료이력 → 직전에러 → 이번지시** 순으로 쌓였는지 눈으로 확인하세요.
- 이 실습의 핵심은 "정답"이 아니라 **컨텍스트를 어떻게 쌓는가**입니다. 더 모르겠으면 강사에게 질문하세요.
