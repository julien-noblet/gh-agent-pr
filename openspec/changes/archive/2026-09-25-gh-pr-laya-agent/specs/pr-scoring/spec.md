# Spec Delta

## Purpose

Automates the discovery and risk assessment of open GitHub pull requests using `rtk gh` and the Laya System-1 decision engine, producing calibrated confidence scores and CLI reports.

## ADDED Requirements

### Requirement: Repository and Pull Request Discovery
The system SHALL retrieve open pull requests from user-specified repositories or configured defaults using `rtk gh`.

#### Scenario: Discover PRs for specified repositories
- **WHEN** user executes the command with a list of target repositories
- **THEN** system queries `rtk gh pr list` for each repository and collects open pull requests

#### Scenario: Fallback to configuration file when no repository specified
- **WHEN** user executes the command without repository flags and a configuration file exists
- **THEN** system reads the repository list from the configuration file

### Requirement: Context Distillation for Pull Requests
The system SHALL build a compact textual state for each open PR containing metadata, CI check status, review states, file statistics, and filtered code diffs within token limits.

#### Scenario: Compact summary generation
- **WHEN** a PR contains multiple commits, CI statuses, and file modifications
- **THEN** system summarizes status check rollups, reviews, changed file counts, and truncates large diffs while excluding non-code assets and lockfiles

### Requirement: Laya Merge Risk Evaluation and Confidence Scoring
The system SHALL evaluate the PR state using Laya's decision router with a typed choice question classifying the PR into `merge_ready`, `needs_review`, or `blocked`, returning the chosen category and calibrated confidence score.

#### Scenario: Evaluating a safe PR
- **WHEN** a PR has green CI checks, positive reviews, well-scoped diff, and relevant tests
- **THEN** Laya classifies the PR as `merge_ready` with a high confidence score

#### Scenario: Evaluating a failing or high-risk PR
- **WHEN** a PR has failing CI status, breaking changes, or missing critical tests
- **THEN** Laya classifies the PR as `blocked` or `needs_review` with appropriate confidence

### Requirement: Formatted CLI Reporting
The system SHALL output a formatted console table summarizing repository name, PR number, title, CI status, decision category, and confidence score.

#### Scenario: Output display in terminal
- **WHEN** all targeted PRs have been analyzed
- **THEN** system renders a clean terminal table sorted by repository and PR number displaying the evaluations
