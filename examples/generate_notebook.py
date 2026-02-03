#!/usr/bin/env python3
"""Generate the DuckGuard 3.0 Complete Guide notebook (getting_started.ipynb).

This script programmatically builds the Jupyter notebook JSON and writes it
to examples/getting_started.ipynb.
"""

import json
import os

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def md(source_lines):
    """Create a markdown cell."""
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": _to_source(source_lines),
    }


def code(source_lines):
    """Create a code cell."""
    return {
        "cell_type": "code",
        "metadata": {},
        "source": _to_source(source_lines),
        "outputs": [],
        "execution_count": None,
    }


def _to_source(lines):
    """Convert lines to the notebook source list (each element ends with \\n except last)."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    result = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            result.append(line + "\n")
        else:
            result.append(line)
    return result


# ---------------------------------------------------------------------------
# Build cells
# ---------------------------------------------------------------------------

cells = []

# ===== 1. Introduction & Setup ==============================================

cells.append(md([
    "# DuckGuard 3.0 - Complete Guide",
    "",
    "A comprehensive walkthrough of **every** feature in DuckGuard 3.0 -- the Python-native data quality toolkit built on DuckDB.",
    "",
    "Topics covered:",
    "",
    "| # | Section | # | Section |",
    "|---|---------|---|---------|",
    "| 1 | Introduction & Setup | 12 | Multi-Column Checks |",
    "| 2 | Connecting to Data | 13 | Query-Based Checks |",
    "| 3 | Exploring Columns | 14 | Distributional Checks |",
    "| 4 | Column Validation | 15 | Anomaly Detection |",
    "| 5 | Row-Level Error Debugging | 16 | Auto-Profiling & Semantic Types |",
    "| 6 | Quality Scoring | 17 | YAML Rules & Data Contracts |",
    "| 7 | Cross-Dataset Validation | 18 | Reports & Notifications |",
    "| 8 | Reconciliation | 19 | Freshness, Schema & History |",
    "| 9 | Distribution Drift Detection | 20 | Integrations |",
    "| 10 | Group-By Validation | 21 | Enhanced Error Messages |",
    "| 11 | Conditional Checks | 22 | Quick Reference |",
]))

cells.append(md([
    "## 1. Introduction & Setup",
]))

cells.append(code([
    "# Install DuckGuard (uncomment if running in Colab / fresh environment)",
    "# !pip install duckguard",
]))

# --- Sample data -----------------------------------------------------------

cells.append(md([
    "### Create sample data",
    "",
    "We write an in-memory CSV string to a file so every cell is self-contained.",
]))

cells.append(code([
    'import os, csv, io',
    '',
    'ORDERS_CSV = """order_id,customer_id,product_name,quantity,unit_price,subtotal,tax,shipping,total_amount,status,country,email,phone,created_at,ship_date',
    'ORD-001,C100,Widget A,2,25.00,50.00,4.50,5.00,59.50,shipped,US,alice@example.com,+12125551001,2024-01-15,2024-01-17',
    'ORD-002,C101,Widget B,1,49.99,49.99,4.50,5.00,59.49,shipped,US,bob@example.com,+12125551002,2024-01-16,2024-01-18',
    'ORD-003,C102,Gadget X,3,15.00,45.00,4.05,5.00,54.05,delivered,UK,carol@example.co.uk,+442071234567,2024-01-16,2024-01-19',
    'ORD-004,C103,Widget A,1,25.00,25.00,2.25,5.00,32.25,pending,US,dave@example.com,+12125551004,2024-01-17,',
    'ORD-005,C100,Gadget Y,500,10.00,5000.00,450.00,5.00,5455.00,shipped,CA,alice@example.com,+12125551001,2024-01-17,2024-01-19',
    'ORD-006,C104,Widget C,2,35.00,70.00,6.30,5.00,81.30,shipped,US,eve@example.com,,2024-01-18,2024-01-20',
    'ORD-007,C105,Gadget X,1,15.00,15.00,1.35,5.00,21.35,cancelled,DE,frank@example.de,+4930123456,2024-01-18,',
    'ORD-008,C106,Widget B,4,49.99,199.96,18.00,5.00,222.96,delivered,US,grace@example.com,+12125551008,2024-01-19,2024-01-22',
    'ORD-009,C107,Premium Z,1,999.99,999.99,90.00,0.00,1089.99,shipped,JP,hiro@example.jp,+81312345678,2024-01-19,2024-01-23',
    'ORD-010,C108,Widget A,10,25.00,250.00,22.50,5.00,277.50,pending,US,ivan@example.com,+12125551010,2024-01-20,',
    'ORD-011,C109,Gadget Y,2,10.00,20.00,1.80,5.00,26.80,shipped,UK,jane@example.co.uk,+442079876543,2024-01-20,2024-01-22',
    'ORD-012,C110,Widget C,1,35.00,35.00,3.15,5.00,43.15,delivered,US,karl@example.com,+12125551012,2024-01-21,2024-01-23',
    'ORD-013,C111,Premium Z,2,999.99,1999.98,180.00,0.00,2179.98,pending,CA,liam@example.ca,+14165551013,2024-01-21,',
    'ORD-014,C112,Widget A,3,25.00,75.00,6.75,5.00,86.75,shipped,US,,+12125551014,2024-01-22,2024-01-24',
    'ORD-015,C113,Gadget X,1,15.00,15.00,1.35,5.00,21.35,shipped,DE,nina@example.de,+4930234567,2024-01-22,2024-01-25',
    'ORD-016,C114,Widget B,2,49.99,99.98,9.00,5.00,113.98,delivered,US,oscar@example.com,+12125551016,2024-01-23,2024-01-25',
    'ORD-017,C115,Gadget Y,5,10.00,50.00,4.50,5.00,59.50,shipped,UK,pat@example.co.uk,+442071239999,2024-01-23,2024-01-26',
    'ORD-018,C116,Widget C,1,35.00,35.00,3.15,5.00,43.15,pending,US,quinn@example.com,+12125551018,2024-01-24,',
    'ORD-019,C117,Premium Z,1,999.99,999.99,90.00,0.00,1089.99,cancelled,JP,rina@example.jp,,2024-01-24,',
    'ORD-020,C118,Widget A,2,25.00,50.00,4.50,5.00,59.50,shipped,CA,sam@example.ca,+14165551020,2024-01-25,2024-01-27',
    'ORD-021,C119,Gadget X,4,15.00,60.00,5.40,5.00,70.40,delivered,US,tom@example.com,+12125551021,2024-01-25,2024-01-28',
    'ORD-022,,Widget B,1,49.99,49.99,4.50,5.00,59.49,pending,US,,+12125551022,2024-01-26,',
    'ORD-023,C121,Gadget Y,-2,10.00,-20.00,-1.80,5.00,-16.80,returned,DE,uma@example.de,+4930345678,2024-01-26,',
    'ORD-024,C122,Widget A,1,25.00,25.00,2.25,5.00,32.25,shipped,US,vera@example.com,+12125551024,2024-01-27,2024-01-29',
    'ORD-025,C123,Premium Z,1,999.99,999.99,90.00,0.00,1089.99,shipped,UK,will@example.co.uk,+442071231111,2024-01-27,2024-01-30',
    'ORD-026,C124,Widget C,3,35.00,105.00,9.45,5.00,119.45,delivered,CA,xena@example.ca,+14165551026,2024-01-28,2024-01-30',
    'ORD-027,C125,Gadget X,2,15.00,30.00,2.70,5.00,37.70,shipped,US,yuri@example.com,+12125551027,2024-01-28,2024-01-31',
    'ORD-028,C126,Widget B,1,49.99,49.99,4.50,5.00,59.49,pending,JP,zoe@example.jp,+81312349999,2024-01-29,',
    'ORD-029,C127,Gadget Y,0,10.00,0.00,0.00,5.00,5.00,cancelled,US,adam@example.com,+12125551029,2024-01-29,',
    'ORD-030,C128,Widget A,1,25.00,25.00,2.25,5.00,32.25,shipped,DE,beth@example.de,+4930456789,2024-01-30,2024-02-01',
    '"""',
    '',
    '# Write to file',
    'os.makedirs("sample_data", exist_ok=True)',
    'with open("sample_data/orders.csv", "w", newline="") as f:',
    '    f.write(ORDERS_CSV.strip())',
    '',
    'print("[OK] sample_data/orders.csv written (" + str(len(ORDERS_CSV.strip().splitlines())-1) + " data rows)")',
]))

