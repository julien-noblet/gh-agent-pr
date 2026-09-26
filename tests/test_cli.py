import json
from io import StringIO
from rich.console import Console
from gh_agent_pr.config import Config
from gh_agent_pr.cli import run_pipeline
from gh_agent_pr.scorer import ScoringResult


class DummyGitHubClient:
    def __init__(self):
        self.listed_repos = []

    def list_user_repos(self, limit=10):
        return ["user/discovered-repo"]

    def list_open_prs(self, repo, limit=20):
        self.listed_repos.append(repo)
        return [
            {"number": 1, "title": "fix: critical memory leak"}
        ]

    def view_pr(self, repo, pr_number):
        return {
            "number": 1,
            "title": "fix: critical memory leak",
            "body": "Fixes leak by releasing connection",
            "mergeable": "MERGEABLE",
            "files": [{"path": "conn.py", "additions": 5, "deletions": 2}],
            "statusCheckRollup": [{"name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"}],
            "reviews": [{"state": "APPROVED"}]
        }

    def get_pr_diff(self, repo, pr_number):
        return "diff --git a/conn.py b/conn.py\n+ conn.close()\n"


class DummyScorer:
    def score_context(self, context, model="english"):
        return ScoringResult(
            decision="merge_ready",
            confidence=0.96,
            probabilities={"merge_ready": 0.96, "needs_review": 0.03, "blocked": 0.01},
            model_used=model
        )


def test_run_pipeline_with_configured_repos():
    config = Config(repos=["test/repo-1"], limit=5)
    client = DummyGitHubClient()
    scorer = DummyScorer()
    console = Console(file=StringIO())

    evaluations = run_pipeline(config, client=client, scorer=scorer, console=console)
    assert len(evaluations) == 1
    ev = evaluations[0]
    assert ev["repo"] == "test/repo-1"
    assert ev["pr_number"] == 1
    assert ev["decision"] == "merge_ready"
    assert ev["confidence"] == 0.96
    assert "PASSED" in ev["ci_status"]


def test_run_pipeline_auto_discovery():
    config = Config(repos=[], limit=5)
    client = DummyGitHubClient()
    scorer = DummyScorer()
    console = Console(file=StringIO())

    evaluations = run_pipeline(config, client=client, scorer=scorer, console=console)
    assert len(evaluations) == 1
    assert evaluations[0]["repo"] == "user/discovered-repo"


def test_run_pipeline_failed_ci_inspected():
    class FailingClient(DummyGitHubClient):
        def list_open_prs(self, repo, limit=20):
            return [{"number": 2514, "title": "Update typescript to v7"}]

        def view_pr(self, repo, pr_number):
            return {
                "number": 2514,
                "title": "Update typescript to v7",
                "mergeable": "MERGEABLE",
                "files": [{"path": "package.json", "additions": 1, "deletions": 1}],
                "statusCheckRollup": [
                    {
                        "name": "build",
                        "status": "COMPLETED",
                        "conclusion": "FAILURE",
                        "detailsUrl": "https://github.com/owner/repo/actions/runs/998877"
                    }
                ],
                "reviews": []
            }

        def get_failed_run_log(self, repo, run_id):
            assert run_id == 998877
            return "TypeError: Cannot read properties of undefined (reading 'Cjs')\nProcess completed with exit code 1."

    from gh_agent_pr.scorer import LayaScorer

    config = Config(repos=["owner/repo"])
    client = FailingClient()
    scorer = LayaScorer(router=DummyScorer())  # Dummy router would say merge_ready
    console = Console(file=StringIO())

    evaluations = run_pipeline(config, client=client, scorer=scorer, console=console)
    assert len(evaluations) == 1
    ev = evaluations[0]
    assert ev["pr_number"] == 2514
    assert ev["decision"] == "blocked"
    assert ev["confidence"] == 0.99
    assert "TypeError: Cannot read properties of undefined (reading 'Cjs')" in ev["details"]


