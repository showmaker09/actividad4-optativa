"""Dashboard analítico de la Biblioteca Virtual Eclesiástica.

Actividad 4: el reporte se calcula en MongoDB Atlas con un pipeline de
agregación. No se descargan los libros con find({}) ni se procesan con
ciclos en Python.

Las credenciales se leen solo del entorno local (.env). No se escriben
en este archivo.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

NOMBRE_COLECCION = "libros_historicos"
BASE_PREDETERMINADA = "biblioteca_virtual"

# Dataset de muestra de la actividad. replace_one(..., upsert=True)
# inserta o actualiza cada libro sin duplicarlo.
DATOS_MUESTRA = [
    {
        "_id": "LIB-001",
        "titulo": "Crónicas de Mérida",
        "estado": "Publicado",
        "anio_publicacion": 1890,
        "iglesia_origen": "Catedral de San Ildefonso",
        "paginas": [
            {"conteo_palabras": 300},
            {"conteo_palabras": 450},
        ],
    },
    {
        "_id": "LIB-002",
        "titulo": "Archivos Parroquiales",
        "estado": "Publicado",
        "anio_publicacion": 1915,
        "iglesia_origen": "Parroquia de Santiago",
        "paginas": [
            {"conteo_palabras": 500},
            {"conteo_palabras": 550},
        ],
    },
    {
        "_id": "LIB-003",
        "titulo": "Borrador Antiguo",
        "estado": "Borrador",
        "anio_publicacion": 1810,
        "iglesia_origen": "Catedral de San Ildefonso",
        "paginas": [
            {"conteo_palabras": 200},
        ],
    },
]

# Resultados que el dataset de muestra debe producir por sí solo.
# Si la colección real contiene más libros publicados desde 1850,
# el reporte de Atlas puede incluir filas adicionales.
RESULTADOS_ESPERADOS_MUESTRA = [
    {
        "_id": "Parroquia de Santiago",
        "total_paginas": 2,
        "total_palabras": 1050,
        "promedio_palabras": 525,
    },
    {
        "_id": "Catedral de San Ildefonso",
        "total_paginas": 2,
        "total_palabras": 750,
        "promedio_palabras": 375,
    },
]


class CloudDatabaseManager:
    """Conexión a MongoDB Atlas a partir de variables de entorno."""

    @classmethod
    def get_connection(cls):
        """Devuelve la base de datos configurada.

        La actividad define MONGODB_URI. Si el .env local usa el nombre
        MONGO_URI, también se acepta. DB_NAME vale biblioteca_virtual
        cuando no está definida.
        """
        uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
        if not uri:
            raise RuntimeError(
                "Falta la cadena de conexión. Define MONGODB_URI en el "
                "archivo .env local o en el entorno de ejecución. "
                "No coloques la contraseña en el código fuente."
            )

        nombre_db = os.getenv("DB_NAME", BASE_PREDETERMINADA)
        cliente = MongoClient(uri, serverSelectionTimeoutMS=15000)
        cliente.admin.command("ping")
        return cliente[nombre_db]


def cargar_datos_muestra(db):
    """Inserta o actualiza el dataset de prueba de la actividad."""
    coleccion = db[NOMBRE_COLECCION]
    for libro in DATOS_MUESTRA:
        coleccion.replace_one({"_id": libro["_id"]}, libro, upsert=True)
    return coleccion


def generar_reporte_dashboard(db):
    """Ejecuta el pipeline analítico dentro del clúster de Atlas."""
    coleccion = db[NOMBRE_COLECCION]

    pipeline = [
        {
            "$match": {
                "estado": "Publicado",
                "anio_publicacion": {"$gte": 1850},
            }
        },
        {
            "$unwind": "$paginas",
        },
        {
            "$group": {
                "_id": "$iglesia_origen",
                "total_paginas": {"$sum": 1},
                "total_palabras": {
                    "$sum": "$paginas.conteo_palabras",
                },
                "promedio_palabras": {
                    "$avg": "$paginas.conteo_palabras",
                },
            }
        },
        {
            "$sort": {
                "total_palabras": -1,
            }
        },
    ]

    return list(coleccion.aggregate(pipeline))


def _mensaje_sin_secretos(error):
    """Evita imprimir la URI si el controlador la incluye en el error."""
    texto = str(error)
    marcadores = ("mongodb", "://", "@", "password", "auth")
    if any(marca in texto.lower() for marca in marcadores):
        return (
            "No se pudo operar con MongoDB Atlas. Revisa la conectividad "
            "y las variables MONGODB_URI (o MONGO_URI) y DB_NAME en .env."
        )
    return texto


def main():
    try:
        db = CloudDatabaseManager.get_connection()
        cargar_datos_muestra(db)
        reporte = generar_reporte_dashboard(db)
    except (RuntimeError, PyMongoError, OSError) as error:
        raise SystemExit(_mensaje_sin_secretos(error)) from None

    print(f"Base de datos: {db.name}")
    print(f"Colección: {NOMBRE_COLECCION}")
    print("Reporte obtenido desde MongoDB Atlas:")
    if not reporte:
        print("  (sin filas)")
    for fila in reporte:
        promedio = fila.get("promedio_palabras")
        print(
            f"  - {fila.get('_id')}: "
            f"total_paginas={fila.get('total_paginas')}, "
            f"total_palabras={fila.get('total_palabras')}, "
            f"promedio_palabras={promedio}"
        )

    print()
    print("Referencia del dataset de muestra (solo LIB-001, LIB-002 y LIB-003):")
    for fila in RESULTADOS_ESPERADOS_MUESTRA:
        print(
            f"  - {fila['_id']}: "
            f"total_paginas={fila['total_paginas']}, "
            f"total_palabras={fila['total_palabras']}, "
            f"promedio_palabras={fila['promedio_palabras']}"
        )
    print(
        "LIB-003 queda fuera del reporte porque su estado es Borrador "
        "y su año es 1810."
    )
    print(
        "Si Atlas ya tenía otros libros publicados desde 1850, el reporte "
        "real incluye esas iglesias además de la referencia de muestra."
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Bloque 3. Justificación arquitectónica
# =============================================================================
#
# Pregunta 1
# ¿Por qué es una regla crítica de rendimiento colocar $match al inicio
# del pipeline, antes de $unwind y $group, considerando el uso de índices
# B-Tree y el límite de 100 MB de memoria RAM por etapa en los nodos de
# MongoDB Atlas?
#
# Filtrar al principio reduce la cantidad de documentos que atraviesan las
# etapas posteriores. Aquí solo siguen los libros con estado "Publicado" y
# anio_publicacion mayor o igual a 1850. El borrador de 1810 se descarta
# antes de descomponer páginas o agrupar.
#
# Un índice B-Tree adecuado puede ayudar a localizar los documentos que
# cumplen el filtro, sin examinar toda la colección, cuando ese índice
# existe y MongoDB puede usarlo para este $match. En este entregable no se
# afirma que libros_historicos ya tenga ese índice: el aprovechamiento
# depende de ambas condiciones. Colocar $match al inicio deja el pipeline
# en condiciones de usar el índice si está disponible.
#
# $unwind sobre "$paginas" multiplica los documentos de trabajo: cada
# libro pasa a ser un documento por página. Reducir el conjunto antes de
# $unwind y de $group disminuye el trabajo del clúster y la presión sobre
# la memoria. Eso es relevante frente al límite de 100 MB de RAM por etapa
# en los nodos de MongoDB Atlas. Una agrupación que materializa demasiados
# datos puede acercarse a ese tope, fallar o tener que volcar a disco.
# Calcular en el servidor también evita traer toda la colección a Python
# con find({}), lo que aumentaría la RAM local y el costo de transferencia
# de datos (egress).
#
# Pregunta 2
# ¿Qué error lógico o estructural ocurre si ejecutamos $group directamente
# sobre el arreglo "$paginas.conteo_palabras" sin utilizar previamente
# $unwind, al calcular $sum y $avg?
#
# paginas es un arreglo de subdocumentos, no un único valor numérico. Cada
# elemento trae su propio conteo_palabras. Sin $unwind no aparece un
# registro independiente por cada página: el libro sigue siendo un solo
# documento y el arreglo permanece anidado.
#
# Los acumuladores necesitan recibir los valores numéricos de
# conteo_palabras con granularidad de página. $sum y $avg, usados dentro
# de $group, no recorren un arreglo para sumar o promediar sus elementos:
# tratan el arreglo como un valor no numérico y lo ignoran. $sum: 1
# contaría libros, no páginas. El total y el promedio dejarían de
# representar las métricas que pide la actividad.
#
# $unwind aplana "$paginas" y deja un subdocumento por cada documento de
# trabajo. Entonces "$paginas.conteo_palabras" es un número, $sum acumula
# cada palabra y $avg calcula el promedio de las páginas procesadas. Ese
# promedio por página no equivale al promedio por libro. Por ejemplo,
# Crónicas de Mérida aporta dos páginas (300 y 450): después de $unwind
# suman 750 palabras y promedian 375. Sin aplanar el arreglo, ese cálculo
# por página no se obtiene.
