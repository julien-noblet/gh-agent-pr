# Proposal

## Why

Developers currently have to manually cross-reference CLI scoring results with the browser or run separate `gh pr merge` commands to act on pull requests. An interactive execution mode allows developers to act immediately on safe pull requests, enabling GitHub's auto-merge (`--auto --rebase --delete-branch`) on the fly as each PR is evaluated, saving context-switching time while strictly gating action behind verified `MERGE READY` assessments.

## What Changes

- Add an interactive execution flag `-i` / `--interactive` in CLI arguments and config.
- In `GitHubClient`:
  - Query `autoMergeRequest` in `view_pr` to detect whether auto-merge is already active on a PR.
  - Add `enable_automerge(repo, pr_number, strategy="rebase", delete_branch=True)` calling `rtk gh pr merge <number> --repo <repo> --auto --rebase --delete-branch`.
  - Add `open_in_browser(repo, pr_number)` calling `rtk gh pr view <number> --web`.
- In `cli.py`:
  - When `--interactive` is enabled, prompt the user on the fly ("au fil de l'eau") immediately after evaluating each PR.
  - Restrict auto-merge prompts strictly to pull requests classified as `MERGE READY`.
  - Provide interactive actions: `[y]` enable auto-merge with rebase, `[o]` open in browser, `[n]` skip to next PR, and `[q]` quit interactive mode.
  - Pull requests classified as `BLOCKED` or `NEEDS REVIEW` display their diagnostic details without triggering auto-merge prompts.
  - Display the comprehensive report table upon completion or when quitting interactive mode.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `pr-scoring`: Add interactive execution mode allowing immediate rebase auto-merge enablement for pull requests classified as `MERGE READY`.

## Impact

- Affected modules: `gh_agent_pr.config`, `gh_agent_pr.github`, `gh_agent_pr.cli`.
- Subprocess operations: `rtk gh pr merge <number> --repo <repo> --auto --rebase --delete-branch`, `rtk gh pr view <number> --web`.
- Interactive prompts: uses `rich.prompt.Prompt` with graceful fallback when standard input is not a terminal.
