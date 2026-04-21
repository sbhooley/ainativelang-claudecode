# AINL Graph Memory for Claude Code

**Production-grade graph-native memory system with first-class AINL language integration.**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![AINL](https://img.shields.io/badge/AINL-v1.7.0+-orange.svg)](https://ainativelang.com)

## What is This?

AINL Graph Memory is a **Claude Code plugin** that provides:

1. **Graph-native memory system** - Persistent, queryable knowledge graph for your coding sessions
2. **First-class AINL language support** - Full integration with AI Native Lang (AINL)
3. **Smart workflow suggestions** - Auto-detects when to use .ainl for cost savings
4. **Pattern memory** - Stores and recalls successful AINL workflows

**Powered by:** [AI Native Lang (AINL)](https://ainativelang.com) - The graph-canonical programming language designed for AI agents.

### Key Innovation

> **Graph-as-Memory Paradigm:** Every coding turn, tool invocation, and decision becomes a typed node in a persistent graph. No separate retrieval layer—the execution graph IS the memory.

## Features

✅ **Typed Graph Memory** - Episode, Semantic, Procedural, Persona, and Failure nodes  
✅ **Soft Axes Persona Evolution** - Learn project/developer preferences without LLM calls  
✅ **Pattern Extraction** - Automatically promote successful workflows to reusable patterns  
✅ **Context-Aware Retrieval** - Inject only relevant memories (ranked by project, recency, fitness)  
✅ **AINL Compression & Eco Mode** - 40-70% token savings on memory context (Balanced/Aggressive modes)  
✅ **Advanced Compression Pipeline** - Adaptive eco, semantic scoring, project profiles, cache awareness  
✅ **Project Isolation** - Memories never leak between different codebases  
✅ **Graceful Degradation** - Hooks never break Claude Code, even on errors  
✅ **Inspectable** - CLI tools for debugging and exploration

## Quick Start

### Installation

```bash
# Clone or download to Claude Code plugins directory
cd ~/.claude/plugins
git clone https://github.com/claude-code/ainl-graph-memory.git

# Install dependencies
cd ainl-graph-memory
pip install -r requirements.txt

# Verify installation
python3 mcp_server/server.py --help
```

### Usage

**That's it!** The plugin automatically:

1. **Captures** your tool usage (Read, Edit, Bash, etc.) via hooks
2. **Stores** typed graph nodes (episodes, facts, patterns, personas) in SQLite
3. **Retrieves** relevant context and injects it before each Claude response
4. **Evolves** persona traits based on your coding style

Memory accumulates automatically as you work.

### Inspecting Your Memory

```bash
# View recent episodes
python3 cli/memory_cli.py list --type episode --limit 10

# Search memory
python3 cli/memory_cli.py search "authentication error"

# View persona traits
python3 cli/memory_cli.py list --type persona

# Check graph integrity
python3 cli/memory_cli.py validate
```

### Managing Compression (Eco Mode)

```bash
# Check current compression settings
python3 cli/compression_cli.py config

# Set compression mode (off, balanced, aggressive)
python3 cli/compression_cli.py config --mode aggressive

# Test compression on sample text
python3 cli/compression_cli.py test --file prompt.txt --show-output

# Benchmark compression modes
python3 cli/compression_cli.py benchmark
```

**Typical savings:**
- Balanced mode: 40-50% token reduction
- Aggressive mode: 55-70% token reduction

See [docs/COMPRESSION_ECO_MODE.md](docs/COMPRESSION_ECO_MODE.md) for details.

### Advanced Compression Features (v0.2+)

```bash
# Test unified compression pipeline
echo "Your text" | python3 cli/compression_advanced_cli.py test -p myproject

# Show adaptive mode statistics
python3 cli/compression_advanced_cli.py adaptive

# Show quality preservation scores
python3 cli/compression_advanced_cli.py quality

# Auto-detect best mode for project
python3 cli/compression_advanced_cli.py auto-detect -p myproject --apply

# Show all advanced features config
python3 cli/compression_advanced_cli.py config
```

**Advanced features:**
- **Adaptive Eco Mode** - Auto-select compression based on content
- **Semantic Scoring** - Track quality without embeddings
- **Project Profiles** - Learn optimal mode per codebase
- **Cache Awareness** - Coordinate with prompt cache (5min TTL)
- **Output Compression** - Optionally compress responses

See [docs/ADVANCED_COMPRESSION.md](docs/ADVANCED_COMPRESSION.md) for full documentation.

### Memory Location

Your graph memory lives at:
```
~/.claude/projects/[project-hash]/graph_memory/ainl_memory.db
```

Each project gets its own isolated graph.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Session                      │
└──────────────────┬───────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐   ┌─────▼─────┐   ┌───▼────┐
│ Hooks  │   │    MCP    │   │  Auto  │
│ System │◄─►│  Memory   │◄─►│ Memory │
│        │   │  Server   │   │        │
└────────┘   └─────┬─────┘   └────────┘
                   │
            ┌──────▼──────┐
            │   SQLite    │
            │ Graph Store │
            └─────────────┘
```

### Components

- **Hooks** - Lifecycle event capture (UserPromptSubmit, PostToolUse, Stop)
- **MCP Server** - Graph read/write/search tools exposed to Claude
- **Graph Store** - SQLite with typed nodes, edges, and FTS5 search
- **Retrieval** - AINL-inspired ranking algorithm for context compilation
- **Persona Engine** - Soft axes evolution with EMA smoothing
- **Pattern Extractor** - Automatic procedural pattern promotion

## AINL Concepts

This plugin demonstrates six core concepts from the AINL architecture:

### 1. Graph-as-Memory Paradigm

Execution IS the memory, not a separate retrieval layer. Every agent turn, tool call, and delegation becomes a typed graph node.

### 2. Typed Node System

- **Episode** - What happened (coding turn with tools, files, outcome)
- **Semantic** - What was learned (facts with confidence scores)
- **Procedural** - How to do it (reusable workflow patterns)
- **Persona** - Who I am (evolving developer/project traits)
- **Failure** - What went wrong (errors + resolutions)

### 3. Soft Axes Persona Evolution

Persona traits evolve through **metadata-only signals**:
- Axes represent spectrums (verbosity: concise ↔ detailed)
- Signals apply directional force with strength
- EMA smoothing with decay prevents overfitting
- No LLM calls needed for evolution

### 4. Pattern Extraction and Promotion

Successful tool sequences automatically become reusable patterns:
- Detection: repeated sequences with success outcomes
- Promotion: min occurrences + fitness score threshold
- Fitness tracking: EMA of success/failure ratio
- Tool canonicalization: `bash`/`shell`/`sh` → `bash`

### 5. Intelligent Compression (Eco Mode)

Embedding-free prompt compression reduces token costs:
- **Balanced**: ~55% retention (40-50% savings)
- **Aggressive**: ~35% retention (55-70% savings)
- Preserves code blocks, technical terms, user intent
- Strips filler phrases and meta-commentary
- Sub-30ms latency

### 6. Inbox Pattern for Multi-Writer Sync

Safe memory updates from multiple processes:
- Hooks append to lightweight capture files
- MCP server drains inbox into SQLite
- No DB locking conflicts
- Eventual consistency

See [docs/AINL_CONCEPTS.md](docs/AINL_CONCEPTS.md) and [docs/COMPRESSION_ECO_MODE.md](docs/COMPRESSION_ECO_MODE.md) for detailed explanations.

## Configuration

The plugin works out-of-the-box with sensible defaults. Advanced users can configure:

- **Memory retrieval thresholds** - Edit `mcp_server/retrieval.py`
- **Persona evolution axes** - Edit `mcp_server/persona_engine.py`
- **Pattern promotion criteria** - Edit `mcp_server/extractor.py`
- **Logging levels** - Edit `hooks/shared/logger.py`

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=mcp_server --cov-report=html
```

### Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Inspired By

This plugin is directly inspired by the **AINL (AINativeLang) unified graph execution engine** from the [ArmaraOS](https://github.com/sbhooley/armaraos) project:

- **ainl-memory** - GraphStore trait, typed nodes, SQLite backend
- **ainl-persona** - Soft axes evolution, signal ingestion
- **ainl-graph-extractor** - Pattern detection, recurrence tracking
- **ainl-runtime** - Turn orchestration, memory context compilation
- **ainl-semantic-tagger** - Tool canonicalization
- **ainl-compression** - Prompt compression algorithms, eco modes

All core architectural concepts and compression algorithms are attributed to the AINL project.

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright 2026 AINL Graph Memory Plugin Contributors

## Learn More

### AINL Resources
- **Official Website**: https://ainativelang.com
- **AINL on PyPI**: https://pypi.org/project/ainativelang/
- **GitHub**: https://github.com/sbhooley/ainativelang
- **Documentation**: https://ainativelang.com/docs

### Related Projects
- **ArmaraOS**: https://github.com/sbhooley/armaraos (Desktop agent OS built on AINL)
- **ainl-memory crate**: https://crates.io/crates/ainl-memory
- **ainl-runtime crate**: https://crates.io/crates/ainl-runtime

## Roadmap

### v0.2
- [ ] Semantic embeddings for vector search (local model)
- [ ] Cross-project pattern library
- [ ] Web-based memory explorer UI
- [ ] Export/import graph snapshots

### v0.3
- [ ] Rust MCP server (performance)
- [ ] Integration with ainl-runtime as library
- [ ] Collaborative team memory
- [ ] Advanced persona axes (domain-specific)

### v0.4
- [ ] AINL IR pattern compilation
- [ ] GraphPatch integration
- [ ] Memory consolidation/pruning strategies
- [ ] Analytics dashboard

---

**Built with ❤️ by the Claude Code community**

**Powered by AINL architecture from ArmaraOS**
