#!/usr/bin/env python3
"""
Combine OTEL metrics with session JSONL files for comprehensive analysis.

Usage:
    python combine_sources.py [--db <database_file>]
    
Example:
    python combine_sources.py --db ~/claude_metrics.db
"""

import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime


def create_messages_table(conn):
    """Create table for session messages if not exists."""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TIMESTAMP,
            role TEXT,
            content_preview TEXT,
            tool_use TEXT,
            usage_input_tokens INTEGER,
            usage_output_tokens INTEGER,
            usage_cache_read INTEGER,
            usage_cache_creation INTEGER
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_session ON session_messages(session_id)
    ''')
    conn.commit()


def parse_session_jsonl(jsonl_path):
    """Parse a session JSONL file."""
    entries = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def find_session_files():
    """Find all session JSONL files."""
    claude_dir = Path.home() / '.claude' / 'projects'
    if not claude_dir.exists():
        return []
    
    return list(claude_dir.glob('**/*.jsonl'))


def extract_usage_from_entry(entry):
    """Extract usage info from a JSONL entry."""
    usage = entry.get('usage', {})
    return {
        'input_tokens': usage.get('input_tokens', 0),
        'output_tokens': usage.get('output_tokens', 0),
        'cache_read': usage.get('cache_read_input_tokens', 0),
        'cache_creation': usage.get('cache_creation_input_tokens', 0)
    }


def merge_data(db_path):
    """Merge OTEL metrics with session JSONL data."""
    conn = sqlite3.connect(db_path)
    create_messages_table(conn)
    cursor = conn.cursor()
    
    session_files = find_session_files()
    
    if not session_files:
        print("No session JSONL files found in ~/.claude/projects/")
        print("Make sure you have Claude Code sessions saved locally.")
        conn.close()
        return
    
    total_entries = 0
    for jsonl_file in session_files:
        session_id = jsonl_file.stem
        entries = parse_session_jsonl(jsonl_file)
        
        for entry in entries:
            role = entry.get('role', 'unknown')
            content = entry.get('content', '')
            
            # Handle content that might be a list
            if isinstance(content, list):
                if content and isinstance(content[0], dict):
                    content = content[0].get('text', str(content[0]))
                else:
                    content = str(content[0]) if content else ''
            
            content_preview = content[:200] if content else ''
            
            # Extract tool use info
            tool_use = None
            if isinstance(entry.get('content'), list):
                for item in entry.get('content', []):
                    if isinstance(item, dict) and item.get('type') == 'tool_use':
                        tool_use = item.get('name', 'unknown_tool')
                        break
            
            # Extract usage
            usage = extract_usage_from_entry(entry)
            
            cursor.execute('''
                INSERT INTO session_messages 
                (session_id, role, content_preview, tool_use, 
                 usage_input_tokens, usage_output_tokens, 
                 usage_cache_read, usage_cache_creation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, role, content_preview, tool_use,
                usage['input_tokens'], usage['output_tokens'],
                usage['cache_read'], usage['cache_creation']
            ))
            total_entries += 1
    
    conn.commit()
    conn.close()
    print(f"Merged {len(session_files)} session files with {total_entries} total entries")


def generate_combined_report(db_path):
    """Generate a report combining OTEL metrics and session data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    report = []
    report.append("# Combined Metrics Report")
    report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # OTEL metrics summary
    report.append("## OTEL Metrics Summary\n")
    
    cursor.execute('SELECT COUNT(DISTINCT session_id) FROM sessions')
    result = cursor.fetchone()[0]
    report.append(f"- **OTEL Sessions**: {result}")
    
    cursor.execute('SELECT SUM(value) FROM token_usage')
    result = cursor.fetchone()[0]
    report.append(f"- **OTEL Total Tokens**: {result:,}" if result else "- **OTEL Total Tokens**: 0")
    
    # Session JSONL summary
    report.append("\n## Session JSONL Summary\n")
    
    cursor.execute('SELECT COUNT(DISTINCT session_id) FROM session_messages')
    result = cursor.fetchone()[0]
    report.append(f"- **JSONL Sessions**: {result}")
    
    cursor.execute('SELECT COUNT(*) FROM session_messages')
    result = cursor.fetchone()[0]
    report.append(f"- **Total Messages**: {result:,}")
    
    cursor.execute('''
        SELECT role, COUNT(*) as count
        FROM session_messages
        GROUP BY role
    ''')
    for row in cursor.fetchall():
        report.append(f"- **{row[0]} messages**: {row[1]:,}")
    
    # Token usage from JSONL (if available)
    cursor.execute('''
        SELECT 
            SUM(usage_input_tokens) as input,
            SUM(usage_output_tokens) as output,
            SUM(usage_cache_read) as cache_read,
            SUM(usage_cache_creation) as cache_creation
        FROM session_messages
    ''')
    row = cursor.fetchone()
    if row[0]:
        report.append("\n## Token Usage from JSONL\n")
        report.append(f"- **Input Tokens**: {row[0]:,}")
        report.append(f"- **Output Tokens**: {row[1]:,}")
        report.append(f"- **Cache Read Tokens**: {row[2]:,}")
        report.append(f"- **Cache Creation Tokens**: {row[3]:,}")
    
    # Tool usage
    cursor.execute('''
        SELECT tool_use, COUNT(*) as count
        FROM session_messages
        WHERE tool_use IS NOT NULL
        GROUP BY tool_use
        ORDER BY count DESC
        LIMIT 10
    ''')
    tools = cursor.fetchall()
    if tools:
        report.append("\n## Most Used Tools\n")
        report.append("| Tool | Usage Count |")
        report.append("|------|-------------|")
        for row in tools:
            report.append(f"| {row[0]} | {row[1]:,} |")
    
    conn.close()
    return '\n'.join(report)


def main():
    parser = argparse.ArgumentParser(
        description='Combine OTEL metrics with session JSONL files'
    )
    parser.add_argument('--db', default='~/.claude-metrics/metrics.db',
                        help='Path to SQLite database file')
    parser.add_argument('--report', '-r', action='store_true',
                        help='Generate combined report after merging')
    parser.add_argument('--output', '-o', help='Output file for report')
    
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser()
    
    # Ensure database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Merge data
    merge_data(str(db_path))
    
    # Generate report if requested
    if args.report:
        report = generate_combined_report(str(db_path))
        if args.output:
            output_path = Path(args.output).expanduser()
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"Report saved to: {output_path}")
        else:
            print(report)


if __name__ == '__main__':
    main()
