#!/usr/bin/env python3
"""
PostToolUse Hook - Capture Execution

Captures tool outcomes and buffers for MCP server consolidation.
Follows AINL pattern: lightweight capture, async consolidation.
"""

import sys
import json
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from shared.project_id import get_project_id
from shared.logger import log_event, log_error, get_logger

logger = get_logger("post_tool_use")


# Tool canonicalization (matches extractor.py)
TOOL_CANON = {
    'Bash': 'bash', 'Shell': 'bash', 'sh': 'bash',
    'Read': 'read', 'FileRead': 'read',
    'Edit': 'edit', 'FileEdit': 'edit',
    'Write': 'write', 'FileWrite': 'write',
    'Grep': 'grep', 'Search': 'grep',
    'Glob': 'glob',
    'WebSearch': 'web_search',
    'WebFetch': 'web_fetch',
}


def canonicalize_tool(tool_name: str) -> str:
    """Canonicalize tool name"""
    return TOOL_CANON.get(tool_name, tool_name.lower())


def extract_tool_capture(tool: str, tool_input: dict, result: dict) -> dict:
    """
    Extract relevant data from tool execution.

    Returns capture dict ready for buffering.
    """
    capture = {
        "tool": tool,
        "timestamp": int(time.time())
    }

    # Tool-specific extraction
    if tool == 'edit':
        capture['type'] = 'file_edit'
        capture['file'] = tool_input.get('file_path')
        capture['success'] = 'error' not in result

    elif tool == 'write':
        capture['type'] = 'file_write'
        capture['file'] = tool_input.get('file_path')
        capture['success'] = 'error' not in result

    elif tool == 'read':
        capture['type'] = 'file_read'
        capture['file'] = tool_input.get('file_path')
        capture['success'] = True

    elif tool == 'bash':
        capture['type'] = 'command'
        capture['command'] = tool_input.get('command', '')[:200]  # Limit length
        capture['success'] = 'error' not in result

        # Extract error if present
        if not capture['success']:
            error_text = result.get('error', '')
            if error_text:
                capture['error'] = error_text[:500]  # Limit error text

    elif tool == 'grep':
        capture['type'] = 'search'
        capture['pattern'] = tool_input.get('pattern', '')
        capture['success'] = True

    else:
        # Generic capture
        capture['type'] = 'generic'
        capture['success'] = 'error' not in result

    return capture


def buffer_capture(project_id: str, capture: dict) -> None:
    """
    Buffer capture for later consolidation.

    Writes to session inbox file (AINL inbox pattern).
    """
    # Create inbox directory
    inbox_dir = Path.home() / ".claude" / "plugins" / "ainl-graph-memory" / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    inbox_file = inbox_dir / f"{project_id}_captures.jsonl"

    # Append capture as JSON line
    try:
        with open(inbox_file, 'a') as f:
            f.write(json.dumps(capture) + '\n')

        logger.debug(f"Buffered capture: {capture['type']} - {capture['tool']}")

    except Exception as e:
        logger.warning(f"Failed to buffer capture: {e}")
        # Non-fatal - continue


def main():
    """Main hook entry point"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        tool_info = input_data.get('tool', {})
        tool_name = tool_info.get('name', '')
        tool_input = tool_info.get('input', {})
        tool_result = input_data.get('result', {})

        # Get project ID
        project_id = get_project_id()

        # Canonicalize tool name
        canonical_tool = canonicalize_tool(tool_name)

        logger.debug(f"Processing tool: {tool_name} → {canonical_tool}")

        # Extract capture
        capture = extract_tool_capture(canonical_tool, tool_input, tool_result)

        # Add project context
        capture['project_id'] = project_id

        # Buffer for consolidation
        buffer_capture(project_id, capture)

        # Log event
        log_event("post_tool_use", {
            "tool": canonical_tool,
            "project_id": project_id,
            "success": capture.get('success', False),
            "type": capture.get('type')
        })

        # No output needed for this hook
        print(json.dumps({}), file=sys.stdout)

    except Exception as e:
        # Fail gracefully
        log_error("post_tool_use_error", e, {
            "tool": tool_name if 'tool_name' in locals() else None
        })
        print(json.dumps({}), file=sys.stdout)

    finally:
        # Always exit 0
        sys.exit(0)


if __name__ == "__main__":
    main()
