#!/usr/bin/env python3
"""
PreCompact Hook - Save Session State

Saves active session state before context compaction.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.project_id import get_project_id
from shared.logger import log_event, get_logger

logger = get_logger("pre_compact")


def main():
    try:
        input_data = json.load(sys.stdin)
        project_id = get_project_id()

        log_event("pre_compact", {"project_id": project_id})

        # TODO: Implement state persistence when needed
        logger.debug("PreCompact hook executed")

        print(json.dumps({}), file=sys.stdout)
    except Exception as e:
        logger.error(f"PreCompact error: {e}")
        print(json.dumps({}), file=sys.stdout)
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
