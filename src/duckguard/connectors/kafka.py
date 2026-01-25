"""Apache Kafka connector for streaming data quality."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class KafkaConnector(Connector):
    """
    Connector for Apache Kafka topics.

    Consumes messages from a Kafka topic and validates them.
    Supports JSON, Avro, and string message formats.

    Examples:
        # Using connection string
        data = connect(
            "kafka://broker1:9092,broker2:9092/my-topic",
            sample_size=1000
        )

        # Using options
        data = connect(
            "kafka://localhost:9092",
            table="my-topic",  # topic name
            group_id="duckguard-validator",
            sample_size=5000,
            format="json"
        )

        # With authentication
        data = connect(
            "kafka://broker:9092/topic",
            security_protocol="SASL_SSL",
            sasl_mechanism="PLAIN",
            sasl_username="user",
            sasl_password="pass"
        )
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._consumer = None

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to Kafka and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        try:
            from kafka import KafkaConsumer
        except ImportError:
            raise ImportError(
                "Kafka support requires kafka-python. "
                "Install with: pip install duckguard[kafka]"
            )

        # Parse connection parameters
        conn_params = self._parse_connection_string(config.source, config)

        topic = config.table or conn_params.get("topic")
        if not topic:
            raise ValueError("Topic name is required for Kafka connections")

        bootstrap_servers = conn_params.get("bootstrap_servers", "localhost:9092")
        group_id = conn_params.get("group_id", "duckguard-validator")
        sample_size = conn_params.get("sample_size", 1000)
        message_format = conn_params.get("format", "json")

        # Build consumer config
        consumer_config = {
            "bootstrap_servers": bootstrap_servers,
            "group_id": group_id,
            "auto_offset_reset": "earliest",
            "enable_auto_commit": False,
            "consumer_timeout_ms": conn_params.get("timeout_ms", 10000),
        }

        # Add security config if present
        if conn_params.get("security_protocol"):
            consumer_config["security_protocol"] = conn_params["security_protocol"]
        if conn_params.get("sasl_mechanism"):
            consumer_config["sasl_mechanism"] = conn_params["sasl_mechanism"]
        if conn_params.get("sasl_username"):
            consumer_config["sasl_plain_username"] = conn_params["sasl_username"]
        if conn_params.get("sasl_password"):
            consumer_config["sasl_plain_password"] = conn_params["sasl_password"]

        # Create consumer
        self._consumer = KafkaConsumer(topic, **consumer_config)

        return KafkaDataset(
            source=topic,
            engine=self.engine,
            name=topic,
            consumer=self._consumer,
            sample_size=sample_size,
            message_format=message_format,
        )

    def _parse_connection_string(self, conn_string: str, config: ConnectionConfig) -> dict:
        """Parse Kafka connection string."""
        params: dict[str, Any] = {}

        # Parse URL format: kafka://broker1:9092,broker2:9092/topic
        if conn_string.lower().startswith("kafka://"):
            # Remove protocol
            rest = conn_string[8:]

            # Split path
            if "/" in rest:
                brokers_part, path = rest.split("/", 1)
                params["topic"] = path.split("?")[0] if path else None
            else:
                brokers_part = rest.split("?")[0]

            params["bootstrap_servers"] = brokers_part

            # Parse query parameters
            parsed = urlparse(conn_string)
            if parsed.query:
                query_params = parse_qs(parsed.query)
                for key, values in query_params.items():
                    params[key] = values[0] if len(values) == 1 else values

        # Override with config options
        options = config.options or {}
        for key in [
            "bootstrap_servers",
            "group_id",
            "sample_size",
            "format",
            "timeout_ms",
            "security_protocol",
            "sasl_mechanism",
            "sasl_username",
            "sasl_password",
        ]:
            if key in options:
                params[key] = options[key]

        if config.table:
            params["topic"] = config.table

        return params

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a Kafka connection string."""
        return source.lower().startswith("kafka://")

    @classmethod
    def get_priority(cls) -> int:
        """Kafka connector has high priority."""
        return 55


class KafkaDataset(Dataset):
    """
    Dataset that consumes from Kafka topic.

    Samples messages and loads them into DuckDB for validation.
    """

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine,
        name: str,
        consumer: Any,
        sample_size: int = 1000,
        message_format: str = "json",
    ):
        super().__init__(source=source, engine=engine, name=name)
        self._consumer = consumer
        self._sample_size = sample_size
        self._message_format = message_format
        self._loaded = False
        self._view_name = f"_duckguard_kafka_{name.replace('-', '_')}"
        self._messages_consumed = 0

    def _ensure_loaded(self) -> None:
        """Consume messages and load into DuckDB if not already done."""
        if self._loaded:
            return

        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Kafka connector requires pandas for data loading. "
                "Install with: pip install pandas"
            )

        messages = []
        count = 0

        # Consume messages
        for message in self._consumer:
            try:
                if self._message_format == "json":
                    value = json.loads(message.value.decode("utf-8"))
                else:
                    value = {"value": message.value.decode("utf-8")}

                # Add metadata
                value["_kafka_topic"] = message.topic
                value["_kafka_partition"] = message.partition
                value["_kafka_offset"] = message.offset
                value["_kafka_timestamp"] = message.timestamp

                messages.append(value)
                count += 1

                if count >= self._sample_size:
                    break
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                # Skip malformed messages but track them
                messages.append(
                    {
                        "_kafka_topic": message.topic,
                        "_kafka_partition": message.partition,
                        "_kafka_offset": message.offset,
                        "_kafka_error": str(e),
                    }
                )
                count += 1

        self._messages_consumed = count

        if not messages:
            df = pd.DataFrame()
        else:
            df = pd.json_normalize(messages)

        # Register with DuckDB
        self._engine.conn.register(self._view_name, df)
        self._source = self._view_name
        self._loaded = True

        # Close consumer
        self._consumer.close()

    @property
    def row_count(self) -> int:
        """Get number of messages consumed."""
        self._ensure_loaded()
        return self._messages_consumed

    @property
    def columns(self) -> list[str]:
        """Get column names from consumed messages."""
        if self._columns_cache is None:
            self._ensure_loaded()
            self._columns_cache = self._engine.get_columns(self._view_name)
        return self._columns_cache

    @property
    def messages_consumed(self) -> int:
        """Get the actual number of messages consumed."""
        self._ensure_loaded()
        return self._messages_consumed

    @property
    def parse_error_count(self) -> int:
        """Get count of messages that failed to parse."""
        self._ensure_loaded()
        sql = f"SELECT COUNT(*) FROM {self._view_name} WHERE _kafka_error IS NOT NULL"
        return self._engine.fetch_value(sql) or 0


class KafkaStreamValidator:
    """
    Continuous streaming validator for Kafka.

    Validates messages in real-time as they arrive.

    Example:
        validator = KafkaStreamValidator(
            "kafka://localhost:9092/orders",
            rules=[
                lambda msg: msg.get("amount", 0) > 0,
                lambda msg: msg.get("customer_id") is not None,
            ]
        )

        # Start validation (blocks)
        validator.start()

        # Or get validation results
        for result in validator.validate_stream():
            if not result.passed:
                print(f"Validation failed: {result.message}")
    """

    def __init__(
        self,
        source: str,
        rules: list[callable] | None = None,
        **options: Any,
    ):
        self.source = source
        self.rules = rules or []
        self.options = options
        self._consumer = None
        self._stats = {
            "messages_processed": 0,
            "messages_passed": 0,
            "messages_failed": 0,
        }

    def add_rule(self, rule: callable) -> KafkaStreamValidator:
        """Add a validation rule."""
        self.rules.append(rule)
        return self

    def validate_message(self, message: dict) -> tuple[bool, list[str]]:
        """Validate a single message against all rules."""
        failures = []
        for i, rule in enumerate(self.rules):
            try:
                if not rule(message):
                    failures.append(f"Rule {i + 1} failed")
            except Exception as e:
                failures.append(f"Rule {i + 1} error: {e}")

        return len(failures) == 0, failures

    @property
    def stats(self) -> dict[str, int]:
        """Get validation statistics."""
        return self._stats.copy()
