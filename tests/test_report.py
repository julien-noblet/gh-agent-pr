from io import StringIO
from rich.console import Console
from gh_agent_pr.report import (
    create_confidence_bar,
    render_report_table,
    render_to_string,
    render_pr_card,
    print_pr_card,
)


def test_confidence_bar():
    assert create_confidence_bar(1.0) == "[==========]"
    assert create_confidence_bar(0.0) == "[          ]"
    assert create_confidence_bar(0.5) == "[=====     ]"


def test_render_report_table():
    sample_evals = [
        {
            "repo": "user/api",
            "pr_number": 42,
            "title": "fix: null check in auth",
            "ci_status": "PASSED (3/3 checks successful)",
            "decision": "merge_ready",
            "confidence": 0.94,
            "details": "Routine update",
        },
        {
            "repo": "user/web",
            "pr_number": 105,
            "title": "feat: complex redesign",
            "ci_status": "FAILED (1 failed)",
            "decision": "blocked",
            "confidence": 0.99,
            "details": "TypeError: Cannot read properties of undefined (reading 'Cjs')",
        }
    ]

    out = render_to_string(sample_evals)
    assert "Pull Request Merge Confidence Report" in out
    assert "user/api" in out
    assert "#42" in out
    assert "fix: null check in auth" in out
    assert "MERGE READY" in out
    assert "94%" in out
    assert "user/web" in out
    assert "#105" in out
    assert "BLOCKED" in out
    assert "TypeError: Cannot read properties" in out
    assert "Details" in out


def test_render_pr_card_merge_ready():
    eval_item = {
        "repo": "org/repo",
        "pr_number": 123,
        "title": "Fix memory leak",
        "ci_status": "PASSED (2/2)",
        "decision": "merge_ready",
        "confidence": 0.98,
        "details": "",
    }
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, color_system=None, width=100)
    print_pr_card(eval_item, console=console)
    output = buf.getvalue()
    assert "org/repo#123: Fix memory leak" in output
    assert "CI: PASS" in output
    assert "Decision: MERGE READY" in output
    assert "Confidence: 98%" in output


def test_render_pr_card_blocked_with_reason():
    eval_item = {
        "repo": "org/repo",
        "pr_number": 456,
        "title": "Break build",
        "ci_status": "FAILED (1 failed)",
        "decision": "blocked",
        "confidence": 0.99,
        "details": "SyntaxError: Unexpected token",
    }
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, color_system=None, width=100)
    render_pr_card(eval_item, console=console)
    output = buf.getvalue()
    assert "org/repo#456: Break build" in output
    assert "CI: FAIL" in output
    assert "Decision: BLOCKED" in output
    assert "Confidence: 99%" in output
    assert "Reason: SyntaxError: Unexpected token" in output

