# API Reference

Core classes and functions exported by `duckguard`.

## Entry Point

```python
from duckguard import connect

data = connect("data.csv")
```

### `connect(source, *, table=None, schema=None, database=None, **options) → Dataset`

Connect to any data source. Auto-detects format from file extension or connection string prefix.

## Core Classes

### Dataset

```python
from duckguard import Dataset
```

| Property / Method | Returns | Description |
|-------------------|---------|-------------|
| `row_count` | `int` | Number of rows |
| `columns` | `list[str]` | Column names |
| `column_count` | `int` | Number of columns |
| `source` | `str` | Source path |
| `name` | `str` | Dataset name |
| `data.column_name` | `Column` | Access column by attribute |
| `data["column_name"]` | `Column` | Access column by bracket |
| `column(name)` | `Column` | Access column by method |
| `has_column(name)` | `bool` | Check column exists |
| `head(n=5)` | `list[dict]` | First n rows |
| `sample(n=10)` | `list[dict]` | Sample n rows |
| `execute_sql(sql)` | `list[tuple]` | Run custom SQL |
| `score(weights=None)` | `QualityScore` | Quality score |
| `freshness` | `FreshnessResult` | Freshness info |
| `is_fresh(max_age)` | `bool` | Freshness check |
| `group_by(columns)` | `GroupedDataset` | Group for validation |
| `reconcile(target, ...)` | `ReconciliationResult` | Compare datasets |
| `row_count_matches(other, tolerance)` | `ValidationResult` | Compare row counts |

#### Multi-Column Methods

| Method | Description |
|--------|-------------|
| `expect_column_pair_satisfy(column_a, column_b, expression, threshold)` | Column pair relationship |
| `expect_columns_unique(columns, threshold)` | Composite key uniqueness |
| `expect_multicolumn_sum_to_equal(columns, expected_sum, threshold)` | Sum constraint |

#### Query Methods

| Method | Description |
|--------|-------------|
| `expect_query_to_return_no_rows(query, message)` | Query returns 0 rows |
| `expect_query_to_return_rows(query, message)` | Query returns ≥1 row |
| `expect_query_result_to_equal(query, expected, tolerance)` | Scalar result match |
| `expect_query_result_to_be_between(query, min_value, max_value)` | Scalar in range |

### Column

Accessed via `dataset.column_name` or `dataset["column_name"]`.

| Property / Method | Description |
|-------------------|-------------|
| `null_count`, `null_percent` | Null statistics |
| `unique_count`, `unique_percent` | Uniqueness statistics |
| `total_count` | Non-null count |
| `min`, `max`, `mean`, `median` | Numeric statistics |
| `between(min, max)` | Range validation |
| `isin(values)` | Allowed values check |
| `matches(pattern)` | Regex pattern check |
| `has_no_duplicates()` | Uniqueness check |
| `greater_than(value)` | Minimum check |
| `less_than(value)` | Maximum check |
| `not_null_when(condition)` | Conditional null check |
| `unique_when(condition)` | Conditional uniqueness |
| `between_when(min, max, condition)` | Conditional range |
| `isin_when(values, condition)` | Conditional allowed values |
| `matches_when(pattern, condition)` | Conditional pattern |
| `expect_distribution_normal()` | Normal distribution test |
| `expect_distribution_uniform()` | Uniform distribution test |
| `expect_ks_test(distribution)` | KS test |
| `expect_chi_square_test()` | Chi-square test |

### ValidationResult

```python
from duckguard import ValidationResult
```

| Property / Method | Description |
|-------------------|-------------|
| `passed` | `bool` — check passed |
| `actual_value` | Actual value found |
| `expected_value` | Expected value |
| `message` | Summary string |
| `details` | Metadata dict |
| `failed_rows` | `list[FailedRow]` — sample failures |
| `total_failures` | Total failure count |
| `summary()` | Human-readable summary |
| `to_dataframe()` | Export to pandas DataFrame |
| `get_failed_values()` | List of bad values |
| `get_failed_row_indices()` | List of row indices |

### QualityScore

```python
score = data.score()
score.overall       # 0-100
score.grade         # A, B, C, D, F
score.completeness  # Dimension score
score.uniqueness    # Dimension score
score.validity      # Dimension score
score.consistency   # Dimension score
```

## Top-Level Functions

| Function | Description |
|----------|-------------|
| `connect(source)` | Connect to data source |
| `profile(dataset)` | Profile dataset |
| `load_rules(path)` | Load YAML rules |
| `execute_rules(ruleset)` | Execute rules |
| `generate_rules(dataset)` | Auto-generate rules |
| `load_contract(path)` | Load data contract |
| `validate_contract(contract, source)` | Validate against contract |
| `generate_contract(source)` | Auto-generate contract |
| `diff_contracts(old, new)` | Compare contracts |
| `detect_type(dataset, column)` | Detect semantic type |
| `detect_types_for_dataset(dataset)` | Detect all types |
| `detect_anomalies(dataset)` | Anomaly detection |
| `score(dataset)` | Quality score |
