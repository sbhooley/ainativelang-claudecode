"""
Project ID Detection

Stable project identification following AINL pattern.
Priority: git remote → cwd hash
"""

import hashlib
import subprocess
from pathlib import Path
from typing import Optional


def get_project_id(cwd: Optional[Path] = None) -> str:
    """
    Compute stable project ID (matches AINL pattern).

    Args:
        cwd: Working directory (defaults to Path.cwd())

    Returns:
        16-character hex hash
    """
    if cwd is None:
        cwd = Path.cwd()

    # Try git remote first
    try:
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0 and result.stdout.strip():
            remote = result.stdout.strip()
            return hashlib.sha256(remote.encode()).hexdigest()[:16]

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: hash of canonical path
    canonical_path = str(cwd.resolve())
    return hashlib.sha256(canonical_path.encode()).hexdigest()[:16]


def get_project_info(cwd: Optional[Path] = None) -> dict:
    """
    Get extended project information.

    Returns dict with project_id, path, git info, etc.
    """
    if cwd is None:
        cwd = Path.cwd()

    info = {
        "project_id": get_project_id(cwd),
        "path": str(cwd.resolve()),
        "is_git": False,
        "git_remote": None,
        "git_branch": None
    }

    # Try to get git info
    try:
        # Check if git repo
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            cwd=cwd,
            capture_output=True,
            timeout=2
        )

        if result.returncode == 0:
            info["is_git"] = True

            # Get remote
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                info["git_remote"] = result.stdout.strip()

            # Get branch
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                info["git_branch"] = result.stdout.strip()

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return info
