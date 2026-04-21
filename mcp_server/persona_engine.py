"""
AINL Persona Evolution Engine

Soft axes persona evolution inspired by ainl-persona.
No LLM calls - pure metadata signals with EMA smoothing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PersonaAxis:
    """
    Soft axis for persona evolution (AINL pattern).

    Represents a spectrum like verbosity: concise ↔ detailed
    Current value ranges from -1.0 to 1.0
    """
    name: str
    current: float = 0.0         # -1.0 to 1.0
    decay_rate: float = 0.95      # EMA decay
    min_threshold: float = 0.1    # Zero out if below this

    def apply_signal(self, direction: float, strength: float) -> None:
        """
        Apply evolution signal with EMA smoothing.

        Args:
            direction: -1.0 to 1.0 (which pole to move toward)
            strength: 0.0 to 1.0 (how much force)
        """
        delta = direction * strength
        self.current = self.current * self.decay_rate + delta * (1 - self.decay_rate)

        # Clamp to valid range
        self.current = max(-1.0, min(1.0, self.current))

        # Zero out if below threshold (prevent noise accumulation)
        if abs(self.current) < self.min_threshold:
            self.current = 0.0


@dataclass
class EvolutionSignal:
    """
    Metadata signal for persona evolution.

    Example: User ran many tests → testing_rigor axis +0.7
    """
    axis: str
    direction: float  # -1.0 to 1.0
    strength: float   # 0.0 to 1.0
    evidence: str     # Node ID
    reason: Optional[str] = None


class PersonaEvolutionEngine:
    """
    Soft axes persona evolution (inspired by ainl-persona EvolutionEngine).

    No LLM calls - evolution driven purely by metadata signals
    extracted from tool usage, file patterns, and outcomes.
    """

    # Developer preference axes
    DEVELOPER_AXES = {
        'verbosity': 'concise ↔ detailed',
        'testing_rigor': 'minimal ↔ comprehensive',
        'type_safety': 'dynamic ↔ strict',
        'error_handling': 'permissive ↔ defensive',
    }

    # Project style axes
    PROJECT_AXES = {
        'architecture': 'monolithic ↔ modular',
        'documentation': 'sparse ↔ rich',
        'performance_focus': 'dev_speed ↔ optimization',
    }

    def __init__(self):
        self.axes: Dict[str, PersonaAxis] = {}

        # Initialize all axes at neutral (0.0)
        for name in self.DEVELOPER_AXES:
            self.axes[name] = PersonaAxis(name=name)
        for name in self.PROJECT_AXES:
            self.axes[name] = PersonaAxis(name=name)

        logger.info(f"Initialized persona engine with {len(self.axes)} axes")

    def ingest_signals(self, signals: List[EvolutionSignal]) -> None:
        """
        Ingest evolution signals and update axes.

        This is the core evolution method - call after extracting
        signals from episode/tool data.
        """
        for signal in signals:
            if signal.axis not in self.axes:
                logger.warning(f"Unknown axis: {signal.axis}")
                continue

            axis = self.axes[signal.axis]
            axis.apply_signal(signal.direction, signal.strength)

            logger.debug(
                f"Applied signal to {signal.axis}: "
                f"dir={signal.direction:.2f}, str={signal.strength:.2f} → "
                f"new value={axis.current:.2f}"
            )

    def extract_signals_from_episode(self, episode_data: Dict[str, Any]) -> List[EvolutionSignal]:
        """
        Extract persona signals from episode data (heuristic).

        These are simple pattern-based rules. More sophisticated
        extraction can be added later.
        """
        signals = []

        tools = episode_data.get('tool_calls', [])
        files = episode_data.get('files_touched', [])
        task = episode_data.get('task_description', '').lower()

        # Testing rigor signal
        # If task mentions test OR used bash with test files
        test_indicators = sum([
            'test' in task,
            any('test' in f.lower() for f in files),
            'bash' in tools and any('test' in f.lower() for f in files)
        ])

        if test_indicators > 0:
            strength = min(test_indicators / 3.0, 1.0)
            signals.append(EvolutionSignal(
                axis='testing_rigor',
                direction=1.0,  # Toward comprehensive
                strength=strength,
                evidence=episode_data.get('turn_id', ''),
                reason=f"Test-related activity (indicators: {test_indicators})"
            ))

        # Type safety signal (heuristic: Rust/TypeScript/Python with types)
        typed_langs = sum([
            any(f.endswith('.rs') for f in files),      # Rust
            any(f.endswith('.ts') for f in files),      # TypeScript
            any(f.endswith(('.hs', '.ml')) for f in files),  # Haskell/OCaml
        ])

        if typed_langs > 0:
            signals.append(EvolutionSignal(
                axis='type_safety',
                direction=1.0,  # Toward strict
                strength=0.5,
                evidence=episode_data.get('turn_id', ''),
                reason=f"Working with statically-typed languages"
            ))

        # Documentation signal
        doc_files = sum([
            any(f.endswith('.md') for f in files),
            any(f.endswith(('.rst', '.txt')) for f in files),
            'doc' in task or 'readme' in task
        ])

        if doc_files > 0:
            signals.append(EvolutionSignal(
                axis='documentation',
                direction=1.0,  # Toward rich
                strength=min(doc_files / 2.0, 1.0),
                evidence=episode_data.get('turn_id', ''),
                reason="Documentation file activity"
            ))

        # Architecture signal (modular if many small files)
        if len(files) > 3:
            signals.append(EvolutionSignal(
                axis='architecture',
                direction=1.0,  # Toward modular
                strength=0.3,
                evidence=episode_data.get('turn_id', ''),
                reason=f"Multi-file change ({len(files)} files)"
            ))

        # Error handling signal (defensive if outcome is failure but has resolution)
        if episode_data.get('outcome') == 'failure' and episode_data.get('error_message'):
            signals.append(EvolutionSignal(
                axis='error_handling',
                direction=1.0,  # Toward defensive
                strength=0.4,
                evidence=episode_data.get('turn_id', ''),
                reason="Encountered and handled error"
            ))

        return signals

    def get_active_traits(self, min_strength: float = 0.1) -> List[Dict[str, Any]]:
        """
        Get current persona traits above threshold (for injection).

        Returns list of trait dicts suitable for persona node creation.
        """
        traits = []

        for name, axis in self.axes.items():
            if abs(axis.current) >= min_strength:
                # Determine polarity and interpretation
                if axis.current > 0:
                    if name in self.DEVELOPER_AXES:
                        interpretation = self.DEVELOPER_AXES[name].split(' ↔ ')[1]
                    else:
                        interpretation = self.PROJECT_AXES[name].split(' ↔ ')[1]
                    polarity = 'positive'
                else:
                    if name in self.DEVELOPER_AXES:
                        interpretation = self.DEVELOPER_AXES[name].split(' ↔ ')[0]
                    else:
                        interpretation = self.PROJECT_AXES[name].split(' ↔ ')[0]
                    polarity = 'negative'

                traits.append({
                    'trait_name': f"{name}_{interpretation.replace(' ', '_')}",
                    'axis': name,
                    'strength': abs(axis.current),
                    'polarity': polarity,
                    'layer': 'adaptive',
                    'interpretation': interpretation
                })

        # Sort by strength descending
        traits.sort(key=lambda t: t['strength'], reverse=True)
        return traits

    def get_snapshot_json(self) -> str:
        """
        Get JSON snapshot of current axes state.

        Used for RuntimeStateNode persistence.
        """
        import json
        snapshot = {
            axis_name: {
                'current': axis.current,
                'decay_rate': axis.decay_rate,
                'min_threshold': axis.min_threshold
            }
            for axis_name, axis in self.axes.items()
        }
        return json.dumps(snapshot)

    def load_snapshot_json(self, snapshot_json: str) -> None:
        """Restore axes from JSON snapshot"""
        import json
        snapshot = json.loads(snapshot_json)

        for axis_name, state in snapshot.items():
            if axis_name in self.axes:
                self.axes[axis_name].current = state['current']
                # Optionally restore decay_rate and min_threshold