# --- YAML rules file -------------------------------------------------------

cells.append(code([
    '# Also create a duckguard.yaml rules file for later use',
    'RULES_YAML = """',
    'name: orders_validation',
    'description: Quality checks for the orders dataset',
    '',
    'columns:',
    '  order_id:',
    '    checks:',
    '      - type: not_null',
    '      - type: unique',
    '',
    '  customer_id:',
    '    checks:',
    '      - type: not_null',
    '',
    '  quantity:',
    '    checks:',
    '      - type: between',
    '        value: [1, 1000]',
    '',
    '  status:',
    '    checks:',
    '      - type: allowed_values',
    '        value: [pending, shipped, delivered, cancelled, returned]',
    '"""',
    '',
    'with open("sample_data/duckguard.yaml", "w") as f:',
    '    f.write(RULES_YAML.strip())',
    '',
    'print("[OK] sample_data/duckguard.yaml written")',
]))

# --- Imports ---------------------------------------------------------------

cells.append(md([
    "### Imports",
]))

cells.append(code([
    'from duckguard import (',
    '    connect,',
    '    AutoProfiler,',
    '    SemanticAnalyzer,',
    '    detect_type,',
    '    detect_types_for_dataset,',
    '    load_rules_from_string,',
    '    execute_rules,',
    '    generate_rules,',
    '    RuleSet,',
    '    generate_contract,',
    '    validate_contract,',
    '    diff_contracts,',
    '    detect_anomalies,',
    '    AnomalyDetector,',
    '    ColumnNotFoundError,',
    '    ValidationError,',
    '    UnsupportedConnectorError,',
    ')',
    'from duckguard.contracts import contract_to_yaml',
    'from duckguard.anomaly import BaselineMethod, KSTestMethod, SeasonalMethod',
    'from duckguard.freshness import FreshnessMonitor',
    'from duckguard.schema_history import SchemaTracker, SchemaChangeAnalyzer',
    'from duckguard.history import HistoryStorage, TrendAnalyzer',
    'from duckguard.notifications import (',
    '    EmailNotifier,',
    '    SlackNotifier,',
    '    TeamsNotifier,',
    '    format_results_text,',
    '    format_results_markdown,',
    ')',
    'from duckguard.reports import generate_html_report',
    '',
    'import tempfile, os, shutil',
    '',
    'print("[OK] All imports successful - DuckGuard", end=" ")',
    'from duckguard import __version__',
    'print(__version__)',
]))

# ===== 2. Connecting to Data ================================================

cells.append(md([
    "## 2. Connecting to Data",
]))

cells.append(code([
    '# Connect to the CSV file',
    'orders = connect("sample_data/orders.csv")',
    '',
    '# Dataset metadata',
    'print("Row count  :", orders.row_count)',
    'print("Columns    :", orders.columns)',
    'print("Col count  :", orders.column_count)',
]))

cells.append(code([
    '# Preview the first 5 rows',
    'for row in orders.head(5):',
    '    print(row)',
]))

cells.append(code([
    '# --- Alternative connection methods (commented) --------------------------',
    '#',
    '# Parquet',
    '# orders = connect("data/orders.parquet")',
    '#',
    '# JSON / NDJSON',
    '# orders = connect("data/orders.json")',
    '#',
    '# Amazon S3',
    '# orders = connect("s3://my-bucket/orders.parquet")',
    '#',
    '# PostgreSQL',
    '# orders = connect("postgresql://user:pass@localhost:5432/mydb", table="orders")',
    '#',
    '# Snowflake',
    '# orders = connect("snowflake://user:pass@account/db/schema", table="orders")',
    '#',
    '# pandas DataFrame',
    '# import pandas as pd',
    '# df = pd.read_csv("orders.csv")',
    '# orders = connect(df)',
]))

# ===== 3. Exploring Columns ================================================

cells.append(md([
    "## 3. Exploring Columns",
]))

cells.append(code([
    '# Access columns via dot notation or bracket notation',
    'col_status = orders.status          # dot notation',
    'col_email  = orders["email"]        # bracket notation',
    '',
    '# String column statistics',
    'print("=== status column ===")',
    'print("Null count   :", col_status.null_count)',
    'print("Unique count :", col_status.unique_count)',
    '',
    '# Numeric column statistics',
    'qty = orders.quantity',
    'print("\\n=== quantity column ===")',
    'print("Min    :", qty.min)',
    'print("Max    :", qty.max)',
    'print("Mean   :", qty.mean)',
    'print("Median :", qty.median)',
    'print("Stddev :", qty.stddev)',
]))

cells.append(code([
    '# Value counts - top values by frequency',
    'print("Status value counts:")',
    'for val, cnt in orders.status.get_value_counts().items():',
    '    print(f"  {val}: {cnt}")',
]))

cells.append(code([
    '# Distinct values',
    'print("Distinct countries:", orders.country.get_distinct_values())',
]))

# ===== 4. Column Validation =================================================

cells.append(md([
    "## 4. Column Validation",
]))

