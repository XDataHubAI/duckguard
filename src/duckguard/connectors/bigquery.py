"""BigQuery connector."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class BigQueryConnector(Connector):
    """
    Connector for Google BigQuery.

    Uses the google-cloud-bigquery package to connect and query,
    then processes results with DuckDB for validation.

    Examples:
        # Using connection string
        data = connect(
            "bigquery://project-id/dataset",
            table="orders"
        )

        # Using options with service account
        data = connect(
            "bigquery://project-id",
            table="orders",
            dataset="my_dataset",
            credentials_path="/path/to/service-account.json"
        )
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._client = None

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to BigQuery and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        try:
            from google.cloud import bigquery
        except ImportError:
            raise ImportError(
                "BigQuery support requires google-cloud-bigquery. "
                "Install with: pip install duckguard[bigquery]"
            )

        if not config.table:
            raise ValueError("Table name is required for BigQuery connections")

        # Parse connection parameters
        conn_params = self._parse_connection_string(config.source, config)

        # Initialize BigQuery client
        if conn_params.get("credentials_path"):
            self._client = bigquery.Client.from_service_account_json(
                conn_params["credentials_path"]
            )
        else:
            self._client = bigquery.Client(project=conn_params.get("project"))

        table = config.table
        dataset = conn_params.get("dataset", "")
        project = conn_params.get("project", self._client.project)

        # Build fully qualified table name
        if project and dataset:
            fq_table = f"`{project}.{dataset}.{table}`"
        elif dataset:
            fq_table = f"`{dataset}.{table}`"
        else:
            fq_table = f"`{table}`"

        return BigQueryDataset(
            source=fq_table,
            engine=self.engine,
            name=table,
            client=self._client,
        )

    def _parse_connection_string(
        self, conn_string: str, config: ConnectionConfig
    ) -> dict[str, Any]:
        """Parse BigQuery connection string and merge with config options."""
        params: dict[str, Any] = {}

        # Parse URL format: bigquery://project-id/dataset
        if conn_string.lower().startswith("bigquery://"):
            parsed = urlparse(conn_string)

            params["project"] = parsed.hostname or ""

            # Parse path for dataset
            path_parts = [p for p in parsed.path.split("/") if p]
            if len(path_parts) >= 1:
                params["dataset"] = path_parts[0]

        # Override with config options
        options = config.options or {}
        for key in ["project", "dataset", "credentials_path", "location"]:
            if key in options:
                params[key] = options[key]

        if config.database:
            params["dataset"] = config.database
        if config.schema:
            params["dataset"] = config.schema

        return params

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a BigQuery connection string."""
        return source.lower().startswith("bigquery://")

    @classmethod
    def get_priority(cls) -> int:
        """BigQuery connector has high priority."""
        return 60


class BigQueryDataset(Dataset):
    """Dataset that queries BigQuery directly."""

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine,
        name: str,
        client: Any,
    ):
        super().__init__(source=source, engine=engine, name=name)
        self._bq_client = client

    def _execute_bq_query(self, sql: str) -> list[Any]:
        """Execute a query on BigQuery."""
        query_job = self._bq_client.query(sql)
        return list(query_job.result())

    def _fetch_bq_value(self, sql: str) -> Any:
        """Execute query and return single value."""
        rows = self._execute_bq_query(sql)
        return rows[0][0] if rows else None

    @property
    def row_count(self) -> int:
        """Get row count from BigQuery."""
        if self._row_count_cache is None:
            sql = f"SELECT COUNT(*) FROM {self._source}"
            self._row_count_cache = self._fetch_bq_value(sql) or 0
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """Get column names from BigQuery."""
        if self._columns_cache is None:
            sql = f"SELECT * FROM {self._source} LIMIT 0"
            query_job = self._bq_client.query(sql)
            result = query_job.result()
            self._columns_cache = [field.name for field in result.schema]
        return self._columns_cache
