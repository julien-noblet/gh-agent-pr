"""GitHub CLI (rtk gh) wrapper for retrieving pull requests and diffs."""

import json
import logging
import shutil
import subprocess
from typing import Callable, List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Type for custom command runner: takes command list, returns (stdout, stderr, returncode)
CommandRunner = Callable[[List[str]], tuple[str, str, int]]


def default_command_runner(cmd: List[str]) -> tuple[str, str, int]:
    """Execute command in shell and return stdout, stderr, returncode."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except Exception as e:
        return "", str(e), 1


class GitHubClient:
    def __init__(self, runner: Optional[CommandRunner] = None):
        self.runner = runner or default_command_runner
        # Check whether 'rtk' is available
        self.use_rtk = shutil.which("rtk") is not None

    def _build_gh_cmd(self, subargs: List[str]) -> List[str]:
        if self.use_rtk:
            return ["rtk", "gh"] + subargs
        return ["gh"] + subargs

    def list_open_prs(self, repo: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List open pull requests for a repository."""
        cmd = self._build_gh_cmd([
            "pr", "list",
            "--repo", repo,
            "--state", "open",
            "--limit", str(limit),
            "--json", "number,title,author,headRefName,baseRefName,labels,reviewDecision,updatedAt"
        ])
        stdout, stderr, code = self.runner(cmd)
        if code != 0:
            logger.error("Failed to list PRs for %s: %s", repo, stderr.strip())
            return []
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON output for %s: %s", repo, stdout[:200])
            return []

    def view_pr(self, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve detailed PR metadata, files, checks, and reviews."""
        cmd = self._build_gh_cmd([
            "pr", "view", str(pr_number),
            "--repo", repo,
            "--json", "number,title,body,author,headRefName,baseRefName,files,statusCheckRollup,reviews,mergeable,autoMergeRequest"
        ])
        stdout, stderr, code = self.runner(cmd)
        if code != 0:
            logger.error("Failed to view PR #%d in %s: %s", pr_number, repo, stderr.strip())
            return None
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON view for PR #%d in %s: %s", pr_number, repo, stdout[:200])
            return None

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Retrieve raw git diff for a PR."""
        cmd = self._build_gh_cmd([
            "pr", "diff", str(pr_number),
            "--repo", repo,
        ])
        stdout, stderr, code = self.runner(cmd)
        if code != 0:
            logger.error("Failed to fetch diff for PR #%d in %s: %s", pr_number, repo, stderr.strip())
            return ""
        return stdout

    def get_failed_run_log(self, repo: str, run_id: int) -> str:
        """Retrieve failed logs for a workflow run using gh run view --log-failed."""
        cmd = self._build_gh_cmd([
            "run", "view", str(run_id),
            "--repo", repo,
            "--log-failed",
        ])
        stdout, stderr, code = self.runner(cmd)
        if code != 0:
            logger.error("Failed to fetch failed logs for run %d in %s: %s", run_id, repo, stderr.strip())
            return ""
        return stdout

    def enable_automerge(
        self,
        repo: str,
        pr_number: int,
        strategy: str = "rebase",
        delete_branch: bool = True,
    ) -> tuple[bool, str]:
        """Enable GitHub auto-merge on a pull request."""
        subargs = ["pr", "merge", str(pr_number), "--repo", repo, "--auto"]
        if strategy == "rebase":
            subargs.append("--rebase")
        elif strategy == "squash":
            subargs.append("--squash")
        elif strategy == "merge":
            subargs.append("--merge")

        if delete_branch:
            subargs.append("--delete-branch")

        cmd = self._build_gh_cmd(subargs)
        stdout, stderr, code = self.runner(cmd)
        if code != 0:
            err_msg = stderr.strip() or stdout.strip() or "Unknown error"
            logger.error("Failed to enable auto-merge on PR #%d in %s: %s", pr_number, repo, err_msg)
            return False, err_msg
        return True, stdout.strip()

    def open_in_browser(self, repo: str, pr_number: int) -> bool:
        """Open PR in web browser using gh pr view --web."""
        cmd = self._build_gh_cmd([
            "pr", "view", str(pr_number),
            "--repo", repo,
            "--web",
        ])
        stdout, stderr, code = self.runner(cmd)
        return code == 0

    def list_user_repos(self, limit: int = 30) -> List[str]:
        """Discover user's owned repositories."""
        cmd = self._build_gh_cmd([
            "repo", "list",
            "--limit", str(limit),
            "--json", "nameWithOwner",
        ])
        stdout, stderr, code = self.runner(cmd)
        if code != 0:
            logger.error("Failed to discover repos: %s", stderr.strip())
            return []
        try:
            items = json.loads(stdout)
            return [item["nameWithOwner"] for item in items if "nameWithOwner" in item]
        except json.JSONDecodeError:
            return []
