# Tasks

## 1. GitHub Client and Lockfile Filter

- [x] 1.1 Add `bun.lock` and `bun.lockb` to `IGNORED_DIFF_PATTERNS` in `distill.py` and verify via unit test
- [x] 1.2 Implement `get_failed_run_log(repo: str, run_id: int) -> str` in `GitHubClient` using `rtk gh run view` and verify via mock unit test

## 2. Failure Log Extraction and Distillation

- [x] 2.1 Add helper in `distill.py` to extract failed run IDs from `statusCheckRollup` details URLs and verify via unit test
- [x] 2.2 Implement `extract_failure_reason(log_text: str) -> str` in `distill.py` to parse compiler/test error lines and verify with unit tests
- [x] 2.3 Store `ci_failure_reason` on `PRSummary` and populate during distillation when failed run logs are available

## 3. Scorer Guardrails and CLI Reporting

- [x] 3.1 Enforce deterministic `BLOCKED` decision with 99% confidence and failure reasoning in `scorer.py` on CI failure or merge conflict, and verify with unit tests
- [x] 3.2 Update `report.py` and `cli.py` to include a failure diagnostic column in the CLI table and verify with unit tests
- [x] 3.3 Run full test suite with `rtk pytest` to verify 100% pass rate
- [x] 3.4 Run live evaluation on `julien-noblet/cad-killer` PR #2514 to verify it is classified as `BLOCKED` with 99% confidence and displays the TypeScript compiler failure
