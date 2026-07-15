"""Bootstrap questions — required configuration choices for a plan.

Questions are pure data; QuestionSet is an immutable value object.
Discovery reads questions; unresolved questions block any write operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class QuestionValidationError(ValueError):
    """Raised when a Question or QuestionSet is structurally invalid."""


@dataclass(frozen=True)
class Question:
    """A single required configuration choice.

    id:      stable dot-separated identifier (e.g. "repo.default_branch")
    prompt:  human-readable question text shown to the operator
    default: suggested value, or None if no sensible default exists
    """

    id: str
    prompt: str
    default: str | None

    def __post_init__(self) -> None:
        if not self.id:
            raise QuestionValidationError("Question id must not be empty")
        if not self.prompt:
            raise QuestionValidationError("Question prompt must not be empty")


@dataclass(frozen=True)
class Answer:
    """A confirmed answer binding a Question to a concrete value."""

    question: Question
    value: str | None


@dataclass(frozen=True)
class QuestionSet:
    """An immutable ordered set of questions with optional answers.

    Mutating methods return new QuestionSet instances; the original is
    never changed.
    """

    questions: list[Question]
    _answers: dict[str, Answer] = field(
        default_factory=dict, compare=False, repr=False, hash=False
    )

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for q in self.questions:
            if q.id in seen:
                raise QuestionValidationError(
                    f"duplicate question id {q.id!r}"
                )
            seen.add(q.id)

    def answer(self, question: Question, value: str | None) -> "QuestionSet":
        """Return a new QuestionSet with the given question answered."""
        if question.id not in {q.id for q in self.questions}:
            raise KeyError(question.id)
        updated = dict(self._answers)
        updated[question.id] = Answer(question=question, value=value)
        return QuestionSet(questions=self.questions, _answers=updated)

    @property
    def is_resolved(self) -> bool:
        """True when every question has a recorded answer."""
        return all(q.id in self._answers for q in self.questions)

    @property
    def unresolved_ids(self) -> set[str]:
        """Set of question IDs that have not yet been answered."""
        answered = set(self._answers)
        return {q.id for q in self.questions} - answered
