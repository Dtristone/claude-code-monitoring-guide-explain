#!/usr/bin/env python3
"""
Generate reports from local SQLite metrics database.

Usage:
    python generate_local_report.py [--db <database_file>] [--output <output_file>]
    
Example:
    python generate_local_report.py --db ~/claude_metrics.db --output report.md
"""

import sqlite3
import argparse
from datetime import datetime
from pathlib import Path


def get_summary_stats(cursor):
    """Get overall summary statistics."""
    stats = {}
    
    # Total sessions
    cursor.execute('SELECT COUNT(DISTINCT session_id) FROM sessions')
    stats['total_sessions'] = cursor.fetchone()[0]
    
    # Total tokens by type
    cursor.execute('''
        SELECT token_type, SUM(value) as total
        FROM token_usage
        GROUP BY token_type
    ''')
    stats['tokens_by_type'] = dict(cursor.fetchall())
    
    # Total cost
    cursor.execute('SELECT SUM(value) FROM cost_usage')
    result = cursor.fetchone()[0]
    stats['total_cost'] = result if result else 0
    
    # Total active time
    cursor.execute('SELECT SUM(value) FROM active_time')
    result = cursor.fetchone()[0]
    stats['total_active_time'] = result if result else 0
    
    # Model usage
    cursor.execute('''
        SELECT model, SUM(value) as total
        FROM token_usage
        GROUP BY model
    ''')
    stats['tokens_by_model'] = dict(cursor.fetchall())
    
    # Cost by model
    cursor.execute('''
        SELECT model, SUM(value) as total
        FROM cost_usage
        GROUP BY model
    ''')
    stats['cost_by_model'] = dict(cursor.fetchall())
    
    return stats