cells.append(code([
    '# is_not_null - check that a column has no nulls',
    'result = orders.order_id.is_not_null()',
    'print("[PASS]" if result.passed else "[FAIL]", "order_id is_not_null:", result.message)',
    '',
    '# is_unique - check that all values are unique',
    'result = orders.order_id.is_unique()',
    'print("[PASS]" if result.passed else "[FAIL]", "order_id is_unique:", result.message)',
]))

cells.append(code([
    '# between - range check',
    'result = orders.unit_price.between(1, 2000)',
    'print("[PASS]" if result.passed else "[FAIL]", "unit_price between(1,2000):", result.message)',
    '',
    '# greater_than / less_than',
    'result = orders.unit_price.greater_than(0)',
    'print("[PASS]" if result.passed else "[FAIL]", "unit_price > 0:", result.message)',
    '',
    'result = orders.unit_price.less_than(5000)',
    'print("[PASS]" if result.passed else "[FAIL]", "unit_price < 5000:", result.message)',
]))

cells.append(code([
    '# matches - regex pattern check',
    'result = orders.order_id.matches(r"^ORD-\\d{3}$")',
    'print("[PASS]" if result.passed else "[FAIL]", "order_id pattern:", result.message)',
]))

cells.append(code([
    '# isin - enum / allowed values check',
    'allowed = ["pending", "shipped", "delivered", "cancelled", "returned"]',
    'result = orders.status.isin(allowed)',
    'print("[PASS]" if result.passed else "[FAIL]", "status isin:", result.message)',
]))

cells.append(code([
    '# has_no_duplicates',
    'result = orders.order_id.has_no_duplicates()',
    'print("[PASS]" if result.passed else "[FAIL]", "order_id no duplicates:", result.message)',
]))

cells.append(code([
    '# value_lengths_between - string length range',
    'result = orders.order_id.value_lengths_between(5, 10)',
    'print("[PASS]" if result.passed else "[FAIL]", "order_id length [5,10]:", result.message)',
]))

# ===== 5. Row-Level Error Debugging =========================================

cells.append(md([
    "## 5. Row-Level Error Debugging",
    "",
    "When a validation fails, DuckGuard captures the offending rows so you can debug immediately.",
]))

cells.append(code([
    '# Intentionally trigger a failure: quantity should be between 1 and 100',
    'result = orders.quantity.between(1, 100)',
    'print("Passed:", result.passed)',
    'print()',
    'print(result.summary())',
]))

cells.append(code([
    '# Iterate over individual failed rows',
    'for row in result.failed_rows:',
    '    print(f"  Row {row.row_number}: value={row.value}, expected={row.expected}, reason={row.reason}")',
]))

cells.append(code([
    '# Convenience helpers',
    'print("Failed values       :", result.get_failed_values())',
    'print("Failed row indices  :", result.get_failed_row_indices())',
]))

cells.append(code([
    '# Disable failure capture for performance on large datasets',
    'result_fast = orders.quantity.between(1, 100, capture_failures=False)',
    'print("Passed:", result_fast.passed, "| failed_rows captured:", len(result_fast.failed_rows))',
]))

# ===== 6. Quality Scoring ===================================================

cells.append(md([
    "## 6. Quality Scoring",
]))

cells.append(code([
    'score = orders.score()',
    'print("Overall score :", score.overall)',
    'print("Grade         :", score.grade)',
    'print("Completeness  :", score.completeness)',
    'print("Uniqueness    :", score.uniqueness)',
    'print("Validity      :", score.validity)',
    'print("Consistency   :", score.consistency)',
]))

# ===== 7. Cross-Dataset Validation ==========================================

cells.append(md([
    "## 7. Cross-Dataset Validation",
]))

cells.append(code([
    '# Create temporary CSV files for cross-dataset checks',
    'tmpdir = tempfile.mkdtemp(prefix="dg_cross_")',
    '',
    'customers_csv = """customer_id,name,email',
    'C100,Alice,alice@example.com',
    'C101,Bob,bob@example.com',
    'C102,Carol,carol@example.co.uk',
    'C103,Dave,dave@example.com',
    'C104,Eve,eve@example.com',
    'C105,Frank,frank@example.de',
    'C106,Grace,grace@example.com',
    'C107,Hiro,hiro@example.jp',
    'C108,Ivan,ivan@example.com',
    'C109,Jane,jane@example.co.uk',
    'C110,Karl,karl@example.com',
    '"""',
    '',
    'orders_orphans_csv = """order_id,customer_id',
    'ORD-100,C100',
    'ORD-101,C999',
    'ORD-102,C888',
    'ORD-103,C101',
    'ORD-104,',
    '"""',
    '',
    'cust_path = os.path.join(tmpdir, "customers.csv")',
    'orp_path  = os.path.join(tmpdir, "orders_orphans.csv")',
    '',
    'with open(cust_path, "w", newline="") as f:',
    '    f.write(customers_csv.strip())',
    'with open(orp_path, "w", newline="") as f:',
    '    f.write(orders_orphans_csv.strip())',
    '',
    'customers = connect(cust_path)',
    'orders_orp = connect(orp_path)',
    '',
    'print("[OK] Temporary datasets created")',
]))

cells.append(code([
    '# exists_in -- foreign-key check',
    'result = orders_orp.customer_id.exists_in(customers.customer_id)',
    'print("[PASS]" if result.passed else "[FAIL]", result.message)',
]))

cells.append(code([
    '# references() with allow_nulls',
    'result_allow = orders_orp.customer_id.references(customers.customer_id, allow_nulls=True)',
    'print("allow_nulls=True  =>", "[PASS]" if result_allow.passed else "[FAIL]", result_allow.message)',
    '',
    'result_strict = orders_orp.customer_id.references(customers.customer_id, allow_nulls=False)',
    'print("allow_nulls=False =>", "[PASS]" if result_strict.passed else "[FAIL]", result_strict.message)',
]))

cells.append(code([
    '# find_orphans - quick list of orphan values',
    'orphans = orders_orp.customer_id.find_orphans(customers.customer_id)',
    'print("Orphan customer IDs:", orphans)',
]))

cells.append(code([
    '# matches_values - compare distinct value sets',
    'result = orders_orp.customer_id.matches_values(customers.customer_id)',
    'print("[PASS]" if result.passed else "[FAIL]", result.message)',
]))

cells.append(code([
    '# row_count_matches - compare row counts with tolerance',
    'result = orders.row_count_matches(customers, tolerance=25)',
    'print("[PASS]" if result.passed else "[FAIL]", result.message)',
    '',
    '# Clean up temp files',
    'shutil.rmtree(tmpdir, ignore_errors=True)',
]))

# ===== 8. Reconciliation ====================================================

