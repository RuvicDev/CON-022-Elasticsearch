"""Cliente de solo lectura para Elasticsearch.

Capacidades:
- list_indices():       listar índices del clúster con su tamaño y conteo de documentos.
- search_documents():   buscar documentos en un índice (Query DSL).
- count_documents():    contar documentos que cumplen una consulta.

Las credenciales SIEMPRE provienen de variables de entorno
RUVIC_ELASTICSEARCH_* (ver config.ElasticsearchConfig.from_env).
Prohibido hardcodearlas.
"""

from __future__ import annotations

from typing import Any

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import (
    ApiError,
    AuthenticationException,
    AuthorizationException,
    BadRequestError,
    ConnectionError as ESConnectionError,
    ConnectionTimeout,
    NotFoundError,
)

from .config import ElasticsearchConfig
from .exceptions import (
    ElasticsearchAuthError,
    ElasticsearchConnectorError,
    ElasticsearchDataError,
    ElasticsearchNetworkError,
)
from .logging_utils import get_logger

_MAX_SEARCH_SIZE = 1_000


def _validate_index(index: str) -> str:
    index = (index or "").strip()
    if not index:
        raise ElasticsearchDataError("index no puede estar vacío.")
    return index


def _validate_query(query: dict[str, Any] | None) -> dict[str, Any]:
    if query is None:
        return {"match_all": {}}
    if not isinstance(query, dict):
        raise ElasticsearchDataError("query debe ser un dict (Query DSL) o None.")
    return query


def _wrap_api_error(exc: ApiError, not_found_message: str) -> ElasticsearchConnectorError:
    """Traduce un error de la API de Elasticsearch a una excepción propia,
    sin dejar escapar nunca el tipo crudo del driver."""
    if isinstance(exc, (AuthenticationException, AuthorizationException)):
        return ElasticsearchAuthError(
            "Credenciales inválidas o sin permiso suficiente sobre ese "
            "índice. Revisa el rol asignado al usuario en el clúster."
        )
    if isinstance(exc, NotFoundError):
        return ElasticsearchDataError(not_found_message)
    if isinstance(exc, BadRequestError):
        return ElasticsearchDataError(f"Consulta inválida: {exc}")
    return ElasticsearchDataError(f"Error de datos: {exc}")


