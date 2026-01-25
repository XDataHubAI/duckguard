"""Dataset class representing a data source for validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from duckguard.core.engine import DuckGuardEngine
from duckguard.core.column import Column

if TYPE_CHECKING:
    from duckguard.core.scoring import QualityScore


class Dataset:
    """
    Represents a data source with validation capabilities.

    A Dataset wraps a data source (file, database table, etc.) and provides
    a Pythonic interface for accessing columns and performing validations.

    Example:
        orders = Dataset("data/orders.csv")
        assert orders.row_count > 0
        assert orders.customer_id.null_percent < 5
    """

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine | None = None,
        name: str | None = None,
    ):
        """
        Initialize a Dataset.

        Args:
            source: Path to file or connection string
            engine: Optional DuckGuardEngine instance (uses singleton if not provided)
            name: Optional name for the dataset (defaults to source)
        """
        self._source = source
        self._engine = engine or DuckGuardEngine.get_instance()
        self._name = name or source
        self._columns_cache: list[str] | None = None
        self._row_count_cache: int | None = None

    @property
    def source(self) -> str:
        """Get the source path or connection string."""
        return self._source

    @property
    def name(self) -> str:
        """Get the dataset name."""
        return self._name

    @property
    def engine(self) -> DuckGuardEngine:
        """Get the underlying engine."""
        return self._engine

    @property
    def row_count(self) -> int:
        """
        Get the number of rows in the dataset.

        Returns:
            Number of rows
        """
        if self._row_count_cache is None:
            self._row_count_cache = self._engine.get_row_count(self._source)
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """
        Get the list of column names.

        Returns:
            List of column names
        """
        if self._columns_cache is None:
            self._columns_cache = self._engine.get_columns(self._source)
        return self._columns_cache

    @property
    def column_count(self) -> int:
        """Get the number of columns."""
        return len(self.columns)

    def __getattr__(self, name: str) -> Column:
        """
        Access columns as attributes.

        This allows Pythonic access like: dataset.customer_id

        Args:
            name: Column name

        Returns:
            Column object for the specified column

        Raises:
            AttributeError: If the column doesn't exist
        """
        # Avoid infinite recursion for private attributes
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Check if column exists
        if name not in self.columns:
            raise AttributeError(
                f"Column '{name}' not found. Available columns: {', '.join(self.columns)}"
            )

        return Column(name, self)

    def __getitem__(self, name: str) -> Column:
        """
        Access columns using bracket notation.

        This allows access like: dataset["customer_id"]

        Args:
            name: Column name

        Returns:
            Column object for the specified column
        """
        if name not in self.columns:
            raise KeyError(
                f"Column '{name}' not found. Available columns: {', '.join(self.columns)}"
            )
        return Column(name, self)

    def column(self, name: str) -> Column:
        """
        Get a Column object by name.

        Args:
            name: Column name

        Returns:
            Column object
        """
        return self[name]

    def has_column(self, name: str) -> bool:
        """
        Check if a column exists.

        Args:
            name: Column name to check

        Returns:
            True if column exists
        """
        return name in self.columns

    def sample(self, n: int = 10) -> list[dict[str, Any]]:
        """
        Get a sample of rows from the dataset.

        Args:
            n: Number of rows to sample

        Returns:
            List of dictionaries representing rows
        """
        ref = self._engine.get_source_reference(self._source)
        sql = f"SELECT * FROM {ref} LIMIT {n}"
        result = self._engine.execute(sql)

        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    def head(self, n: int = 5) -> list[dict[str, Any]]:
        """
        Get the first n rows from the dataset.

        Args:
            n: Number of rows

        Returns:
            List of dictionaries representing rows
        """
        return self.sample(n)

    def execute_sql(self, sql: str) -> list[tuple[Any, ...]]:
        """
        Execute a custom SQL query against this dataset.

        The query can reference the dataset using {source} placeholder.

        Args:
            sql: SQL query with optional {source} placeholder

        Returns:
            Query results as list of tuples
        """
        ref = self._engine.get_source_reference(self._source)
        formatted_sql = sql.format(source=ref)
        return self._engine.fetch_all(formatted_sql)

    def clear_cache(self) -> None:
        """Clear cached values (row count, columns)."""
        self._row_count_cache = None
        self._columns_cache = None

    def __repr__(self) -> str:
        return f"Dataset('{self._source}', rows={self.row_count}, columns={self.column_count})"

    def __str__(self) -> str:
        return f"Dataset: {self._name} ({self.row_count} rows, {self.column_count} columns)"

    def __len__(self) -> int:
        """Return the number of rows."""
        return self.row_count

    def __contains__(self, column: str) -> bool:
        """Check if a column exists."""
        return column in self.columns

    def __iter__(self):
        """Iterate over column names."""
        return iter(self.columns)

    def score(
        self,
        weights: dict | None = None,
    ) -> "QualityScore":
        """
        Calculate data quality score for this dataset.

        Evaluates data across standard quality dimensions:
        - Completeness: Are all required values present?
        - Uniqueness: Are values appropriately unique?
        - Validity: Do values conform to expected formats/ranges?
        - Consistency: Are values consistent?

        Args:
            weights: Optional custom weights for dimensions.
                     Keys: 'completeness', 'uniqueness', 'validity', 'consistency'
                     Values must sum to 1.0

        Returns:
            QualityScore with overall score, grade, and dimension breakdowns.

        Example:
            score = orders.score()
            print(score.overall)        # 87.5
            print(score.grade)          # 'B'
            print(score.completeness)   # 95.0

            # With custom weights
            score = orders.score(weights={
                'completeness': 0.4,
                'uniqueness': 0.2,
                'validity': 0.3,
                'consistency': 0.1,
            })
        """
        from duckguard.core.scoring import QualityScorer, QualityDimension

        # Convert string keys to QualityDimension enums if needed
        scorer_weights = None
        if weights:
            scorer_weights = {}
            key_mapping = {
                "completeness": QualityDimension.COMPLETENESS,
                "uniqueness": QualityDimension.UNIQUENESS,
                "validity": QualityDimension.VALIDITY,
                "consistency": QualityDimension.CONSISTENCY,
            }
            for key, value in weights.items():
                if isinstance(key, str):
                    scorer_weights[key_mapping[key]] = value
                else:
                    scorer_weights[key] = value

        scorer = QualityScorer(weights=scorer_weights)
        return scorer.score(self)
