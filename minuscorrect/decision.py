"""
MinusCorrect Decision Engine Protocol and Providers.
Implements the Middle-Ring decision service supporting LocalRuleEngine (zero-dependency default),
JevProvider (TypeSafe AI System One with automatic fallback), and MockDecisionEngine.
"""

from __future__ import annotations

import abc
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from minuscorrect.types.decision import (
    Choice,
    ChoiceResult,
    DecisionBatch,
    DecisionResponse,
    Noul,
    NoulResult,
    QuestionPrimitive,
    QuestionResult,
    Score,
    ScoreResult,
)


class DecisionEngine(abc.ABC):
    """
    Abstract contract for fast System-1 typed decision services.
    """

    @abc.abstractmethod
    def evaluate(self, batch: DecisionBatch) -> DecisionResponse:
        """
        Evaluate a batch of typed questions against a program state.
        """
        pass


class LocalRuleEngine(DecisionEngine):
    """
    Zero-dependency, deterministic local decision engine.
    Performs fast heuristic scoring and classification with zero external API calls.
    """

    def evaluate(self, batch: DecisionBatch) -> DecisionResponse:
        start_time = time.perf_counter()
        state_lower = batch.state.lower()
        answers: Dict[str, QuestionResult] = {}

        for q_id, question in batch.questions.items():
            if isinstance(question, Choice):
                answers[q_id] = self._evaluate_choice(state_lower, question)
            elif isinstance(question, Score):
                answers[q_id] = self._evaluate_score(state_lower, question)
            elif isinstance(question, Noul):
                answers[q_id] = self._evaluate_noul(state_lower, question)
            else:
                raise TypeError(f"Unsupported question primitive type: {type(question)}")

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return DecisionResponse(
            answers=answers,
            latency_ms=round(latency_ms, 2),
            provider="local-rules",
        )

    def _evaluate_choice(self, state_lower: str, choice_q: Choice) -> ChoiceResult:
        counts: Dict[str, float] = {}
        for opt_key, opt_desc in choice_q.criteria.items():
            score = 0.0
            # Direct key match
            if opt_key.lower() in state_lower:
                score += 3.0
            # Token matches from description
            tokens = [w for w in re.split(r"\W+", opt_desc.lower()) if len(w) > 3]
            for token in tokens:
                if token in state_lower:
                    score += 1.0
            counts[opt_key] = max(0.1, score)

        total = sum(counts.values())
        distribution = {k: round(v / total, 4) for k, v in counts.items()}
        chosen = max(counts.keys(), key=lambda k: counts[k])
        confidence = distribution[chosen]

        return ChoiceResult(
            choice=chosen,
            distribution=distribution,
            confidence=confidence,
        )

    def _evaluate_score(self, state_lower: str, score_q: Score) -> ScoreResult:
        # Evaluate against rubrics or heuristic keyword density
        positive_tokens = {"pass", "safe", "verified", "clean", "contained", "agree", "consensus", "high", "success"}
        negative_tokens = {"fail", "breach", "unsafe", "leak", "fatal", "disagree", "clash", "regression", "error"}

        pos_count = sum(1 for w in positive_tokens if w in state_lower)
        neg_count = sum(1 for w in negative_tokens if w in state_lower)

        ratio = 0.5
        total_signals = pos_count + neg_count
        if total_signals > 0:
            ratio = pos_count / total_signals

        raw_score = score_q.min_val + ratio * (score_q.max_val - score_q.min_val)
        score = round(raw_score, 2)
        confidence = round(min(1.0, 0.5 + 0.1 * total_signals), 2)

        return ScoreResult(
            score=score,
            confidence=confidence,
            explanation=f"Signal count: {pos_count} positive, {neg_count} negative",
        )

    def _evaluate_noul(self, state_lower: str, noul_q: Noul) -> NoulResult:
        # Check instruction alignment in state
        instr_tokens = [w for w in re.split(r"\W+", noul_q.instructions.lower()) if len(w) > 3]
        matches = sum(1 for token in instr_tokens if token in state_lower)

        # Baseline probability with signal reinforcement
        if not instr_tokens:
            prob = 0.5
        else:
            fraction = matches / len(instr_tokens)
            prob = round(min(0.99, max(0.01, 0.2 + 0.7 * fraction)), 3)

        passed = prob >= noul_q.threshold
        confidence = round(abs(prob - 0.5) * 2.0, 3)

        return NoulResult(
            probability=prob,
            passed=passed,
            confidence=confidence,
        )


