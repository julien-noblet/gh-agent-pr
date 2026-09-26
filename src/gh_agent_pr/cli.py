import argparse
import json
import sys
from typing import List, Dict, Any, Optional, Callable
from rich.console import Console
from rich.prompt import Prompt

from gh_agent_pr import __version__
from gh_agent_pr.config import load_config, Config
from gh_agent_pr.github import GitHubClient
from gh_agent_pr.distill import (
    build_pr_context,
    summarize_ci,
    distill_pr,
    extract_failed_run_ids,
)
from gh_agent_pr.scorer import LayaScorer
from gh_agent_pr.report import render_report_table, render_pr_card


def prompt_pr_action(
    repo: str,
    pr_number: int,
    client: GitHubClient,
    console: Console,
) -> str:
    """Prompt user for action on a MERGE READY pull request.
    
    Returns chosen action: 'y' (merge enabled), 'n' (skipped), 'q' (quit).
    """
    while True:
        choice = Prompt.ask(
            f"  [bold yellow]?[/bold yellow] Enable auto-merge (rebase) for [bold]{repo}#{pr_number}[/bold]?",
            choices=["y", "n", "o", "q"],
            default="n",
            console=console,
        ).lower().strip()

        if choice == "y":
            console.print(f"    [dim]Enabling auto-merge (rebase) on {repo}#{pr_number}...[/dim]")
            success, msg = client.enable_automerge(repo, pr_number, strategy="rebase", delete_branch=True)
            if success:
                console.print(f"    [bold green]✓ Auto-merge (rebase) enabled for #{pr_number}[/bold green]")
            else:
                console.print(f"    [bold red]✗ Failed to enable auto-merge: {msg}[/bold red]")
            return "y"
        elif choice == "o":
            console.print(f"    [dim]Opening #{pr_number} in browser...[/dim]")
            client.open_in_browser(repo, pr_number)
            continue
        elif choice == "q":
            console.print("    [dim]Quitting interactive mode...[/dim]")
            return "q"
        else:
            return "n"


def run_pipeline(
    config: Config,
    client: Optional[GitHubClient] = None,
    scorer: Optional[LayaScorer] = None,
    console: Optional[Console] = None,
    prompt_handler: Optional[Callable[[str, int, GitHubClient, Console], str]] = None,
) -> List[Dict[str, Any]]:
    """Execute the discovery, distillation, scoring, and reporting pipeline."""
    client = client or GitHubClient()
    scorer = scorer or LayaScorer(default_model=config.laya_model)
    console = console or Console()

    repos = config.repos
    if not repos:
        console.print("[dim]No repositories specified. Auto-discovering user repositories via rtk gh...[/dim]")
        repos = client.list_user_repos(limit=10)
        if not repos:
            console.print("[bold red]No repositories found or access restricted. Specify via --repo owner/repo.[/bold red]")
            return []

    evaluations: List[Dict[str, Any]] = []
    quit_interactive = False
    is_interactive = config.interactive and (prompt_handler is not None or sys.stdin.isatty())
    if config.interactive and not is_interactive:
        console.print("[yellow]Warning: Standard input is not a terminal. Interactive mode disabled.[/yellow]")

    for repo in repos:
        if quit_interactive:
            break
        console.print(f"[cyan]Scanning repository:[/cyan] [bold]{repo}[/bold]...")
        open_prs = client.list_open_prs(repo, limit=config.limit)
        if not open_prs:
            console.print(f"  [dim]No open PRs found in {repo}[/dim]")
            continue

        for pr in open_prs:
            pr_number = pr.get("number")
            if not pr_number:
                continue

            console.print(f"  Evaluating PR #{pr_number}: {pr.get('title', '')[:50]}...")
            pr_detail = client.view_pr(repo, pr_number) or pr
            diff = client.get_pr_diff(repo, pr_number)

            status_rollup = pr_detail.get("statusCheckRollup", [])
            ci_status = summarize_ci(status_rollup)

            failure_log = ""
            if any(w in ci_status.upper() for w in ("FAILED", "CANCELLED", "ACTION_REQUIRED", "TIMED_OUT")):
                failed_run_ids = extract_failed_run_ids(status_rollup)
                if failed_run_ids and hasattr(client, "get_failed_run_log"):
                    console.print(f"    [dim]Inspecting failed CI log for run {failed_run_ids[0]}...[/dim]")
                    failure_log = client.get_failed_run_log(repo, failed_run_ids[0])

            summary = distill_pr(pr_detail, raw_diff=diff, failure_log=failure_log)
            if hasattr(scorer, "score_pr"):
                result = scorer.score_pr(summary, model=config.laya_model)
            else:
                result = scorer.score_context(summary.context, model=config.laya_model)

            details_str = result.rationale or summary.ci_failure_reason or ""
            eval_item = {
                "repo": repo,
                "pr_number": pr_number,
                "title": pr.get("title", ""),
                "ci_status": summary.ci_status,
                "decision": result.decision,
                "confidence": result.confidence,
                "probabilities": result.probabilities,
                "model": result.model_used,
                "details": details_str,
                "auto_merge": bool(pr_detail.get("autoMergeRequest")),
            }

            if is_interactive:
                render_pr_card(eval_item, console=console)

            action = "n"
            if is_interactive and result.decision == "merge_ready":
                if pr_detail.get("autoMergeRequest"):
                    console.print(f"    [dim cyan]ℹ Auto-merge is already enabled for #{pr_number}[/dim cyan]")
                    action = "already_enabled"
                else:
                    handler = prompt_handler or prompt_pr_action
                    action = handler(repo, pr_number, client, console)

            auto_merge_flag = (action in ("y", "already_enabled")) or bool(pr_detail.get("autoMergeRequest"))
            if not eval_item["details"] and auto_merge_flag:
                eval_item["details"] = "Auto-merge enabled"
            eval_item["auto_merge"] = auto_merge_flag

            evaluations.append(eval_item)

            if action == "q":
                quit_interactive = True
                break

    if evaluations:
        render_report_table(evaluations, console=console)
    else:
        console.print("[yellow]No pull requests evaluated across targeted repositories.[/yellow]")

    return evaluations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="gh-agent-pr: Pull Request merge confidence scoring using rtk gh & Laya System-1 engine."
    )
    parser.add_argument(
        "-r", "--repo",
        action="append",
        dest="cli_repos",
        help="Repository in format owner/repo (can specify multiple times or comma-separated).",
    )
    parser.add_argument(
        "-c", "--config",
        dest="config_path",
        help="Path to YAML configuration file.",
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=None,
        help="Maximum open PRs to query per repository (default: 20).",
    )
    parser.add_argument(
        "-m", "--model",
        dest="laya_model",
        choices=["english", "multilingual"],
        default=None,
        help="Laya model checkpoint (default: english).",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        dest="interactive",
        help="Interactive mode: prompt to enable rebase auto-merge for MERGE READY PRs on the fly.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON array of evaluations.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"gh-agent-pr {__version__}",
    )

    args = parser.parse_args()

    # Flatten any comma-separated repos in --repo
    flattened_repos = []
    if args.cli_repos:
        for r in args.cli_repos:
            for item in r.split(","):
                if item.strip():
                    flattened_repos.append(item.strip())

    config = load_config(
        config_path=args.config_path,
        cli_repos=flattened_repos,
        limit=args.limit,
        laya_model=args.laya_model,
        interactive=args.interactive if args.interactive else None,
    )

    console = Console(stderr=args.json)
    evaluations = run_pipeline(config, console=console)

    if args.json:
        print(json.dumps(evaluations, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
