import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional

IGNORED_DIFF_PATTERNS = [
    r"package-lock\.json",
    r"pnpm-lock\.yaml",
    r"yarn\.lock",
    r"bun\.lockb?",
    r"Cargo\.lock",
    r"poetry\.lock",
    r"go\.sum",
    r"\.min\.(js|css)",
    r"\.(svg|png|jpg|jpeg|gif|ico|webp)$",
]

TEST_PATH_PATTERNS = [
    r"(^|/)(test|tests)/",
    r"(_|-)test\.",
    r"\.test\.",
    r"(_|-)spec\.",
    r"\.spec\.",
    r"test_.*\.py$",
]

CODE_FILE_EXTENSIONS = {
    ".py", ".ts", ".js", ".jsx", ".tsx", ".rs", ".go", ".c", ".cpp", ".h", ".hpp",
    ".java", ".kt", ".scala", ".rb", ".php", ".cs", ".swift", ".sh", ".bash", ".zsh"
}

KNOWN_BOT_PATTERNS = [
    r"renovate",
    r"dependabot",
    r"imgbot",
    r"github-actions",
    r"\[bot\]",
    r"bot$",
]


def is_bot_author(author: str) -> bool:
    """Detect if PR author is an automated bot."""
    if not author:
        return False
    return any(re.search(pat, author, re.IGNORECASE) for pat in KNOWN_BOT_PATTERNS)


def classify_files(paths: List[str]) -> Tuple[bool, bool]:
    """Return (has_code_files, only_config_or_docs)."""
    if not paths:
        return False, False
    has_code = False
    for p in paths:
        ext = ("." + p.split(".")[-1].lower()) if "." in p else ""
        if ext in CODE_FILE_EXTENSIONS:
            has_code = True
            break
    return has_code, not has_code