def test_prompt_pr_action_yes(monkeypatch):
    from gh_agent_pr.cli import prompt_pr_action
    from gh_agent_pr.github import GitHubClient

    actions_run = []
    def mock_runner(cmd):
        actions_run.append(cmd)
        return "Auto-merge enabled", "", 0

    client = GitHubClient(runner=mock_runner)
    console = Console(file=StringIO())

    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: "y")
    res = prompt_pr_action("org/repo", 42, client, console)
    assert res == "y"
    assert len(actions_run) == 1
    assert "merge" in actions_run[0]
    assert "--auto" in actions_run[0]
    assert "--rebase" in actions_run[0]


def test_prompt_pr_action_skip(monkeypatch):
    from gh_agent_pr.cli import prompt_pr_action
    from gh_agent_pr.github import GitHubClient

    client = GitHubClient(runner=lambda cmd: ("", "", 0))
    console = Console(file=StringIO())

    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: "n")
    res = prompt_pr_action("org/repo", 42, client, console)
    assert res == "n"


def test_run_pipeline_interactive_merge_ready():
    config = Config(repos=["test/repo-1"], interactive=True)
    client = DummyGitHubClient()
    scorer = DummyScorer()
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, color_system=None, width=120)

    prompted_prs = []
    output_before_prompt = []

    def mock_prompt_handler(repo, pr_number, cl, con):
        output_before_prompt.append(buf.getvalue())
        prompted_prs.append((repo, pr_number))
        return "y"

    evaluations = run_pipeline(
        config,
        client=client,
        scorer=scorer,
        console=console,
        prompt_handler=mock_prompt_handler
    )
    assert len(evaluations) == 1
    assert prompted_prs == [("test/repo-1", 1)]
    assert evaluations[0]["auto_merge"] is True
    assert evaluations[0]["details"] == "Auto-merge enabled"

    # Verify that the evaluation card was rendered to console BEFORE prompting the user
    assert len(output_before_prompt) == 1
    card_output = output_before_prompt[0]
    assert "test/repo-1#1: fix: critical memory leak" in card_output
    assert "CI: PASS" in card_output
    assert "Decision: MERGE READY" in card_output
    assert "Confidence: 96%" in card_output


def test_run_pipeline_interactive_suppressed_for_blocked():
    class BlockedClient(DummyGitHubClient):
        def view_pr(self, repo, pr_number):
            return {
                "number": 1,
                "title": "broken PR",
                "mergeable": "MERGEABLE",
                "statusCheckRollup": [{"name": "ci", "status": "COMPLETED", "conclusion": "FAILURE"}],
                "reviews": []
            }

    from gh_agent_pr.scorer import LayaScorer
    config = Config(repos=["test/repo-1"], interactive=True)
    client = BlockedClient()
    scorer = LayaScorer(router=DummyScorer())
    console = Console(file=StringIO())

    prompted_prs = []
    def mock_prompt_handler(repo, pr_number, cl, con):
        prompted_prs.append((repo, pr_number))
        return "y"

    evaluations = run_pipeline(
        config,
        client=client,
        scorer=scorer,
        console=console,
        prompt_handler=mock_prompt_handler
    )
    assert len(evaluations) == 1
    assert evaluations[0]["decision"] == "blocked"
    # Never prompted because it is blocked!
    assert prompted_prs == []


def test_run_pipeline_interactive_existing_automerge():
    class AlreadyMergedClient(DummyGitHubClient):
        def view_pr(self, repo, pr_number):
            return {
                "number": 1,
                "title": "PR with automerge already",
                "mergeable": "MERGEABLE",
                "statusCheckRollup": [{"name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS"}],
                "reviews": [],
                "autoMergeRequest": {"enabledAt": "2026-09-24T12:00:00Z"}
            }

    config = Config(repos=["test/repo-1"], interactive=True)
    client = AlreadyMergedClient()
    scorer = DummyScorer()
    console = Console(file=StringIO())

    prompted_prs = []
    def mock_prompt_handler(repo, pr_number, cl, con):
        prompted_prs.append((repo, pr_number))
        return "y"

    evaluations = run_pipeline(
        config,
        client=client,
        scorer=scorer,
        console=console,
        prompt_handler=mock_prompt_handler
    )
    assert len(evaluations) == 1
    assert evaluations[0]["decision"] == "merge_ready"
    assert evaluations[0]["auto_merge"] is True
    # Not prompted because autoMergeRequest was already active!
    assert prompted_prs == []
