import json
import os
from time import perf_counter
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field


API_TITLE = os.getenv("API_TITLE", "API de notas")
POD_NAME = os.getenv("POD_NAME", "ejecucion-local")
APP_VERSION = os.getenv("APP_VERSION", "local")
BACKGROUND_COLOR = os.getenv("BACKGROUND_COLOR", "#e2e8f0")

app = FastAPI(title=f"{API_TITLE} - {POD_NAME}")

NOTES_FILE = Path(os.getenv("NOTES_FILE", "data/notes.json"))
_file_lock = Lock()

NOTES_CREATED = Counter(
    "notes_created",
    "Cantidad total de notas creadas durante la ejecución",
)
NOTES_TOTAL = Gauge(
    "notes_total",
    "Cantidad actual de notas almacenadas",
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Duración de las llamadas HTTP por endpoint",
    ["method", "endpoint", "status_code"],
)


class NoteInput(BaseModel):
    text: str = Field(min_length=1)


def _read_notes() -> dict[str, str]:
    if not NOTES_FILE.exists():
        return {}

    try:
        with NOTES_FILE.open(encoding="utf-8") as notes_file:
            data = json.load(notes_file)
    except json.JSONDecodeError as error:
        raise RuntimeError("El archivo de notas contiene JSON inválido") from error

    if not isinstance(data, dict):
        raise RuntimeError("El archivo de notas tiene un formato inválido")
    return data


def _write_notes(notes: dict[str, str]) -> None:
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = NOTES_FILE.with_suffix(f"{NOTES_FILE.suffix}.tmp")
    with temporary_file.open("w", encoding="utf-8") as notes_file:
        json.dump(notes, notes_file, ensure_ascii=False, indent=2)
    temporary_file.replace(NOTES_FILE)


NOTES_TOTAL.set(len(_read_notes()))


@app.middleware("http")
async def record_request_metrics(request: Request, call_next):
    started_at = perf_counter()
    status_code = "500"

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    finally:
        route = request.scope.get("route")
        endpoint = getattr(route, "path", "unmatched")
        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=status_code,
        ).observe(perf_counter() - started_at)


