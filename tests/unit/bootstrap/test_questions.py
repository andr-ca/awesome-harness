"""Unit tests for bootstrap question resolution.

Questions represent required configuration choices that must be answered
before a plan can be applied.  Discovery is always read-only; unresolved
questions block any write.
"""

from __future__ import annotations

import pytest

from agentharness.bootstrap.questions import (
    Answer,
    Question,
    QuestionSet,
    QuestionValidationError,
)


class TestQuestion:
    def test_question_has_required_fields(self) -> None:
        q = Question(
            id="repo.default_branch",
            prompt="What is the repository's default branch?",
            default="main",
        )
        assert q.id == "repo.default_branch"
        assert q.prompt
        assert q.default == "main"

    def test_question_id_must_be_nonempty(self) -> None:
        with pytest.raises(QuestionValidationError, match="id"):
            Question(id="", prompt="Question?", default=None)

    def test_question_prompt_must_be_nonempty(self) -> None:
        with pytest.raises(QuestionValidationError, match="prompt"):
            Question(id="x", prompt="", default=None)


class TestAnswer:
    def test_answer_binds_question_and_value(self) -> None:
        q = Question(id="q1", prompt="Q?", default=None)
        a = Answer(question=q, value="yes")
        assert a.question is q
        assert a.value == "yes"

    def test_answer_can_use_default(self) -> None:
        q = Question(id="q1", prompt="Q?", default="main")
        a = Answer(question=q, value=q.default)
        assert a.value == "main"


class TestQuestionSet:
    def test_all_answered_is_resolved(self) -> None:
        q1 = Question(id="a", prompt="A?", default=None)
        q2 = Question(id="b", prompt="B?", default=None)
        qs = QuestionSet(questions=[q1, q2])
        qs = qs.answer(q1, "yes").answer(q2, "no")
        assert qs.is_resolved

    def test_partial_answers_not_resolved(self) -> None:
        q1 = Question(id="a", prompt="A?", default=None)
        q2 = Question(id="b", prompt="B?", default=None)
        qs = QuestionSet(questions=[q1, q2])
        qs = qs.answer(q1, "yes")
        assert not qs.is_resolved

    def test_empty_question_set_is_resolved(self) -> None:
        qs = QuestionSet(questions=[])
        assert qs.is_resolved

    def test_answering_unknown_question_raises(self) -> None:
        qs = QuestionSet(questions=[])
        unknown = Question(id="z", prompt="Z?", default=None)
        with pytest.raises(KeyError):
            qs.answer(unknown, "val")

    def test_duplicate_question_ids_raise(self) -> None:
        q1 = Question(id="dup", prompt="First?", default=None)
        q2 = Question(id="dup", prompt="Second?", default=None)
        with pytest.raises(QuestionValidationError, match="duplicate"):
            QuestionSet(questions=[q1, q2])

    def test_question_set_is_immutable(self) -> None:
        q = Question(id="q", prompt="Q?", default=None)
        qs = QuestionSet(questions=[q])
        qs2 = qs.answer(q, "v")
        # Original unchanged
        assert not qs.is_resolved
        # New set has the answer
        assert qs2.is_resolved

    def test_unresolved_question_ids(self) -> None:
        q1 = Question(id="a", prompt="A?", default=None)
        q2 = Question(id="b", prompt="B?", default=None)
        qs = QuestionSet(questions=[q1, q2]).answer(q1, "yes")
        assert qs.unresolved_ids == {"b"}
