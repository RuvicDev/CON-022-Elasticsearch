---
name: elasticsearch
description: >
  Usa la librería ruvic_elasticsearch_connector para consultar clústeres
  Elasticsearch en modo solo lectura - listar índices con su tamaño y
  conteo de documentos (list_indices), buscar documentos con Query DSL
  (search_documents) y contar documentos que cumplen una consulta
  (count_documents). Úsala cuando el usuario pida buscar, consultar o
  explorar datos indexados en Elasticsearch.
triggers:
- elasticsearch
- elastic
- búsqueda
- índice
- buscar documentos
---

# Conector Elasticsearch (ruvic_elasticsearch_connector)

Librería Python de solo lectura para Elasticsearch. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/Dgirto/Elasticsearch.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `elasticsearch` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_ELASTICSEARCH_HOST` | Host del clúster |
| `RUVIC_ELASTICSEARCH_PORT` | Puerto (default 9200) |
| `RUVIC_ELASTICSEARCH_USERNAME` | Usuario |
| `RUVIC_ELASTICSEARCH_PASSWORD` | Contraseña |
| `RUVIC_ELASTICSEARCH_USE_SSL` | (opcional) `true`/`false`, default `true` |
| `RUVIC_ELASTICSEARCH_VERIFY_CERTS` | (opcional) `true`/`false`, default `true` |
| `RUVIC_ELASTICSEARCH_CONNECT_TIMEOUT` | (opcional) timeout en segundos |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Conexión (siempre igual)

```python
from ruvic_elasticsearch_connector import ElasticsearchClient

client = ElasticsearchClient()  # lee RUVIC_ELASTICSEARCH_* del entorno automáticamente
```

## Capacidad 1 — Listar índices

```python
indices = client.list_indices()
for idx in indices:
    print(f"{idx['index']}: {idx['documents']} documentos, {idx['size']}")
```

Por defecto excluye índices de sistema (los que empiezan con `.`); pasa `include_system=True` si necesitas verlos.

## Capacidad 2 — Buscar documentos (Query DSL)

```python
hits = client.search_documents(
    "productos",
    {"match": {"categoria": "electronica"}},
    size=20,
)
for hit in hits:
    print(hit["id"], hit["score"], hit["source"])
```

`query` acepta cualquier consulta válida de [Query DSL](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html) de Elasticsearch (`match`, `term`, `range`, `bool`, etc.). Pasa `None` para traer todos los documentos (`match_all`) hasta el límite de `size`.

## Capacidad 3 — Contar documentos

```python
total = client.count_documents("productos")
en_categoria = client.count_documents("productos", {"match": {"categoria": "electronica"}})
```

Acepta el mismo tipo de `query` que `search_documents`.

## Manejo de errores

```python
from ruvic_elasticsearch_connector import (
    ElasticsearchAuthError, ElasticsearchDataError, ElasticsearchNetworkError,
)

try:
    hits = client.search_documents("pedidos", {"match_all": {}})
except ElasticsearchAuthError:
    print("Credenciales inválidas o sin permiso sobre ese índice")
except ElasticsearchNetworkError:
    print("No se pudo alcanzar el clúster — revisa host/puerto/red")
except ElasticsearchDataError as e:
    print(f"Error de datos: {e}")  # ej. el índice no existe, o la query es inválida
```

## Comportamiento conversacional

### Cuándo pedir aclaración (y cuándo NO)

Pide aclaración únicamente cuando la búsqueda requiere filtrar por una entidad
específica (ej. un cliente), el usuario no la nombró ni dio nada que la
identifique, y existe más de una posible. En cualquier otro caso, responde
directo — nunca preguntes "de más".

| Situación | ¿Preguntar? |
|---|---|
| El usuario pide una agregación, ranking o promedio ("¿cuál cliente compró más?", "total del mes") | No — usa una agregación de Query DSL (`terms`, `sum`, etc.) y responde, sin necesitar que el usuario elija nada |
| El usuario pide documentos de "el cliente" sin decir cuál, y hay varios posibles | Sí — pregunta cuál, mostrando las opciones disponibles si las tienes a mano |
| El usuario nombra la entidad, exacta o aproximada (ej. "empresa cinco" en vez de "Empresa 5") | No — resuélvelo con un `match` de texto (Elasticsearch ya tolera variaciones), no pidas que lo repita exacto |
| El usuario nombra una entidad que no existe en los datos | No es ambigüedad — informa que no existe y, si es útil, muestra qué valores sí hay en ese índice |

### Sugerencias de seguimiento

Después de responder, ofrece una sugerencia de seguimiento solo si deja algo
útil sin resolver — no la agregues en cada respuesta, se vuelve ruido. Ejemplo:
si mostraste los documentos de un cliente, puede tener sentido ofrecer
compararlo contra el promedio general; si ya mostraste un ranking completo,
no sugieras nada más, la respuesta ya está completa.

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_ELASTICSEARCH_*` (el constructor de `ElasticsearchClient` ya lo hace).
2. Nunca imprimas `RUVIC_ELASTICSEARCH_PASSWORD` en logs ni en la salida.
3. La librería es de SOLO LECTURA: no intentes indexar, actualizar ni eliminar documentos con ella.
4. Usa `size` razonable en `search_documents` (default 10, máximo 1000) para no traer resultados masivos.
5. Construye el `query` como Query DSL válido; si no estás seguro de la sintaxis, usa `{"match": {"campo": "valor"}}` para búsquedas simples de texto.