@app.get("/", response_class=HTMLResponse)
def health_check() -> str:
    return f"""
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{API_TITLE} {APP_VERSION}</title>
        <style>
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            background: {BACKGROUND_COLOR};
            color: #172033;
            font-family: Arial, sans-serif;
          }}
          main {{ width: min(880px, 92%); margin: 36px auto; }}
          header, form, .note {{
            background: white;
            border-radius: 14px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, .08);
          }}
          header {{ padding: 24px; margin-bottom: 20px; }}
          header h1 {{ margin: 0 0 8px; }}
          header p {{ margin: 4px 0; color: #64748b; }}
          form {{ padding: 20px; display: grid; gap: 12px; }}
          label {{ font-weight: bold; }}
          input, textarea {{
            width: 100%; padding: 11px; border: 1px solid #cbd5e1;
            border-radius: 8px; font: inherit;
          }}
          textarea {{ min-height: 90px; resize: vertical; }}
          button {{
            border: 0; border-radius: 8px; padding: 10px 14px;
            background: #2563eb; color: white; cursor: pointer;
          }}
          button.danger {{ background: #dc2626; }}
          button.secondary {{ background: #475569; }}
          #status {{ min-height: 22px; margin: 12px 2px; font-weight: bold; }}
          #notes {{ display: grid; gap: 12px; }}
          .note {{ padding: 18px; }}
          .note h3 {{ margin: 0 0 8px; }}
          .note p {{ white-space: pre-wrap; }}
          .actions {{ display: flex; gap: 8px; }}
          .empty {{ color: #64748b; text-align: center; padding: 24px; }}
        </style>
      </head>
      <body>
        <main>
          <header>
            <h1>{API_TITLE}</h1>
            <p>Versión {APP_VERSION} · Pod: <strong>{POD_NAME}</strong></p>
            <p>Creá, editá y eliminá notas guardadas en el volumen Docker.</p>
          </header>

          <form id="note-form">
            <label for="note-id">Identificador</label>
            <input id="note-id" required placeholder="ejemplo: compras">
            <label for="note-text">Texto</label>
            <textarea id="note-text" required placeholder="Escribí la nota..."></textarea>
            <button type="submit">Crear nota</button>
          </form>

          <div id="status"></div>
          <section id="notes"></section>
        </main>

        <script>
          const statusElement = document.getElementById('status');
          const notesElement = document.getElementById('notes');

          function showStatus(message, isError = false) {{
            statusElement.textContent = message;
            statusElement.style.color = isError ? '#b91c1c' : '#166534';
          }}

          async function request(url, options = {{}}) {{
            const response = await fetch(url, options);
            const body = await response.json();
            if (!response.ok) throw new Error(body.detail || 'Ocurrió un error');
            return body;
          }}

          function createButton(label, className, onClick) {{
            const button = document.createElement('button');
            button.textContent = label;
            button.className = className;
            button.addEventListener('click', onClick);
            return button;
          }}

          async function loadNotes() {{
            try {{
              const notes = await request('/list');
              notesElement.replaceChildren();
              if (notes.length === 0) {{
                const empty = document.createElement('p');
                empty.className = 'empty';
                empty.textContent = 'Todavía no hay notas.';
                notesElement.appendChild(empty);
                return;
              }}

              for (const note of notes) {{
                const article = document.createElement('article');
                article.className = 'note';
                const title = document.createElement('h3');
                title.textContent = note.id;
                const text = document.createElement('p');
                text.textContent = note.text;
                const actions = document.createElement('div');
                actions.className = 'actions';
                actions.append(
                  createButton('Editar', 'secondary', () => editNote(note)),
                  createButton('Eliminar', 'danger', () => deleteNote(note.id))
                );
                article.append(title, text, actions);
                notesElement.appendChild(article);
              }}
            }} catch (error) {{
              showStatus(error.message, true);
            }}
          }}

          async function editNote(note) {{
            const text = window.prompt('Nuevo texto para la nota:', note.text);
            if (text === null) return;
            try {{
              await request(`/edit/${{encodeURIComponent(note.id)}}`, {{
                method: 'PUT',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{text}})
              }});
              showStatus('Nota editada.');
              await loadNotes();
            }} catch (error) {{
              showStatus(error.message, true);
            }}
          }}

          async function deleteNote(id) {{
            if (!window.confirm(`¿Eliminar la nota "${{id}}"?`)) return;
            try {{
              await request(`/delete/${{encodeURIComponent(id)}}`, {{method: 'DELETE'}});
              showStatus('Nota eliminada.');
              await loadNotes();
            }} catch (error) {{
              showStatus(error.message, true);
            }}
          }}

          document.getElementById('note-form').addEventListener('submit', async event => {{
            event.preventDefault();
            const id = document.getElementById('note-id').value.trim();
            const text = document.getElementById('note-text').value.trim();
            try {{
              await request(`/add/${{encodeURIComponent(id)}}`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{text}})
              }});
              event.target.reset();
              showStatus('Nota creada.');
              await loadNotes();
            }} catch (error) {{
              showStatus(error.message, true);
            }}
          }});

          loadNotes();
        </script>
      </body>
    </html>
    """


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/add/{note_id}", status_code=201)
def add_note(note_id: str, note: NoteInput) -> dict[str, str]:
    with _file_lock:
        notes = _read_notes()
        if note_id in notes:
            raise HTTPException(status_code=409, detail="Ya existe una nota con ese id")

        notes[note_id] = note.text
        _write_notes(notes)
        NOTES_CREATED.inc()
        NOTES_TOTAL.set(len(notes))

    return {"id": note_id, "text": note.text}


@app.put("/edit/{note_id}")
def edit_note(note_id: str, note: NoteInput) -> dict[str, str]:
    with _file_lock:
        notes = _read_notes()
        if note_id not in notes:
            raise HTTPException(status_code=404, detail="La nota no existe")

        notes[note_id] = note.text
        _write_notes(notes)

    return {"id": note_id, "text": note.text}


@app.delete("/delete/{note_id}")
def delete_note(note_id: str) -> dict[str, str]:
    with _file_lock:
        notes = _read_notes()
        if note_id not in notes:
            raise HTTPException(status_code=404, detail="La nota no existe")

        del notes[note_id]
        _write_notes(notes)
        NOTES_TOTAL.set(len(notes))

    return {"id": note_id, "message": "Nota eliminada"}


@app.get("/list")
def list_notes() -> list[dict[str, str]]:
    with _file_lock:
        notes = _read_notes()
        NOTES_TOTAL.set(len(notes))
    return [{"id": note_id, "text": text} for note_id, text in notes.items()]
