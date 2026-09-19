"""
Decision Types and Typed Primitives for MinusCorrect.
Defines Choice, Score, and Noul (probabilistic boolean) decision schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union


@dataclass
class Choice:
    """
    Closed-set categorical selection prompt primitive.
    """
    instructions: str
    criteria: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "choice",
            "instructions": self.instructions,
            "criteria": dict(self.criteria),
        }


@dataclass
class ChoiceResult:
    """
    Result of a Choice evaluation.
    """
    choice: str
    distribution: Dict[str, float]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "choice": self.choice,
            "distribution": self.distribution,
            "confidence": self.confidence,
        }


@dataclass
class Score:
    """
    Rubric-based or bounded scalar evaluation primitive.
    """
    instructions: str
    criteria: Optional[Dict[str, str]] = None
    min_val: float = 0.0
    max_val: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "score",
            "instructions": self.instructions,
            "criteria": dict(self.criteria) if self.criteria else None,
            "min_val": self.min_val,
            "max_val": self.max_val,
        }


@dataclass
class ScoreResult:
    """
    Result of a Score evaluation.
    """
    score: float
    confidence: float
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


@dataclass
class Noul:
    """
    Calibrated probabilistic truth assessment primitive (0.0 <= probability <= 1.0).
    Distinct from strict boolean by carrying epistemic uncertainty.
    """
    instructions: str
    threshold: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "noul",
            "instructions": self.instructions,
            "threshold": self.threshold,
        }


@dataclass
class NoulResult:
    """
    Result of a Noul probabilistic evaluation.
    """
    probability: float
    passed: bool
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probability": self.probability,
            "passed": self.passed,
            "confidence": self.confidence,
        }


QuestionPrimitive = Union[Choice, Score, Noul]
QuestionResult = Union[ChoiceResult, ScoreResult, NoulResult]


@dataclass
class DecisionBatch:
    """
    Batch of questions evaluated against a single program or council state.
    """
    state: str
    questions: Dict[str, QuestionPrimitive]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "questions": {k: v.to_dict() for k, v in self.questions.items()},
        }


@dataclass
class DecisionResponse:
    """
    Aggregated response from a decision engine provider.
    """
    answers: Dict[str, QuestionResult]
    latency_ms: float
    provider: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answers": {k: v.to_dict() for k, v in self.answers.items()},
            "latency_ms": self.latency_ms,
            "provider": self.provider,
        }
