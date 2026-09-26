import json
from gh_agent_pr.github import GitHubClient


def test_list_open_prs_mock():
    mock_response = json.dumps([
        {"number": 101, "title": "fix: resolve bug", "author": {"login": "alice"}},
        {"number": 102, "title": "feat: add feature", "author": {"login": "bob"}}
    ])

    def mock_runner(cmd):
        assert "pr" in cmd
        assert "list" in cmd
        assert "--repo" in cmd
        assert "owner/my-repo" in cmd
        return mock_response, "", 0

    client = GitHubClient(runner=mock_runner)
    prs = client.list_open_prs("owner/my-repo")
    assert len(prs) == 2
    assert prs[0]["number"] == 101
    assert prs[1]["title"] == "feat: add feature"


def test_view_pr_mock():
    mock_pr = json.dumps({
        "number": 42,
        "title": "refactor: clean up auth",
        "body": "Detailed description here",
        "mergeable": "MERGEABLE",
        "files": [{"path": "auth.py", "additions": 10, "deletions": 5}],
        "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
        "autoMergeRequest": {"enabledAt": "2026-09-24T12:00:00Z", "mergeMethod": "REBASE"}
    })

    def mock_runner(cmd):
        assert "pr" in cmd
        assert "view" in cmd
        assert "42" in cmd
        assert "--json" in cmd
        return mock_pr, "", 0

    client = GitHubClient(runner=mock_runner)
    pr = client.view_pr("owner/my-repo", 42)
    assert pr is not None
    assert pr["number"] == 42
    assert pr["mergeable"] == "MERGEABLE"
    assert pr["autoMergeRequest"] is not None


def test_enable_automerge_mock():
    def mock_runner(cmd):
        assert "pr" in cmd
        assert "merge" in cmd
        assert "42" in cmd
        assert "--repo" in cmd
        assert "owner/my-repo" in cmd
        assert "--auto" in cmd
        assert "--rebase" in cmd
        assert "--delete-branch" in cmd
        return "Auto-merge enabled for pull request #42", "", 0

    client = GitHubClient(runner=mock_runner)
    success, msg = client.enable_automerge("owner/my-repo", 42, strategy="rebase", delete_branch=True)
    assert success is True
    assert "Auto-merge enabled" in msg


def test_open_in_browser_mock():
    def mock_runner(cmd):
        assert "pr" in cmd
        assert "view" in cmd
        assert "42" in cmd
        assert "--web" in cmd
        return "", "", 0

    client = GitHubClient(runner=mock_runner)
    assert client.open_in_browser("owner/my-repo", 42) is True


def test_get_pr_diff_mock():
    mock_diff = "diff --git a/auth.py b/auth.py\n+new line\n-old line"

    def mock_runner(cmd):
        assert "diff" in cmd
        return mock_diff, "", 0

    client = GitHubClient(runner=mock_runner)
    diff = client.get_pr_diff("owner/my-repo", 42)
    assert "+new line" in diff


def test_get_failed_run_log_mock():
    mock_log = "Run build\nError: Process completed with exit code 1."

    def mock_runner(cmd):
        assert "run" in cmd
        assert "view" in cmd
        assert "12345" in cmd
        assert "--log-failed" in cmd
        assert "--repo" in cmd
        assert "owner/my-repo" in cmd
        return mock_log, "", 0

    client = GitHubClient(runner=mock_runner)
    log = client.get_failed_run_log("owner/my-repo", 12345)
    assert "Error: Process completed with exit code 1." in log


def test_list_user_repos_mock():
    mock_repos = json.dumps([
        {"nameWithOwner": "alice/proj1"},
        {"nameWithOwner": "alice/proj2"}
    ])

    def mock_runner(cmd):
        assert "repo" in cmd
        assert "list" in cmd
        return mock_repos, "", 0

    client = GitHubClient(runner=mock_runner)
    repos = client.list_user_repos()
    assert repos == ["alice/proj1", "alice/proj2"]
