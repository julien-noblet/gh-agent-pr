# gh-agent-pr

A CLI agent evaluating GitHub Pull Request merge confidence based on `rtk gh` (or GitHub CLI `gh`) and the **[Laya](https://github.com/NandhaKishorM/laya)** System-1 decision engine.

`gh-agent-pr` analyzes open pull requests across your repositories, distills their context (CI status, reviews, modified files, diffs, and failure diagnostics), and scores each PR into `MERGE READY`, `NEEDS REVIEW`, or `BLOCKED` with calibrated confidence scores and safety guardrails.

---

## Features

- **Automated PR Discovery**: Queries open pull requests across specific repositories or automatically discovers owned repositories using `rtk gh` / `gh`.
- **Intelligent Context Distillation**: Filters noisy lockfiles and binary assets, summarizes CI check statuses, detects test coverage changes, and extracts concise root-cause diagnostics on CI failures.
- **System-1 Decision Engine**: Evaluates pull requests with typed decisions using Laya models.
- **Deterministic Safety Guardrails**: Instantly blocks PRs with failing CI checks or git merge conflicts at 99% confidence.
- **Interactive Auto-merge Mode**: Optionally prompts to enable GitHub auto-merge (rebase) on safe pull requests.
- **Nix & Direnv Ready**: Zero-configuration reproducible environment with Nix Flakes and `direnv`.

---

## Installation

### Using Nix Flakes & Direnv (Recommended)

If you use `direnv` and Nix:
```bash
direnv allow
```
The `gh-agent-pr` command is automatically built and added to your `PATH`.

You can also run it directly without cloning via Nix:
```bash
nix run github:julien-noblet/gh-agent-pr -- --help
```

Or build locally:
```bash
nix build
./result/bin/gh-agent-pr --help
```

### Using standard Python Virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

*Requirements*: Python `>=3.10` and [GitHub CLI](https://cli.github.com/) (`gh` or `rtk gh`).

---

## Usage

### 1. Specific repositories via CLI:
```bash
gh-agent-pr --repo owner/repo-1 --repo owner/repo-2
```

### 2. Auto-discovery of user repositories:
```bash
gh-agent-pr
```

### 3. Interactive auto-merge mode:
Prompt to enable rebase auto-merge for PRs classified as `MERGE READY`:
```bash
gh-agent-pr --repo owner/repo --interactive
```

### 4. With a configuration file (`gh-agent-pr.yaml`):
```yaml
repos:
  - owner/repo-api
  - owner/repo-frontend
limit: 20
laya_model: english # or multilingual
interactive: false
```

Then run:
```bash
gh-agent-pr --config gh-agent-pr.yaml
```

### 5. JSON output for CI/CD pipelines:
```bash
gh-agent-pr --repo owner/repo --json
```

---

## How It Works

1. **Discovery (`rtk gh` / `gh`)**: Interrogates open PRs via `gh pr list`, fetches full metadata (`gh pr view`), and inspects git diffs (`gh pr diff`).
2. **Context Distillation**: Summarizes CI checks and reviews, classifies touched file types (code, docs, tests, configs), strips lockfile noise, and extracts failure logs when checks fail.
3. **Laya Decision Engine**: Classifies PRs into `merge_ready`, `needs_review`, or `blocked` with calibrated probability margins.
4. **Safety Guardrails**: Hard deterministic overrides ensure that broken builds or conflicts can never be marked as mergeable.
5. **Console Reporting**: Displays an interactive Rich table with colored badges, confidence progress bars, and diagnostics.

---

## License

Apache-2.0
