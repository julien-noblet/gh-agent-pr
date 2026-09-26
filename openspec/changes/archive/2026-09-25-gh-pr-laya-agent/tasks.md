# Tasks

## 1. Project Setup and Environment

- [x] 1.1 Initialize Python project layout (`pyproject.toml` or `requirements.txt` with `laya`, `rich` / `tabulate`) and verify installation with `python -m pip check`
- [x] 1.2 Implement configuration loader (`config.yaml` or CLI arguments) for repository targets and verify with unit tests

## 2. GitHub PR Discovery & Context Distillation

- [x] 2.1 Implement `rtk gh` wrapper module to query open pull requests (`gh pr list`, `gh pr view`, `gh pr diff`) and verify JSON output parsing with mock CLI outputs
- [x] 2.2 Implement PR context distillation module (summarizing commits, CI check rollups, reviews, filtering lockfiles/assets from diffs) and verify truncation rules with test fixtures

## 3. Laya Decision Engine Integration

- [x] 3.1 Implement Laya Router wrapper with typed `choice` question structure (`merge_ready`, `needs_review`, `blocked`) and verify inference output against sample PR states
- [x] 3.2 Implement confidence score calculation and categorization mapping from Laya output and verify with unit tests

## 4. CLI Reporting and Integration

- [x] 4.1 Implement formatted terminal table output displaying repository, PR ID, title, CI status, decision, and confidence score and verify layout with sample data
- [x] 4.2 Assemble end-to-end CLI entrypoint connecting repository discovery, distillation, scoring, and rendering, and verify execution on test repository
