from gh_agent_pr.scorer import (
    LayaScorer,
    ScoringResult,
    compute_calibrated_confidence,
    DEFAULT_QUESTIONS,
)


def test_compute_calibrated_confidence():
    # Dominant winner (~65% in 3-choice) should calibrate to >= 90%
    probs_dominant = {"merge_ready": 0.65, "needs_review": 0.25, "blocked": 0.10}
    conf_dom = compute_calibrated_confidence("merge_ready", probs_dominant)
    assert conf_dom >= 0.90

    # Narrow margin should remain moderate (~50-65%)
    probs_narrow = {"merge_ready": 0.38, "needs_review": 0.35, "blocked": 0.27}
    conf_narrow = compute_calibrated_confidence("merge_ready", probs_narrow)
    assert 0.50 <= conf_narrow <= 0.65

    # Empty probabilities fallback
    assert compute_calibrated_confidence("merge_ready", {}, answer_confidence=0.7) == 0.7


class MockRouter:
    def __init__(self, choice="merge_ready", probabilities=None, answer_confidence=0.65):
        self.choice = choice
        self.probabilities = probabilities or {
            "merge_ready": 0.65,
            "needs_review": 0.25,
            "blocked": 0.10
        }
        self.answer_confidence = answer_confidence
        self.last_state = None
        self.last_questions = None

    def predict(self, state, questions, model="english"):
        self.last_state = state
        self.last_questions = questions
        return {
            "answers": {
                "merge_risk": {
                    "choice": self.choice,
                    "confidence": 0.27,  # Shannon entropy
                    "answer_confidence": self.answer_confidence,
                    "probabilities": self.probabilities
                }
            },
            "routing": {"model": model}
        }


def test_scorer_merge_ready():
    mock_router = MockRouter(choice="merge_ready")
    scorer = LayaScorer(router=mock_router)

    result = scorer.score_context("Sample PR state with green CI")
    assert result.decision == "merge_ready"
    assert result.confidence >= 0.90
    assert result.probabilities["merge_ready"] == 0.65
    assert result.model_used == "english"
    assert "Sample PR state" in mock_router.last_state


def test_scorer_blocked():
    mock_router = MockRouter(
        choice="blocked",
        probabilities={"merge_ready": 0.05, "needs_review": 0.15, "blocked": 0.80},
        answer_confidence=0.80
    )
    scorer = LayaScorer(router=mock_router)

    result = scorer.score_context("Sample PR state with failed CI")
    assert result.decision == "blocked"
    assert result.confidence >= 0.95


def test_scorer_exception_fallback():
    class BrokenRouter:
        def predict(self, *args, **kwargs):
            raise RuntimeError("Model download failed")

    scorer = LayaScorer(router=BrokenRouter())
    result = scorer.score_context("Any state")
    assert result.decision == "needs_review"
    assert result.confidence == 0.5
    assert "Inference error" in result.rationale


def test_scorer_guardrail_failed_ci_overrides_model():
    # Router would choose merge_ready
    mock_router = MockRouter(choice="merge_ready")
    scorer = LayaScorer(router=mock_router)

    context = (
        "PULL REQUEST #2514: Update typescript\n"
        "CI Status: FAILED (1 failed: build)\n"
        "CI Failure Diagnostics:\n"
        "TypeError: Cannot read properties of undefined (reading 'Cjs')\n"
    )

    result = scorer.score_context(context)
    assert result.decision == "blocked"
    assert result.confidence == 0.99
    assert result.model_used == "guardrail"
    assert "TypeError: Cannot read properties of undefined" in result.rationale
    # Ensure router predict was not even called or bypassed
    assert mock_router.last_state is None


def test_scorer_guardrail_conflicting_mergeable():
    mock_router = MockRouter(choice="merge_ready")
    scorer = LayaScorer(router=mock_router)

    result = scorer.score_context(
        context="PULL REQUEST #10: Feature\nMergeable: CONFLICTING\nCI Status: PASSED",
        mergeable="CONFLICTING",
    )
    assert result.decision == "blocked"
    assert result.confidence == 0.99
    assert result.model_used == "guardrail"
    assert "conflict" in result.rationale.lower()
