# Design

## Context

See proposal.md - Why.
The project is built as a standalone Python CLI tool running on Python 3.10+, utilizing the `laya` package for decision inference and calling `rtk gh` for GitHub interactions.

## Goals / Non-Goals

**Goals:**
- Fast System-1 evaluation of pull requests (< 100 ms per PR decision with Laya).
- Zero setup for authentication by reusing user's existing `gh` session through `rtk gh`.
- Clear, readable terminal summary table highlighting high-confidence mergeable PRs vs high-risk ones.

**Non-Goals:**
- Automated merge execution or pushing approvals/rejections (read-only scoring).
- Deep AST code analysis or whole-repository semantic graph scanning.

## Decisions

### 1. GitHub Integration via `rtk gh` Subprocesses
- **Decision**: Query GitHub metadata and diffs via `rtk gh` commands (`gh pr list`, `gh pr view`, `gh pr diff`) instead of direct REST/GraphQL client with separate personal access tokens.
- **Rationale**: Honors user token-reduction rules (`rtk`), reuses existing local `gh auth` session seamlessly, and avoids secrets management.
- **Alternatives**: Octokit / PyGithub (requires PAT configuration and environment variables).

### 2. Context Distillation Pipeline
- **Decision**: Extract structured fields (title, body, CI check status rollup, review decision, changed file paths) and append an excerpt of the code diff filtered to exclude noisy files (`package-lock.json`, `pnpm-lock.yaml`, compiled assets, migrations). Truncate total text state to fit comfortably within Laya's optimal context window.
- **Rationale**: Raw diffs can be tens of thousands of tokens, which would overflow Laya's encoder or dilute decision accuracy.

### 3. Laya Choice & Confidence Modeling
- **Decision**: Use Laya's `choice` question type with 3 defined categories:
  - `merge_ready`: Low risk, green CI, tests present or trivial change.
  - `needs_review`: Moderate risk, non-trivial logic, requires human review.
  - `blocked`: High risk, failing CI, breaking changes, or conflicts.
  Extract the predicted choice and Laya's calibrated confidence score (0.0 to 1.0) formatted as a percentage.
- **Rationale**: `choice` provides both discrete actionable categorization and calibrated probabilistic confidence.
- **Alternatives**: Numeric ordinal `score` alone (less explanatory) or binary `noul` (lacks the intermediate "needs review" state).

### 4. CLI Framework
- **Decision**: Standard library `argparse` or lightweight `rich` / `tabulate` for terminal output formatting.

## Risks / Trade-offs

- **[Risk] Initial Laya model checkpoint download delay** → Mitigation: Print progress message on first invocation indicating checkpoint setup.
- **[Risk] High-volume repositories with huge PR backlogs** → Mitigation: Limit query to `--limit` (default: 20 most recent open PRs per repo).
- **[Risk] Flaky or incomplete PR descriptions** → Mitigation: State builder gives higher weight to CI status and test file diff presence when PR description is short.
