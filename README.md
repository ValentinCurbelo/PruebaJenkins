# RAMA DEVEL

Esta rama se utiliza para probar el pipeline multibranch.

## Uso de la aplicación

Con el contenedor en ejecución, abre `http://localhost:8000`. Desde esa
pantalla se pueden crear, editar y eliminar notas. Los datos se guardan en el
volumen Docker `notas-data`.

La API también ofrece estas rutas:

- `GET /list`: lista todas las notas.
- `POST /add/{id}`: crea una nota.
- `PUT /edit/{id}`: cambia el texto de una nota.
- `DELETE /delete/{id}`: elimina una nota.
- `GET /docs`: documentación interactiva de FastAPI.

## Métricas y monitoreo

La API expone métricas compatibles con Prometheus en `GET /metrics`:

- `notes_created_total`: notas creadas desde que inició el proceso.
- `notes_total`: cantidad actual de notas almacenadas.
- `http_request_duration_seconds`: histograma de duración y llamadas por endpoint.

Prometheus consulta `notas-api:8000/metrics` cada 15 segundos. El dashboard
`API de Notas - Observabilidad` está disponible en
`http://localhost:3000/d/notas-api-monitoring/api-de-notas-observabilidad`.
Incluye cantidades de notas, tráfico, errores, latencia p95, llamadas por
endpoint, códigos HTTP y evolución temporal. Su definición reproducible está
en `monitoring/grafana-dashboard.json`.
