#!/usr/bin/env python3
"""
execute.py 테스트 (Track A).

빈칸(build_preamble / commit_message / execute_step)을 채우면 모든 테스트가 통과한다.
실행: python3 -m pytest -q scripts/test_execute.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import execute  # noqa: E402


def _sample_phase() -> dict:
    return {
        "phase": "mvp",
        "commit_scope": "mvp",
        "steps": [
            {"id": "step-1", "title": "정산 함수 시그니처", "prompt": "calc_settlement 시그니처를 만든다",
             "status": "completed", "summary": "calc_settlement(amount, side) 추가"},
            {"id": "step-2", "title": "수수료·세금 규칙", "prompt": "수수료와 세금을 반영한다",
             "status": "pending", "summary": ""},
        ],
    }


class TestDocsLoading(unittest.TestCase):
    """★ 제공: docs 로딩은 '알파벳 정렬' 이어야 결정적이다."""

    def test_docs_sorted(self):
        docs = execute.list_docs()
        names = [p.name for p in docs]
        self.assertEqual(names, sorted(names), "docs/ 는 알파벳 순서로 로드되어야 한다")


class TestBuildPreamble(unittest.TestCase):
    """☐ 실습 1: build_preamble 검증."""

    def setUp(self):
        self.phase = _sample_phase()
        self.step = self.phase["steps"][1]

    def test_includes_guardrails_and_instruction(self):
        pre = execute.build_preamble(self.phase, self.step)
        # TODO 실습: 프리앰블이 (1) CLAUDE.md 의 내용과 (5) 이번 step 지시를 포함하는지 단언하세요.
        #   예) self.assertIn("가드레일", pre)  /  self.assertIn(self.step["prompt"], pre)
        self.fail("실습: test_includes_guardrails_and_instruction 의 단언을 채우세요.")

    def test_includes_completed_step_history(self):
        pre = execute.build_preamble(self.phase, self.step)
        # TODO 실습: 이미 completed 된 step-1 의 흔적(제목 또는 요약)이 들어있는지 단언하세요.
        self.fail("실습: 완료 단계 이력이 프리앰블에 포함되는지 단언하세요.")

    def test_previous_error_appended_only_when_present(self):
        without = execute.build_preamble(self.phase, self.step, previous_error="")
        with_err = execute.build_preamble(self.phase, self.step, previous_error="ZeroDivisionError 발생")
        # TODO 실습: 에러가 있을 때만 프리앰블에 그 에러가 포함되는지 단언하세요.
        self.fail("실습: previous_error 분기 동작을 단언하세요.")


class TestCommitMessage(unittest.TestCase):
    """☐ 실습 3: commit_message 규약."""

    def test_format(self):
        phase = _sample_phase()
        msg = execute.commit_message(phase, phase["steps"][1])
        # TODO 실습: "feat(mvp): 수수료·세금 규칙" 형태인지 단언하세요.
        self.fail("실습: commit_message 형식을 단언하세요.")


class TestStateMachine(unittest.TestCase):
    """☐ 실습 2: 상태 전이 — dry-run 으로 실제 호출 없이 검증."""

    def test_pending_to_completed_on_success(self):
        phase = _sample_phase()
        step = phase["steps"][1]
        ok = execute.execute_step(phase, step, dry_run=True, max_retries=3)
        # TODO 실습: dry-run 은 항상 성공하므로 ok 가 True 이고 step["status"] 가 "completed" 인지 단언하세요.
        self.fail("실습: 성공 시 상태 전이를 단언하세요.")


if __name__ == "__main__":
    unittest.main()
