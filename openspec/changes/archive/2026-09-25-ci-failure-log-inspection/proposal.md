# Proposal

## Why

A pull request with failing CI checks (e.g. PR #2514 with broken TypeScript 7 compiler errors) must never be marked `MERGE READY`. Currently, when CI fails, the system lacks visibility into the exact error and relies solely on zero-shot LLM classification which can hallucinate a safe merge. Developers need deterministic blocking on CI failures combined with automatic extraction of the exact compilation or test failure logs from GitHub Actions.

## What Changes

- Add failed check log retrieval in `GitHubClient` using `rtk gh run view <run_id> --log-failed`.
- Extract run IDs from `statusCheckRollup` details URLs (e.g. `/actions/runs/<id>`).
- Implement failure log distillation to extract the root-cause error (e.g. `TypeError`, `SyntaxError`, `Process completed with exit code X`).
- Add strict deterministic guardrail: if CI checks failed or merge conflicts exist, force the decision to `BLOCKED` with 99% confidence and record the failure reason.
- Add `bun.lock` and `bun.lockb` to ignored diff patterns so lockfile churn does not displace meaningful code modifications.
- Update CLI report table to display the failure reason/details column.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `pr-scoring`: Add CI failure log inspection via `rtk gh run view --log-failed`, enforce strict deterministic guardrails on failed checks, and display root-cause failure diagnostics.

## Impact

- Affected modules: `gh_agent_pr.github`, `gh_agent_pr.distill`, `gh_agent_pr.scorer`, `gh_agent_pr.report`, `gh_agent_pr.cli`.
- System calls: `rtk gh run view <run_id> --repo <repo> --log-failed`.
