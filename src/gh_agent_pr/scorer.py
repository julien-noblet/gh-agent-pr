import logging
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

MERGE_CHOICE_CRITERIA = {
    "merge_ready": (
        "Safe to merge: CI tests are passing/green, well-scoped change, routine automated bot update or minor configuration change, tests included or not required, no breaking changes."
    ),
    "needs_review": (
        "Requires human review: Non-trivial business logic, refactoring, sensitive architecture, breaking changes, or code needing unit tests."
    ),
    "blocked": (
        "Blocked / High risk: Failing CI tests, merge conflicts, dangerous modifications, or broken builds."
    ),
}

DEFAULT_QUESTIONS = {
    "merge_risk": {
        "type": "choice",
        "instructions": "Evaluate the risk and confidence of merging this Pull Request into the main branch.",
        "criteria": MERGE_CHOICE_CRITERIA,
    }
}


def compute_calibrated_confidence(
    choice: str,
    probabilities: Dict[str, float],
    answer_confidence: Optional[float] = None
) -> float:
    """Calibrate zero-shot probability distribution into intuitive confidence (0.0 to 1.0).
    
    Laya's 3-way choice softmax operates in effective zero-shot range [0.33, 0.68].
    An answer with P=0.65 and margin 0.35 over the runner-up represents
    dominant certainty in zero-shot classification (~90%+).
    """
    if not probabilities:
        return float(answer_confidence or 0.5)

    p_top = probabilities.get(choice, 0.33)
    other_probs = [v for k, v in probabilities.items() if k != choice]
    p_runner_up = max(other_probs) if other_probs else 0.0

    margin = max(0.0, p_top - p_runner_up)
    p_norm = max(0.0, min(1.0, (p_top - 0.33) / (0.68 - 0.33)))
    margin_norm = max(0.0, min(1.0, margin * 2.5))

    calibrated = 0.50 + 0.50 * (0.60 * p_norm + 0.40 * margin_norm)
    return round(max(0.10, min(0.99, calibrated)), 4)


@dataclass
class ScoringResult:
    decision: str  # merge_ready, needs_review, blocked
    confidence: float  # calibrated confidence 0.0 to 1.0
    probabilities: Dict[str, float]
    model_used: str
    rationale: str = ""


def check_guardrail(
    context: str = "",
    ci_status: Optional[str] = None,
    mergeable: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> Optional[ScoringResult]:
    """Enforce hard safety guardrail for failing CI or merge conflicts."""
    is_ci_failed = False
    if ci_status:
        upper = ci_status.upper()
        if any(w in upper for w in ("FAILED", "CANCELLED", "ACTION_REQUIRED", "TIMED_OUT")):
            is_ci_failed = True
    elif "CI Status: FAILED" in context or "CI Status: CANCELLED" in context:
        is_ci_failed = True

    is_conflicted = False
    if mergeable and mergeable.upper() == "CONFLICTING":
        is_conflicted = True
    elif "Mergeable: CONFLICTING" in context:
        is_conflicted = True

    if not is_ci_failed and not is_conflicted:
        return None

    # Determine rationale
    if failure_reason:
        rationale = failure_reason
    elif is_ci_failed:
        diag_match = re.search(r"CI Failure Diagnostics:\s*\n?([^\n]+)", context)
        if diag_match and diag_match.group(1).strip():
            rationale = diag_match.group(1).strip()
        else:
            rationale = "CI checks failed"
    else:
        rationale = "Git merge conflicts detected"

    return ScoringResult(
        decision="blocked",
        confidence=0.99,
        probabilities={"merge_ready": 0.0, "needs_review": 0.01, "blocked": 0.99},
        model_used="guardrail",
        rationale=rationale,
    )


class LayaScorer:
    def __init__(self, router: Optional[Any] = None, default_model: str = "english"):
        self.default_model = default_model
        if router is not None:
            self._router = router
        else:
            from laya import Router
            self._router = Router()

    def score_context(
        self,
        context: str,
        model: Optional[str] = None,
        ci_status: Optional[str] = None,
        mergeable: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> ScoringResult:
        """Run Laya System-1 prediction over the distilled PR context, applying safety guardrails."""
        guardrail_result = check_guardrail(
            context=context,
            ci_status=ci_status,
            mergeable=mergeable,
            failure_reason=failure_reason,
        )
        if guardrail_result is not None:
            return guardrail_result

        selected_model = model or self.default_model
        try:
            result = self._router.predict(
                state=context,
                questions=DEFAULT_QUESTIONS,
                model=selected_model,
            )
        except Exception as e:
            logger.error("Error running Laya predict: %s", e)
            return ScoringResult(
                decision="needs_review",
                confidence=0.5,
                probabilities={"merge_ready": 0.2, "needs_review": 0.6, "blocked": 0.2},
                model_used=selected_model,
                rationale=f"Inference error: {str(e)}"
            )

        answers = result.get("answers", {})
        merge_eval = answers.get("merge_risk", {})
        chosen = merge_eval.get("choice", "needs_review")
        
        probs = merge_eval.get("probabilities", {})
        answer_conf = merge_eval.get("answer_confidence")
        
        # Calculate calibrated confidence
        clean_probs = {k: float(v) for k, v in probs.items()} if probs else {}
        calibrated_conf = compute_calibrated_confidence(
            choice=chosen,
            probabilities=clean_probs,
            answer_confidence=float(answer_conf) if answer_conf is not None else None,
        )

        routing_info = result.get("routing", {})
        model_used = routing_info.get("model", selected_model)

        return ScoringResult(
            decision=chosen,
            confidence=calibrated_conf,
            probabilities=clean_probs,
            model_used=model_used,
        )

    def score_pr(
        self,
        summary_or_context: Any,
        model: Optional[str] = None,
        ci_status: Optional[str] = None,
        mergeable: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> ScoringResult:
        """Score a PR from a PRSummary dataclass or context string."""
        if hasattr(summary_or_context, "context"):
            return self.score_context(
                context=summary_or_context.context,
                model=model,
                ci_status=getattr(summary_or_context, "ci_status", None),
                mergeable=getattr(summary_or_context, "mergeable", None),
                failure_reason=getattr(summary_or_context, "ci_failure_reason", None),
            )
        return self.score_context(
            context=str(summary_or_context),
            model=model,
            ci_status=ci_status,
            mergeable=mergeable,
            failure_reason=failure_reason,
        )
