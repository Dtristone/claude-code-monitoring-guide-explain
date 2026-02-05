#!/usr/bin/env python3
"""
Generate timeline visualization from local SQLite metrics database.

Usage:
    python generate_timeline.py [--db <database_file>] [--output <output_file>]
    
Example:
    python generate_timeline.py --db ~/claude_metrics.db --output timeline.html
"""

import sqlite3
import argparse
from datetime import datetime
from pathlib import Path


def get_timeline_data(cursor):
    """Get timeline data for all sessions."""
    cursor.execute('''
        SELECT 
            t.timestamp,
            t.session_id,
            t.token_type,
            t.value,
            t.model
        FROM token_usage t
        ORDER BY t.timestamp
    ''')
    
    return cursor.fetchall()


def generate_text_timeline(cursor):
    """Generate a text-based timeline."""
    timeline = []
    
    cursor.execute('''
        SELECT 
            t.timestamp,
            t.session_id,
            t.model,
            GROUP_CONCAT(t.token_type || ':' || t.value, ', ') as tokens
        FROM token_usage t
        GROUP BY t.timestamp, t.session_id, t.model
        ORDER BY t.timestamp
    ''')
    
    timeline.append("=" * 80)
    timeline.append("CLAUDE CODE METRICS TIMELINE")
    timeline.append("=" * 80)
    timeline.append("")
    
    current_session = None
    for row in cursor.fetchall():
        timestamp, session_id, model, tokens = row
        
        if session_id != current_session:
            current_session = session_id
            timeline.append(f"\n{'─' * 40}")
            timeline.append(f"SESSION: {session_id[:16]}...")
            timeline.append(f"MODEL: {model}")
            timeline.append(f"{'─' * 40}")
        
        timeline.append(f"  [{timestamp}] {tokens}")
    
    # Add summary
    cursor.execute('''
        SELECT 
            token_type,
            SUM(value) as total
        FROM token_usage
        GROUP BY token_type
    ''')
    
    timeline.append("\n" + "=" * 80)
    timeline.append("SUMMARY")
    timeline.append("=" * 80)
    for row in cursor.fetchall():
        timeline.append(f"  {row[0]}: {row[1]:,} tokens")
    
    return '\n'.join(timeline)


def generate_csv_timeline(cursor):
    """Generate CSV export of timeline data."""
    csv_lines = ['timestamp,session_id,model,token_type,value,cumulative']
    
    cursor.execute('''
        SELECT 
            t.timestamp,
            t.session_id,
            t.model,
            t.token_type,
            t.value,
            SUM(t.value) OVER (PARTITION BY t.token_type ORDER BY t.timestamp) as cumulative
        FROM token_usage t
        ORDER BY t.timestamp
    ''')
    
    for row in cursor.fetchall():
        csv_lines.append(','.join(str(x) for x in row))
    
    return '\n'.join(csv_lines)


def generate_html_timeline(cursor):
    """Generate an HTML timeline with basic visualization."""
    timeline_data = get_timeline_data(cursor)
    
    # Get totals for chart
    cursor.execute('''
        SELECT token_type, SUM(value) as total
        FROM token_usage
        GROUP BY token_type
    ''')
    totals = dict(cursor.fetchall())
    
    html = '''<!DOCTYPE html>
<html>
<head>
    <title>Claude Code Metrics Timeline</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: flex; justify-content: space-around; margin-bottom: 30px; flex-wrap: wrap; }
        .stat-box { background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; margin: 10px; min-width: 150px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #333; }
        .stat-label { color: #666; margin-top: 5px; }
        .timeline { margin-top: 20px; }
        .timeline-item { display: flex; margin-bottom: 10px; padding: 10px; background: #fafafa; border-radius: 4px; }
        .timeline-time { width: 200px; color: #666; font-size: 12px; }
        .timeline-content { flex: 1; }
        .token-input { color: #2196F3; }
        .token-output { color: #4CAF50; }
        .token-cacheRead { color: #9C27B0; }
        .token-cacheCreation { color: #FF9800; }
        .bar-chart { margin-top: 30px; }
        .bar { height: 30px; margin-bottom: 5px; border-radius: 4px; display: flex; align-items: center; padding-left: 10px; color: white; font-weight: bold; }
        .bar-input { background: #2196F3; }
        .bar-output { background: #4CAF50; }
        .bar-cacheRead { background: #9C27B0; }
        .bar-cacheCreation { background: #FF9800; }
        .bar-unknown { background: #607D8B; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Claude Code Metrics Timeline</h1>
        <p>Generated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
    </div>
    
    <div class="summary">
'''
    
    # Add summary boxes
    for token_type, total in totals.items():
        html += f'''
        <div class="stat-box">
            <div class="stat-value">{total:,}</div>
            <div class="stat-label">{token_type} tokens</div>
        </div>
'''
    
    html += '''
    </div>
    
    <h2>Token Distribution</h2>
    <div class="bar-chart">
'''
    
    # Add bar chart
    max_val = max(totals.values()) if totals else 1
    for token_type, total in totals.items():
        width = (total / max_val) * 100
        html += f'        <div class="bar bar-{token_type}" style="width: {max(width, 5)}%">{token_type}: {total:,}</div>\n'
    
    html += '''
    </div>
    
    <h2>Timeline</h2>
    <div class="timeline">
'''
    
    # Add timeline items (limit to last 100)
    for row in timeline_data[-100:]:
        timestamp, session_id, token_type, value, model = row
        html += f'''
        <div class="timeline-item">
            <div class="timeline-time">{timestamp}</div>
            <div class="timeline-content">
                <span class="token-{token_type}">{token_type}</span>: {value:,} tokens
                <small style="color: #999">({model})</small>
            </div>
        </div>
'''
    
    html += '''
    </div>
</body>
</html>
'''
    
    return html


def generate_timeline(db_path, output_path=None, format='text'):
    """Generate timeline from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if format == 'html':
        content = generate_html_timeline(cursor)
    elif format == 'csv':
        content = generate_csv_timeline(cursor)
    else:
        content = generate_text_timeline(cursor)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"Timeline saved to: {output_path}")
    else:
        print(content)
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Generate timeline visualization from local SQLite metrics database'
    )
    parser.add_argument('--db', default='~/.claude-metrics/metrics.db',
                        help='Path to SQLite database file')
    parser.add_argument('--output', '-o', help='Output file path (default: print to stdout)')
    parser.add_argument('--format', '-f', choices=['text', 'html', 'csv'], default='text',
                        help='Output format (default: text)')
    
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser()
    output_path = Path(args.output).expanduser() if args.output else None
    
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        print("Run parse_otel_metrics.py first to create the database.")
        return 1
    
    generate_timeline(str(db_path), str(output_path) if output_path else None, args.format)
    return 0


if __name__ == '__main__':
    exit(main())
