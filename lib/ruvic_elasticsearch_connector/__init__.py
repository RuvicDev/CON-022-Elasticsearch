"""Conector Ruvic de solo lectura para Elasticsearch."""

from .client import ElasticsearchClient
from .config import ENV_PREFIX, ElasticsearchConfig
from .exceptions import (
    ElasticsearchAuthError,
    ElasticsearchConnectorError,
    ElasticsearchDataError,
    ElasticsearchNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "ElasticsearchAuthError",
    "ElasticsearchClient",
    "ElasticsearchConfig",
    "ElasticsearchConnectorError",
    "ElasticsearchDataError",
    "ElasticsearchNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
