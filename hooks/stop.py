#!/usr/bin/env python3
"""
Stop Hook - Session Finalization

Finalizes session, creates episode node, runs extraction.
Follows AINL pattern: episode write + extraction + persona evolution.
"""

import sys
import json
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from shared.project_id import get_project_id, get_project_info
from shared.logger import log_event, log_error, get_logger

logger = get_logger("stop")


def drain_session_inbox(project_id: str) -> dict:
    """
    Drain buffered captures from inbox.

    Returns session data aggregated from all captures.
    """
    inbox_dir = Path.home() / ".claude" / "plugins" / "ainl-graph-memory" / "inbox"
    inbox_file = inbox_dir / f"{project_id}_captures.jsonl"

    session_data = {
        "tool_captures": [],
        "files_touched": set(),
        "tools_used": set(),
        "had_errors": False
    }

    if not inbox_file.exists():
        logger.debug("No inbox file found")
        return session_data

    try:
        with open(inbox_file, 'r') as f:
            for line in f:
                if line.strip():
                    capture = json.loads(line)
                    session_data["tool_captures"].append(capture)

                    # Aggregate data
                    session_data["tools_used"].add(capture.get("tool", "unknown"))

                    file = capture.get("file")
                    if file:
                        session_data["files_touched"].add(file)

                    if not capture.get("success", True):
                        session_data["had_errors"] = True

        # Clear inbox after reading
        inbox_file.unlink()

        logger.info(f"Drained {len(session_data['tool_captures'])} captures")

    except Exception as e:
        logger.warning(f"Failed to drain inbox: {e}")

    # Convert sets to lists for JSON serialization
    session_data["files_touched"] = list(session_data["files_touched"])
    session_data["tools_used"] = list(session_data["tools_used"])

    return session_data


def create_episode_summary(session_data: dict) -> str:
    """Generate task description summary from session"""
    tools_count = len(session_data["tools_used"])
    files_count = len(session_data["files_touched"])

    # Basic summary
    summary = f"Coding session: {tools_count} tools, {files_count} files"

    # Add specific details
    if session_data["had_errors"]:
        summary += " (encountered errors)"

    return summary


def finalize_session(project_id: str, session_data: dict) -> None:
    """
    Finalize session by creating episode and triggering extraction.

    This would call MCP server in production.
    For now, we just log the intent.
    """
    # TODO: Implement MCP client call when integrated

    task_summary = create_episode_summary(session_data)
    outcome = "partial" if session_data["had_errors"] else "success"

    logger.info(
        f"Would create episode: project={project_id}, "
        f"task={task_summary}, outcome={outcome}"
    )

    # Log structured data for later processing
    log_event("session_finalized", {
        "project_id": project_id,
        "task_summary": task_summary,
        "tools_used": session_data["tools_used"],
        "files_touched": session_data["files_touched"],
        "outcome": outcome,
        "capture_count": len(session_data["tool_captures"])
    })


def main():
    """Main hook entry point"""
    try:
        # Read input (may be empty for Stop hook)
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            input_data = {}

        # Get project info
        project_info = get_project_info()
        project_id = project_info["project_id"]

        logger.info(f"Finalizing session for project {project_id}")

        # Drain session inbox
        session_data = drain_session_inbox(project_id)

        # Finalize if we have meaningful data
        if session_data["tool_captures"]:
            finalize_session(project_id, session_data)
        else:
            logger.debug("No session data to finalize")

        # No output needed
        print(json.dumps({}), file=sys.stdout)

    except Exception as e:
        # Fail gracefully
        log_error("stop_error", e, {
            "project_id": project_id if 'project_id' in locals() else None
        })
        print(json.dumps({}), file=sys.stdout)

    finally:
        # Always exit 0
        sys.exit(0)


if __name__ == "__main__":
    main()
