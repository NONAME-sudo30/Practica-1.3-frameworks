import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import models

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()
# Logger para guardar el error real en la consola del servidor
logger = logging.getLogger("app")

app = FastAPI()


# ---------- MIDDLEWARE PERSONALIZADO: X-Process-Time ----------
# Lo registro primero para que quede por dentro de CORS (luego explico por qué)
@app.middleware("http")
async def añadir_tiempo_de_proceso(request: Request, call_next):
    inicio = time.perf_counter()  # momento en que llega la petición

    try:
        respuesta = await call_next(request)
    except Exception:
        # Si algo peta, lo capturo aquí para que la respuesta de error
        # también lleve la cabecera X-Process-Time y las cabeceras de CORS
        logger.exception("Error no controlado en %s", request.url.path)
        respuesta = JSONResponse(
            status_code=500,
            content={"error": "Error interno del servidor"},
        )

    # Paso de segundos a milisegundos
    milisegundos = (time.perf_counter() - inicio) * 1000
    respuesta.headers["X-Process-Time"] = f"{milisegundos:.2f} ms"
    return respuesta


# ---------- CORS ----------
# Lo registro DESPUÉS para que sea el middleware más externo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # origen del frontend (Vite)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],  # así el JS del frontend puede leerla
)


# ---------- EXCEPTION HANDLER GLOBAL ----------
# Red de seguridad: captura cualquier excepción que no haya controlado nadie
@app.exception_handler(Exception)
async def manejador_global_de_excepciones(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Error interno del servidor"},  # sin stacktrace
    )


# ---------- RUTAS DE PRUEBA ----------
@app.get("/")
async def inicio():
    return {"mensaje": "Todo correcto"}


@app.get("/error")
async def forzar_error():
    # Excepción forzada para comprobar que el servidor no se cae
    raise RuntimeError("Fallo provocado a propósito")
