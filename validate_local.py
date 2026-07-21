"""Validación local del conector elasticsearch: ejercita las 3 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_ELASTICSEARCH_* exportadas en el entorno, y
un índice "productos" accesible con al menos un documento con el campo
"ciudad": "Bogota".
"""

from ruvic_elasticsearch_connector import ElasticsearchClient, setup_logging

setup_logging("INFO")
client = ElasticsearchClient()

print("== 1. Índices ==")
for idx in client.list_indices():
    print(f"  {idx['index']} ({idx['documents']} documentos, {idx['size']})")

print("== 2. Buscar documentos (ciudad=Bogota) ==")
hits = client.search_documents("productos", {"match": {"ciudad": "Bogota"}}, size=10)
for hit in hits:
    print(f"  id={hit['id']} score={hit['score']} {hit['source']}")

print("== 3. Contar documentos ==")
total = client.count_documents("productos")
bogota = client.count_documents("productos", {"match": {"ciudad": "Bogota"}})
print(f"  total={total} en_bogota={bogota}")
