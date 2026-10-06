import json

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Aísla cada test en su propio archivo de notas temporal."""
    monkeypatch.setattr(app, "NOTES_FILE", tmp_path / "notes.json")
    app.NOTES_TOTAL.set(0)
    return TestClient(app.app)


def test_health_check_muestra_version_e_instancia(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Versión local" in response.text
    assert "ejecucion-local" in response.text


def test_lista_inicialmente_vacia(client):
    response = client.get("/list")

    assert response.status_code == 200
    assert response.json() == []


def test_agrega_y_lista_una_nota(client):
    created = client.post("/add/1", json={"text": "Comprar leche"})

    assert created.status_code == 201
    assert created.json() == {"id": "1", "text": "Comprar leche"}
    assert client.get("/list").json() == [
        {"id": "1", "text": "Comprar leche"}
    ]


def test_persiste_la_nota_en_json(client):
    response = client.post("/add/nota-ñ", json={"text": "Repasar Kubernetes"})

    assert response.status_code == 201
    assert json.loads(app.NOTES_FILE.read_text(encoding="utf-8")) == {
        "nota-ñ": "Repasar Kubernetes"
    }


def test_rechaza_id_duplicado_sin_sobrescribir(client):
    client.post("/add/1", json={"text": "Primera"})

    duplicate = client.post("/add/1", json={"text": "Segunda"})

    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Ya existe una nota con ese id"}
    assert client.get("/list").json() == [{"id": "1", "text": "Primera"}]


@pytest.mark.parametrize("body", [{"text": ""}, {}, {"text": None}])
def test_rechaza_texto_invalido(client, body):
    response = client.post("/add/1", json=body)

    assert response.status_code == 422
    assert client.get("/list").json() == []


def test_detecta_archivo_json_corrupto(client):
    app.NOTES_FILE.write_text("no es json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="JSON inválido"):
        client.get("/list")


def test_expone_metricas_prometheus(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "notes_created_total" in response.text
    assert "notes_total" in response.text
    assert "http_request_duration_seconds" in response.text


def test_actualiza_contador_y_medidor_al_crear_nota(client):
    counter_before = app.NOTES_CREATED._value.get()

    response = client.post("/add/metric-test", json={"text": "Nota observable"})

    assert response.status_code == 201
    assert app.NOTES_CREATED._value.get() == counter_before + 1
    assert app.NOTES_TOTAL._value.get() == 1


def test_histograma_registra_endpoint(client):
    labels = {"method": "GET", "endpoint": "/list", "status_code": "200"}
    count_before = REGISTRY.get_sample_value(
        "http_request_duration_seconds_count", labels
    ) or 0

    response = client.get("/list")

    assert response.status_code == 200
    count_after = REGISTRY.get_sample_value(
        "http_request_duration_seconds_count", labels
    )
    assert count_after == count_before + 1