cells.append(md([
    "## 8. Reconciliation",
]))

cells.append(code([
    'tmpdir = tempfile.mkdtemp(prefix="dg_recon_")',
    '',
    'source_csv = """id,name,amount,status',
    '1,Alpha,100.00,active',
    '2,Beta,200.00,active',
    '3,Gamma,300.00,inactive',
    '4,Delta,400.00,active',
    '5,Epsilon,500.00,active',
    '"""',
    '',
    'target_csv = """id,name,amount,status',
    '1,Alpha,100.00,active',
    '2,Beta,210.00,active',
    '3,Gamma,300.00,active',
    '5,Epsilon,500.00,active',
    '6,Zeta,600.00,active',
    '"""',
    '',
    'src_path = os.path.join(tmpdir, "source.csv")',
    'tgt_path = os.path.join(tmpdir, "target.csv")',
    '',
    'with open(src_path, "w", newline="") as f:',
    '    f.write(source_csv.strip())',
    'with open(tgt_path, "w", newline="") as f:',
    '    f.write(target_csv.strip())',
    '',
    'source_ds = connect(src_path)',
    'target_ds = connect(tgt_path)',
    '',
    'recon = source_ds.reconcile(',
    '    target_ds,',
    '    key_columns=["id"],',
    '    compare_columns=["name", "amount", "status"],',
    ')',
    '',
    'print("Match %          :", recon.match_percentage)',
    'print("Missing in target:", recon.missing_in_target)',
    'print("Extra in target  :", recon.extra_in_target)',
    'print("Value mismatches :", recon.value_mismatches)',
    'print()',
    'print(recon.summary())',
    '',
    'shutil.rmtree(tmpdir, ignore_errors=True)',
]))

# ===== 9. Distribution Drift Detection ======================================

cells.append(md([
    "## 9. Distribution Drift Detection",
]))

cells.append(code([
    'tmpdir = tempfile.mkdtemp(prefix="dg_drift_")',
    '',
    '# Baseline: normal-ish amounts',
    'baseline_csv = "amount\\n" + "\\n".join(str(v) for v in [',
    '    100, 105, 98, 110, 95, 102, 108, 97, 103, 99,',
    '    101, 106, 94, 112, 96, 104, 107, 93, 111, 100,',
    '])',
    '',
    '# Drifted: shifted higher',
    'drifted_csv = "amount\\n" + "\\n".join(str(v) for v in [',
    '    200, 210, 195, 220, 205, 215, 198, 225, 202, 208,',
    '    190, 230, 197, 212, 207, 218, 193, 222, 201, 209,',
    '])',
    '',
    'bl_path = os.path.join(tmpdir, "baseline.csv")',
    'dr_path = os.path.join(tmpdir, "drifted.csv")',
    '',
    'with open(bl_path, "w", newline="") as f:',
    '    f.write(baseline_csv)',
    'with open(dr_path, "w", newline="") as f:',
    '    f.write(drifted_csv)',
    '',
    'baseline_ds = connect(bl_path)',
    'drifted_ds  = connect(dr_path)',
    '',
    'drift = drifted_ds.amount.detect_drift(baseline_ds.amount)',
    '',
    'print("P-value   :", drift.p_value)',
    'print("Statistic :", drift.statistic)',
    'print("Is drifted:", drift.is_drifted)',
    'print("Message   :", drift.message)',
    '',
    'shutil.rmtree(tmpdir, ignore_errors=True)',
]))

# ===== 10. Group-By Validation ==============================================

cells.append(md([
    "## 10. Group-By Validation",
]))

cells.append(code([
    'tmpdir = tempfile.mkdtemp(prefix="dg_grp_")',
    '',
    'grp_csv = """region,sales',
    'North,100',
    'North,110',
    'North,95',
    'South,200',
    'South,210',
    'East,50',
    'East,55',
    'East,60',
    'East,45',
    'West,300',
    '"""',
    '',
    'grp_path = os.path.join(tmpdir, "grouped.csv")',
    'with open(grp_path, "w", newline="") as f:',
    '    f.write(grp_csv.strip())',
    '',
    'grp_ds = connect(grp_path)',
    'grouped = grp_ds.group_by("region")',
    '',
    '# Group metadata',
    'print("Groups      :", grouped.groups)',
    'print("Group count :", grouped.group_count)',
    '',
    '# Stats per group',
    'print("\\nStats:")',
    'for s in grouped.stats():',
    '    print(f"  {s}")',
    '',
    '# Validate each group has at least 2 rows',
    'result = grouped.row_count_greater_than(2)',
    'print("\\nAll groups > 2 rows?", result.passed)',
    'for g in result.get_failed_groups():',
    '    print(f"  [FAIL] {g.key_string}: {g.row_count} rows")',
    '',
    'shutil.rmtree(tmpdir, ignore_errors=True)',
]))

# ===== 11. Conditional Checks ===============================================

cells.append(md([
    "## 11. Conditional Checks",
    "",
    "Validate columns only when a condition is true.",
]))

cells.append(code([
    '# not_null_when: email must not be null when status = shipped',
    'result = orders.email.not_null_when("status = \'shipped\'")',
    'print("[PASS]" if result.passed else "[FAIL]", "email not_null_when shipped:", result.message)',
]))

cells.append(code([
    '# unique_when: order_id must be unique among shipped orders',
    'result = orders.order_id.unique_when("status = \'shipped\'")',
    'print("[PASS]" if result.passed else "[FAIL]", "order_id unique_when shipped:", result.message)',
]))

cells.append(code([
    '# between_when: quantity between 1-100 when country = US',
    'result = orders.quantity.between_when(1, 100, "country = \'US\'")',
    'print("[PASS]" if result.passed else "[FAIL]", "quantity between_when US:", result.message)',
]))

cells.append(code([
    '# isin_when: status must be shipped/delivered when country = UK',
    "result = orders.status.isin_when(['shipped', 'delivered'], \"country = 'UK'\")",
    'print("[PASS]" if result.passed else "[FAIL]", "status isin_when UK:", result.message)',
]))

cells.append(code([
    '# matches_when: email must match pattern when status = delivered',
    "result = orders.email.matches_when(r'^[\\\\w\\\\.\\\\-]+@[\\\\w\\\\.\\\\-]+\\\\.[a-zA-Z]{2,}$', \"status = 'delivered'\")",
    'print("[PASS]" if result.passed else "[FAIL]", "email matches_when delivered:", result.message)',
]))

# ===== 12. Multi-Column Checks ==============================================

cells.append(md([
    "## 12. Multi-Column Checks",
]))

