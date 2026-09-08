import json
import os
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


API_TITLE = os.getenv("API_TITLE", "API de notas")
POD_NAME = os.getenv("POD_NAME", "ejecucion-local")
APP_VERSION = os.getenv("APP_VERSION", "local")
BACKGROUND_COLOR = os.getenv("BACKGROUND_COLOR", "#e2e8f0")

app = FastAPI(title=f"{API_TITLE} - {POD_NAME}")

NOTES_FILE = Path(os.getenv("NOTES_FILE", "data/notes.json"))
_file_lock = Lock()


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


@app.get("/", response_class=HTMLResponse)
def health_check() -> str:
    return f"""
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>{API_TITLE} {APP_VERSION}</title>
      </head>
      <body style="background:{BACKGROUND_COLOR}; font-family:Arial,sans-serif;
                   text-align:center; padding-top:80px;">
        <h1>{API_TITLE}</h1>
        <h2>Versión {APP_VERSION}</h2>
        <p>La API está activa</p>
        <p>Pod: <strong>{POD_NAME}</strong></p>
      </body>
    </html>
    """


@app.post("/add/{note_id}", status_code=201)
def add_note(note_id: str, note: NoteInput) -> dict[str, str]:
    with _file_lock:
        notes = _read_notes()
        if note_id in notes:
            raise HTTPException(status_code=409, detail="Ya existe una nota con ese id")

        notes[note_id] = note.text
        _write_notes(notes)

    return {"id": note_id, "text": note.text}


@app.get("/list")
def list_notes() -> list[dict[str, str]]:
    with _file_lock:
        notes = _read_notes()
    return [{"id": note_id, "text": text} for note_id, text in notes.items()]