def summarize_ci(status_rollup: Any) -> str:
    """Summarize CI status from statusCheckRollup list."""
    if not status_rollup or not isinstance(status_rollup, list):
        return "UNKNOWN / NO CHECKS"

    total = len(status_rollup)
    failed = []
    pending = []
    success_count = 0

    for check in status_rollup:
        if not isinstance(check, dict):
            continue
        name = check.get("name") or check.get("context", "check")
        status = check.get("status", "")
        conclusion = check.get("conclusion", "")

        if conclusion in ("FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "CANCELLED"):
            failed.append(name)
        elif status in ("IN_PROGRESS", "QUEUED", "PENDING") or conclusion == "PENDING":
            pending.append(name)
        elif conclusion in ("SUCCESS", "NEUTRAL", "SKIPPED"):
            success_count += 1

    if failed:
        return f"FAILED ({len(failed)} failed: {', '.join(failed[:3])})"
    if pending:
        return f"PENDING ({len(pending)} in progress, {success_count} passed)"
    if success_count > 0:
        return f"PASSED ({success_count}/{total} checks successful)"
    return "UNKNOWN"


def extract_failed_run_ids(status_rollup: Any) -> List[int]:
    """Extract GitHub Actions workflow run IDs from failed checks."""
    if not status_rollup or not isinstance(status_rollup, list):
        return []

    run_ids: List[int] = []
    for check in status_rollup:
        if not isinstance(check, dict):
            continue
        status = check.get("status", "")
        conclusion = check.get("conclusion", "")
        if conclusion in ("FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "CANCELLED", "STARTUP_FAILURE") or (
            status == "COMPLETED" and conclusion not in ("SUCCESS", "NEUTRAL", "SKIPPED", "")
        ):
            details_url = check.get("detailsUrl") or check.get("details_url") or check.get("target_url") or ""
            match = re.search(r"/actions/runs/(\d+)", details_url)
            if match:
                run_id = int(match.group(1))
                if run_id not in run_ids:
                    run_ids.append(run_id)
    return run_ids


def extract_failure_reason(log_text: str) -> str:
    """Parse failed step log to extract the concise root-cause error message."""
    if not log_text or not log_text.strip():
        return ""

    lines = log_text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        line = re.sub(r"^[^\t]+\t[^\t]+\t\d{4}-\d{2}-\d{2}T[0-9:.]+Z\s*", "", line)
        line = re.sub(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z\s*", "", line).strip()
        if line:
            cleaned_lines.append(line)

    if not cleaned_lines:
        return ""

    # Priority 1: Specific language/compiler/runtime errors
    specific_patterns = [
        r"^(?:(?:[A-Z][a-zA-Z]+)?Error|Exception|panic|fatal|error\[E\d+\]|TS\d+:)\b.*",
        r"^(?:FAIL|FAILED)\s+.*",
        r"^(?:SyntaxError|TypeError|ReferenceError|AssertionError|ImportError|RuntimeError)\b.*",
    ]
    for line in reversed(cleaned_lines):
        for pat in specific_patterns:
            if re.search(pat, line):
                clean = re.sub(r"^##\[error\]\s*", "", line).strip()
                if "Process completed with exit code" not in clean:
                    return clean[:120]

    # Priority 2: Any ##[error] lines that aren't generic exit codes
    for line in reversed(cleaned_lines):
        if line.startswith("##[error]"):
            clean = re.sub(r"^##\[error\]\s*", "", line).strip()
            if "Process completed with exit code" not in clean:
                return clean[:120]

    # Priority 3: Exit code or command failures
    for line in reversed(cleaned_lines):
        if re.search(r"(?:Process completed with exit code|failed with exit code|command .* failed)", line, re.IGNORECASE):
            clean = re.sub(r"^##\[error\]\s*", "", line).strip()
            return clean[:120]

    # Priority 4: Fallback to last non-empty line
    return cleaned_lines[-1][:120]


def summarize_reviews(reviews: Any) -> str:
    """Summarize pull request reviews."""
    if not reviews or not isinstance(reviews, list):
        return "NO REVIEWS"

    states = [r.get("state") for r in reviews if isinstance(r, dict) and "state" in r]
    if "CHANGES_REQUESTED" in states:
        return "CHANGES REQUESTED"
    if "APPROVED" in states:
        approvals = states.count("APPROVED")
        return f"APPROVED ({approvals} approval{'s' if approvals > 1 else ''})"
    return "PENDING / COMMENTED"


def filter_diff(diff: str, max_chars: int = 2500) -> str:
    """Filter out noise (lockfiles, assets) and truncate diff."""
    if not diff:
        return "(No diff available)"

    chunks = diff.split("diff --git ")
    filtered_chunks = []

    for chunk in chunks:
        if not chunk.strip():
            continue
        first_line = chunk.split("\n", 1)[0]
        is_ignored = any(re.search(pat, first_line, re.IGNORECASE) for pat in IGNORED_DIFF_PATTERNS)
        if not is_ignored:
            filtered_chunks.append("diff --git " + chunk)

    reconstructed = "\n".join(filtered_chunks)
    if len(reconstructed) > max_chars:
        return reconstructed[:max_chars] + "\n... [diff truncated for length]"
    return reconstructed


def analyze_files(files: List[Dict[str, Any]]) -> Tuple[List[str], bool, int, int]:
    """Extract touched paths, presence of tests, additions, deletions."""
    paths = []
    has_tests = False
    additions = 0
    deletions = 0

    for f in files:
        path = f.get("path", "")
        paths.append(path)
        additions += f.get("additions", 0)
        deletions += f.get("deletions", 0)
        if any(re.search(pat, path, re.IGNORECASE) for pat in TEST_PATH_PATTERNS):
            has_tests = True

    return paths, has_tests, additions, deletions


@dataclass
class PRSummary:
    number: int
    title: str
    author: str
    mergeable: str
    ci_status: str
    reviews: str
    context: str
    failed_run_ids: List[int] = field(default_factory=list)
    ci_failure_reason: Optional[str] = None


def build_pr_context(
    pr_data: Dict[str, Any],
    raw_diff: str = "",
    max_diff_chars: int = 2500,
    failure_reason: Optional[str] = None,
) -> str:
    """Build a compact and informative textual state for Laya decision engine."""
    number = pr_data.get("number", 0)
    title = pr_data.get("title", "Untitled")
    body = (pr_data.get("body") or "").strip()
    author = pr_data.get("author", {}).get("login", "unknown")
    mergeable = pr_data.get("mergeable", "UNKNOWN")
    files = pr_data.get("files", [])

    paths, has_tests, additions, deletions = analyze_files(files)
    _, only_config_or_docs = classify_files(paths)
    is_bot = is_bot_author(author)

    ci_summary = summarize_ci(pr_data.get("statusCheckRollup", []))
    review_summary = summarize_reviews(pr_data.get("reviews", []))
    diff_excerpt = filter_diff(raw_diff, max_chars=max_diff_chars)

    # Format test status with nuanced context
    if has_tests:
        test_status = "YES (Tests included in changes)"
    elif only_config_or_docs:
        test_status = "NOT APPLICABLE (Configuration / Documentation / Non-code only)"
    elif is_bot:
        test_status = "NOT APPLICABLE (Automated bot dependency update)"
    else:
        test_status = "NO (Executable code modified without tests)"

    author_display = f"{author} [Automated Bot]" if is_bot else author
    review_display = "NO REVIEWS (Automated bot PR)" if (is_bot and review_summary == "NO REVIEWS") else review_summary

    # Truncate body if very long
    if len(body) > 600:
        body = body[:600] + "... [description truncated]"
    elif not body:
        body = "(No description provided)"

    file_list_str = "\n".join(f"- {p}" for p in paths[:12])
    if len(paths) > 12:
        file_list_str += f"\n- ... and {len(paths) - 12} other files"

    resolved_failure = failure_reason or pr_data.get("ci_failure_reason")
    diagnostics_section = f"\nCI Failure Diagnostics:\n{resolved_failure}\n" if resolved_failure else ""

    context = f"""PULL REQUEST #{number}: {title}
Author: {author_display}
Mergeable: {mergeable}
CI Status: {ci_summary}
Reviews: {review_display}
Files Changed: {len(paths)} (+{additions}, -{deletions})
Tests Status: {test_status}
{diagnostics_section}
Description:
{body}

Modified Files:
{file_list_str or 'None'}

Diff Excerpt:
{diff_excerpt}
"""
    return context.strip()


def distill_pr(
    pr_data: Dict[str, Any],
    raw_diff: str = "",
    failure_log: str = "",
    max_diff_chars: int = 2500,
) -> PRSummary:
    """Distill PR metadata, CI checks, reviews, and logs into a structured PRSummary."""
    number = pr_data.get("number", 0)
    title = pr_data.get("title", "Untitled")
    author = pr_data.get("author", {}).get("login", "unknown")
    mergeable = pr_data.get("mergeable", "UNKNOWN")
    status_rollup = pr_data.get("statusCheckRollup", [])

    ci_status = summarize_ci(status_rollup)
    reviews = summarize_reviews(pr_data.get("reviews", []))
    failed_run_ids = extract_failed_run_ids(status_rollup)

    ci_failure_reason = pr_data.get("ci_failure_reason")
    if not ci_failure_reason and failure_log:
        ci_failure_reason = extract_failure_reason(failure_log)

    context = build_pr_context(
        pr_data=pr_data,
        raw_diff=raw_diff,
        max_diff_chars=max_diff_chars,
        failure_reason=ci_failure_reason,
    )

    return PRSummary(
        number=number,
        title=title,
        author=author,
        mergeable=mergeable,
        ci_status=ci_status,
        reviews=reviews,
        context=context,
        failed_run_ids=failed_run_ids,
        ci_failure_reason=ci_failure_reason,
    )