cells.append(code([
    '# Column pair satisfy: ship_date >= created_at',
    '# (only rows where both are non-null are checked)',
    'result = orders.expect_column_pair_satisfy(',
    '    column_a="ship_date",',
    '    column_b="created_at",',
    '    expression="ship_date >= created_at",',
    ')',
    'print("[PASS]" if result.passed else "[FAIL]", "ship_date >= created_at:", result.message)',
]))

cells.append(code([
    '# Composite key uniqueness: (order_id, customer_id)',
    'result = orders.expect_columns_unique(columns=["order_id", "customer_id"])',
    'print("[PASS]" if result.passed else "[FAIL]", "composite key unique:", result.message)',
]))

cells.append(code([
    '# Multi-column sum: subtotal + tax + shipping = total_amount',
    '# Note: this checks the row-level sum per row against a fixed expected value.',
    '# We pick a known row value to demonstrate -- ORD-001: 50 + 4.50 + 5 = 59.50',
    '# For a general "all rows" check, use expect_query_to_return_no_rows instead.',
    'result = orders.expect_multicolumn_sum_to_equal(',
    '    columns=["subtotal", "tax", "shipping"],',
    '    expected_sum=59.50,',
    '    threshold=0.01,',
    ')',
    'print("[PASS]" if result.passed else "[FAIL]", "multicolumn sum:", result.message)',
]))

# ===== 13. Query-Based Checks ===============================================

cells.append(md([
    "## 13. Query-Based Checks",
]))

cells.append(code([
    '# expect_query_to_return_no_rows: find violations',
    '# Find rows where quantity is negative (should have none for valid orders)',
    'result = orders.expect_query_to_return_no_rows(',
    '    "SELECT * FROM table WHERE quantity < 0"',
    ')',
    'print("[PASS]" if result.passed else "[FAIL]", "no negative qty:", result.message)',
]))

cells.append(code([
    '# expect_query_to_return_rows: ensure data exists',
    'result = orders.expect_query_to_return_rows(',
    '    "SELECT * FROM table WHERE status = \'shipped\'"',
    ')',
    'print("[PASS]" if result.passed else "[FAIL]", "shipped rows exist:", result.message)',
]))

cells.append(code([
    '# expect_query_result_to_equal: exact value check',
    'result = orders.expect_query_result_to_equal(',
    '    "SELECT COUNT(*) FROM table",',
    '    expected=30,',
    ')',
    'print("[PASS]" if result.passed else "[FAIL]", "row count = 30:", result.message)',
]))

cells.append(code([
    '# expect_query_result_to_be_between: range check on aggregate',
    'result = orders.expect_query_result_to_be_between(',
    '    "SELECT AVG(unit_price) FROM table",',
    '    min_value=10.0,',
    '    max_value=500.0,',
    ')',
    'print("[PASS]" if result.passed else "[FAIL]", "avg unit_price in [10,500]:", result.message)',
]))

# ===== 14. Distributional Checks ============================================

cells.append(md([
    "## 14. Distributional Checks",
    "",
    "These checks require **scipy**. They are wrapped in try/except so the notebook",
    "runs even if scipy is not installed.",
]))

cells.append(code([
    '# expect_distribution_normal',
    'try:',
    '    result = orders.unit_price.expect_distribution_normal()',
    '    print("[PASS]" if result.passed else "[FAIL]", "normal distribution:", result.message)',
    'except ImportError:',
    '    print("[SKIP] scipy not installed -- pip install scipy")',
    'except Exception as e:',
    '    print("[INFO]", type(e).__name__, str(e)[:120])',
]))

cells.append(code([
    '# expect_ks_test',
    'try:',
    '    result = orders.quantity.expect_ks_test(distribution="norm")',
    '    print("[PASS]" if result.passed else "[FAIL]", "KS test (norm):", result.message)',
    'except ImportError:',
    '    print("[SKIP] scipy not installed")',
    'except Exception as e:',
    '    print("[INFO]", type(e).__name__, str(e)[:120])',
]))

cells.append(code([
    '# expect_chi_square_test',
    'try:',
    '    result = orders.status.expect_chi_square_test()',
    '    print("[PASS]" if result.passed else "[FAIL]", "chi-square test:", result.message)',
    'except ImportError:',
    '    print("[SKIP] scipy not installed")',
    'except Exception as e:',
    '    print("[INFO]", type(e).__name__, str(e)[:120])',
]))

# ===== 15. Anomaly Detection ================================================

cells.append(md([
    "## 15. Anomaly Detection",
]))

cells.append(code([
    '# detect_anomalies (high-level, z-score)',
    'report = detect_anomalies(orders, method="zscore", columns=["quantity", "unit_price", "total_amount"])',
    'print("Has anomalies:", report.has_anomalies)',
    'print("Anomaly count:", report.anomaly_count)',
    'for a in report.anomalies:',
    '    tag = "[!]" if a.is_anomaly else "[ ]"',
    '    print(f"  {tag} {a.column}: score={a.score:.2f}, threshold={a.threshold}, msg={a.message}")',
]))

cells.append(code([
    '# AnomalyDetector with IQR method',
    'detector = AnomalyDetector(method="iqr", threshold=1.5)',
    'iqr_report = detector.detect(orders, columns=["quantity", "total_amount"])',
    'print("IQR anomaly count:", iqr_report.anomaly_count)',
    'for a in iqr_report.get_anomalies():',
    '    print(f"  [!] {a.column}: {a.message}")',
]))

cells.append(code([
    '# BaselineMethod: fit + score',
    'bl = BaselineMethod(sensitivity=2.0)',
    'bl.fit([100, 102, 98, 105, 97, 103, 108, 96, 104, 99])',
    '',
    'print("Baseline mean:", bl.baseline_mean)',
    'print("Baseline std :", bl.baseline_std)',
    '',
    'sc_normal = bl.score(101)',
    'sc_outlier = bl.score(250)',
    'print(f"Score 101 -> anomaly={sc_normal.is_anomaly}, score={sc_normal.score:.2f}")',
    'print(f"Score 250 -> anomaly={sc_outlier.is_anomaly}, score={sc_outlier.score:.2f}")',
]))

cells.append(code([
    '# KSTestMethod: compare_distributions',
    'ks = KSTestMethod(p_value_threshold=0.05)',
    'ks.fit([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])',
    '',
    'comp = ks.compare_distributions([5, 6, 7, 8, 9, 10, 11, 12, 13, 14])',
    'print("Is drift :", comp.is_drift)',
    'print("P-value  :", comp.p_value)',
    'print("Message  :", comp.message)',
]))

cells.append(code([
    '# SeasonalMethod: basic demo (without timestamps falls back to global stats)',
    'sm = SeasonalMethod(period="daily", sensitivity=2.0)',
    'sm.fit([10, 12, 11, 13, 9, 14, 10, 11, 12, 10])',
    '',
    'sc = sm.score(50)  # way outside normal range',
    'print("Score 50 -> anomaly:", sc.is_anomaly, "score:", f"{sc.score:.2f}")',
]))

