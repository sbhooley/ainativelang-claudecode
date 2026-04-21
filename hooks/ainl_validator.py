#!/usr/bin/env python3
"""AINL auto-validation hook for Claude Code.

Automatically validates .ainl files after tool use (Read/Edit/Write).
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Try to import AINL tools
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from mcp_server.ainl_tools import AINLTools, _HAS_AINL
except ImportError:
    _HAS_AINL = False


class AINLValidator:
    """Auto-validates .ainl files."""

    def __init__(self):
        self.tools = AINLTools() if _HAS_AINL else None

    def should_validate(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Check if we should validate based on event.

        Returns:
            File path if should validate, None otherwise
        """
        # Check tool name
        tool_name = event.get("toolName", "")
        if tool_name not in ["Read", "Edit", "Write"]:
            return None

        # Check for .ainl file
        tool_input = event.get("toolInput", {})

        # Read/Edit: check file_path
        file_path = tool_input.get("file_path")
        if file_path and file_path.endswith(".ainl"):
            return file_path

        # Write: check file_path
        file_path = tool_input.get("file_path")
        if file_path and file_path.endswith(".ainl"):
            return file_path

        return None

    def validate_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Validate .ainl file and return diagnostics.

        Returns:
            Validation result or None if can't validate
        """
        if not self.tools:
            return None

        try:
            # Read file
            with open(file_path, 'r') as f:
                source = f.read()

            # Validate with strict mode
            result = self.tools.validate(source, strict=True)

            return result

        except FileNotFoundError:
            return None
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {e}"
            }

    def format_validation_output(
        self,
        file_path: str,
        validation: Dict[str, Any]
    ) -> str:
        """Format validation results as markdown."""

        if validation.get("valid"):
            return f"""
**AINL Validation:** ✅ {Path(file_path).name}

{validation.get('message', 'Valid')}

**Next steps:** {', '.join(validation.get('recommended_next_tools', []))}
"""

        # Validation failed
        diagnostics = validation.get("diagnostics", [])
        primary = validation.get("primary_diagnostic")

        output = f"""
**AINL Validation:** ❌ {Path(file_path).name}

"""

        if primary:
            output += f"**Error:** {primary.get('message', 'Unknown error')}\n"
            if "line" in primary:
                output += f"**Line:** {primary['line']}\n"
            output += "\n"

        repair_steps = validation.get("agent_repair_steps", [])
        if repair_steps:
            output += "**How to fix:**\n"
            for step in repair_steps:
                output += f"- {step}\n"
            output += "\n"

        if len(diagnostics) > 1:
            output += f"\n**{len(diagnostics) - 1} additional issue(s)**\n"

        resources = validation.get("recommended_resources", [])
        if resources:
            output += f"\n**Resources:** {', '.join(resources)}\n"

        return output


def main():
    """Hook entry point for PostToolUse."""
    if not _HAS_AINL:
        # Silently skip if AINL not installed
        return

    try:
        # Read event from stdin
        event = json.loads(sys.stdin.read())

        validator = AINLValidator()

        # Check if we should validate
        file_path = validator.should_validate(event)
        if not file_path:
            return

        # Validate
        validation = validator.validate_file(file_path)
        if not validation:
            return

        # Format output
        output_text = validator.format_validation_output(file_path, validation)

        # Output as context injection
        output = {
            "contextInjection": {
                "priority": "high",
                "content": output_text,
                "metadata": {
                    "source": "ainl_validator",
                    "file": file_path,
                    "valid": validation.get("valid", False)
                }
            }
        }

        print(json.dumps(output))

    except Exception as e:
        # Silent failure
        sys.stderr.write(f"AINL validator error: {e}\n")
        pass


if __name__ == "__main__":
    main()
