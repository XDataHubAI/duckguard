# Cross-Dataset Validation

Validate foreign key relationships, reconcile datasets, and detect distribution drift between data sources.

## Foreign Key Checks

```python
from duckguard import connect

orders = connect("orders.csv")
customers = connect("customers.csv")

# All customer_ids must exist in customers table
result = orders.customer_id.exists_in(customers.customer_id)

# FK with null handling
result = orders.customer_id.references(customers.customer_id, allow_nulls=True)
```

## Finding Orphans

```python
orphans = orders.customer_id.find_orphans(customers.customer_id)
print(f"Invalid IDs: {orphans}")
# ['CUST-999', 'CUST-deleted']
```

## Value Set Comparison

```python
# Check if two columns share the same distinct values
result = orders.status.matches_values(lookup.code)
```

## Row Count Comparison

```python
# With tolerance (allows ±10 rows)
result = orders.row_count_matches(backup, tolerance=10)
```

## Reconciliation

Full row-by-row comparison between two datasets:

```python
source = connect("orders_source.parquet")
target = connect("orders_migrated.parquet")

recon = source.reconcile(
    target,
    key_columns=["order_id"],
    compare_columns=["amount", "status", "customer_id"],
)

print(recon.match_percentage)    # 95.5
print(recon.missing_in_target)   # 3
print(recon.extra_in_target)     # 1
print(recon.value_mismatches)    # {'amount': 5, 'status': 2}
print(recon.summary())
```

Use cases:

- Validating data migrations
- Comparing source vs. warehouse
- Verifying ETL transformations

## Distribution Drift Detection

Detect statistical drift between a baseline and current data using the Kolmogorov-Smirnov test:

```python
baseline = connect("orders_jan.parquet")
current = connect("orders_feb.parquet")

drift = current.amount.detect_drift(baseline.amount)

print(drift.is_drifted)    # True/False
print(drift.p_value)       # 0.0023
print(drift.statistic)     # KS statistic
print(drift.message)       # "Significant drift detected (p=0.0023)"
```

Use cases:

- Detecting data source changes
- ML feature drift monitoring
- Data pipeline regression testing
