# Design

## Context

See `proposal.md` for motivation. In PR #2514 (`julien-noblet/cad-killer`), a major TypeScript v6 to v7 upgrade failed compilation with `TypeError: Cannot read properties of undefined (reading 'Cjs')`. Because Renovate authored the PR and touched mostly package/lock files, Laya's zero-shot router evaluated it as `merge_ready` despite CI failure. Relying on zero-shot LLM prompts to override bot heuristics on raw compilation logs is prone to hallucinations. A deterministic guardrail combined with log extraction provides guaranteed safety and clear diagnostics.

## Goals / Non-Goals

**Goals:**
- Deterministic guardrail: Never allow a PR with failing CI or git merge conflicts to be classified as `merge_ready` or `needs_review` when clearly broken; force `blocked` with 99% confidence.
- Inspect failed CI logs: Query `rtk gh run view <run_id> --repo <repo> --log-failed` for failed workflow runs.
- Distill root-cause error lines: Extract concise error diagnostics (e.g. compiler error, test failure summary, stack trace top) to present in the CLI output.
- Filter lockfile noise: Ignore `bun.lock` and `bun.lockb` in git diffs.
- CLI presentation: Display the extracted root-cause failure in a dedicated details column in the report table.

**Non-Goals:**
- Downloading full artifact logs or providing interactive log pagers.
- Automated PR remediation or fixing broken builds.
- Supporting non-GitHub-Actions CI providers (e.g. external CircleCI/Jenkins URLs where `gh run view` is inapplicable).

## Decisions

### 1. Deterministic Safety Floor in Scorer
- **Decision**: In `scorer.py`, check `pr.ci_status`. If `ci_status == CIStatus.FAILED` (or `CANCELLED`, `ACTION_REQUIRED`), or `pr.is_conflicted` is True:
  - Force `category = DecisionCategory.BLOCKED`
  - Force `calibrated_confidence = 0.99`
  - Set reasoning to the extracted CI failure diagnostic or conflict notice.
- **Rationale**: CI failure is a hard blocker in production software workflows. Code that does not build or pass tests must never be merged, regardless of who authored it.
- **Alternatives Considered**: Passing log failure snippets into Laya router prompt. Rejected because Laya small models often hallucinate or fail to weigh compiler stack traces against bot author templates.

### 2. Run ID Extraction & Log Retrieval
- **Decision**: In `GitHubClient`, add `get_failed_run_log(repo: str, run_id: int) -> str`.
- In `distill.py`, scan `statusCheckRollup` entries where `conclusion == "FAILURE"` or `status == "COMPLETED"` with negative conclusion. Extract run ID using regex `r"/actions/runs/(\d+)"`.
- Call `rtk gh run view <run_id> --repo <repo> --log-failed`.
- **Rationale**: `rtk gh run view --log-failed` only prints the step that actually failed, drastically reducing token/data overhead.

### 3. Log Distillation / Error Extractor
- **Decision**: Implement `extract_failure_reason(log_text: str) -> str`:
  - Strip GitHub Actions timestamps (`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*`).
  - Scan for error signatures (`Error:`, `TypeError:`, `SyntaxError:`, `FAIL `, `##[error]`).
  - Fall back to the last non-empty line of the failed step log if no specific pattern matches.
  - Limit to 120 characters for clean tabular display.

### 4. Lockfile Diff Filtering
- **Decision**: Add `"bun.lock"` and `"bun.lockb"` to `IGNORED_DIFF_PATTERNS` in `distill.py`.
- **Rationale**: Bun v1.2+ uses text `bun.lock` or binary `bun.lockb`. Large lockfile diffs crowd out the actual `package.json` diff.

## Risks / Trade-offs

- [External CI providers] URLs not matching `/actions/runs/<id>` cannot be inspected via `gh run view`. → Mitigation: Gracefully handle missing run ID or `gh run view` error and fall back to generic "CI failed (check detailsUrl)".
- [Network overhead] Extra CLI call per failed PR. → Mitigation: Only fetched for PRs where CI status is actually failed; routine passing PRs make 0 extra calls.
