"""
Metrics extraction and aggregation for session analysis.

Extracts automated metrics from llm_log.jsonl and world state changes
to enable quantitative measurement of guiding principles.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from collections import defaultdict, Counter
import re


@dataclass
class DimensionScore:
    """LLM-scored dimension with evidence."""
    score: Optional[int] = None  # 1-10
    notes: str = ""
    evidence: List[str] = field(default_factory=list)


@dataclass
class NarrativeCoherenceMetrics:
    """Automated metrics for narrative coherence."""
    actor_usage_distribution: Dict[str, int] = field(default_factory=dict)
    actor_usage_entropy: float = 0.0
    action_type_distribution: Dict[str, int] = field(default_factory=dict)
    consecutive_narration_repetitions: int = 0
    context_action_mismatches: int = 0
    # LLM-scored
    llm_score: Optional[DimensionScore] = None


@dataclass
class DramaticPacingMetrics:
    """Automated metrics for dramatic pacing."""
    total_turns: int = 0
    scene_type_distribution: Dict[str, int] = field(default_factory=dict)
    dramatic_purpose_distribution: Dict[str, int] = field(default_factory=dict)
    quest_completions: int = 0
    quest_advancements: int = 0
    combat_encounters: int = 0
    location_changes: int = 0
    revelation_events: int = 0
    story_beats_completed: int = 0
    # LLM-scored
    llm_score: Optional[DimensionScore] = None


@dataclass
class CharacterAuthenticityMetrics:
    """Automated metrics for character authenticity."""
    character_action_counts: Dict[str, int] = field(default_factory=dict)
    character_tool_usage: Dict[str, Dict[str, int]] = field(default_factory=dict)
    dialogue_to_action_ratio: float = 0.0
    unique_speakers: int = 0
    # LLM-scored
    llm_score: Optional[DimensionScore] = None


@dataclass
class WorldResponsivenessMetrics:
    """Automated metrics for world responsiveness."""
    dm_modify_calls: int = 0
    world_state_changes: int = 0
    quest_progress_events: int = 0
    npc_interactions: int = 0
    # LLM-scored
    llm_score: Optional[DimensionScore] = None


@dataclass
class ProseQualityMetrics:
    """Automated metrics for prose quality."""
    avg_narration_length: float = 0.0
    unique_speakers_count: int = 0
    sensory_word_count: int = 0
    total_words: int = 0
    repetitive_phrase_count: int = 0
    most_common_phrases: List[str] = field(default_factory=list)
    # LLM-scored
    llm_score: Optional[DimensionScore] = None


@dataclass
class SystemEfficiencyMetrics:
    """Automated system efficiency metrics."""
    total_llm_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    error_count: int = 0
    tool_call_success_rate: float = 0.0
    estimated_cost_usd: float = 0.0


@dataclass
class SessionMetrics:
    """Complete session metrics combining automated and LLM-scored dimensions."""
    session_id: str
    timestamp: str
    
    # Automated metrics by dimension
    narrative_coherence: NarrativeCoherenceMetrics = field(default_factory=NarrativeCoherenceMetrics)
    dramatic_pacing: DramaticPacingMetrics = field(default_factory=DramaticPacingMetrics)
    character_authenticity: CharacterAuthenticityMetrics = field(default_factory=CharacterAuthenticityMetrics)
    world_responsiveness: WorldResponsivenessMetrics = field(default_factory=WorldResponsivenessMetrics)
    prose_quality: ProseQualityMetrics = field(default_factory=ProseQualityMetrics)
    system_efficiency: SystemEfficiencyMetrics = field(default_factory=SystemEfficiencyMetrics)
    
    # Overall assessment
    overall_score: Optional[int] = None
    overall_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {}
        for key, value in asdict(self).items():
            if isinstance(value, dict) and value:
                result[key] = value
            elif value is not None and value != "" and value != 0 and value != 0.0:
                result[key] = value
        return result


class MetricsExtractor:
    """Extract automated metrics from llm_log.jsonl and session data."""
    
    def __init__(self, llm_log_path: Path, session_dir: Path):
        self.llm_log_path = Path(llm_log_path)
        self.session_dir = Path(session_dir)
        self.llm_calls = []
        self._load_llm_log()
    
    def _load_llm_log(self):
        """Load all LLM calls from jsonl file."""
        if not self.llm_log_path.exists():
            return
        
        with open(self.llm_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.llm_calls.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    
    def _identify_agent_type(self, call: Dict) -> str:
        """Identify which agent made this call from system prompt."""
        try:
            system_msg = call.get('req', {}).get('messages', [{}])[0].get('content', '')
            system_lower = system_msg.lower()
            
            if 'storyteller' in system_lower:
                return 'storyteller'
            elif 'dungeon master' in system_lower or 'dm' in system_lower:
                return 'dm'
            elif 'director' in system_lower:
                return 'director'
            elif 'character' in system_lower or 'you are' in system_lower:
                return 'character'
            elif 'reviewer' in system_lower:
                return 'reviewer'
            else:
                return 'unknown'
        except (KeyError, IndexError):
            return 'unknown'
    
    def _extract_tool_calls(self, call: Dict) -> List[Dict[str, Any]]:
        """Extract tool calls from response."""
        try:
            choices = call.get('resp', {}).get('choices', [])
            if not choices:
                return []
            
            tool_calls = choices[0].get('message', {}).get('tool_calls', [])
            return tool_calls or []
        except (KeyError, IndexError):
            return []
    
    def extract_narrative_coherence(self) -> NarrativeCoherenceMetrics:
        """Extract narrative coherence metrics."""
        metrics = NarrativeCoherenceMetrics()
        
        # Actor usage distribution
        actor_counts = defaultdict(int)
        action_types = defaultdict(int)
        
        for call in self.llm_calls:
            agent = self._identify_agent_type(call)
            actor_counts[agent] += 1
            
            tool_calls = self._extract_tool_calls(call)
            for tc in tool_calls:
                tool_name = tc.get('function', {}).get('name', '')
                action_types[tool_name] += 1
        
        metrics.actor_usage_distribution = dict(actor_counts)
        metrics.action_type_distribution = dict(action_types)
        
        # Calculate entropy for actor usage
        if actor_counts:
            total = sum(actor_counts.values())
            import math
            entropy = -sum((count/total) * math.log2(count/total) for count in actor_counts.values() if count > 0)
            metrics.actor_usage_entropy = entropy
        
        # Detect consecutive narration repetitions (simple heuristic)
        narrations = []
        for call in self.llm_calls:
            if self._identify_agent_type(call) == 'dm':
                try:
                    content = call.get('resp', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content:
                        narrations.append(content.lower())
                except (KeyError, IndexError):
                    continue
        
        # Count similar consecutive narrations
        repetitions = 0
        for i in range(len(narrations) - 1):
            # Simple similarity: check for common phrases
            words1 = set(narrations[i].split()[:20])  # First 20 words
            words2 = set(narrations[i+1].split()[:20])
            overlap = len(words1 & words2) / max(len(words1), len(words2), 1)
            if overlap > 0.6:  # 60% overlap threshold
                repetitions += 1
        
        metrics.consecutive_narration_repetitions = repetitions
        
        return metrics
    
    def extract_dramatic_pacing(self, world_state: Optional[Dict] = None) -> DramaticPacingMetrics:
        """Extract dramatic pacing metrics."""
        metrics = DramaticPacingMetrics()
        
        # Scene types and dramatic purposes from storyteller calls
        for call in self.llm_calls:
            if self._identify_agent_type(call) == 'storyteller':
                tool_calls = self._extract_tool_calls(call)
                for tc in tool_calls:
                    tool_name = tc.get('function', {}).get('name', '')
                    args = tc.get('function', {}).get('arguments', {})
                    
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            args = {}
                    
                    if tool_name:
                        metrics.scene_type_distribution[tool_name] = metrics.scene_type_distribution.get(tool_name, 0) + 1
                    
                    purpose = args.get('dramatic_purpose', args.get('purpose', ''))
                    if purpose:
                        metrics.dramatic_purpose_distribution[purpose] = metrics.dramatic_purpose_distribution.get(purpose, 0) + 1
        
        # Location changes from move tool calls
        for call in self.llm_calls:
            tool_calls = self._extract_tool_calls(call)
            for tc in tool_calls:
                if tc.get('function', {}).get('name') == 'move':
                    metrics.location_changes += 1
        
        # Count total turns (approximate from DM + character actions)
        dm_actions = sum(1 for call in self.llm_calls if self._identify_agent_type(call) in ['dm', 'character'])
        metrics.total_turns = dm_actions
        
        # Extract from world state if provided
        if world_state:
            metrics.story_beats_completed = len(world_state.get('story_beats', []))
        
        return metrics
    
    def extract_character_authenticity(self) -> CharacterAuthenticityMetrics:
        """Extract character authenticity metrics."""
        metrics = CharacterAuthenticityMetrics()
        
        character_actions = defaultdict(int)
        character_tools = defaultdict(lambda: defaultdict(int))
        dialogue_count = 0
        action_count = 0
        speakers = set()
        
        for call in self.llm_calls:
            if self._identify_agent_type(call) == 'character':
                tool_calls = self._extract_tool_calls(call)
                
                for tc in tool_calls:
                    tool_name = tc.get('function', {}).get('name', '')
                    args = tc.get('function', {}).get('arguments', {})
                    
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            args = {}
                    
                    char_id = args.get('character_id', 'unknown')
                    character_actions[char_id] += 1
                    character_tools[char_id][tool_name] += 1
                    
                    if tool_name == 'speak':
                        dialogue_count += 1
                        speakers.add(char_id)
                    elif tool_name in ['act', 'move']:
                        action_count += 1
        
        metrics.character_action_counts = dict(character_actions)
        metrics.character_tool_usage = {k: dict(v) for k, v in character_tools.items()}
        metrics.unique_speakers = len(speakers)
        
        if action_count > 0:
            metrics.dialogue_to_action_ratio = dialogue_count / action_count
        
        return metrics
    
    def extract_world_responsiveness(self, world_state: Optional[Dict] = None) -> WorldResponsivenessMetrics:
        """Extract world responsiveness metrics."""
        metrics = WorldResponsivenessMetrics()
        
        # Count DM modify calls
        for call in self.llm_calls:
            tool_calls = self._extract_tool_calls(call)
            for tc in tool_calls:
                tool_name = tc.get('function', {}).get('name', '')
                if tool_name == 'modify':
                    metrics.dm_modify_calls += 1
        
        # Extract from world state if provided
        if world_state:
            # Count changes in quests
            quests = world_state.get('quests', {})
            metrics.quest_progress_events = sum(1 for q in quests.values() if q.get('status') != 'available')
        
        return metrics
    
    def extract_prose_quality(self) -> ProseQualityMetrics:
        """Extract prose quality metrics."""
        metrics = ProseQualityMetrics()
        
        narrations = []
        all_phrases = []
        
        for call in self.llm_calls:
            if self._identify_agent_type(call) == 'dm':
                try:
                    content = call.get('resp', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content:
                        narrations.append(content)
                        # Extract 3-word phrases
                        words = content.lower().split()
                        for i in range(len(words) - 2):
                            phrase = ' '.join(words[i:i+3])
                            all_phrases.append(phrase)
                except (KeyError, IndexError):
                    continue
        
        if narrations:
            lengths = [len(n.split()) for n in narrations]
            metrics.avg_narration_length = sum(lengths) / len(lengths)
            metrics.total_words = sum(lengths)
            
            # Count sensory words (simple heuristic)
            sensory_words = {'see', 'sight', 'look', 'watch', 'hear', 'sound', 'listen', 'smell', 'scent', 
                           'taste', 'flavor', 'feel', 'touch', 'warm', 'cold', 'rough', 'smooth',
                           'bright', 'dark', 'loud', 'quiet', 'soft', 'hard'}
            
            for narration in narrations:
                words = narration.lower().split()
                metrics.sensory_word_count += sum(1 for w in words if w in sensory_words)
        
        # Find repetitive phrases
        phrase_counts = Counter(all_phrases)
        repeated = [(phrase, count) for phrase, count in phrase_counts.items() if count > 2]
        metrics.repetitive_phrase_count = len(repeated)
        metrics.most_common_phrases = [phrase for phrase, _ in sorted(repeated, key=lambda x: x[1], reverse=True)[:5]]
        
        return metrics
    
    def extract_system_efficiency(self) -> SystemEfficiencyMetrics:
        """Extract system efficiency metrics."""
        metrics = SystemEfficiencyMetrics()
        
        if not self.llm_calls:
            return metrics
        
        metrics.total_llm_calls = len(self.llm_calls)
        
        latencies = []
        errors = 0
        tool_call_successes = 0
        tool_call_attempts = 0
        
        for call in self.llm_calls:
            # Tokens
            usage = call.get('resp', {}).get('usage', {})
            metrics.total_prompt_tokens += usage.get('prompt_tokens', 0)
            metrics.total_completion_tokens += usage.get('completion_tokens', 0)
            metrics.total_tokens += usage.get('total_tokens', 0)
            
            # Latency
            ms = call.get('ms', 0)
            if ms > 0:
                latencies.append(ms)
            
            # Tool calls
            tool_calls = self._extract_tool_calls(call)
            if tool_calls:
                tool_call_successes += 1
                tool_call_attempts += 1
            elif call.get('req', {}).get('tools'):  # Had tools available but didn't use
                tool_call_attempts += 1
            
            # Errors (check for error indicators)
            if call.get('resp', {}).get('error') or 'error' in str(call.get('resp', {})).lower():
                errors += 1
        
        if latencies:
            metrics.avg_latency_ms = sum(latencies) / len(latencies)
            metrics.max_latency_ms = max(latencies)
            metrics.min_latency_ms = min(latencies)
        
        metrics.error_count = errors
        
        if tool_call_attempts > 0:
            metrics.tool_call_success_rate = tool_call_successes / tool_call_attempts
        
        # Estimate cost (rough approximation for common models)
        # Assuming $0.03 per 1M tokens for simplicity
        metrics.estimated_cost_usd = (metrics.total_tokens / 1_000_000) * 0.03
        
        return metrics
    
    def extract_all(self, world_state: Optional[Dict] = None) -> SessionMetrics:
        """Extract all metrics for a session."""
        session_id = self.session_dir.name
        
        # Get timestamp from first LLM call or use current
        timestamp = ""
        if self.llm_calls:
            timestamp = self.llm_calls[0].get('ts', '')
        
        metrics = SessionMetrics(
            session_id=session_id,
            timestamp=timestamp,
        )
        
        metrics.narrative_coherence = self.extract_narrative_coherence()
        metrics.dramatic_pacing = self.extract_dramatic_pacing(world_state)
        metrics.character_authenticity = self.extract_character_authenticity()
        metrics.world_responsiveness = self.extract_world_responsiveness(world_state)
        metrics.prose_quality = self.extract_prose_quality()
        metrics.system_efficiency = self.extract_system_efficiency()
        
        return metrics


def extract_session_metrics(llm_log_path: str, session_dir: str, world_state: Optional[Dict] = None) -> SessionMetrics:
    """Convenience function to extract metrics from a session.
    
    Args:
        llm_log_path: Path to llm_log.jsonl file
        session_dir: Path to session directory
        world_state: Optional world state dictionary
        
    Returns:
        SessionMetrics object with all extracted metrics
    """
    extractor = MetricsExtractor(Path(llm_log_path), Path(session_dir))
    return extractor.extract_all(world_state)
