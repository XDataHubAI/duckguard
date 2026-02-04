"""
DuckGuard Performance Benchmarks

Generates a large dataset, then times DuckGuard operations vs naive pandas equivalents.
Outputs a markdown table for README/docs.

Usage:
    python benchmarks/benchmark.py [--rows 1000000] [--output benchmarks/results.md]
"""

import argparse
import csv
import os
import random
import string
import sys
import tempfile
import time
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def generate_dataset(path: str, num_rows: int) -> str:
    """Generate a realistic CSV dataset with num_rows rows."""
    print(f"Generating {num_rows:,} row dataset...")
    start = time.time()

    statuses = ["pending", "shipped", "delivered", "cancelled", "returned"]
    countries = ["US", "UK", "CA", "DE", "JP", "FR", "AU", "BR", "IN", "MX"]
    products = [
        "Widget Pro", "Gadget Plus", "Super Gizmo", "Basic Widget",
        "Premium Bundle", "Starter Kit", "Enterprise Pack", "Lite Edition",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order_id", "customer_id", "product_name", "quantity",
            "unit_price", "subtotal", "tax", "shipping", "total_amount",
            "status", "country", "email", "created_at",
        ])

        for i in range(num_rows):
            oid = f"ORD{i+1:08d}"
            cid = f"CUST{random.randint(1, num_rows // 10):06d}"
            product = random.choice(products)
            qty = random.randint(1, 20)
            price = round(random.uniform(5.0, 500.0), 2)
            subtotal = round(qty * price, 2)
            tax = round(subtotal * 0.09, 2)
            shipping = round(random.choice([0.0, 4.99, 9.99, 14.99]), 2)
            total = round(subtotal + tax + shipping, 2)
            status = random.choice(statuses)
            country = random.choice(countries)
            # ~2% null emails, ~1% malformed
            if random.random() < 0.02:
                email = ""
            elif random.random() < 0.01:
                email = "not-an-email"
            else:
                name = "".join(random.choices(string.ascii_lowercase, k=8))
                email = f"{name}@example.com"
            date = f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
            writer.writerow([
                oid, cid, product, qty, price, subtotal, tax, shipping,
                total, status, country, email, date,
            ])

    elapsed = time.time() - start
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  Generated {size_mb:.1f} MB in {elapsed:.1f}s")
    return path


def bench_duckguard(csv_path: str) -> dict:
    """Benchmark DuckGuard operations."""
    from duckguard import connect, AutoProfiler, detect_anomalies

    results = {}

    # Connect
    t0 = time.time()
    data = connect(csv_path)
    _ = data.row_count  # force load
    results["connect"] = time.time() - t0

    # Column validations
    t0 = time.time()
    data.order_id.is_not_null()
    data.order_id.is_unique()
    data.quantity.between(1, 100)
    data.total_amount.greater_than(0)
    data.status.isin(["pending", "shipped", "delivered", "cancelled", "returned"])
    results["validate_5_checks"] = time.time() - t0

    # Quality score
    t0 = time.time()
    score = data.score()
    results["quality_score"] = time.time() - t0

    # Profile
    t0 = time.time()
    profile = AutoProfiler().profile(data)
    results["profile"] = time.time() - t0

    # Anomaly detection
    t0 = time.time()
    report = detect_anomalies(data, method="zscore", columns=["quantity", "total_amount"])
    results["anomaly_detect"] = time.time() - t0

    # Total
    results["total"] = sum(results.values())

    return results


def bench_pandas(csv_path: str) -> dict:
    """Benchmark equivalent operations with pandas."""
    import pandas as pd

    results = {}

    # Load
    t0 = time.time()
    df = pd.read_csv(csv_path)
    results["connect"] = time.time() - t0

    # Validations (equivalent checks)
    t0 = time.time()
    _ = df["order_id"].notna().all()
    _ = df["order_id"].is_unique
    _ = df["quantity"].between(1, 100).all()
    _ = (df["total_amount"] > 0).all()
    _ = df["status"].isin(["pending", "shipped", "delivered", "cancelled", "returned"]).all()
    results["validate_5_checks"] = time.time() - t0

    # Quality score (manual equivalent)
    t0 = time.time()
    completeness = (1 - df.isnull().sum().sum() / df.size) * 100
    uniqueness = df.nunique().mean() / len(df) * 100
    results["quality_score"] = time.time() - t0

    # Profile (describe)
    t0 = time.time()
    _ = df.describe(include="all")
    _ = df.dtypes
    _ = df.isnull().sum()
    _ = df.nunique()
    results["profile"] = time.time() - t0

    # Anomaly detection (manual z-score)
    t0 = time.time()
    for col in ["quantity", "total_amount"]:
        series = df[col].dropna()
        mean, std = series.mean(), series.std()
        if std > 0:
            z_scores = ((series - mean) / std).abs()
            _ = (z_scores > 3).sum()
    results["anomaly_detect"] = time.time() - t0

    results["total"] = sum(results.values())

    return results


def format_results(dg: dict, pd_results: dict, num_rows: int, file_size_mb: float) -> str:
    """Format benchmark results as markdown."""
    lines = [
        f"# DuckGuard Benchmarks",
        f"",
        f"**Dataset:** {num_rows:,} rows, {file_size_mb:.0f} MB CSV",
        f"",
        f"| Operation | DuckGuard | pandas | Speedup |",
        f"|-----------|-----------|--------|---------|",
    ]

    for key in ["connect", "validate_5_checks", "quality_score", "profile", "anomaly_detect", "total"]:
        label = key.replace("_", " ").title()
        dg_t = dg[key]
        pd_t = pd_results[key]
        speedup = pd_t / dg_t if dg_t > 0 else float("inf")

        if speedup >= 1:
            speed_str = f"**{speedup:.1f}x faster**"
        else:
            speed_str = f"{1/speedup:.1f}x slower"

        lines.append(f"| {label} | {dg_t:.3f}s | {pd_t:.3f}s | {speed_str} |")

    lines.extend([
        "",
        f"*Generated with `python benchmarks/benchmark.py --rows {num_rows}`*",
        f"",
        f"Note: pandas comparison is basic (no equivalent features for PII detection, ",
        f"semantic analysis, row-level errors, data contracts, etc.). DuckGuard provides ",
        f"significantly more functionality per line of code.",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="DuckGuard benchmarks")
    parser.add_argument("--rows", type=int, default=1_000_000, help="Number of rows")
    parser.add_argument("--output", type=str, default="benchmarks/results.md")
    args = parser.parse_args()

    # Generate dataset
    tmp = tempfile.mktemp(suffix=".csv")
    try:
        generate_dataset(tmp, args.rows)
        file_size_mb = os.path.getsize(tmp) / (1024 * 1024)

        # Run benchmarks
        print(f"\nBenchmarking DuckGuard on {args.rows:,} rows ({file_size_mb:.0f} MB)...")
        dg_results = bench_duckguard(tmp)
        print(f"  DuckGuard total: {dg_results['total']:.3f}s")

        print(f"\nBenchmarking pandas on {args.rows:,} rows...")
        pd_results = bench_pandas(tmp)
        print(f"  pandas total: {pd_results['total']:.3f}s")

        # Format and save
        report = format_results(dg_results, pd_results, args.rows, file_size_mb)
        print(f"\n{report}")

        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nSaved to {args.output}")

    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == "__main__":
    main()
