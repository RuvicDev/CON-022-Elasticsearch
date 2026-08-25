"""Prueba de conexión estándar del conector elasticsearch.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_ELASTICSEARCH_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Conecta a Elasticsearch y pide info del clúster usando las env vars
    RUVIC_ELASTICSEARCH_*."""
    try:
        from ruvic_elasticsearch_connector import (
            ElasticsearchAuthError,
            ElasticsearchClient,
            ElasticsearchDataError,
            ElasticsearchNetworkError,
        )
    except ImportError:
        return (
            False,
            (
                "La librería ruvic-elasticsearch-connector no está instalada. "
                "Instala con: pip install git+https://github.com/Dgirto/"
                "Elasticsearch.git#subdirectory=lib"
            ),
        )

    try:
        client = ElasticsearchClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except ElasticsearchAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except ElasticsearchNetworkError as exc:
        return False, f"Error de red: {exc}"
    except ElasticsearchDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # noqa: BLE001 - red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (
        True,
        f"Conexión exitosa a {client.config.host}:{client.config.port}",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
