# Conector Elasticsearch (CON-022)

Conector Ruvic de solo lectura para Elasticsearch. Permite listar índices
con su tamaño y conteo de documentos, buscar documentos con Query DSL y
contar documentos que cumplen una consulta.

## Instalación

```bash
pip install git+https://github.com/Dgirto/Elasticsearch.git#subdirectory=lib
```

Python 3.10+. Dependencia única: `elasticsearch>=8.10,<9.0` (cliente oficial).

## Permisos requeridos en el clúster

Crea un usuario dedicado de solo lectura (no reutilizar `elastic` ni un
usuario de aplicación). Con Elasticsearch 8.x (seguridad activada por
defecto), usa la API de seguridad o Kibana:

```
POST /_security/role/ruvic_reader
{
  "cluster": ["monitor"],
  "indices": [
    { "names": ["*"], "privileges": ["read", "view_index_metadata"] }
  ]
}

POST /_security/user/ruvic_reader
{
  "password": "CAMBIA_ESTA_CONTRASEÑA",
  "roles": ["ruvic_reader"]
}
```

- `monitor` a nivel de clúster: necesario para `db.list_indices` (usa
  `_cat/indices`).
- `read` y `view_index_metadata` sobre los índices a exponer: necesario
  para `db.search` y `db.count`. Ajusta `names` a un patrón específico
  (ej. `["productos-*"]`) en vez de `"*"` si quieres limitar el acceso a
  ciertos índices.
- No se otorgan privilegios de escritura (`index`, `delete`, `write`) ni
  de administración (`manage`, `all`).

## Variables de entorno (`RUVIC_ELASTICSEARCH_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_ELASTICSEARCH_HOST` | Sí | Host del clúster |
| `RUVIC_ELASTICSEARCH_PORT` | No (default `9200`) | Puerto |
| `RUVIC_ELASTICSEARCH_USERNAME` | Sí | Usuario |
| `RUVIC_ELASTICSEARCH_PASSWORD` | Sí | Contraseña |
| `RUVIC_ELASTICSEARCH_USE_SSL` | No (default `true`) | Usar HTTPS |
| `RUVIC_ELASTICSEARCH_VERIFY_CERTS` | No (default `true`) | Verificar certificado TLS |
| `RUVIC_ELASTICSEARCH_CONNECT_TIMEOUT` | No (default `10`) | Timeout de conexión en segundos |

## Pruebas locales

Con Docker (clúster de un solo nodo, sin seguridad, solo para pruebas):

```bash
docker run -d --name es-test \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  -p 9200:9200 \
  docker.elastic.co/elasticsearch/elasticsearch:8.13.0

curl -X POST "localhost:9200/productos/_doc/1" -H "Content-Type: application/json" -d '{"nombre":"ACME","ciudad":"Bogota"}'
curl -X POST "localhost:9200/productos/_doc/2" -H "Content-Type: application/json" -d '{"nombre":"Globex","ciudad":"Medellin"}'
curl -X POST "localhost:9200/productos/_refresh"
```

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_ELASTICSEARCH_HOST=localhost
export RUVIC_ELASTICSEARCH_PORT=9200
export RUVIC_ELASTICSEARCH_USERNAME=elastic
export RUVIC_ELASTICSEARCH_PASSWORD=cualquier-valor
export RUVIC_ELASTICSEARCH_USE_SSL=false
export RUVIC_ELASTICSEARCH_VERIFY_CERTS=false

python test_connection.py
python validate_local.py
```

> Con `xpack.security.enabled=false` el clúster de prueba no valida
> usuario/contraseña; en producción siempre debe estar activada la
> seguridad.

Prueba también los casos de error (contraseña incorrecta, host
inalcanzable, índice inexistente) y verifica que los mensajes sean claros.

## Notas de integración

- El conector es de solo lectura: nunca llama a `index`, `update`,
  `delete` ni `bulk`. Solo usa `search`, `count`, `cat.indices` e `info`.
- `search_documents` y `count_documents` aceptan cualquier Query DSL
  válido; el conector no valida su semántica, solo que sea un dict.
- `list_indices` excluye por defecto los índices de sistema (prefijo
  `.`); pásale `include_system=True` para verlos.
- La mayoría de clústeres Elasticsearch 8.x requieren HTTPS y validan
  certificados por defecto; desactiva `VERIFY_CERTS` solo en entornos de
  prueba con certificados autofirmados, nunca en producción.
