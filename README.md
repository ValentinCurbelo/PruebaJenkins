# API de notas

API HTTP mínima para almacenar notas de forma persistente.

## Endpoints

- `GET /`: comprueba que la API está activa.
- `POST /add/{nota_id}`: crea una nota. El cuerpo debe ser JSON, por ejemplo
  `{"text": "Comprar agua"}`. Devuelve `409` si el identificador ya existe.
- `GET /list`: devuelve todas las notas creadas.

## Ejecución local

Instalar las dependencias de `requirements.txt` e iniciar la aplicación ASGI
indicando `app:app`. La documentación interactiva queda disponible en `/docs`.

Las notas se almacenan por defecto en `data/notes.json`. La variable de entorno
`NOTES_FILE` permite cambiar la ruta del archivo. Para persistirlas en un volumen,
el entorno de ejecución debe montar el volumen en la ruta elegida y configurar
`NOTES_FILE` con el archivo ubicado dentro de ese montaje.

No se incluye ni se modifica configuración de Docker.

## Tests unitarios

Instalar las dependencias de desarrollo y ejecutar pytest:

```text
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Integración continua

El `Jenkinsfile` prepara un entorno virtual, instala las dependencias de
desarrollo, publica los resultados JUnit y construye la imagen
`notas-api:<número-del-build>` solamente cuando los tests terminan correctamente.
El agente de Jenkins debe tener Python 3, Docker y acceso al daemon de Docker.
