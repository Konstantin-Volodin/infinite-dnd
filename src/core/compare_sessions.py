"""
Cross-session comparison utility for tracking improvements over time.

Loads multiple session reviews and metrics to show trends in guiding principles.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class SessionComparison:
    """Comparison results across multiple sessions."""
    sessions: List[str] = field(default_factory=list)
    
    # Score trends (session_id -> score)
    overall_scores: Dict[str, int] = field(default_factory=dict)
    narrative_coherence_scores: Dict[str, int] = field(default_factory=dict)
    dramatic_pacing_scores: Dict[str, int] = field(default_factory=dict)
    character_authenticity_scores: Dict[str, int] = field(default_factory=dict)
    world_responsiveness_scores: Dict[str, int] = field(default_factory=dict)
    prose_quality_scores: Dict[str, int] = field(default_factory=dict)
    
    # Automated metrics trends
    avg_tokens_per_turn: Dict[str, float] = field(default_factory=dict)
    avg_latency_ms: Dict[str, float] = field(default_factory=dict)
    actor_diversity: Dict[str, float] = field(default_factory=dict)  # entropy
    
    # Aggregate statistics
    avg_overall_score: float = 0.0
    best_session: Optional[str] = None
    worst_session: Optional[str] = None
    improvement_trend: str = ""  # "improving", "declining", "stable"
    
    def to_report(self) -> str:
        """Generate a human-readable comparison report."""
        lines = ["=" * 80]
        lines.append("SESSION COMPARISON REPORT")
        lines.append("=" * 80)
        lines.append(f"\nTotal Sessions Analyzed: {len(self.sessions)}")
        lines.append(f"Average Overall Score: {self.avg_overall_score:.1f}/10")
        lines.append(f"Trend: {self.improvement_trend.upper()}")
        
        if self.best_session:
            best_score = self.overall_scores.get(self.best_session, 0)
            lines.append(f"\nBest Session: {self.best_session} ({best_score}/10)")
        
        if self.worst_session:
            worst_score = self.overall_scores.get(self.worst_session, 0)
            lines.append(f"Worst Session: {self.worst_session} ({worst_score}/10)")
        
        lines.append("\n" + "-" * 80)
        lines.append("GUIDING PRINCIPLES - SCORE TRENDS")
        lines.append("-" * 80)
        
        principles = [
            ("Narrative Coherence", self.narrative_coherence_scores),
            ("Dramatic Pacing", self.dramatic_pacing_scores),
            ("Character Authenticity", self.character_authenticity_scores),
            ("World Responsiveness", self.world_responsiveness_scores),
            ("Prose Quality", self.prose_quality_scores),
        ]
        
        for name, scores in principles:
            if scores:
                avg = sum(scores.values()) / len(scores)
                values = [scores.get(s, 0) for s in self.sessions]
                trend = self._calculate_trend(values)
                lines.append(f"\n{name}:")
                lines.append(f"  Average: {avg:.1f}/10")
                lines.append(f"  Trend: {trend}")
                lines.append(f"  Scores: {' → '.join(str(v) for v in values)}")
        
        lines.append("\n" + "-" * 80)
        lines.append("AUTOMATED METRICS - TRENDS")
        lines.append("-" * 80)
        
        if self.avg_tokens_per_turn:
            avg = sum(self.avg_tokens_per_turn.values()) / len(self.avg_tokens_per_turn)
            lines.append(f"\nTokens per Turn: {avg:.0f} (avg)")
            lines.append(f"  {' → '.join(f'{v:.0f}' for v in self.avg_tokens_per_turn.values())}")
        
        if self.avg_latency_ms:
            avg = sum(self.avg_latency_ms.values()) / len(self.avg_latency_ms)
            lines.append(f"\nAverage Latency: {avg:.0f}ms")
            lines.append(f"  {' → '.join(f'{v:.0f}ms' for v in self.avg_latency_ms.values())}")
        
        if self.actor_diversity:
            avg = sum(self.actor_diversity.values()) / len(self.actor_diversity)
            lines.append(f"\nActor Diversity (entropy): {avg:.2f}")
            lines.append(f"  {' → '.join(f'{v:.2f}' for v in self.actor_diversity.values())}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Determine if values are improving, declining, or stable."""
        if len(values) < 2:
            return "insufficient data"
        
        # Simple linear trend
        first_half = sum(values[:len(values)//2]) / max(len(values)//2, 1)
        second_half = sum(values[len(values)//2:]) / max(len(values) - len(values)//2, 1)
        
        diff = second_half - first_half
        
        if diff > 0.5:
            return "📈 improving"
        elif diff < -0.5:
            return "📉 declining"
        else:
            return "➡️  stable"


class SessionComparer:
    """Compare multiple sessions to track improvement."""
    
    def __init__(self, logs_dir: Path):
        self.logs_dir = Path(logs_dir)
    
    def compare(self, session_ids: Optional[List[str]] = None, limit: int = 10) -> SessionComparison:
        """Compare sessions and generate comparison object.
        
        Args:
            session_ids: Specific session IDs to compare, or None for most recent
            limit: Maximum number of sessions to compare if session_ids is None
            
        Returns:
            SessionComparison object with trends and statistics
        """
        comparison = SessionComparison()
        
        # Find sessions to compare
        if session_ids:
            sessions = session_ids
        else:
            # Get most recent sessions
            session_dirs = sorted([d for d in self.logs_dir.iterdir() if d.is_dir() and d.name.startswith('session-')],
                                reverse=True)[:limit]
            sessions = [d.name for d in session_dirs]
        
        comparison.sessions = sessions
        
        # Load reviews and metrics for each session
        for session_id in sessions:
            session_dir = self.logs_dir / session_id
            
            # Load review
            review_path = session_dir / "review.json"
            if review_path.exists():
                try:
                    with open(review_path, 'r', encoding='utf-8') as f:
                        review = json.load(f)
                    
                    overall = review.get('overall_score', 0)
                    if overall:
                        comparison.overall_scores[session_id] = overall
                    
                    nc = review.get('narrative_coherence', {}).get('score', 0)
                    if nc:
                        comparison.narrative_coherence_scores[session_id] = nc
                    
                    dp = review.get('dramatic_pacing', {}).get('score', 0)
                    if dp:
                        comparison.dramatic_pacing_scores[session_id] = dp
                    
                    ca = review.get('character_authenticity', {}).get('score', 0)
                    if ca:
                        comparison.character_authenticity_scores[session_id] = ca
                    
                    wr = review.get('world_responsiveness', {}).get('score', 0)
                    if wr:
                        comparison.world_responsiveness_scores[session_id] = wr
                    
                    pq = review.get('prose_quality', {}).get('score', 0)
                    if pq:
                        comparison.prose_quality_scores[session_id] = pq
                        
                except Exception as e:
                    print(f"Warning: Could not load review for {session_id}: {e}")
            
            # Load metrics
            metrics_path = session_dir / "session_metrics.json"
            if metrics_path.exists():
                try:
                    with open(metrics_path, 'r', encoding='utf-8') as f:
                        metrics = json.load(f)
                    
                    # Extract automated metrics
                    efficiency = metrics.get('system_efficiency', {})
                    total_tokens = efficiency.get('total_tokens', 0)
                    total_turns = metrics.get('dramatic_pacing', {}).get('total_turns', 1)
                    
                    if total_turns > 0:
                        comparison.avg_tokens_per_turn[session_id] = total_tokens / total_turns
                    
                    avg_latency = efficiency.get('avg_latency_ms', 0)
                    if avg_latency:
                        comparison.avg_latency_ms[session_id] = avg_latency
                    
                    entropy = metrics.get('narrative_coherence', {}).get('actor_usage_entropy', 0)
                    if entropy:
                        comparison.actor_diversity[session_id] = entropy
                        
                except Exception as e:
                    print(f"Warning: Could not load metrics for {session_id}: {e}")
        
        # Calculate aggregate statistics
        if comparison.overall_scores:
            comparison.avg_overall_score = sum(comparison.overall_scores.values()) / len(comparison.overall_scores)
            comparison.best_session = max(comparison.overall_scores.items(), key=lambda x: x[1])[0]
            comparison.worst_session = min(comparison.overall_scores.items(), key=lambda x: x[1])[0]
            
            # Determine overall trend
            score_values = [comparison.overall_scores.get(s, 0) for s in sessions]
            comparison.improvement_trend = comparison._calculate_trend(score_values).replace("📈 ", "").replace("📉 ", "").replace("➡️  ", "")
        
        return comparison
    
    def generate_report(self, session_ids: Optional[List[str]] = None, limit: int = 10, 
                       output_path: Optional[Path] = None) -> str:
        """Generate and optionally save a comparison report.
        
        Args:
            session_ids: Specific session IDs to compare, or None for most recent
            limit: Maximum number of sessions to compare if session_ids is None
            output_path: Path to save report, or None to just return string
            
        Returns:
            Report text
        """
        comparison = self.compare(session_ids, limit)
        report = comparison.to_report()
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report


def compare_sessions(logs_dir: str, session_ids: Optional[List[str]] = None, 
                    limit: int = 10, output_path: Optional[str] = None) -> str:
    """Convenience function to compare sessions.
    
    Args:
        logs_dir: Path to logs directory containing session folders
        session_ids: Specific session IDs to compare, or None for most recent
        limit: Maximum number of sessions if session_ids is None
        output_path: Optional path to save report
        
    Returns:
        Comparison report text
    """
    comparer = SessionComparer(Path(logs_dir))
    return comparer.generate_report(
        session_ids=session_ids,
        limit=limit,
        output_path=Path(output_path) if output_path else None
    )


if __name__ == "__main__":
    # CLI usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.core.compare_sessions <logs_dir> [limit] [output_file]")
        print("Example: python -m src.core.compare_sessions infinite-dnd/logs 5 comparison.txt")
        sys.exit(1)
    
    logs_dir = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    report = compare_sessions(logs_dir, limit=limit, output_path=output_file)
    print(report)
