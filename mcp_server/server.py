#!/usr/bin/env python3
"""
AINL Graph Memory MCP Server

Main MCP stdio server exposing graph memory tools.
Follows MCP protocol for Claude Code integration.
"""

import sys
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio

# Configure logging
log_dir = Path.home() / ".claude" / "plugins" / "ainl-graph-memory" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "mcp_server.log"),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

# Import our modules
try:
    from .graph_store import SQLiteGraphStore
    from .node_types import (
        create_episode_node, create_semantic_node, create_procedural_node,
        create_persona_node, create_failure_node, create_edge,
        NodeType, EdgeType
    )
    from .retrieval import MemoryRetrieval, RetrievalContext
    from .persona_engine import PersonaEvolutionEngine
    from .extractor import PatternExtractor, canonicalize_tool_sequence
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    # Try relative imports for when run as script
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from graph_store import SQLiteGraphStore
    from node_types import (
        create_episode_node, create_semantic_node, create_procedural_node,
        create_persona_node, create_failure_node, create_edge,
        NodeType, EdgeType
    )
    from retrieval import MemoryRetrieval, RetrievalContext
    from persona_engine import PersonaEvolutionEngine
    from extractor import PatternExtractor, canonicalize_tool_sequence


class AINLGraphMemoryServer:
    """
    AINL Graph Memory MCP Server.

    Exposes graph memory operations as MCP tools for Claude Code.
    """

    def __init__(self):
        self.db_path = self._get_db_path()
        self.store = SQLiteGraphStore(self.db_path)
        self.retrieval = MemoryRetrieval(self.store)
        self.persona_engine = PersonaEvolutionEngine()
        self.extractor = PatternExtractor()

        logger.info(f"AINL Graph Memory Server initialized with DB: {self.db_path}")

    def _get_db_path(self) -> Path:
        """Get database path (project-specific if possible)"""
        # Try to detect project from CWD
        cwd = Path.cwd()

        # Check if we have a project-specific path
        project_hash = self._compute_project_hash(cwd)

        memory_dir = Path.home() / ".claude" / "projects" / project_hash / "graph_memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        return memory_dir / "ainl_memory.db"

    def _compute_project_hash(self, cwd: Path) -> str:
        """Compute stable project hash"""
        import hashlib
        import subprocess

        try:
            # Try git remote
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
        except:
            pass

        # Fallback: hash of cwd
        return hashlib.sha256(str(cwd.resolve()).encode()).hexdigest()[:16]

    # ========================================================================
    # MCP Tool Implementations
    # ========================================================================

    async def memory_store_episode(
        self,
        project_id: str,
        task_description: str,
        tool_calls: List[str],
        files_touched: List[str],
        outcome: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Store an episode node with automatic canonicalization and linking.

        Returns node ID and created edges.
        """
        try:
            # Canonicalize tool calls
            canonical_tools = canonicalize_tool_sequence(tool_calls)

            # Create episode node
            node = create_episode_node(
                project_id=project_id,
                task_description=task_description,
                tool_calls=canonical_tools,
                files_touched=files_touched,
                outcome=outcome,
                **kwargs
            )

            self.store.write_node(node)

            # Create FOLLOWS edge to previous episode (if exists)
            prev_episodes = self.store.query_episodes_since(
                since=0,
                limit=2,
                project_id=project_id
            )

            edges_created = []
            if len(prev_episodes) > 1:
                prev_ep = prev_episodes[1]  # [0] is the one we just created
                edge = create_edge(
                    from_node=node.id,
                    to_node=prev_ep.id,
                    edge_type=EdgeType.FOLLOWS,
                    project_id=project_id
                )
                self.store.write_edge(edge)
                edges_created.append(edge.id)

            return {
                "node_id": node.id,
                "node_type": "episode",
                "canonical_tools": canonical_tools,
                "edges_created": edges_created
            }

        except Exception as e:
            logger.error(f"Failed to store episode: {e}")
            return {"error": str(e)}

    async def memory_store_semantic(
        self,
        project_id: str,
        fact: str,
        confidence: float,
        source_turn_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Store a semantic fact node"""
        try:
            node = create_semantic_node(
                project_id=project_id,
                fact=fact,
                confidence=confidence,
                source_turn_id=source_turn_id,
                **kwargs
            )

            self.store.write_node(node)

            return {
                "node_id": node.id,
                "node_type": "semantic",
                "fact": fact
            }

        except Exception as e:
            logger.error(f"Failed to store semantic: {e}")
            return {"error": str(e)}

    async def memory_store_failure(
        self,
        project_id: str,
        error_type: str,
        tool: str,
        error_message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Store a failure node"""
        try:
            node = create_failure_node(
                project_id=project_id,
                error_type=error_type,
                tool=tool,
                error_message=error_message,
                **kwargs
            )

            self.store.write_node(node)

            return {
                "node_id": node.id,
                "node_type": "failure",
                "error_type": error_type
            }

        except Exception as e:
            logger.error(f"Failed to store failure: {e}")
            return {"error": str(e)}

    async def memory_promote_pattern(
        self,
        project_id: str,
        pattern_name: str,
        trigger: str,
        tool_sequence: List[str],
        evidence_ids: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Promote a procedural pattern"""
        try:
            # Canonicalize tool sequence
            canonical_tools = canonicalize_tool_sequence(tool_sequence)

            node = create_procedural_node(
                project_id=project_id,
                pattern_name=pattern_name,
                trigger=trigger,
                tool_sequence=canonical_tools,
                success_count=len(evidence_ids),
                evidence_ids=evidence_ids,
                **kwargs
            )

            self.store.write_node(node)

            # Create PATTERN_FOR edges to evidence episodes
            edges_created = []
            for evidence_id in evidence_ids[:5]:  # Limit to prevent explosion
                edge = create_edge(
                    from_node=node.id,
                    to_node=evidence_id,
                    edge_type=EdgeType.PATTERN_FOR,
                    project_id=project_id
                )
                try:
                    self.store.write_edge(edge)
                    edges_created.append(edge.id)
                except Exception as edge_err:
                    logger.warning(f"Failed to create edge to {evidence_id}: {edge_err}")

            return {
                "node_id": node.id,
                "node_type": "procedural",
                "pattern_name": pattern_name,
                "edges_created": edges_created
            }

        except Exception as e:
            logger.error(f"Failed to promote pattern: {e}")
            return {"error": str(e)}

    async def memory_recall_context(
        self,
        project_id: str,
        current_task: Optional[str] = None,
        files_mentioned: Optional[List[str]] = None,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        Compile working memory context for injection.

        Returns structured context ready for formatting into brief.
        """
        try:
            context = RetrievalContext(
                project_id=project_id,
                current_task=current_task,
                files_mentioned=files_mentioned or []
            )

            memory_context = self.retrieval.compile_memory_context(context, max_nodes)

            return {
                "context": memory_context,
                "node_count": sum(
                    len(v) for k, v in memory_context.items()
                    if isinstance(v, list)
                )
            }

        except Exception as e:
            logger.error(f"Failed to recall context: {e}")
            return {"error": str(e)}

    async def memory_search(
        self,
        query: str,
        project_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Full-text search across graph memory"""
        try:
            results = self.store.search_fts(query, project_id, limit)

            return {
                "results": [node.to_dict() for node in results],
                "count": len(results)
            }

        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return {"error": str(e)}

    async def memory_evolve_persona(
        self,
        project_id: str,
        episode_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evolve persona from episode data.

        Extracts signals and updates persona engine.
        """
        try:
            # Extract signals from episode
            signals = self.persona_engine.extract_signals_from_episode(episode_data)

            # Ingest signals
            self.persona_engine.ingest_signals(signals)

            # Get active traits
            traits = self.persona_engine.get_active_traits()

            # Optionally persist persona nodes
            nodes_created = []
            for trait in traits[:3]:  # Top 3 traits
                node = create_persona_node(
                    project_id=project_id,
                    trait_name=trait['trait_name'],
                    strength=trait['strength'],
                    learned_from=[episode_data.get('turn_id', '')],
                    axis=trait['axis']
                )
                self.store.write_node(node)
                nodes_created.append(node.id)

            return {
                "signals_extracted": len(signals),
                "active_traits": traits,
                "nodes_created": nodes_created
            }

        except Exception as e:
            logger.error(f"Failed to evolve persona: {e}")
            return {"error": str(e)}

    # ========================================================================
    # MCP Protocol Handling
    # ========================================================================

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP request.

        This is a simplified MCP implementation - production would use
        the full MCP SDK.
        """
        method = request.get("method")
        params = request.get("params", {})

        logger.info(f"Handling request: {method}")

        try:
            if method == "memory_store_episode":
                result = await self.memory_store_episode(**params)
            elif method == "memory_store_semantic":
                result = await self.memory_store_semantic(**params)
            elif method == "memory_store_failure":
                result = await self.memory_store_failure(**params)
            elif method == "memory_promote_pattern":
                result = await self.memory_promote_pattern(**params)
            elif method == "memory_recall_context":
                result = await self.memory_recall_context(**params)
            elif method == "memory_search":
                result = await self.memory_search(**params)
            elif method == "memory_evolve_persona":
                result = await self.memory_evolve_persona(**params)
            elif method == "list_tools":
                result = self._list_tools()
            else:
                result = {"error": f"Unknown method: {method}"}

            return {"result": result}

        except Exception as e:
            logger.error(f"Error handling {method}: {e}", exc_info=True)
            return {"error": str(e)}

    def _list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        return [
            {
                "name": "memory_store_episode",
                "description": "Store a coding session episode with tool calls and outcomes",
                "parameters": {
                    "project_id": "string",
                    "task_description": "string",
                    "tool_calls": "list[string]",
                    "files_touched": "list[string]",
                    "outcome": "success|failure|partial"
                }
            },
            {
                "name": "memory_store_semantic",
                "description": "Store a semantic fact with confidence score",
                "parameters": {
                    "project_id": "string",
                    "fact": "string",
                    "confidence": "float",
                    "source_turn_id": "string (optional)"
                }
            },
            {
                "name": "memory_recall_context",
                "description": "Retrieve relevant memory context for current task",
                "parameters": {
                    "project_id": "string",
                    "current_task": "string (optional)",
                    "files_mentioned": "list[string] (optional)"
                }
            },
            {
                "name": "memory_search",
                "description": "Full-text search across graph memory",
                "parameters": {
                    "query": "string",
                    "project_id": "string",
                    "limit": "int (default: 20)"
                }
            },
            {
                "name": "memory_promote_pattern",
                "description": "Promote a procedural pattern from evidence episodes",
                "parameters": {
                    "project_id": "string",
                    "pattern_name": "string",
                    "trigger": "string",
                    "tool_sequence": "list[string]",
                    "evidence_ids": "list[string]"
                }
            },
            {
                "name": "memory_evolve_persona",
                "description": "Evolve persona traits from episode data",
                "parameters": {
                    "project_id": "string",
                    "episode_data": "dict"
                }
            }
        ]

    async def run(self):
        """
        Run MCP server in stdio mode.

        Reads JSON-RPC requests from stdin, writes responses to stdout.
        """
        logger.info("AINL Graph Memory MCP Server starting...")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line.strip())
                response = await self.handle_request(request)

                # Write response to stdout
                json.dump(response, sys.stdout)
                sys.stdout.write("\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                error_response = {"error": f"Invalid JSON: {e}"}
                json.dump(error_response, sys.stdout)
                sys.stdout.write("\n")
                sys.stdout.flush()

            except Exception as e:
                logger.error(f"Server error: {e}", exc_info=True)
                error_response = {"error": str(e)}
                json.dump(error_response, sys.stdout)
                sys.stdout.write("\n")
                sys.stdout.flush()


async def main():
    """Main entry point"""
    server = AINLGraphMemoryServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
