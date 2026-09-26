"""CLI Table formatting and rendering for PR evaluations."""

import io
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def create_confidence_bar(confidence: float, width: int = 10) -> str:
    """Create a visual text bar representing confidence percentage."""
    filled = int(round(confidence * width))
    filled = max(0, min(width, filled))
    empty = width - filled
    return f"[{'=' * filled}{' ' * empty}]"


def render_report_table(
    evaluations: List[Dict[str, Any]],
    console: Optional[Console] = None,
) -> Table:
    """Construct a rich Table from evaluation results."""
    table = Table(
        title="Pull Request Merge Confidence Report",
        header_style="bold magenta",
        show_lines=True,
    )

    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("PR", style="bold white", justify="right")
    table.add_column("Title", style="white", max_width=40)
    table.add_column("CI Status", justify="center")
    table.add_column("Decision", justify="center")
    table.add_column("Confidence", justify="right")
    table.add_column("Confidence Bar", justify="left")
    table.add_column("Details", style="dim", max_width=35)

    for item in evaluations:
        repo = item.get("repo", "-")
        pr_id = f"#{item.get('pr_number', 0)}"
        title = item.get("title", "")
        ci_raw = item.get("ci_status", "UNKNOWN")
        decision = item.get("decision", "needs_review")
        conf = float(item.get("confidence", 0.0))
        details = item.get("details") or item.get("rationale") or ""

        # Format CI style
        if "PASSED" in ci_raw:
            ci_text = Text("PASS", style="bold green")
        elif "FAILED" in ci_raw:
            ci_text = Text("FAIL", style="bold red")
        elif "PENDING" in ci_raw:
            ci_text = Text("PEND", style="yellow")
        else:
            ci_text = Text("NONE", style="dim")

        # Format Decision style
        if decision == "merge_ready":
            decision_text = Text("MERGE READY", style="bold green")
            bar_color = "green"
        elif decision == "blocked":
            decision_text = Text("BLOCKED", style="bold red")
            bar_color = "red"
        else:
            decision_text = Text("NEEDS REVIEW", style="bold yellow")
            bar_color = "yellow"

        pct_text = f"{int(round(conf * 100))}%"
        bar_text = Text(create_confidence_bar(conf), style=bar_color)

        if decision == "blocked" and details:
            details_text = Text(details, style="bold red")
        elif details:
            details_text = Text(details, style="dim")
        else:
            details_text = Text("-", style="dim")

        table.add_row(
            repo,
            pr_id,
            title,
            ci_text,
            decision_text,
            pct_text,
            bar_text,
            details_text,
        )

    if console is not None:
        console.print(table)

    return table


def render_to_string(evaluations: List[Dict[str, Any]], width: int = 160) -> str:
    """Render table to a string (useful for testing and captures)."""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, color_system=None, width=width)
    render_report_table(evaluations, console=console)
    return buf.getvalue()


def render_pr_card(
    eval_data: Dict[str, Any],
    console: Optional[Console] = None,
) -> Panel:
    """Construct and optionally print a rich Panel summarizing a single PR evaluation."""
    repo = eval_data.get("repo", "-")
    pr_id = f"#{eval_data.get('pr_number', 0)}"
    title = eval_data.get("title", "")
    ci_raw = str(eval_data.get("ci_status", "UNKNOWN"))
    decision = eval_data.get("decision", "needs_review")
    conf = float(eval_data.get("confidence", 0.0))
    details = eval_data.get("details") or eval_data.get("rationale") or ""

    # Format CI style
    if "PASSED" in ci_raw:
        ci_text = Text("PASS", style="bold green")
    elif "FAILED" in ci_raw:
        ci_text = Text("FAIL", style="bold red")
    elif "PENDING" in ci_raw:
        ci_text = Text("PEND", style="yellow")
    else:
        ci_text = Text("NONE", style="dim")

    # Format Decision style
    if decision == "merge_ready":
        dec_text = Text("MERGE READY", style="bold green")
        border_style = "green"
        bar_color = "green"
    elif decision == "blocked":
        dec_text = Text("BLOCKED", style="bold red")
        border_style = "red"
        bar_color = "red"
    else:
        dec_text = Text("NEEDS REVIEW", style="bold yellow")
        border_style = "yellow"
        bar_color = "yellow"

    pct_str = f"{int(round(conf * 100))}%"
    bar_str = create_confidence_bar(conf)
    conf_text = Text(f"{pct_str} {bar_str}", style=bar_color)

    content = Text()
    content.append("CI: ")
    content.append_text(ci_text)
    content.append("    Decision: ")
    content.append_text(dec_text)
    content.append("    Confidence: ")
    content.append_text(conf_text)

    if details:
        content.append("\nReason: ")
        if decision == "blocked":
            content.append(details, style="bold red")
        else:
            content.append(details, style="dim")

    header = f"{repo}{pr_id}: {title}" if title else f"{repo}{pr_id}"
    panel = Panel(
        content,
        title=f"[bold]{header}[/bold]",
        title_align="left",
        border_style=border_style,
    )

    if console is not None:
        console.print(panel)

    return panel


def print_pr_card(eval_data: Dict[str, Any], console: Console) -> None:
    """Print PR evaluation card to the console."""
    render_pr_card(eval_data, console=console)

