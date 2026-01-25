"""Basic usage example for DuckGuard data quality tool."""

from duckguard import connect

# Connect to a CSV file
orders = connect("examples/sample_data/orders.csv")

# Basic dataset info
print(f"Dataset: {orders.name}")
print(f"Rows: {orders.row_count}")
print(f"Columns: {orders.columns}")
print()

# Simple assertions (like pytest!)
assert orders.row_count > 0, "Dataset should not be empty"
assert orders.order_id.null_percent == 0, "order_id should not have nulls"
assert orders.order_id.has_no_duplicates(), "order_id should be unique"

# Column statistics
print("Column Statistics:")
print(f"  order_id unique: {orders.order_id.unique_percent:.1f}%")
print(f"  customer_id nulls: {orders.customer_id.null_percent:.1f}%")
print(f"  total_amount range: {orders.total_amount.min} - {orders.total_amount.max}")
print()

# Validation checks
print("Validation Results:")

# Check null percentage
result = orders.email.is_not_null(threshold=5)
print(f"  email not null (threshold 5%): {'PASS' if result else 'FAIL'}")

# Check values are in range
result = orders.quantity.between(1, 100)
print(f"  quantity between 1-100: {'PASS' if result else 'FAIL'}")

# Check enum values
result = orders.status.isin(['pending', 'shipped', 'delivered'])
print(f"  status valid values: {'PASS' if result else 'FAIL'}")

# Check email pattern
result = orders.email.matches(r'^[\w\.-]+@[\w\.-]+\.\w+$')
print(f"  email valid format: {'PASS' if result else 'FAIL'}")

print()
print("All validations passed!")
