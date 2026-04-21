"""Tests for AINL pattern memory."""
import pytest
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.ainl_patterns import AINLPatternStore


@pytest.fixture
def temp_db():
    """Create temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def pattern_store(temp_db):
    """Create pattern store with temp DB."""
    return AINLPatternStore(db_path=temp_db)


@pytest.fixture
def sample_ainl_source():
    """Sample AINL source."""
    return """
# Monitor workflow
health_monitor @cron "*/5 * * * *":
  response = http.GET health_url {} 10
  status = core.GET response "status"

  if status != "healthy":
    http.POST alert_webhook {text: "Alert!"}
    out {alerted: true}

  out {ok: true}
"""


class TestPatternExtraction:
    """Test pattern extraction and storage."""

    def test_extract_pattern(self, pattern_store, sample_ainl_source):
        """Test extracting a pattern."""
        pattern_id = pattern_store.extract_pattern(
            ainl_source=sample_ainl_source,
            description="Health monitoring workflow",
            pattern_type="monitor",
            success=True
        )

        assert isinstance(pattern_id, str)
        assert len(pattern_id) == 16  # SHA256 hash truncated

        # Verify pattern stored
        pattern = pattern_store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["pattern_type"] == "monitor"
        assert pattern["fitness_score"] == 1.0
        assert pattern["uses"] == 1

    def test_extract_duplicate_pattern(self, pattern_store, sample_ainl_source):
        """Test extracting same pattern twice."""
        # First extraction
        id1 = pattern_store.extract_pattern(
            ainl_source=sample_ainl_source,
            description="Monitor",
            pattern_type="monitor",
            success=True
        )

        # Second extraction (same source)
        id2 = pattern_store.extract_pattern(
            ainl_source=sample_ainl_source,
            description="Monitor",
            pattern_type="monitor",
            success=True
        )

        # Should be same pattern ID
        assert id1 == id2

        # Uses should increment
        pattern = pattern_store.get_pattern(id1)
        assert pattern["uses"] == 2
        assert pattern["successes"] == 2

    def test_pattern_with_failure(self, pattern_store, sample_ainl_source):
        """Test pattern with failed execution."""
        pattern_id = pattern_store.extract_pattern(
            ainl_source=sample_ainl_source,
            description="Failing workflow",
            pattern_type="monitor",
            success=False
        )

        pattern = pattern_store.get_pattern(pattern_id)
        assert pattern["fitness_score"] == 0.5  # Initial failure
        assert pattern["failures"] == 1


class TestFitnessScore:
    """Test fitness score calculations."""

    def test_fitness_increases_with_success(self, pattern_store, sample_ainl_source):
        """Test fitness score increases with successes."""
        # Initial with failure
        pattern_id = pattern_store.extract_pattern(
            sample_ainl_source, "Test", "general", success=False
        )

        initial_fitness = pattern_store.get_pattern(pattern_id)["fitness_score"]

        # Add successes
        for _ in range(5):
            pattern_store.update_fitness(pattern_id, success=True)

        final_fitness = pattern_store.get_pattern(pattern_id)["fitness_score"]

        assert final_fitness > initial_fitness

    def test_fitness_decreases_with_failure(self, pattern_store, sample_ainl_source):
        """Test fitness score decreases with failures."""
        # Initial success
        pattern_id = pattern_store.extract_pattern(
            sample_ainl_source, "Test", "general", success=True
        )

        initial_fitness = pattern_store.get_pattern(pattern_id)["fitness_score"]

        # Add failures
        for _ in range(3):
            pattern_store.update_fitness(pattern_id, success=False)

        final_fitness = pattern_store.get_pattern(pattern_id)["fitness_score"]

        assert final_fitness < initial_fitness


class TestPatternRecall:
    """Test pattern recall and search."""

    def test_recall_by_description(self, pattern_store):
        """Test recalling patterns by description."""
        # Add some patterns
        pattern_store.extract_pattern(
            "L1:\n  R http.GET url ->r\n  J r",
            "API health monitor",
            "monitor",
            success=True
        )

        pattern_store.extract_pattern(
            "L1:\n  R solana.GET_BALANCE addr ->b\n  J b",
            "Blockchain balance checker",
            "blockchain_monitor",
            success=True
        )

        # Recall health-related patterns
        results = pattern_store.recall_similar("health monitor")

        assert len(results) > 0
        assert any("health" in r["description"].lower() for r in results)

    def test_recall_with_type_filter(self, pattern_store):
        """Test recalling with pattern type filter."""
        # Add patterns of different types
        pattern_store.extract_pattern(
            "L1:\n  R http.GET url ->r\n  J r",
            "Monitor",
            "monitor",
            success=True
        )

        pattern_store.extract_pattern(
            "L1:\n  R http.POST url data ->r\n  J r",
            "API workflow",
            "api_workflow",
            success=True
        )

        # Recall only monitors
        results = pattern_store.recall_similar(
            "workflow",
            pattern_type="monitor"
        )

        # Should only return monitor patterns
        for r in results:
            assert r["pattern_type"] == "monitor"

    def test_recall_with_min_fitness(self, pattern_store):
        """Test recalling with minimum fitness filter."""
        # Add pattern with low fitness
        id1 = pattern_store.extract_pattern(
            "L1:\n  R core.ADD 1 1 ->r\n  J r",
            "Low quality",
            "general",
            success=False
        )

        # Add pattern with high fitness
        id2 = pattern_store.extract_pattern(
            "L1:\n  R core.SUB 2 1 ->r\n  J r",
            "High quality",
            "general",
            success=True
        )

        # Recall with high fitness threshold
        results = pattern_store.recall_similar(
            "quality",
            min_fitness=0.8
        )

        # Should only include high-fitness pattern
        ids = [r["id"] for r in results]
        assert id2 in ids
        assert id1 not in ids


class TestListPatterns:
    """Test pattern listing."""

    def test_list_all_patterns(self, pattern_store):
        """Test listing all patterns."""
        # Add some patterns
        for i in range(3):
            pattern_store.extract_pattern(
                f"L1:\n  R core.ADD {i} 1 ->r\n  J r",
                f"Pattern {i}",
                "general",
                success=True
            )

        results = pattern_store.list_patterns()

        assert len(results) == 3

    def test_list_by_type(self, pattern_store):
        """Test listing by pattern type."""
        pattern_store.extract_pattern(
            "L1:\n  R http.GET url ->r\n  J r",
            "Monitor",
            "monitor",
            success=True
        )

        pattern_store.extract_pattern(
            "L1:\n  R http.POST url data ->r\n  J r",
            "Workflow",
            "api_workflow",
            success=True
        )

        results = pattern_store.list_patterns(pattern_type="monitor")

        assert len(results) == 1
        assert results[0]["pattern_type"] == "monitor"

    def test_list_sorted_by_fitness(self, pattern_store):
        """Test patterns sorted by fitness."""
        # Add patterns with different fitness
        id1 = pattern_store.extract_pattern(
            "L1:\n  R core.ADD 1 1 ->r\n  J r",
            "Low",
            "general",
            success=False
        )

        id2 = pattern_store.extract_pattern(
            "L1:\n  R core.SUB 2 1 ->r\n  J r",
            "High",
            "general",
            success=True
        )

        results = pattern_store.list_patterns()

        # Should be sorted by fitness (descending)
        assert results[0]["fitness_score"] >= results[-1]["fitness_score"]


class TestHelperMethods:
    """Test helper methods."""

    def test_extract_adapters(self, pattern_store):
        """Test adapter extraction."""
        source = """
L1:
  R http.GET url ->r1
  R core.ADD 1 2 ->r2
  R solana.GET_BALANCE addr ->r3
  J r3
"""
        adapters = pattern_store._extract_adapters(source)

        assert "http" in adapters
        assert "core" in adapters
        assert "solana" in adapters
        assert len(adapters) == 3

    def test_extract_tags(self, pattern_store):
        """Test tag extraction."""
        description = "Health monitor with API calls"
        source = "R http.GET url\nL1 @cron"

        tags = pattern_store._extract_tags(description, source)

        assert "monitor" in tags
        assert "api" in tags
        assert "cron" in tags
