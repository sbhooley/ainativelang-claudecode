"""Tests for AINL MCP tools integration."""
import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.ainl_tools import AINLTools, _HAS_AINL


# Skip all tests if AINL not installed
pytestmark = pytest.mark.skipif(
    not _HAS_AINL,
    reason="ainativelang package not installed"
)


@pytest.fixture
def ainl_tools():
    """Create AINLTools instance."""
    return AINLTools()


@pytest.fixture
def simple_ainl_source():
    """Simple valid AINL source."""
    return """
S app core noop

L1:
  R core.ADD 2 3 ->sum
  J sum
"""


@pytest.fixture
def compact_ainl_source():
    """Compact syntax AINL source."""
    return """
# Simple adder
adder:
  result = core.ADD 2 3
  out result
"""


class TestValidate:
    """Test ainl_validate functionality."""

    def test_validate_success(self, ainl_tools, simple_ainl_source):
        """Test successful validation."""
        result = ainl_tools.validate(simple_ainl_source, strict=True)

        assert result["valid"] is True
        assert "message" in result
        assert result["diagnostics"] == []
        assert "recommended_next_tools" in result

    def test_validate_failure(self, ainl_tools):
        """Test validation failure."""
        invalid_source = """
S app core noop

L1:
  R unknown.VERB arg ->result
  J result
"""
        result = ainl_tools.validate(invalid_source, strict=True)

        assert result["valid"] is False
        assert len(result.get("diagnostics", [])) > 0
        assert "agent_repair_steps" in result

    def test_validate_compact_syntax(self, ainl_tools, compact_ainl_source):
        """Test validation of compact syntax."""
        result = ainl_tools.validate(compact_ainl_source, strict=True)

        # Note: May depend on preprocessor availability
        assert "valid" in result


class TestCompile:
    """Test ainl_compile functionality."""

    def test_compile_success(self, ainl_tools, simple_ainl_source):
        """Test successful compilation."""
        result = ainl_tools.compile(simple_ainl_source, strict=True)

        assert result["ok"] is True
        assert "ir" in result
        assert "runtime_version" in result
        assert "labels" in result["ir"]

    def test_compile_with_frame_hints(self, ainl_tools):
        """Test frame hints extraction."""
        source = """
# frame: api_key: string
# frame: count: number

S app core noop

L1:
  R core.ADD 2 3 ->sum
  J sum
"""
        result = ainl_tools.compile(source, strict=True)

        assert result["ok"] is True
        assert "frame_hints" in result
        hints = result["frame_hints"]
        assert len(hints) == 2
        assert hints[0]["name"] == "api_key"
        assert hints[0]["type"] == "string"
        assert hints[1]["name"] == "count"
        assert hints[1]["type"] == "number"

    def test_compile_failure(self, ainl_tools):
        """Test compilation failure."""
        invalid_source = "INVALID AINL"

        result = ainl_tools.compile(invalid_source, strict=True)

        assert result["ok"] is False
        assert "error" in result


class TestRun:
    """Test ainl_run functionality."""

    def test_run_success(self, ainl_tools, simple_ainl_source):
        """Test successful execution."""
        result = ainl_tools.run(simple_ainl_source)

        assert result["ok"] is True
        assert result["result"] == 5
        assert "stats" in result

    def test_run_with_frame(self, ainl_tools):
        """Test execution with frame variables."""
        source = """
S app core noop

L1:
  R core.ADD x y ->sum
  J sum
"""
        result = ainl_tools.run(
            source,
            frame={"x": 10, "y": 20}
        )

        assert result["ok"] is True
        assert result["result"] == 30

    def test_run_with_http_adapter(self, ainl_tools):
        """Test execution with HTTP adapter (mocked)."""
        source = """
S app core noop

L1:
  R core.ADD 1 1 ->result
  J result
"""
        result = ainl_tools.run(
            source,
            adapters={
                "enable": ["http"],
                "http": {
                    "allow_hosts": ["example.com"],
                    "timeout_s": 30
                }
            }
        )

        # Should succeed even though we don't use HTTP
        assert result["ok"] is True

    def test_run_failure(self, ainl_tools):
        """Test execution failure."""
        invalid_source = """
S app core noop

L1:
  R nonexistent.OP arg ->result
  J result
"""
        result = ainl_tools.run(invalid_source)

        assert result["ok"] is False
        assert "error" in result


class TestCapabilities:
    """Test ainl_capabilities functionality."""

    def test_capabilities(self, ainl_tools):
        """Test capabilities listing."""
        result = ainl_tools.capabilities()

        assert "runtime_version" in result
        assert "adapters" in result
        assert "core" in result["adapters"]
        assert "http" in result["adapters"]


class TestSecurityReport:
    """Test ainl_security_report functionality."""

    def test_security_report(self, ainl_tools, simple_ainl_source):
        """Test security analysis."""
        result = ainl_tools.security_report(simple_ainl_source)

        assert result["ok"] is True
        assert "report" in result
        assert "summary" in result


class TestIRDiff:
    """Test ainl_ir_diff functionality."""

    def test_ir_diff(self, ainl_tools):
        """Test IR diff."""
        source_a = """
S app core noop

L1:
  R core.ADD 2 3 ->sum
  J sum
"""
        source_b = """
S app core noop

L1:
  R core.ADD 5 7 ->sum
  J sum
"""
        result = ainl_tools.ir_diff(source_a, source_b)

        assert result["ok"] is True
        assert "diff" in result
        assert "summary" in result


class TestHelpers:
    """Test helper methods."""

    def test_extract_frame_hints(self, ainl_tools):
        """Test frame hints extraction."""
        source = """
# frame: api_key: string
# frame: count: number
# frame: flag

L1:
  R core.ADD 1 1 ->x
  J x
"""
        hints = ainl_tools._extract_frame_hints(source, {})

        assert len(hints) == 3
        assert hints[0] == {"name": "api_key", "type": "string", "source": "comment"}
        assert hints[1] == {"name": "count", "type": "number", "source": "comment"}
        assert hints[2] == {"name": "flag", "type": "any", "source": "comment"}

    def test_get_repair_steps(self, ainl_tools):
        """Test repair steps generation."""
        diagnostic = {
            "kind": "unknown_adapter_verb",
            "message": "unknown adapter 'httP'"
        }

        steps = ainl_tools._get_repair_steps(diagnostic)

        assert len(steps) > 0
        assert any("capabilities" in step.lower() for step in steps)
