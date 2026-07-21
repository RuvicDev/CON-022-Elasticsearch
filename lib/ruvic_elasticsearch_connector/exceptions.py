"""Excepciones propias del conector Elasticsearch.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del driver subyacente.
"""


class ElasticsearchConnectorError(Exception):
    """Error base del conector."""


class ElasticsearchAuthError(ElasticsearchConnectorError):
    """Credenciales inválidas o permisos insuficientes."""


class ElasticsearchNetworkError(ElasticsearchConnectorError):
    """No se pudo alcanzar el clúster (host/puerto/red/timeout)."""


class ElasticsearchDataError(ElasticsearchConnectorError):
    """La operación es válida pero el índice/consulta es inválido."""
