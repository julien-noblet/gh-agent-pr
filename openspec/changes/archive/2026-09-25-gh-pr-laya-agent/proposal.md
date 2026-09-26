# Proposal

## Why

Reviewing and triaging open pull requests across multiple repositories is time-consuming and cognitively demanding. Developers need a fast, automated way to inspect open PRs, evaluate merge risk, and assign a calibrated confidence score to identify which PRs are safe to merge immediately and which require careful human review.

## What Changes

- Create a CLI agent that discovers open PRs for configured user repositories using `rtk gh`.
- Build a compact PR context summarizer extracting metadata, CI check status, review approvals, touched file categories, and truncated diffs without exceeding token budgets.
- Integrate the Laya System-1 non-autoregressive decision engine (`Router.predict`) using typed `choice` evaluations (`merge_ready`, `needs_review`, `blocked`) and associated probability/confidence distributions.
- Implement a CLI terminal report formatting PR status, risk category, and confidence score.

## Capabilities

### New Capabilities
- `pr-scoring`: Collection of open PRs via `rtk gh`, context distillation, Laya-based typed merge risk classification, confidence score computation, and formatted CLI output.

### Modified Capabilities
<!-- None -->

## Impact

- **Dependencies**: Python 3.10+, `laya` decision engine package, GitHub CLI (`gh` wrapped via `rtk`).
- **APIs/Tools**: `rtk gh pr list`, `rtk gh pr view`, `rtk gh pr diff`.
- **System**: Local command-line tool with zero remote service requirements outside GitHub API calls via `gh`.