cells.append(md([
    "### Anomaly Methods Reference",
    "",
    "| Method | Class | Best For |",
    "|--------|-------|----------|",
    "| `zscore` | `ZScoreMethod` | Normally distributed data |",
    "| `iqr` | `IQRMethod` | Robust to outliers |",
    "| `percent_change` | `PercentChangeMethod` | Monitoring metrics over time |",
    "| `modified_zscore` | `ModifiedZScoreMethod` | Non-normal distributions |",
    "| `baseline` | `BaselineMethod` | ML-based baseline comparison |",
    "| `ks_test` | `KSTestMethod` | Distribution drift detection |",
    "| `seasonal` | `SeasonalMethod` | Seasonal pattern detection |",
]))

# ===== 16. Auto-Profiling & Semantic Types ==================================

cells.append(md([
    "## 16. Auto-Profiling & Semantic Types",
]))

cells.append(code([
    '# AutoProfiler',
    'profiler = AutoProfiler()',
    'profile = profiler.profile(orders)',
    '',
    'print(f"Profiled {profile.column_count} columns, {profile.row_count} rows")',
    'print(f"Suggested rules ({len(profile.suggested_rules)}):")',
    'for rule in profile.suggested_rules[:10]:',
    '    print(f"  {rule}")',
    'if len(profile.suggested_rules) > 10:',
    '    print(f"  ... and {len(profile.suggested_rules) - 10} more")',
]))

cells.append(code([
    '# detect_type - individual column',
    'sem = detect_type(orders, "email")',
    'print("email semantic type:", sem)',
    '',
    'sem2 = detect_type(orders, "country")',
    'print("country semantic type:", sem2)',
]))

cells.append(code([
    '# detect_types_for_dataset - all columns at once',
    'type_map = detect_types_for_dataset(orders)',
    'for col, stype in type_map.items():',
    '    print(f"  {col:20s} -> {stype}")',
]))

cells.append(code([
    '# SemanticAnalyzer - full analysis with PII detection',
    'analyzer = SemanticAnalyzer()',
    'analysis = analyzer.analyze(orders)',
    '',
    'print("PII columns found:", analysis.pii_columns)',
    'for col in analysis.columns[:5]:',
    '    print(f"  {col.name:20s} type={col.semantic_type.value:15s} conf={col.confidence:.2f} pii={col.is_pii}")',
]))

cells.append(md([
    "### Supported Semantic Types (selection)",
    "",
    "| Category | Types |",
    "|----------|-------|",
    "| Identity | `primary_key`, `foreign_key`, `uuid`, `id` |",
    "| Contact | `email`, `phone`, `url`, `ip_address` |",
    "| PII | `ssn`, `credit_card`, `person_name`, `address` |",
    "| Location | `country`, `state`, `city`, `zipcode`, `latitude`, `longitude` |",
    "| Date/Time | `date`, `datetime`, `timestamp`, `time`, `year`, `month` |",
    "| Numeric | `currency`, `percentage`, `quantity`, `age` |",
    "| Categorical | `boolean`, `enum`, `status`, `category`, `gender` |",
    "| Text | `text`, `description`, `title`, `slug`, `code` |",
]))

# ===== 17. YAML Rules & Data Contracts ======================================

cells.append(md([
    "## 17. YAML Rules & Data Contracts",
]))

cells.append(code([
    '# load_rules_from_string - define rules inline',
    'yaml_str = """',
    'name: inline_orders',
    'description: Inline validation rules',
    '',
    'columns:',
    '  order_id:',
    '    checks:',
    '      - type: not_null',
    '      - type: unique',
    '  quantity:',
    '    checks:',
    '      - type: between',
    '        value: [0, 1000]',
    '  status:',
    '    checks:',
    '      - type: allowed_values',
    '        value: [pending, shipped, delivered, cancelled, returned]',
    '"""',
    '',
    'rules = load_rules_from_string(yaml_str)',
    'print("Loaded rules:", rules.name)',
    'print("Columns with rules:", list(rules.columns.keys()))',
]))

cells.append(code([
    '# execute_rules',
    'exec_result = execute_rules(rules, "sample_data/orders.csv")',
    'print("Passed    :", exec_result.passed)',
    'print("Total     :", exec_result.total_checks)',
    'print("Passed    :", exec_result.passed_count)',
    'print("Failed    :", exec_result.failed_count)',
    'for r in exec_result.results:',
    '    tag = "[PASS]" if r.passed else "[FAIL]"',
    '    print(f"  {tag} {r.message}")',
]))

cells.append(code([
    '# generate_rules - auto-generate from data',
    'auto_rules = generate_rules("sample_data/orders.csv")',
    'print("Auto-generated rules for:", auto_rules.name)',
    'print("Columns:", list(auto_rules.columns.keys())[:5], "...")',
]))

cells.append(code([
    '# RuleSet programmatic usage',
    'from duckguard.rules.schema import RuleSet, ColumnRules, Check, CheckType',
    '',
    'rs = RuleSet(',
    '    name="programmatic_rules",',
    '    columns={',
    '        "order_id": ColumnRules(',
    '            name="order_id",',
    '            checks=[',
    '                Check(type=CheckType.NOT_NULL),',
    '                Check(type=CheckType.UNIQUE),',
    '            ]',
    '        )',
    '    }',
    ')',
    'print("RuleSet:", rs.name, "| columns:", list(rs.columns.keys()))',
]))

cells.append(code([
    '# generate_contract - create a data contract from a live dataset',
    'contract = generate_contract(orders, name="orders_contract", owner="data-team")',
    'print("Contract:", contract.name)',
    'print("Version :", contract.version)',
    'print("Fields  :", len(contract.schema))',
]))

cells.append(code([
    '# validate_contract',
    'validation = validate_contract(contract, "sample_data/orders.csv")',
    'print("Contract valid:", validation.passed)',
    'if not validation.passed:',
    '    for v in validation.violations[:5]:',
    '        print(f"  - {v}")',
]))

cells.append(code([
    '# contract_to_yaml',
    'yaml_out = contract_to_yaml(contract)',
    'print(yaml_out[:500])',
    'print("..." if len(yaml_out) > 500 else "")',
]))

cells.append(code([
    '# diff_contracts - detect breaking changes between two contract versions',
    'contract_v1 = generate_contract(orders, name="orders_v1")',
    '',
    '# Simulate v2 by modifying v1',
    'import copy',
    'contract_v2 = copy.deepcopy(contract_v1)',
    'contract_v2.version = "2.0.0"',
    '# Remove a field to simulate a breaking change',
    'if len(contract_v2.schema) > 2:',
    '    removed = contract_v2.schema.pop()',
    '    print("Simulated removing field:", removed.name)',
    '',
    'diff = diff_contracts(contract_v1, contract_v2)',
    'print("Has breaking changes:", diff.has_breaking_changes)',
    'print("Changes:")',
    'for c in diff.changes[:5]:',
    '    print(f"  - {c}")',
]))

