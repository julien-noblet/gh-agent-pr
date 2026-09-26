# Tasks

## 1. GitHub Client Operations

- [x] 1.1 Include `autoMergeRequest` in `GitHubClient.view_pr` JSON query and verify via unit test
- [x] 1.2 Implement `enable_automerge(repo, pr_number, strategy="rebase", delete_branch=True)` in `GitHubClient` and verify via mock unit test
- [x] 1.3 Implement `open_in_browser(repo, pr_number)` in `GitHubClient` and verify via mock unit test

## 2. Configuration and Interactive Prompt Loop

- [x] 2.1 Add `interactive: bool` to `Config` and `-i` / `--interactive` flag to CLI parser in `cli.py` and verify via unit test
- [x] 2.2 Implement `prompt_pr_action` in `cli.py` with options `[y]` enable auto-merge, `[o]` open in browser, `[n]` skip, and `[q]` quit
- [x] 2.3 Integrate interactive per-PR prompt loop into `run_pipeline`, strictly restricting auto-merge prompts to `MERGE READY` PRs, and verify via unit tests

## 3. Verification and Integration

- [x] 3.1 Run full pytest test suite with `rtk pytest` to verify 100% pass rate
- [x] 3.2 Verify CLI `--help` displays `--interactive` option
