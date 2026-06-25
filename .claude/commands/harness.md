---
description: 하네스 워크플로 실행 — 컨텍스트를 읽고 단계를 설계해 phases/ 에 쓰고 execute.py 로 굴린다
argument-hint: "[작업 설명] (예: 고객 거래 정산 모듈 만들기)"
allowed-tools: Read, Write, Edit, Bash, Glob
---

# /harness — 하네스 오케스트레이션 실행

요청한 작업: **$ARGUMENTS**

아래 순서를 그대로 따른다. 각 단계는 사용자의 확인을 받고 다음으로 넘어간다.

## A. 컨텍스트 흡수 (먼저 읽기)
- `CLAUDE.md` 의 가드레일(특히 "절대 ~하지 않는다" 류)을 읽는다.
- `docs/` 의 `PRD.md`·`ADR.md`·`ARCHITECTURE.md`·`UI_GUIDE.md` 를 알파벳 순으로 읽어 설계 맥락을 파악한다.
- `docs/SPEC.md` 등 도메인 단일 출처를 확인한다.
- 모호한 가정이 있으면 **추측하지 말고 사용자에게 먼저 질문**한다(가드레일).

## B. 단계 설계 (작게 쪼개기)
- 작업을 **순서 의존이 분명한 작은 step** 으로 나눈다(한 step = 한 가지 책임).
- 구현을 위해 구체화해야하거나 결정할 사항들을 사용자에게 논의를 요청하고, 암묵지를 인터뷰한다. 
- 각 step 에 다음을 적는다: `id`, `title`, `prompt`(시그니처/수용 기준 수준의 구체 지시), `status: "pending"`.
- 설계안을 사용자에게 보여주고 피드백을 받는다.

## C. 단계 정의 파일 생성
- 합의된 설계를 `phases/phase-<name>.json` 으로 쓴다. 스키마는 기존 `phases/phase-mvp.json` 을 따른다
  (`phase`, `commit_scope`, `stop_on_block`, `steps[]`).

## D. 드라이런으로 컨텍스트 점검
```bash
python3 scripts/execute.py --phase <name> --dry-run
```
- 출력 프리앰블이 **가드레일 → docs → 완료이력 → 직전에러 → 이번지시** 순으로 계층화됐는지 눈으로 확인한다.

## E. 실제 실행
```bash
# (선택) 대상 프로젝트를 git 으로 관리하려면 먼저:  git init
python3 scripts/execute.py --phase <name>
```
- `execute.py` 가 step 별로 Claude 를 호출하고, 실패하면 직전 에러를 붙여 **최대 3회 재시도**한 뒤
  성공 시 `feat(<scope>): <step 제목>` 으로 커밋한다.
- 결과 상태는 `phase-<name>-output.json` 에 기록된다.

## F. 마무리
- `blocked` 단계가 있으면 사유를 사람에게 보고하고, 해결 후 해당 step 의 `status` 를 `pending` 으로
  되돌려 재실행한다. 전체 step 이 `completed` 면 산출물 경로와 요약을 보고한다.
