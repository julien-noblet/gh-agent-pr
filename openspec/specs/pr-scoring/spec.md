# Capability: pr-scoring

## Purpose

Automates the discovery and risk assessment of open GitHub pull requests using `rtk gh` and the Laya System-1 decision engine, producing calibrated confidence scores and CLI reports.

## Requirements

### Requirement: Repository and Pull Request Discovery
The system SHALL retrieve open pull requests from user-specified repositories or configured defaults using `rtk gh`.

#### Scenario: Discover PRs for specified repositories
- **WHEN** user executes the command with a list of target repositories
- **THEN** system queries `rtk gh pr list` for each repository and collects open pull requests

#### Scenario: Fallback to configuration file when no repository specified
- **WHEN** user executes the command without repository flags and a configuration file exists
- **THEN** system reads the repository list from the configuration file

### Requirement: Context Distillation for Pull Requests
The system SHALL build a compact textual state for each open PR containing metadata, CI check status, review states, file statistics, author classification, filtered code diffs within token limits, and failure log diagnostics.

#### Scenario: Compact summary generation
- **WHEN** a PR contains multiple commits, CI statuses, and file modifications
- **THEN** system summarizes status check rollups, reviews, changed file counts, and truncates large diffs while excluding non-code assets and lockfiles (including bun.lock and bun.lockb)

#### Scenario: Automated bot and configuration detection
- **WHEN** a PR is submitted by an automated maintenance bot (Renovate, Dependabot, ImgBot) or modifies only configuration/data files without executable source code
- **THEN** system identifies the bot author and marks test presence as not applicable rather than missing

#### Scenario: Context enrichment with CI failure logs
- **WHEN** a PR has one or more failed check runs
- **THEN** system fetches failed step logs and includes the distilled error reason in the PR context summary

### Requirement: CI Failure Log Inspection and Diagnostics
The system SHALL extract workflow run IDs from failed GitHub Actions check runs and fetch failure logs using `rtk gh run view <run_id> --log-failed`, parsing root-cause error messages to explain the failure.

#### Scenario: Extracting run ID from check rollup
- **WHEN** a check run in `statusCheckRollup` fails and has a details URL matching GitHub Actions
- **THEN** system extracts the run ID and queries the failed step logs via `rtk gh`

#### Scenario: Distilling failure root cause
- **WHEN** failed step logs contain error stack traces, compilation failures, or process exit errors
- **THEN** system extracts a concise diagnostic string (e.g. error type and message) and associates it with the PR evaluation

### Requirement: Laya Merge Risk Evaluation and Confidence Scoring
The system SHALL evaluate the PR state using Laya's decision router with a typed choice question classifying the PR into `merge_ready`, `needs_review`, or `blocked`, returning the chosen category and a calibrated confidence score. The system SHALL enforce a deterministic guardrail overriding the classifier to `blocked` whenever CI checks have failed or merge conflicts exist.

#### Scenario: Evaluating a safe PR
- **WHEN** a PR has green CI checks, positive reviews, well-scoped diff, and relevant tests
- **THEN** Laya classifies the PR as `merge_ready` with a high confidence score

#### Scenario: Evaluating a routine automated bot patch
- **WHEN** a PR is a routine patch update from a known bot with passing CI and conflict-free diff
- **THEN** system computes a calibrated confidence score reflecting high certainty (>= 85%)

#### Scenario: Evaluating a failing or high-risk PR
- **WHEN** a PR has failing CI status, breaking changes, or missing critical tests
- **THEN** system deterministically classifies the PR as `blocked` with 99% confidence and attaches the CI failure root cause when CI checks fail, or Laya classifies as `blocked` or `needs_review` with appropriate confidence

#### Scenario: Hard guardrail overriding unsafe recommendation
- **WHEN** CI checks are in a failed, cancelled, or action required state
- **THEN** system forces decision to `blocked` with 99% confidence regardless of bot author or diff simplicity

### Requirement: Formatted CLI Reporting
The system SHALL output a formatted console table summarizing repository name, PR number, title, CI status, decision category, confidence score, and error diagnostic details.

#### Scenario: Output display in terminal
- **WHEN** all targeted PRs have been analyzed
- **THEN** system renders a clean terminal table sorted by repository and PR number displaying the evaluations and failure details for blocked pull requests

### Requirement: Interactive Evaluation and Auto-Merge Execution
The system SHALL provide an interactive mode (`--interactive` / `-i`) evaluating pull requests on the fly and prompting the user to enable rebase auto-merge for pull requests classified as `merge_ready`.

#### Scenario: Prompting for auto-merge on safe PR
- **WHEN** user executes with `--interactive` and a pull request is classified as `merge_ready` without existing auto-merge enabled
- **THEN** system prompts the user to enable auto-merge, open in browser, skip to next PR, or quit

#### Scenario: Enabling rebase auto-merge upon confirmation
- **WHEN** user confirms `y` on the auto-merge prompt
- **THEN** system executes `rtk gh pr merge <number> --repo <repo> --auto --rebase --delete-branch` and reports success or error

#### Scenario: Suppressing auto-merge prompt on non-ready PRs
- **WHEN** a pull request is classified as `blocked` or `needs_review`
- **THEN** system displays the evaluation and diagnostic reason without prompting for auto-merge

#### Scenario: Existing auto-merge detection
- **WHEN** a pull request already has an active `autoMergeRequest`
- **THEN** system informs the user that auto-merge is already enabled without prompting to re-arm it