class ElasticsearchClient:
    """Cliente de solo lectura para Elasticsearch.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_ELASTICSEARCH_* (comportamiento
            estándar en el runtime de la plataforma).

    Ejemplo:
        >>> client = ElasticsearchClient()  # lee RUVIC_ELASTICSEARCH_* del entorno
        >>> client.list_indices()
        [{'index': 'productos', 'documents': 15234, 'size': '8.2 MB', ...}]
    """

    def __init__(self, config: ElasticsearchConfig | None = None) -> None:
        self.config = config or ElasticsearchConfig.from_env()
        self._logger = get_logger()
        self._client: Elasticsearch | None = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_client(self) -> Elasticsearch:
        if self._client is not None:
            return self._client
        scheme = "https" if self.config.use_ssl else "http"
        self._client = Elasticsearch(
            hosts=[f"{scheme}://{self.config.host}:{self.config.port}"],
            basic_auth=(self.config.username, self.config.password),
            verify_certs=self.config.verify_certs,
            request_timeout=self.config.connect_timeout,
        )
        return self._client

    def ping(self) -> bool:
        """Verifica la conexión pidiendo la información del clúster.

        Returns:
            True si la conexión funciona.

        Raises:
            ElasticsearchAuthError / ElasticsearchNetworkError / ElasticsearchDataError.
        """
        try:
            self._get_client().info()
        except (AuthenticationException, AuthorizationException) as exc:
            raise ElasticsearchAuthError(
                "Autenticación fallida: usuario o contraseña inválidos, o "
                "el usuario no tiene permiso para consultar el clúster."
            ) from exc
        except (ESConnectionError, ConnectionTimeout) as exc:
            raise ElasticsearchNetworkError(
                f"No se pudo conectar a {self.config.host}:{self.config.port} "
                f"(timeout {self.config.connect_timeout}s). Verifica host, puerto "
                "y acceso de red."
            ) from exc
        except ApiError as exc:
            raise _wrap_api_error(exc, "No se pudo obtener información del clúster.") from exc
        self._logger.info("Ping exitoso a %s:%s", self.config.host, self.config.port)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: listar índices
    # ------------------------------------------------------------------ #

    def list_indices(self, include_system: bool = False) -> list[dict[str, Any]]:
        """Lista los índices del clúster con su conteo de documentos y tamaño.

        Args:
            include_system: si True, incluye índices de sistema (los que
                empiezan con "."). Default False.

        Returns:
            Lista de dicts: {"index", "health", "status", "documents", "size"}.

        Ejemplo:
            >>> client.list_indices()
            [{'index': 'productos', 'health': 'green', 'status': 'open', 'documents': 15234, 'size': '8.2mb'}]
        """
        client = self._get_client()
        try:
            rows = client.cat.indices(format="json")
        except (AuthenticationException, AuthorizationException) as exc:
            raise ElasticsearchAuthError(
                "El usuario no tiene permiso para listar índices."
            ) from exc
        except (ESConnectionError, ConnectionTimeout) as exc:
            raise ElasticsearchNetworkError(f"No se pudo listar índices: {exc}") from exc
        except ApiError as exc:
            raise _wrap_api_error(exc, "No se pudieron listar los índices.") from exc

        result = [
            {
                "index": row.get("index"),
                "health": row.get("health"),
                "status": row.get("status"),
                "documents": int(row.get("docs.count") or 0),
                "size": row.get("store.size"),
            }
            for row in rows
            if include_system or not str(row.get("index", "")).startswith(".")
        ]
        result.sort(key=lambda r: r["index"] or "")
        self._logger.info("Se listaron %d índices", len(result))
        return result

    # ------------------------------------------------------------------ #
    # Capacidad 2: buscar documentos
    # ------------------------------------------------------------------ #

    def search_documents(
        self,
        index: str,
        query: dict[str, Any] | None = None,
        size: int = 10,
    ) -> list[dict[str, Any]]:
        """Busca documentos en un índice.

        Args:
            index: nombre del índice.
            query: consulta en formato Query DSL de Elasticsearch (ej.
                {"match": {"titulo": "portatil"}}). None o vacío trae
                todos los documentos (match_all), hasta el límite.
            size: máximo de documentos a retornar (default 10, máximo 1000).

        Returns:
            Lista de dicts: {"id", "score", "source"} — "source" es el
            documento original indexado.

        Ejemplo:
            >>> client.search_documents("productos", {"match": {"categoria": "electronica"}})
            [{'id': 'abc123', 'score': 1.8, 'source': {'nombre': 'Portátil', ...}}]
        """
        index = _validate_index(index)
        query = _validate_query(query)
        size = max(1, min(int(size), _MAX_SEARCH_SIZE))
        client = self._get_client()
        try:
            response = client.search(index=index, query=query, size=size)
        except (AuthenticationException, AuthorizationException) as exc:
            raise ElasticsearchAuthError(
                f"El usuario no tiene permiso de lectura sobre el índice {index!r}."
            ) from exc
        except (ESConnectionError, ConnectionTimeout) as exc:
            raise ElasticsearchNetworkError(f"No se pudo buscar documentos: {exc}") from exc
        except ApiError as exc:
            raise _wrap_api_error(exc, f"El índice {index!r} no existe.") from exc

        hits = response["hits"]["hits"]
        results = [
            {"id": hit["_id"], "score": hit.get("_score"), "source": hit["_source"]}
            for hit in hits
        ]
        self._logger.info('Encontrados %d documentos en "%s"', len(results), index)
        return results

    # ------------------------------------------------------------------ #
    # Capacidad 3: contar documentos
    # ------------------------------------------------------------------ #

    def count_documents(self, index: str, query: dict[str, Any] | None = None) -> int:
        """Cuenta los documentos de un índice que cumplen una consulta.

        Args:
            index: nombre del índice.
            query: consulta en formato Query DSL. None o vacío cuenta
                todos los documentos del índice.

        Returns:
            Número de documentos que cumplen la consulta.

        Ejemplo:
            >>> client.count_documents("productos", {"match": {"categoria": "electronica"}})
            342
        """
        index = _validate_index(index)
        query = _validate_query(query)
        client = self._get_client()
        try:
            response = client.count(index=index, query=query)
        except (AuthenticationException, AuthorizationException) as exc:
            raise ElasticsearchAuthError(
                f"El usuario no tiene permiso de lectura sobre el índice {index!r}."
            ) from exc
        except (ESConnectionError, ConnectionTimeout) as exc:
            raise ElasticsearchNetworkError(f"No se pudo contar documentos: {exc}") from exc
        except ApiError as exc:
            raise _wrap_api_error(exc, f"El índice {index!r} no existe.") from exc
        count = response["count"]
        self._logger.info('Contados %d documentos en "%s"', count, index)
        return count
