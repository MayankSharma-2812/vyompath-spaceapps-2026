"""Governance and Privacy Enforcement Tests.

Ensures that private local decision files (e.g. decision.md, DECISION.md,
decisions.md, dheer_decisions.md) are strictly excluded from version control.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def test_no_decision_markdown_files_tracked_in_git():
    """Verify that zero decision markdown files are tracked in version control."""
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = result.stdout.splitlines()

    decision_pattern = re.compile(r".*decision.*\.md$", re.IGNORECASE)
    leaked_decision_files = [
        f for f in tracked_files if decision_pattern.match(f)
    ]

    assert not leaked_decision_files, (
        f"CRITICAL PRIVACY VIOLATION: The following decision files are tracked in Git:\n"
        f"{leaked_decision_files}\n"
        "Decision files are strictly private/local-only and must NEVER be committed to Git. "
        "Remove them using 'git rm --cached <file>'."
    )
