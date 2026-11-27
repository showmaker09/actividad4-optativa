"""Módulo de persistencia resiliente para la Biblioteca Virtual Eclesiástica.

Actividad 5: Tolerancia a Fallos, Exponential Backoff y Resiliencia Cloud.

- Configura la URI de MongoDB Atlas con parámetros de resiliencia y balanceo:
  retryWrites=true, w=majority y readPreference=secondaryPreferred.
- Reintenta únicamente errores transitorios de red (AutoReconnect y
  NetworkTimeout) aplicando Exponential Backoff.
- Aborta de inmediato ante errores lógicos o de negocio (DuplicateKeyError y
  OperationFailure).

Las credenciales se leen únicamente desde variables de entorno (.env).
"""

import os
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import (
    AutoReconnect,
    DuplicateKeyError,
    NetworkTimeout,
    OperationFailure,
)

load_dotenv()

BASE_DATOS = "biblioteca_virtual"
COLECCION_PAGINAS = "paginas_digitalizadas"

PARAMETROS_RESILIENTES = (
    ("retryWrites", "true"),
    ("w", "majority"),
    ("readPreference", "secondaryPreferred"),
)

URI_PLANTILLA_EJEMPLO = (
    "mongodb+srv://<cluster-host>/"
    "?retryWrites=true&w=majority&readPreference=secondaryPreferred"
)


def construir_uri_resiliente(uri_base):
    """Asegura los parámetros de resiliencia en la URI sin duplicarlos."""
    if not uri_base or not uri_base.strip():
        return URI_PLANTILLA_EJEMPLO

    partes = urlsplit(uri_base.strip())
    parametros = parse_qsl(partes.query, keep_blank_values=True)
    claves_requeridas = {clave.lower() for clave, _ in PARAMETROS_RESILIENTES}

    # Conserva parámetros existentes que no entren en conflicto y evita duplicados.
    filtrados = [
        (clave, valor)
        for clave, valor in parametros
        if clave.lower() not in claves_requeridas
    ]
    filtrados.extend(PARAMETROS_RESILIENTES)

    nueva_query = urlencode(filtrados)
    return urlunsplit(
        (partes.scheme, partes.netloc, partes.path, nueva_query, partes.fragment)
    )


_URI_ENTORNO = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or ""

# Bloque 1 — URI resiliente y balanceo.
# Si existe MONGODB_URI (o MONGO_URI) en .env, completa la cadena garantizando
# retryWrites=true, w=majority y readPreference=secondaryPreferred sin duplicar.
URI_RESILIENTE = construir_uri_resiliente(_URI_ENTORNO)


def conectar_cluster():
    """Crea el cliente de MongoDB Atlas y devuelve la base biblioteca_virtual."""
    uri_entorno = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    if not uri_entorno:
        raise RuntimeError(
            "Falta la cadena de conexión. Define MONGODB_URI (o MONGO_URI) "
            "en el archivo .env local sin guardar credenciales en el código."
        )

    uri_final = construir_uri_resiliente(uri_entorno)
    cliente = MongoClient(
        uri_final,
        serverSelectionTimeoutMS=5000,
        tls=True,
    )
    nombre_db = os.getenv("DB_NAME") or BASE_DATOS
    return cliente[nombre_db]


def guardar_pagina_resiliente(db, documento_pagina, max_intentos=3):
    """Inserta una página digitalizada con Exponential Backoff ante fallos de red.

    Reintenta exclusivamente AutoReconnect y NetworkTimeout con espera de
    2 ** (intento - 1) segundos. Aborta inmediatamente ante DuplicateKeyError
    u OperationFailure.
    """
    coleccion = db[COLECCION_PAGINAS]
    ultimo_error = None

    for intento in range(1, max_intentos + 1):
        try:
            resultado = coleccion.insert_one(documento_pagina)
            return resultado.inserted_id
        except (AutoReconnect, NetworkTimeout) as error:
            ultimo_error = error
            espera = 2 ** (intento - 1)
            print(
                f"[ADVERTENCIA] Intento {intento}/{max_intentos} falló por "
                f"error transitorio de red ({type(error).__name__}): {error}. "
                f"Esperando {espera}s antes de continuar..."
            )
            time.sleep(2 ** (intento - 1))
        except (DuplicateKeyError, OperationFailure) as error:
            print(
                f"[ERROR LÓGICO] Fallo en intento {intento}/{max_intentos} "
                f"({type(error).__name__}): {error}. Abortando sin reintentos."
            )
            raise

    raise RuntimeError(
        f"No se pudo guardar la página tras {max_intentos} intentos "
        f"consecutivos por errores transitorios de red."
    ) from ultimo_error


def _mensaje_sin_secretos(error):
    """Evita imprimir credenciales si algún mensaje de error contiene la URI."""
    texto = str(error)
    marcadores = ("mongodb", "://", "@", "password")
    if any(marca in texto.lower() for marca in marcadores):
        return (
            "Error al comunicarse con MongoDB Atlas. Verifica la conectividad "
            "y la configuración de MONGODB_URI / MONGO_URI en .env."
        )
    return texto


if __name__ == "__main__":
    print("=== Biblioteca Virtual Eclesiástica — Persistencia Resiliente ===")

    documento_prueba = {
        "libro_id": "LIB-001",
        "titulo": "Crónicas de Mérida",
        "numero_pagina": 1,
        "iglesia_origen": "Catedral de San Ildefonso",
        "conteo_palabras": 320,
        "estado_ocr": "Completado",
        "texto_ocr": "Registro histórico digitalizado desde nodo remoto.",
    }

    try:
        db = conectar_cluster()
        print(f"Conectado a la base de datos: {db.name}")
        print(f"Insertando documento en la colección '{COLECCION_PAGINAS}'...")
        id_insertado = guardar_pagina_resiliente(db, documento_prueba)
        print(f"[OK] Página guardada correctamente. ID insertado: {id_insertado}")
    except (DuplicateKeyError, OperationFailure) as error:
        print(f"[ABORTADO] Error lógico o de operación: {_mensaje_sin_secretos(error)}")
        raise SystemExit(1) from None
    except RuntimeError as error:
        print(f"[FALLO DEFINITIVO] {_mensaje_sin_secretos(error)}")
        raise SystemExit(1) from None