# ===== 18. Reports & Notifications ==========================================

cells.append(md([
    "## 18. Reports & Notifications",
]))

cells.append(code([
    '# Generate an HTML report from rule execution results',
    'tmpdir = tempfile.mkdtemp(prefix="dg_report_")',
    'report_path = os.path.join(tmpdir, "quality_report.html")',
    '',
    'try:',
    '    result_path = generate_html_report(exec_result, report_path)',
    '    print("[OK] HTML report generated:", result_path)',
    '    # File size',
    '    size = os.path.getsize(str(result_path))',
    '    print(f"     Size: {size:,} bytes")',
    'except Exception as e:',
    '    print("[INFO] Report generation:", e)',
    '',
    'shutil.rmtree(tmpdir, ignore_errors=True)',
]))

cells.append(code([
    '# Notifier configuration examples (NOT sending -- these need real credentials)',
    '',
    '# Email notifier',
    'email_notifier = EmailNotifier(',
    '    smtp_host="smtp.example.com",',
    '    smtp_port=587,',
    '    smtp_user="alerts@example.com",',
    '    smtp_password="app_password_here",',
    '    to_addresses=["team@example.com"],',
    '    from_address="duckguard@example.com",',
    ')',
    'print("[OK] EmailNotifier configured (not sending)")',
    '',
    '# Slack notifier',
    'slack_notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ")',
    'print("[OK] SlackNotifier configured (not sending)")',
    '',
    '# Teams notifier',
    'teams_notifier = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/XXX")',
    'print("[OK] TeamsNotifier configured (not sending)")',
]))

cells.append(code([
    '# Format results as text / markdown (useful for custom integrations)',
    'text_output = format_results_text(exec_result)',
    'print("=== Text Output (first 300 chars) ===")',
    'print(text_output[:300])',
    '',
    'md_output = format_results_markdown(exec_result)',
    'print("\\n=== Markdown Output (first 300 chars) ===")',
    'print(md_output[:300])',
]))

cells.append(md([
    "**Note:** To actually send notifications, replace the dummy credentials above",
    "with real SMTP / webhook settings and call `notifier.send_results(exec_result)`.",
]))

# ===== 19. Freshness, Schema Evolution & History ============================

cells.append(md([
    "## 19. Freshness & Schema Evolution & History",
]))

cells.append(code([
    '# Freshness -- how old is the data?',
    'freshness = orders.freshness',
    'print("Last modified:", freshness.last_modified)',
    'print("Age (human) :", freshness.age_human)',
    'print("Is fresh    :", freshness.is_fresh)',
]))

cells.append(code([
    '# is_fresh with custom threshold',
    'from datetime import timedelta',
    '',
    'print("Fresh (24h)?  :", orders.is_fresh(timedelta(hours=24)))',
    'print("Fresh (1 min)?:", orders.is_fresh(timedelta(minutes=1)))',
]))

cells.append(code([
    '# FreshnessMonitor',
    'monitor = FreshnessMonitor(threshold=timedelta(hours=1))',
    'result = monitor.check(orders)',
    'print("Monitor result:", result.is_fresh, "|", result.age_human)',
]))

cells.append(code([
    '# SchemaTracker - capture snapshots',
    'tracker = SchemaTracker()',
    'snapshot = tracker.capture(orders)',
    'print("Snapshot columns:", len(snapshot.columns))',
    'for cs in snapshot.columns[:5]:',
    '    print(f"  {cs.name}: {cs.dtype}")',
    '',
    '# Get history of snapshots',
    'history = tracker.get_history(orders)',
    'print("\\nSchema history entries:", len(history))',
]))

cells.append(code([
    '# SchemaChangeAnalyzer',
    'change_analyzer = SchemaChangeAnalyzer()',
    'report = change_analyzer.detect_changes(orders)',
    'print("Has breaking changes:", report.has_breaking_changes)',
    'print("Changes:", len(report.changes))',
]))

cells.append(code([
    '# HistoryStorage - store and query validation runs',
    'storage = HistoryStorage()',
    'storage.store(exec_result)',
    '',
    'runs = storage.get_runs("sample_data/orders.csv", limit=5)',
    'print("Stored runs:", len(runs))',
    'for run in runs:',
    '    print(f"  {run.run_id}: passed={run.passed}, checks={run.total_checks}")',
]))

cells.append(code([
    '# TrendAnalyzer',
    'trend_analyzer = TrendAnalyzer(storage)',
    'trends = trend_analyzer.analyze("sample_data/orders.csv", days=30)',
    'print(trends.summary())',
]))

# ===== 20. Integrations =====================================================

cells.append(md([
    "## 20. Integrations",
]))

cells.append(code([
    '# dbt integration - convert rules to dbt tests',
    'try:',
    '    from duckguard.integrations.dbt import rules_to_dbt_tests',
    '    dbt_tests = rules_to_dbt_tests(rules)',
    '    import json as _json',
    '    print(_json.dumps(dbt_tests, indent=2)[:500])',
    'except ImportError as e:',
    '    print("[SKIP] dbt integration requires yaml:", e)',
]))

cells.append(md([
    "### Airflow DAG Example",
    "",
    "```python",
    "from airflow import DAG",
    "from airflow.operators.python import PythonOperator",
    "from datetime import datetime",
    "",
    "def validate_orders():",
    '    from duckguard import connect, load_rules, execute_rules',
    '    rules = load_rules("duckguard.yaml")',
    '    result = execute_rules(rules, "s3://bucket/orders.parquet")',
    '    if not result.passed:',
    '        raise Exception(f"Quality check failed: {result.failed_count} failures")',
    "",
    "dag = DAG('data_quality', schedule_interval='@daily', start_date=datetime(2024, 1, 1))",
    "task = PythonOperator(task_id='validate', python_callable=validate_orders, dag=dag)",
    "```",
]))

cells.append(md([
    "### GitHub Actions Example",
    "",
    "```yaml",
    "name: Data Quality",
    "on: [push]",
    "jobs:",
    "  quality-check:",
    "    runs-on: ubuntu-latest",
    "    steps:",
    "      - uses: actions/checkout@v4",
    "      - uses: actions/setup-python@v5",
    "        with:",
    "          python-version: '3.11'",
    "      - run: pip install duckguard",
    "      - run: duckguard check data/orders.csv --rules duckguard.yaml",
    "```",
]))

