"""
Compare multiple game sessions to track improvement over time.

Usage:
    python compare_sessions.py [--limit N] [--output FILE]
"""

import argparse
from pathlib import Path
from src.core.compare_sessions import compare_sessions


def main():
    parser = argparse.ArgumentParser(
        description="Compare D&D AI sessions to track improvement in guiding principles"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of recent sessions to compare (default: 10)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Optional output file for the report (default: print to console)"
    )
    parser.add_argument(
        "--sessions",
        nargs="+",
        help="Specific session IDs to compare (e.g., session-20260202-150430)"
    )
    
    args = parser.parse_args()
    
    # Default logs directory
    logs_dir = Path(__file__).parent / "logs"
    
    if not logs_dir.exists():
        print(f"Error: Logs directory not found at {logs_dir}")
        return 1
    
    print(f"Analyzing sessions in {logs_dir}...")
    
    report = compare_sessions(
        str(logs_dir),
        session_ids=args.sessions,
        limit=args.limit,
        output_path=args.output
    )
    
    print(report)
    
    if args.output:
        print(f"\n✅ Report saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    exit(main())
