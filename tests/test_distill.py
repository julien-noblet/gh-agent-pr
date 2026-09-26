from gh_agent_pr.distill import (
    summarize_ci,
    summarize_reviews,
    filter_diff,
    analyze_files,
    build_pr_context,
    is_bot_author,
    classify_files,
    extract_failed_run_ids,
    extract_failure_reason,
    distill_pr,
    PRSummary,
)


def test_is_bot_author():
    assert is_bot_author("app/renovate") is True
    assert is_bot_author("dependabot[bot]") is True
    assert is_bot_author("imgbot[bot]") is True
    assert is_bot_author("alice") is False


def test_classify_files():
    has_code, only_config = classify_files(["home/.chezmoidata/asdf.yaml", "README.md"])
    assert has_code is False
    assert only_config is True

    has_code, only_config = classify_files(["src/main.py", "config.yaml"])
    assert has_code is True
    assert only_config is False


def test_summarize_ci_success():
    checks = [
        {"name": "test-suite", "status": "COMPLETED", "conclusion": "SUCCESS"},
        {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"}
    ]
    res = summarize_ci(checks)
    assert "PASSED" in res
    assert "2/2 checks successful" in res


def test_summarize_ci_failure():
    checks = [
        {"name": "test-suite", "status": "COMPLETED", "conclusion": "FAILURE"},
        {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"}
    ]
    res = summarize_ci(checks)
    assert "FAILED" in res
    assert "test-suite" in res


def test_summarize_ci_pending():
    checks = [
        {"name": "test-suite", "status": "IN_PROGRESS", "conclusion": ""},
        {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"}
    ]
    res = summarize_ci(checks)
    assert "PENDING" in res


def test_summarize_reviews():
    assert summarize_reviews([]) == "NO REVIEWS"
    assert "APPROVED" in summarize_reviews([{"state": "APPROVED"}])
    assert "CHANGES REQUESTED" in summarize_reviews([{"state": "CHANGES_REQUESTED"}, {"state": "APPROVED"}])


def test_analyze_files():
    files = [
        {"path": "src/main.py", "additions": 10, "deletions": 2},
        {"path": "tests/test_main.py", "additions": 20, "deletions": 0}
    ]
    paths, has_tests, additions, deletions = analyze_files(files)
    assert len(paths) == 2
    assert has_tests is True
    assert additions == 30
    assert deletions == 2


def test_filter_diff_ignores_lockfile():
    raw_diff = (
        "diff --git a/package-lock.json b/package-lock.json\n"
        "+ lockfile blob\n"
        "diff --git a/bun.lock b/bun.lock\n"
        "+ bun text lockfile\n"
        "diff --git a/bun.lockb b/bun.lockb\n"
        "+ bun binary lockfile\n"
        "diff --git a/src/app.py b/src/app.py\n"
        "+ print('hello')\n"
    )
    filtered = filter_diff(raw_diff, max_chars=1000)
    assert "package-lock.json" not in filtered
    assert "bun.lock" not in filtered
    assert "bun.lockb" not in filtered
    assert "src/app.py" in filtered


def test_build_pr_context_bot_config():
    pr_data = {
        "number": 87,
        "title": "Update dependency rust to v1.98.1",
        "body": "Bumps rust",
        "author": {"login": "app/renovate"},
        "mergeable": "MERGEABLE",
        "files": [{"path": "home/.chezmoidata/asdf.yaml", "additions": 1, "deletions": 1}],
        "statusCheckRollup": [{"name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS"}],
        "reviews": []
    }
    raw_diff = "diff --git a/asdf.yaml\n- 1.98.0\n+ 1.98.1\n"

    context = build_pr_context(pr_data, raw_diff)
    assert "app/renovate [Automated Bot]" in context
    assert "NOT APPLICABLE" in context
    assert "PASSED" in context


def test_extract_failed_run_ids():
    status_rollup = [
        {"name": "test", "status": "COMPLETED", "conclusion": "SUCCESS", "detailsUrl": "https://github.com/org/repo/actions/runs/111"},
        {"name": "build", "status": "COMPLETED", "conclusion": "FAILURE", "detailsUrl": "https://github.com/org/repo/actions/runs/222/job/333"},
        {"name": "lint", "status": "COMPLETED", "conclusion": "FAILURE", "detailsUrl": "https://github.com/org/repo/actions/runs/222/job/444"},
        {"name": "deploy", "status": "COMPLETED", "conclusion": "FAILURE", "detailsUrl": "https://github.com/org/repo/actions/runs/555"},
    ]
    run_ids = extract_failed_run_ids(status_rollup)
    assert run_ids == [222, 555]


def test_extract_failure_reason_compiler_error():
    log_text = """
2026-03-24T22:15:30.1234567Z > cad-killer@0.1.0 build
2026-03-24T22:15:30.1234567Z > bun build ./src/index.ts
2026-03-24T22:15:31.9876543Z TypeError: Cannot read properties of undefined (reading 'Cjs')
2026-03-24T22:15:31.9876543Z     at Object.<anonymous> (/home/runner/work/cad-killer/node_modules/...)
2026-03-24T22:15:32.0000000Z ##[error]Process completed with exit code 1.
"""
    reason = extract_failure_reason(log_text)
    assert reason == "TypeError: Cannot read properties of undefined (reading 'Cjs')"


def test_extract_failure_reason_generic_fallback():
    log_text = """
2026-03-24T22:15:30.1234567Z Starting job
2026-03-24T22:15:32.0000000Z ##[error]Process completed with exit code 1.
"""
    reason = extract_failure_reason(log_text)
    assert "Process completed with exit code 1." in reason


def test_distill_pr_with_failure():
    pr_data = {
        "number": 2514,
        "title": "Update dependency typescript to v7",
        "author": {"login": "app/renovate"},
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {
                "name": "build",
                "status": "COMPLETED",
                "conclusion": "FAILURE",
                "detailsUrl": "https://github.com/julien-noblet/cad-killer/actions/runs/98765"
            }
        ]
    }
    mock_log = "TypeError: Cannot read properties of undefined (reading 'Cjs')\n##[error]Process completed with exit code 1."
    summary = distill_pr(pr_data, raw_diff="diff --git a/package.json...", failure_log=mock_log)

    assert isinstance(summary, PRSummary)
    assert summary.number == 2514
    assert summary.failed_run_ids == [98765]
    assert summary.ci_failure_reason == "TypeError: Cannot read properties of undefined (reading 'Cjs')"
    assert "CI Failure Diagnostics:" in summary.context
    assert "TypeError: Cannot read properties of undefined (reading 'Cjs')" in summary.context