cells.append(md([
    "### pytest Example",
    "",
    "```python",
    "# tests/test_data_quality.py",
    "from duckguard import connect",
    "",
    "def test_orders_quality():",
    '    orders = connect("data/orders.csv")',
    '    assert orders.row_count > 0',
    '    assert orders.order_id.is_not_null()',
    '    assert orders.order_id.is_unique()',
    '    assert orders.quantity.between(0, 10000)',
    '    assert orders.status.isin(["pending", "shipped", "delivered", "cancelled"])',
    "```",
]))

cells.append(md([
    "### CLI Commands Reference",
    "",
    "```bash",
    "# Run checks from YAML rules",
    "duckguard check data.csv --rules duckguard.yaml",
    "",
    "# Auto-discover rules from data",
    "duckguard discover data.csv --output duckguard.yaml",
    "",
    "# Generate a data contract",
    "duckguard contract generate data.csv --output contract.yaml",
    "",
    "# Validate against a contract",
    "duckguard contract validate data.csv --contract contract.yaml",
    "",
    "# Profile dataset",
    "duckguard profile data.csv",
    "```",
]))

# ===== 21. Enhanced Error Messages ==========================================

cells.append(md([
    "## 21. Enhanced Error Messages",
]))

cells.append(code([
    '# ColumnNotFoundError - includes suggestions',
    'try:',
    '    _ = orders.nonexistent_column',
    'except (AttributeError, ColumnNotFoundError) as e:',
    '    print("[ColumnNotFoundError]")',
    '    print(str(e)[:200])',
]))

cells.append(code([
    '# ValidationError',
    'try:',
    '    raise ValidationError(',
    '        check_name="between",',
    '        column="quantity",',
    '        actual_value=500,',
    '        expected_value="[1, 100]",',
    '    )',
    'except ValidationError as e:',
    '    print("[ValidationError]")',
    '    print(str(e)[:200])',
]))

cells.append(code([
    '# UnsupportedConnectorError',
    'try:',
    '    raise UnsupportedConnectorError(source="ftp://data.example.com/file.xyz")',
    'except UnsupportedConnectorError as e:',
    '    print("[UnsupportedConnectorError]")',
    '    print(str(e)[:300])',
]))

# ===== 22. Quick Reference ==================================================

cells.append(md([
    "## 22. Quick Reference",
]))

cells.append(md([
    "### Validation Methods",
    "",
    "| Method | Description | Returns |",
    "|--------|-------------|---------|",
    "| `col.is_not_null()` | Check nulls below threshold | `ValidationResult` |",
    "| `col.is_unique()` | Check uniqueness above threshold | `ValidationResult` |",
    "| `col.between(min, max)` | Range check (inclusive) | `ValidationResult` |",
    "| `col.greater_than(val)` | Minimum check (exclusive) | `ValidationResult` |",
    "| `col.less_than(val)` | Maximum check (exclusive) | `ValidationResult` |",
    "| `col.matches(regex)` | Regex pattern check | `ValidationResult` |",
    "| `col.isin(values)` | Enum / allowed values | `ValidationResult` |",
    "| `col.has_no_duplicates()` | Uniqueness check | `ValidationResult` |",
    "| `col.value_lengths_between(min, max)` | String length check | `ValidationResult` |",
    "| `col.exists_in(ref_col)` | Foreign key check | `ValidationResult` |",
    "| `col.references(ref_col)` | FK with null handling | `ValidationResult` |",
    "| `col.find_orphans(ref_col)` | List orphan values | `list` |",
    "| `col.matches_values(other_col)` | Compare value sets | `ValidationResult` |",
    "| `col.detect_drift(ref_col)` | Distribution drift | `DriftResult` |",
    "| `col.not_null_when(cond)` | Conditional not-null | `ValidationResult` |",
    "| `col.unique_when(cond)` | Conditional uniqueness | `ValidationResult` |",
    "| `col.between_when(min, max, cond)` | Conditional range | `ValidationResult` |",
    "| `col.isin_when(vals, cond)` | Conditional enum | `ValidationResult` |",
    "| `col.matches_when(pat, cond)` | Conditional pattern | `ValidationResult` |",
    "| `col.expect_distribution_normal()` | Normality test | `ValidationResult` |",
    "| `col.expect_ks_test()` | KS distribution test | `ValidationResult` |",
    "| `col.expect_chi_square_test()` | Chi-square test | `ValidationResult` |",
]))

cells.append(md([
    "### Dataset-Level Methods",
    "",
    "| Method | Description |",
    "|--------|-------------|",
    "| `ds.score()` | Quality score (completeness, uniqueness, validity, consistency) |",
    "| `ds.reconcile(target, keys, cols)` | Full reconciliation |",
    "| `ds.row_count_matches(other, tolerance)` | Row count comparison |",
    "| `ds.group_by(cols)` | Group-level validation |",
    "| `ds.expect_column_pair_satisfy(a, b, expr)` | Column pair check |",
    "| `ds.expect_columns_unique(cols)` | Composite key uniqueness |",
    "| `ds.expect_multicolumn_sum_to_equal(cols, sum)` | Multi-column sum |",
    "| `ds.expect_query_to_return_no_rows(sql)` | Custom SQL -- no violations |",
    "| `ds.expect_query_to_return_rows(sql)` | Custom SQL -- data exists |",
    "| `ds.expect_query_result_to_equal(sql, val)` | Custom SQL -- exact value |",
    "| `ds.expect_query_result_to_be_between(sql, min, max)` | Custom SQL -- range |",
    "| `ds.freshness` / `ds.is_fresh(max_age)` | Data freshness |",
]))

cells.append(md([
    "### Next Steps",
    "",
    "- **Documentation**: [github.com/XDataHubAI/duckguard](https://github.com/XDataHubAI/duckguard)",
    "- **PyPI**: `pip install duckguard`",
    "- **CLI**: `duckguard --help`",
    "- **dbt integration**: `from duckguard.integrations.dbt import rules_to_dbt_tests`",
    "- **Notifications**: Slack, Teams, Email -- `from duckguard.notifications import SlackNotifier`",
    "",
    "Happy data quality checking!",
]))

# ---------------------------------------------------------------------------
# Assemble notebook
# ---------------------------------------------------------------------------

notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.11.0",
        },
    },
    "cells": cells,
}

# ---------------------------------------------------------------------------
# Write the notebook
# ---------------------------------------------------------------------------

output_path = os.path.join(os.path.dirname(__file__), "getting_started.ipynb")
with open(output_path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"[OK] Notebook written to: {output_path}")
print(f"     Cells: {len(cells)} ({sum(1 for c in cells if c['cell_type']=='markdown')} markdown, {sum(1 for c in cells if c['cell_type']=='code')} code)")
