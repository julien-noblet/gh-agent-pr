# Spec Delta

## ADDED Requirements

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
