# Tasks

## 1. Distillation Improvements

- [x] 1.1 Add bot author detection and non-code/configuration classification in `distill.py` and verify with unit tests in `tests/test_distill.py`
- [x] 1.2 Update prompt text template in `distill.py` to format bot and test requirements clearly and verify with test fixtures

## 2. Confidence Calibration & Scorer Tuning

- [x] 2.1 Update Laya choice criteria in `scorer.py` to recognize routine bot and config patches and verify with sample PR evaluations
- [x] 2.2 Implement calibrated confidence scoring formula in `scorer.py` and verify with unit tests in `tests/test_scorer.py`
- [x] 2.3 Verify end-to-end scoring output on dotfiles PR #87 to confirm confidence score >= 85%