class JevProvider(DecisionEngine):
    """
    TypeSafe AI System One decision service provider.
    Enforces a strict 2.0-second timeout and silently falls back to LocalRuleEngine
    upon missing credentials, timeouts, or network interruptions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: str = "https://api.typesafe.ai/v1/systemone",
        timeout: float = 2.0,
        fallback_engine: Optional[DecisionEngine] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        self.endpoint = endpoint
        self.timeout = timeout
        self.fallback = fallback_engine or LocalRuleEngine()

    def evaluate(self, batch: DecisionBatch) -> DecisionResponse:
        if not self.api_key:
            return self.fallback.evaluate(batch)

        start_time = time.perf_counter()
        req_payload = {
            "model": "jev-latest",
            "state": batch.state,
            "questions": {q_id: q.to_dict() for q_id, q in batch.questions.items()},
        }

        data_bytes = json.dumps(req_payload).encode("utf-8")
        req = urllib.request.Request(
            url=self.endpoint,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "MinusCorrect/1.0.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                body = response.read().decode("utf-8")
                parsed = json.loads(body)

                answers: Dict[str, QuestionResult] = {}
                raw_answers = parsed.get("answers", {})

                for q_id, raw_ans in raw_answers.items():
                    orig_q = batch.questions.get(q_id)
                    if isinstance(orig_q, Choice):
                        answers[q_id] = ChoiceResult(
                            choice=raw_ans.get("choice", ""),
                            distribution=raw_ans.get("distribution", {}),
                            confidence=raw_ans.get("confidence", 0.0),
                        )
                    elif isinstance(orig_q, Score):
                        answers[q_id] = ScoreResult(
                            score=raw_ans.get("score", 0.0),
                            confidence=raw_ans.get("confidence", 0.0),
                            explanation=raw_ans.get("explanation", ""),
                        )
                    elif isinstance(orig_q, Noul):
                        prob = raw_ans.get("noul", raw_ans.get("probability", 0.0))
                        answers[q_id] = NoulResult(
                            probability=prob,
                            passed=prob >= orig_q.threshold,
                            confidence=raw_ans.get("confidence", 0.0),
                        )

                return DecisionResponse(
                    answers=answers,
                    latency_ms=round(latency_ms, 2),
                    provider="jev-systemone",
                )

        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            # Safe non-blocking fallback to local rule engine
            print(f"[WARN] JevProvider request failed ({exc}); falling back to LocalRuleEngine.", file=sys.stderr)
            return self.fallback.evaluate(batch)


class MockDecisionEngine(DecisionEngine):
    """
    Hermetic mock engine for unit testing and deterministic offline verification.
    """

    def __init__(self, canned_response: Optional[DecisionResponse] = None) -> None:
        self.canned_response = canned_response
        self.recorded_batches: list[DecisionBatch] = []

    def evaluate(self, batch: DecisionBatch) -> DecisionResponse:
        self.recorded_batches.append(batch)
        if self.canned_response:
            return self.canned_response
        # Fallback to local evaluation
        return LocalRuleEngine().evaluate(batch)


def get_decision_engine(name: str = "auto") -> DecisionEngine:
    """
    Factory resolving the active Middle-Ring decision engine.
    # verifies: tests/unit/test_decision.py
    """
    mode = name.lower()
    if mode == "local":
        return LocalRuleEngine()
    if mode == "jev":
        return JevProvider()
    if mode == "mock":
        return MockDecisionEngine()

    # 'auto': Use Jev if TYPESAFE_API_KEY is present, otherwise LocalRuleEngine
    if os.environ.get("TYPESAFE_API_KEY"):
        return JevProvider()
    return LocalRuleEngine()
