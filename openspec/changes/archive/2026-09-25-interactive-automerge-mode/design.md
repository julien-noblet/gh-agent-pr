# Design

## Context

See `proposal.md` for motivation. Currently, `gh-agent-pr` outputs a table and finishes execution. When reviewing multiple automated bot updates or routine maintenance PRs across repositories, developers must manually run `gh pr merge <number> --auto --rebase` or open GitHub in a browser. An interactive mode ("au fil de l'eau") streamlines this workflow by presenting each evaluated PR immediately and providing single-keystroke action on verified `MERGE READY` pull requests.

## Goals / Non-Goals

**Goals:**
- Provide a dedicated `-i` / `--interactive` CLI flag.
- Inspect `autoMergeRequest` in `GitHubClient.view_pr` to avoid redundant merge prompts.
- Implement `enable_automerge(repo, pr_number, strategy="rebase", delete_branch=True)` in `GitHubClient`.
- Implement `open_in_browser(repo, pr_number)` in `GitHubClient`.
- Per-PR interactive loop in `cli.py`: prompt immediately after scoring each PR.
- Gate auto-merge prompts strictly to `MERGE READY` PRs.
- Provide clean interactive controls: `[y]` enable auto-merge, `[o]` open in browser, `[n]` skip, `[q]` quit.
- Display final summary report table upon completion or exit.

**Non-Goals:**
- Allowing auto-merge for `BLOCKED` or `NEEDS REVIEW` PRs.
- Custom commit message authoring within the CLI.
- Batch or non-interactive auto-merging without explicit user prompt.

## Decisions

### 1. Per-PR Streamlined Prompting ("Au fil de l'eau")
- **Decision**: In `run_pipeline`, when `interactive=True`, prompt immediately after evaluating each PR rather than waiting for the entire batch of repositories to finish.
- **Rationale**: For users with many repositories and PRs, waiting for all PRs to be analyzed delays action. Interactive mode provides immediate feedback and actionable decisions in real time.

### 2. Merge Strategy Default
- **Decision**: Use `--rebase` and `--delete-branch` (`rtk gh pr merge <number> --repo <repo> --auto --rebase --delete-branch`).
- **Rationale**: Keeps a linear commit history on base branches without merge commit bubbles, and cleans up remote branches automatically upon completion.

### 3. Graceful TTY Detection
- **Decision**: In `cli.py`, check `sys.stdin.isatty()` before prompting. If standard input is not a TTY (piped input, CI/CD runners), warn and bypass interactive prompting.
- **Rationale**: Prevents crashes or infinite loops in automated environments.

## Risks / Trade-offs

- [Repository settings disable auto-merge or rebase] GitHub repositories must have "Allow auto-merge" and "Allow rebase merging" enabled in repository settings. → Mitigation: Capture stderr from `gh pr merge --auto` and display informative error message if GitHub rejects auto-merge.
- [Premature exit on 'q'] User quits early before analyzing all PRs. → Mitigation: Render the table with all PRs evaluated up to that point so partial work is visible.
