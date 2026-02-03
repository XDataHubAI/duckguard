# Cloud Storage

Connect to files on S3, GCS, and Azure Blob Storage.

## Quick Start

```python
from duckguard import connect

# AWS S3
data = connect("s3://my-bucket/orders.parquet")

# Google Cloud Storage
data = connect("gs://my-bucket/data.csv")

# Azure Blob Storage
data = connect("az://my-container/data.parquet")
```

## AWS S3

DuckGuard uses DuckDB's `httpfs` extension for S3 access.

```python
data = connect("s3://my-bucket/orders.parquet")
data = connect("s3://my-bucket/data/orders.csv")
```

### Authentication

DuckDB picks up AWS credentials automatically from:

1. **Environment variables:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
2. **AWS credentials file:** `~/.aws/credentials`
3. **IAM roles** (EC2, ECS, Lambda)

```bash
# Environment variables
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=secret...
export AWS_DEFAULT_REGION=us-east-1
```

### S3-Compatible Storage

Works with MinIO, LocalStack, and other S3-compatible services:

```python
# MinIO / LocalStack
data = connect("s3://bucket/data.parquet")
# Configure endpoint via DuckDB settings or env vars
```

## Google Cloud Storage

```python
data = connect("gs://my-bucket/orders.parquet")
data = connect("gs://my-bucket/data/events.csv")
```

### Authentication

Uses Google Cloud credentials from:

1. **Environment variable:** `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON)
2. **Default credentials:** `gcloud auth application-default login`
3. **Service account** on GCP compute

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

## Azure Blob Storage

```python
data = connect("az://my-container/orders.parquet")
data = connect("abfss://container@account.dfs.core.windows.net/data.parquet")
```

### Authentication

Uses Azure credentials from:

1. **Environment variables:** `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT` + `AZURE_STORAGE_KEY`
2. **Azure CLI:** `az login`
3. **Managed identity** on Azure compute

```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
```

## Supported File Formats

All cloud connectors support the same formats as local files:

| Format | S3 | GCS | Azure |
|--------|----|----|-------|
| CSV | ✅ | ✅ | ✅ |
| Parquet | ✅ | ✅ | ✅ |
| JSON/JSONL | ✅ | ✅ | ✅ |

## Usage Patterns

```python
data = connect("s3://analytics/orders/2024/orders.parquet")

# Same Dataset API as local files
assert data.row_count > 0
assert data.order_id.null_percent == 0

# Quality scoring
score = data.score()
print(f"Quality: {score.grade}")

# Profiling
from duckguard import profile
result = profile(data)
```

## Performance Tips

- **Use Parquet** on cloud storage — columnar format means DuckDB only reads the columns it needs
- **Partition data** by date/region for faster scans
- **Use regional buckets** close to your compute for lower latency
- DuckDB handles **parallel reads** automatically
