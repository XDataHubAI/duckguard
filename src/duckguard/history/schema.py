"""Database schema for historical result storage.

Defines the SQLite schema for storing validation results over time,
enabling trend analysis and historical comparison.
"""

from __future__ import annotations

# Schema version for migrations
SCHEMA_VERSION = 1

# SQL to create all tables
CREATE_TABLES_SQL = """
-- Validation runs table: stores metadata for each validation execution
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    ruleset_name TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    quality_score REAL NOT NULL,
    total_checks INTEGER NOT NULL,
    passed_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    warning_count INTEGER NOT NULL,
    passed INTEGER NOT NULL,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Individual check results table
CREATE TABLE IF NOT EXISTS check_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    check_type TEXT NOT NULL,
    column_name TEXT,
    passed INTEGER NOT NULL,
    severity TEXT NOT NULL,
    actual_value TEXT,
    expected_value TEXT,
    message TEXT,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Sample of failed rows (limited to avoid large storage)
CREATE TABLE IF NOT EXISTS failed_rows_sample (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    check_id INTEGER,
    row_index INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    value TEXT,
    expected TEXT,
    reason TEXT,
    context TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(run_id),
    FOREIGN KEY (check_id) REFERENCES check_results(id)
);

-- Quality score trends (aggregated daily for efficient queries)
CREATE TABLE IF NOT EXISTS quality_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    date TEXT NOT NULL,
    avg_quality_score REAL NOT NULL,
    min_quality_score REAL NOT NULL,
    max_quality_score REAL NOT NULL,
    run_count INTEGER NOT NULL,
    passed_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    UNIQUE(source, date)
);

-- Schema metadata table
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_runs_source ON runs(source);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_source_started ON runs(source, started_at);
CREATE INDEX IF NOT EXISTS idx_check_results_run_id ON check_results(run_id);
CREATE INDEX IF NOT EXISTS idx_failed_rows_run_id ON failed_rows_sample(run_id);
CREATE INDEX IF NOT EXISTS idx_quality_trends_source_date ON quality_trends(source, date);
"""

# Pre-built queries for common operations
QUERIES = {
    "insert_run": """
        INSERT INTO runs (
            run_id, source, ruleset_name, started_at, finished_at,
            quality_score, total_checks, passed_count, failed_count,
            warning_count, passed, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "insert_check_result": """
        INSERT INTO check_results (
            run_id, check_type, column_name, passed, severity,
            actual_value, expected_value, message, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "insert_failed_row": """
        INSERT INTO failed_rows_sample (
            run_id, check_id, row_index, column_name, value, expected, reason, context
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "get_runs_for_source": """
        SELECT * FROM runs
        WHERE source = ?
        ORDER BY started_at DESC
        LIMIT ?
    """,
    "get_runs_in_period": """
        SELECT * FROM runs
        WHERE source = ?
          AND started_at >= ?
          AND started_at <= ?
        ORDER BY started_at DESC
    """,
    "get_all_runs": """
        SELECT * FROM runs
        ORDER BY started_at DESC
        LIMIT ?
    """,
    "get_quality_trend": """
        SELECT date, avg_quality_score, min_quality_score, max_quality_score,
               run_count, passed_count, failed_count
        FROM quality_trends
        WHERE source = ?
          AND date >= ?
        ORDER BY date
    """,
    "get_latest_run": """
        SELECT * FROM runs
        WHERE source = ?
        ORDER BY started_at DESC
        LIMIT 1
    """,
    "get_check_results_for_run": """
        SELECT * FROM check_results
        WHERE run_id = ?
        ORDER BY id
    """,
    "get_failed_rows_for_run": """
        SELECT * FROM failed_rows_sample
        WHERE run_id = ?
        ORDER BY id
    """,
    "upsert_trend": """
        INSERT INTO quality_trends (
            source, date, avg_quality_score, min_quality_score,
            max_quality_score, run_count, passed_count, failed_count
        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(source, date) DO UPDATE SET
            avg_quality_score = (
                (avg_quality_score * run_count + excluded.avg_quality_score)
                / (run_count + 1)
            ),
            min_quality_score = MIN(min_quality_score, excluded.min_quality_score),
            max_quality_score = MAX(max_quality_score, excluded.max_quality_score),
            run_count = run_count + 1,
            passed_count = passed_count + excluded.passed_count,
            failed_count = failed_count + excluded.failed_count
    """,
    "get_unique_sources": """
        SELECT DISTINCT source FROM runs
        ORDER BY source
    """,
    "delete_old_runs": """
        DELETE FROM runs
        WHERE started_at < ?
    """,
    "get_run_by_id": """
        SELECT * FROM runs
        WHERE run_id = ?
    """,
}
