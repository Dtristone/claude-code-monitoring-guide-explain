#!/usr/bin/env python3
"""
Parse OTEL console output and store metrics in SQLite database.

Usage:
    python parse_otel_metrics.py <log_file> [--db <database_file>]
    
Example:
    python parse_otel_metrics.py ~/claude_metrics.log --db ~/claude_metrics.db
"""

import re
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path


def create_database(db_path):
    """Create SQLite database with schema for OTEL metrics."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript('''
        -- Sessions table
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            user_id TEXT,
            model TEXT,
            started_at TIMESTAMP,
            ended_at TIMESTAMP
        );
        
        -- Token usage table
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model TEXT,
            token_type TEXT,  -- input, output, cacheRead, cacheCreation
            value INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        -- Cost usage table
        CREATE TABLE IF NOT EXISTS cost_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model TEXT,
            value REAL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        -- Active time table
        CREATE TABLE IF NOT EXISTS active_time (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            value REAL,  -- seconds
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        -- Code activity table
        CREATE TABLE IF NOT EXISTS code_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activity_type TEXT,  -- commit, pull_request, lines_of_code
            value INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        -- Raw metrics table (for debugging)
        CREATE TABLE IF NOT EXISTS raw_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metric_name TEXT,
            raw_json TEXT
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_token_session ON token_usage(session_id);
        CREATE INDEX IF NOT EXISTS idx_token_type ON token_usage(token_type);
        CREATE INDEX IF NOT EXISTS idx_cost_session ON cost_usage(session_id);
        CREATE INDEX IF NOT EXISTS idx_activity_session ON code_activity(session_id);
    ''')
    
    conn.commit()
    return conn


def parse_metric_block(block):
    """Parse a single metric block from console output."""
    try:
        # Clean up JavaScript-style output to valid JSON
        # Replace single quotes with double quotes
        cleaned = block.replace("'", '"')
        # Handle unquoted keys
        cleaned = re.sub(r'(\w+):', r'"\1":', cleaned)
        # Handle trailing commas
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def extract_metrics_from_log(log_content):
    """Extract all metric blocks from log file content."""
    metrics = []
    
    # Split by metric markers and parse
    blocks = re.split(r'(?=\{\s*descriptor:)', log_content)
    
    for block in blocks:
        if 'descriptor:' in block:
            # Find the complete JSON object
            brace_count = 0
            start = block.find('{')
            if start == -1:
                continue
                
            end = start
            for i, char in enumerate(block[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            metric_str = block[start:end]
            parsed = parse_metric_block(metric_str)
            if parsed:
                metrics.append(parsed)
    
    return metrics


def store_metric(conn, metric, timestamp=None):
    """Store a parsed metric in the database."""
    if not metric or 'descriptor' not in metric:
        return
    
    cursor = conn.cursor()
    timestamp = timestamp or datetime.now().isoformat()
    
    descriptor = metric.get('descriptor', {})
    metric_name = descriptor.get('name', '')
    data_points = metric.get('dataPoints', [])
    
    # Store raw metric for debugging
    cursor.execute(
        'INSERT INTO raw_metrics (timestamp, metric_name, raw_json) VALUES (?, ?, ?)',
        (timestamp, metric_name, json.dumps(metric))
    )
    
    for dp in data_points:
        attrs = dp.get('attributes', {})
        session_id = attrs.get('session.id', attrs.get('session_id', 'unknown'))
        user_id = attrs.get('user.id', attrs.get('user_id', 'unknown'))
        model = attrs.get('model', 'unknown')
        value = dp.get('value', 0)
        
        # Ensure session exists
        cursor.execute('''
            INSERT OR IGNORE INTO sessions (session_id, user_id, model, started_at)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, model, timestamp))
        
        # Store based on metric type
        if 'token' in metric_name.lower():
            token_type = attrs.get('type', 'unknown')
            cursor.execute('''
                INSERT INTO token_usage (session_id, timestamp, model, token_type, value)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, timestamp, model, token_type, value))
            
        elif 'cost' in metric_name.lower():
            cursor.execute('''
                INSERT INTO cost_usage (session_id, timestamp, model, value)
                VALUES (?, ?, ?, ?)
            ''', (session_id, timestamp, model, value))
            
        elif 'active_time' in metric_name.lower():
            cursor.execute('''
                INSERT INTO active_time (session_id, timestamp, value)
                VALUES (?, ?, ?)
            ''', (session_id, timestamp, value))
            
        elif any(x in metric_name.lower() for x in ['commit', 'pull_request', 'lines_of_code']):
            activity_type = metric_name.split('.')[-1] if '.' in metric_name else metric_name
            cursor.execute('''
                INSERT INTO code_activity (session_id, timestamp, activity_type, value)
                VALUES (?, ?, ?, ?)
            ''', (session_id, timestamp, activity_type, value))
    
    conn.commit()


def parse_log_file(log_path, db_path):
    """Parse a log file and store metrics in database."""
    print(f"Parsing log file: {log_path}")
    print(f"Database: {db_path}")
    
    with open(log_path, 'r') as f:
        content = f.read()
    
    conn = create_database(db_path)
    metrics = extract_metrics_from_log(content)
    
    print(f"Found {len(metrics)} metric blocks")
    
    for metric in metrics:
        store_metric(conn, metric)
    
    # Print summary
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(DISTINCT session_id) FROM sessions')
    session_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM token_usage')
    token_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM cost_usage')
    cost_count = cursor.fetchone()[0]
    
    print(f"\nSummary:")
    print(f"  Sessions: {session_count}")
    print(f"  Token records: {token_count}")
    print(f"  Cost records: {cost_count}")
    
    conn.close()
    print(f"\nDatabase saved to: {db_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Parse OTEL console output and store in SQLite database'
    )
    parser.add_argument('log_file', help='Path to log file with OTEL console output')
    parser.add_argument('--db', default='~/.claude-metrics/metrics.db',
                        help='Path to SQLite database file')
    
    args = parser.parse_args()
    
    log_path = Path(args.log_file).expanduser()
    db_path = Path(args.db).expanduser()
    
    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not log_path.exists():
        print(f"Error: Log file not found: {log_path}")
        return 1
    
    parse_log_file(str(log_path), str(db_path))
    return 0


if __name__ == '__main__':
    exit(main())
