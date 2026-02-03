"""Base connector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


@dataclass
class ConnectionConfig:
    """Configuration for a data source connection."""

    source: str
    table: str | None = None
    schema: str | None = None
    database: str | None = None
    options: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.options is None:
            self.options = {}


class Connector(ABC):
    """
    Base class for data source connectors.

    Connectors handle the logic of connecting to different data sources
    and creating Dataset objects.
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        """
        Initialize the connector.

        Args:
            engine: Optional DuckGuardEngine instance
        """
        self.engine = engine or DuckGuardEngine.get_instance()

    @abstractmethod
    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to a data source and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        pass

    @classmethod
    @abstractmethod
    def can_handle(cls, source: str) -> bool:
        """
        Check if this connector can handle the given source.

        Args:
            source: Source string (path, URL, connection string)

        Returns:
            True if this connector can handle the source
        """
        pass

    @classmethod
    def get_priority(cls) -> int:
        """
        Get the priority of this connector (higher = checked first).

        Returns:
            Priority value
        """
        return 0
