# Changelog

All notable changes to DuckGuard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.1.0] — 2026-01-30

Enhanced profiler: wired 4 existing helper modules into AutoProfiler, added `duckguard profile` CLI command, and made profiling thresholds configurable.

### Added

**Integrated Profiling Pipeline** — AutoProfiler now leverages all 4 helper modules:

- **PatternMatcher** — 25+ built-in patterns (email, SSN, UUID, credit card, etc.) replace the previous 7 hardcoded patterns
- **QualityScorer** — Every column gets a quality score (0–100) and letter grade (A–F)
- **DistributionAnalyzer** (deep mode) — distribution type, skewness, kurtosis, normality test
- **OutlierDetector** (deep mode) — IQR-based outlier count and percentage

**Percentile Statistics** — `median_value`, `p25_value`, `p75_value` now included in column profiles.

**Configurable Thresholds** — `null_threshold`, `unique_threshold`, `enum_max_values`, `pattern_sample_size`, `pattern_min_confidence`

**`duckguard profile` CLI Command:**

```bash
duckguard profile data.csv
duckguard profile data.csv --deep
duckguard profile data.csv --format json -o profile.json
```

### Changed

- `ColumnProfile`: 10 new optional fields (backward-compatible `None` defaults)
- `ProfileResult`: 2 new fields (`overall_quality_score`, `overall_quality_grade`)
- AutoProfiler delegates pattern detection to `PatternMatcher`

---

## [3.0.0] — 2026-01-27

Major feature release — 23 new check types, enterprise-grade security, 100% backward compatible with 2.x.

### Added

**Conditional Expectations (5 check types)** — validate only when a SQL condition is met:

- `not_null_when`, `unique_when`, `between_when`, `isin_when`, `matches_when`

**Multi-Column Expectations (8 check types)** — cross-column validation:

- `expect_column_pair_satisfy`, `expect_columns_unique`, `expect_multicolumn_sum_to_equal`
- Column comparison operators: `column_a_gt_b`, `column_a_gte_b`, `column_a_lt_b`, `column_a_lte_b`, `column_a_eq_b`

**Query-Based Expectations (6 check types)** — custom SQL validation:

- `expect_query_to_return_no_rows`, `expect_query_to_return_rows`
- `expect_query_result_to_equal`, `expect_query_result_to_be_between`
- `query_result_gt`, `query_result_lt`

**Distributional Checks (4 check types)** — statistical tests:

- `expect_distribution_normal`, `expect_distribution_uniform`
- `expect_ks_test`, `expect_chi_square_test`

**Enhanced Profiling:**

- DistributionAnalyzer — best-fit distribution, skewness, kurtosis, normality testing
- OutlierDetector — Z-score, IQR, Isolation Forest, LOF, consensus detection
- PatternMatcher — 25+ built-in patterns with confidence scoring
- QualityScorer — multi-dimensional quality grading (A–F)

**Security:**

- Multi-layer SQL injection prevention
- QueryValidator + QuerySecurityValidator + ExpressionParser
- 80+ security tests, OWASP Top 10 compliance
- READ-ONLY enforcement, 30s timeout, 10K row limit

### Performance

Benchmarks on 1M rows: conditional 2.1s, multi-column 3.8s, query 2.5–7.2s, distributional 8.3s.

### Dependencies

- `scipy>=1.11.0` (optional) — `pip install 'duckguard[statistics]'`
- `scikit-learn>=1.3.0` (optional) — `pip install 'duckguard[profiling]'`

---

## [2.3.0] — 2025-01-25

### Added

- **Cross-dataset validation:** `exists_in()`, `references()`, `find_orphans()`, `matches_values()`
- **Dataset reconciliation:** `reconcile()` with key matching, value comparison, tolerance
- **Distribution drift:** `detect_drift()` using Kolmogorov-Smirnov test
- **Group-by checks:** `group_by().row_count_greater_than()`, `stats()`, `validate()`
- **Row count comparison:** `row_count_matches()` between datasets

---

## [2.2.1] — 2025-01-24

### Fixed

- Resolved lint errors and minor bug fixes

---

## [2.2.0] — 2025-01-23

### Added

- Initial public release with core features:
  - Data profiling and quality scoring
  - YAML-based validation rules
  - Semantic type detection and PII detection
  - Data contracts (generate, validate, diff)
  - Anomaly detection (z-score, IQR, baseline, KS test)
  - CLI interface with Rich output
  - pytest integration
  - Connectors: CSV, Parquet, JSON, Excel, S3, GCS, Azure, PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, Redshift, SQL Server, Databricks, Oracle, MongoDB, Kafka
  - HTML/PDF report generation
  - Slack, Teams, Email notifications
  - Historical tracking and trend analysis
