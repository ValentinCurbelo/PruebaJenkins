# RAMA DEVEL

Esta rama se utiliza para probar el pipeline multibranch.

## Métricas y monitoreo

La API expone métricas compatibles con Prometheus en `GET /metrics`:

- `notes_created_total`: notas creadas desde que inició el proceso.
- `notes_total`: cantidad actual de notas almacenadas.
- `http_request_duration_seconds`: histograma de duración y llamadas por endpoint.

Prometheus consulta `notas-api:8000/metrics` cada 15 segundos. El dashboard
`Monitoreo API de notas` de Grafana muestra estas tres métricas.