def get_session_details(cursor):
    """Get detailed session information."""
    cursor.execute('''
        SELECT 
            s.session_id,
            s.model,
            s.started_at,
            COALESCE(SUM(CASE WHEN t.token_type = 'input' THEN t.value ELSE 0 END), 0) as input_tokens,
            COALESCE(SUM(CASE WHEN t.token_type = 'output' THEN t.value ELSE 0 END), 0) as output_tokens,
            COALESCE(SUM(CASE WHEN t.token_type = 'cacheRead' THEN t.value ELSE 0 END), 0) as cache_read,
            COALESCE(SUM(CASE WHEN t.token_type = 'cacheCreation' THEN t.value ELSE 0 END), 0) as cache_creation,
            COALESCE((SELECT SUM(value) FROM cost_usage WHERE session_id = s.session_id), 0) as cost,
            COALESCE((SELECT SUM(value) FROM active_time WHERE session_id = s.session_id), 0) as active_seconds
        FROM sessions s
        LEFT JOIN token_usage t ON s.session_id = t.session_id
        GROUP BY s.session_id
        ORDER BY s.started_at DESC
    ''')
    
    columns = ['session_id', 'model', 'started_at', 'input_tokens', 'output_tokens', 
               'cache_read', 'cache_creation', 'cost', 'active_seconds']
    
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def calculate_cache_metrics(cursor):
    """Calculate cache efficiency metrics."""
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN token_type = 'cacheRead' THEN value ELSE 0 END) as cache_read,
            SUM(CASE WHEN token_type = 'cacheCreation' THEN value ELSE 0 END) as cache_creation,
            SUM(CASE WHEN token_type = 'input' THEN value ELSE 0 END) as input
        FROM token_usage
    ''')
    
    row = cursor.fetchone()
    cache_read = row[0] or 0
    cache_creation = row[1] or 0
    input_tokens = row[2] or 0
    
    metrics = {
        'cache_read_tokens': cache_read,
        'cache_creation_tokens': cache_creation,
        'input_tokens': input_tokens,
        'cache_hit_ratio': cache_read / (cache_read + cache_creation) if (cache_read + cache_creation) > 0 else 0,
        'cache_efficiency': cache_read / (cache_read + input_tokens) if (cache_read + input_tokens) > 0 else 0,
        'cache_read_creation_ratio': cache_read / cache_creation if cache_creation > 0 else 0,
        # Estimated cost savings (cache reads cost ~10% of regular input)
        'estimated_savings': cache_read * 0.000003 * 0.9
    }
    
    return metrics


def generate_markdown_report(stats, sessions, cache_metrics):
    """Generate a markdown report."""
    report = []
    
    report.append("# Claude Code Local Metrics Report")
    report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Summary section
    report.append("## Summary\n")
    report.append(f"- **Total Sessions**: {stats['total_sessions']}")
    report.append(f"- **Total Cost**: ${stats['total_cost']:.4f}")
    report.append(f"- **Total Active Time**: {stats['total_active_time']:.1f} seconds ({stats['total_active_time']/60:.1f} minutes)")
    
    # Token usage
    report.append("\n## Token Usage\n")
    report.append("| Type | Count |")
    report.append("|------|-------|")
    for token_type, count in stats['tokens_by_type'].items():
        report.append(f"| {token_type} | {count:,} |")
    
    total_tokens = sum(stats['tokens_by_type'].values()) if stats['tokens_by_type'] else 0
    report.append(f"| **Total** | **{total_tokens:,}** |")
    
    # Cost by model
    if stats['cost_by_model']:
        report.append("\n## Cost by Model\n")
        report.append("| Model | Cost (USD) |")
        report.append("|-------|------------|")
        for model, cost in stats['cost_by_model'].items():
            report.append(f"| {model} | ${cost:.4f} |")
    
    # Cache metrics
    report.append("\n## Cache Efficiency\n")
    report.append(f"- **Cache Read Tokens**: {cache_metrics['cache_read_tokens']:,}")
    report.append(f"- **Cache Creation Tokens**: {cache_metrics['cache_creation_tokens']:,}")
    report.append(f"- **Cache Hit Ratio**: {cache_metrics['cache_hit_ratio']*100:.1f}%")
    report.append(f"- **Cache Efficiency**: {cache_metrics['cache_efficiency']*100:.1f}%")
    report.append(f"- **Cache Read:Creation Ratio**: {cache_metrics['cache_read_creation_ratio']:.1f}:1")
    report.append(f"- **Estimated Cost Savings**: ${cache_metrics['estimated_savings']:.4f}")
    
    # Session details
    report.append("\n## Session Details\n")
    report.append("| Session ID | Model | Input | Output | Cache Read | Cost |")
    report.append("|------------|-------|-------|--------|------------|------|")
    for session in sessions[:20]:  # Limit to 20 sessions
        session_short = session['session_id'][:8] + '...' if len(session['session_id']) > 12 else session['session_id']
        report.append(f"| {session_short} | {session['model']} | {session['input_tokens']:,} | {session['output_tokens']:,} | {session['cache_read']:,} | ${session['cost']:.4f} |")
    
    if len(sessions) > 20:
        report.append(f"\n*Showing 20 of {len(sessions)} sessions*")
    
    return '\n'.join(report)


def generate_report(db_path, output_path=None):
    """Generate a full report from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    stats = get_summary_stats(cursor)
    sessions = get_session_details(cursor)
    cache_metrics = calculate_cache_metrics(cursor)
    
    report = generate_markdown_report(stats, sessions, cache_metrics)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"Report saved to: {output_path}")
    else:
        print(report)
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Generate reports from local SQLite metrics database'
    )
    parser.add_argument('--db', default='~/.claude-metrics/metrics.db',
                        help='Path to SQLite database file')
    parser.add_argument('--output', '-o', help='Output file path (default: print to stdout)')
    
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser()
    output_path = Path(args.output).expanduser() if args.output else None
    
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        print("Run parse_otel_metrics.py first to create the database.")
        return 1
    
    generate_report(str(db_path), str(output_path) if output_path else None)
    return 0


if __name__ == '__main__':
    exit(main())
