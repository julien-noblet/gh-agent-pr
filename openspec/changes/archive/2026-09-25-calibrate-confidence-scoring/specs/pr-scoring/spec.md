# Spec Delta

## MODIFIED Requirements

### Requirement: Context Distillation for Pull Requests
The system SHALL build a compact textual state for each open PR containing metadata, CI check status, review states, file statistics, author classification, and filtered code diffs within token limits.

#### Scenario: Compact summary generation
- **WHEN** a PR contains multiple commits, CI statuses, and file modifications
- **THEN** system summarizes status check rollups, reviews, changed file counts, and truncates large diffs while excluding non-code assets and lockfiles

#### Scenario: Automated bot and configuration detection
- **WHEN** a PR is submitted by an automated maintenance bot (Renovate, Dependabot, ImgBot) or modifies only configuration/data files without executable source code
- **THEN** system identifies the bot author and marks test presence as not applicable rather than missing

### Requirement: Laya Merge Risk Evaluation and Confidence Scoring
The system SHALL evaluate the PR state using Laya's decision router with a typed choice question classifying the PR into `merge_ready`, `needs_review`, or `blocked`, returning the chosen category and a calibrated confidence score.

#### Scenario: Evaluating a safe PR
- **WHEN** a PR has green CI checks, positive reviews, well-scoped diff, and relevant tests
- **THEN** Laya classifies the PR as `merge_ready` with a high confidence score

#### Scenario: Evaluating a routine automated bot patch
- **WHEN** a PR is a routine patch update from a known bot with passing CI and conflict-free diff
- **THEN** system computes a calibrated confidence score reflecting high certainty (>= 85%)

#### Scenario: Evaluating a failing or high-risk PR
- **WHEN** a PR has failing CI status, breaking changes, or missing critical tests
- **THEN** Laya classifies the PR as `blocked` or `needs_review` with appropriate confidence
