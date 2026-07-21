"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_ELASTICSEARCH_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_ELASTICSEARCH_"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in _TRUE_VALUES


@dataclass(frozen=True)
class ElasticsearchConfig:
    """Parámetros de conexión a Elasticsearch."""

    host: str
    port: int
    username: str
    password: str
    use_ssl: bool
    verify_certs: bool
    connect_timeout: int = 10

    @classmethod
    def from_env(cls) -> "ElasticsearchConfig":
        """Construye la configuración desde las variables RUVIC_ELASTICSEARCH_*.

        Raises:
            ValueError: si falta alguna variable obligatoria.

        Ejemplo:
            >>> config = ElasticsearchConfig.from_env()
            >>> config.host
            'search.empresa.com'
        """
        missing = [
            f"{ENV_PREFIX}{name}"
            for name in ("HOST", "USERNAME", "PASSWORD")
            if not os.environ.get(f"{ENV_PREFIX}{name}")
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector elasticsearch: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )
        return cls(
            host=os.environ[f"{ENV_PREFIX}HOST"],
            port=int(os.environ.get(f"{ENV_PREFIX}PORT", "9200")),
            username=os.environ[f"{ENV_PREFIX}USERNAME"],
            password=os.environ[f"{ENV_PREFIX}PASSWORD"],
            use_ssl=_as_bool(os.environ.get(f"{ENV_PREFIX}USE_SSL"), True),
            verify_certs=_as_bool(os.environ.get(f"{ENV_PREFIX}VERIFY_CERTS"), True),
            connect_timeout=int(os.environ.get(f"{ENV_PREFIX}CONNECT_TIMEOUT", "10")),
        )
