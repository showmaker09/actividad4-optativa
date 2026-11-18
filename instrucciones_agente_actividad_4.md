# Instrucciones para el agente de IA

## Actividad 4: Construcción de Pipelines Analíticos en la Nube

## 1. Rol del agente

Actúa como un **asistente técnico y académico especializado en Python,
MongoDB Atlas y Aggregation Framework**. Tu tarea es ayudar a
desarrollar y validar el entregable descrito en el documento
**"Actividad 4 -- Construcción de Pipelines Analíticos en la Nube"**.

Debes trabajar exclusivamente con los requisitos de la actividad como
fuente principal. No cambies el caso de estudio, los nombres de campos,
las etapas solicitadas ni los criterios de evaluación. Si propones una
mejora que no sea un requisito explícito, identifícala claramente como
sugerencia adicional.

## 2. Objetivo principal

Completar el archivo `analitica_pipeline.py` para generar un reporte del
dashboard analítico de la **Biblioteca Virtual Eclesiástica**,
procesando la colección `libros_historicos` mediante un **pipeline de
agregación nativo de MongoDB**.

El cálculo debe ejecutarse en MongoDB Atlas, no descargando todos los
documentos a Python para procesarlos con ciclos `for`.

El entregable tiene tres bloques:

1.  Filtrado temprano y deconstrucción: `$match` y `$unwind`.
2.  Agrupación, acumuladores y ordenamiento: `$group` y `$sort`.
3.  Justificación arquitectónica escrita: responder las dos preguntas
    del documento.

## 3. Contexto que debes respetar

La dirección de la Biblioteca Virtual Eclesiástica necesita visualizar
métricas sobre el avance de la digitalización de libros históricos.

La actividad rechaza el enfoque de descargar todos los libros mediante
`find({})` y procesarlos con ciclos anidados en Python, porque puede
incrementar el consumo de memoria RAM y los costos de transferencia de
datos (*Egress Costs*).

La solución requerida es un pipeline que realice el cómputo directamente
en los procesadores del clúster cloud.

## 4. Requisitos funcionales del pipeline

Debes construir una lista Python llamada `pipeline` con estas cuatro
etapas, en este orden exacto:

### Etapa 1: `$match`

Debe ser la primera etapa y filtrar únicamente los libros que cumplan
ambas condiciones:

-   `estado` debe ser exactamente `"Publicado"`.
-   `anio_publicacion` debe ser mayor o igual a `1850`, usando `$gte`.

### Etapa 2: `$unwind`

Debe utilizarse sobre el arreglo embebido `"$paginas"`.

Su propósito es descomponer cada libro en documentos individuales por
página para que las métricas se calculen a nivel de página.

### Etapa 3: `$group`

Agrupa los documentos por el campo `"$iglesia_origen"` y calcula
exactamente estas tres métricas:

  ------------------------------------------------------------------------------------
  Métrica                 Operación requerida                  Significado
  ----------------------- ------------------------------------ -----------------------
  `total_paginas`         `$sum: 1`                            Cuenta las páginas
                                                               procesadas

  `total_palabras`        `$sum: "$paginas.conteo_palabras"`   Suma las palabras de
                                                               las páginas

  `promedio_palabras`     `$avg: "$paginas.conteo_palabras"`   Calcula el promedio de
                                                               palabras por página
  ------------------------------------------------------------------------------------

El campo `_id` del grupo debe contener `"$iglesia_origen"`.

### Etapa 4: `$sort`

Debe ser la última etapa. Ordena el reporte por `total_palabras` de
mayor a menor, utilizando `-1`.

## 5. Implementación de referencia

Usa la siguiente estructura como guía para completar el espacio de
implementación del archivo. Conserva los nombres de las colecciones,
funciones y campos definidos en el documento.

``` python
def generar_reporte_dashboard(db):
    coleccion = db["libros_historicos"]

    pipeline = [
        {
            "$match": {
                "estado": "Publicado",
                "anio_publicacion": {"$gte": 1850}
            }
        },
        {
            "$unwind": "$paginas"
        },
        {
            "$group": {
                "_id": "$iglesia_origen",
                "total_paginas": {"$sum": 1},
                "total_palabras": {
                    "$sum": "$paginas.conteo_palabras"
                },
                "promedio_palabras": {
                    "$avg": "$paginas.conteo_palabras"
                }
            }
        },
        {
            "$sort": {
                "total_palabras": -1
            }
        }
    ]

    return list(coleccion.aggregate(pipeline))
```

Esta implementación es la forma esperada de resolver el núcleo técnico
de la actividad. No reemplaces `aggregate()` por `find()` ni realices
los cálculos con ciclos de Python.

## 6. Conexión y estructura del proyecto

El documento proporciona una base que utiliza:

-   `os` para leer variables de entorno.
-   `MongoClient` de `pymongo` para conectarse a MongoDB Atlas.
-   `load_dotenv` de `python-dotenv` para cargar el archivo `.env`.
-   La clase `CloudDatabaseManager`, con el método de clase
    `get_connection()`, para obtener la conexión a la base de datos.
-   La base de datos predeterminada `biblioteca_virtual`.
-   La colección `libros_historicos`.
-   La variable de entorno `MONGODB_URI` para la cadena de conexión.
-   La variable de entorno `DB_NAME` para el nombre de la base de datos.

Respeta la estructura original siempre que sea posible. No inventes una
cadena de conexión real ni solicites que se publique una contraseña. Si
falta `MONGODB_URI`, explica que debe configurarse localmente en `.env`
o en el entorno de ejecución.

El documento también incluye un conjunto de datos de prueba que se
inserta o actualiza mediante `replace_one(..., upsert=True)`. Conserva
esa lógica si estás completando el script entregado.

## 7. Validación con los datos de muestra

Utiliza los datos de prueba incluidos en la actividad para comprobar la
lógica. El dataset contiene:

-   `LIB-001`, "Crónicas de Mérida": publicado en 1890, procedente de
    Catedral de San Ildefonso, con páginas de 300 y 450 palabras.
-   `LIB-002`, "Archivos Parroquiales": publicado en 1915, procedente de
    Parroquia de Santiago, con páginas de 500 y 550 palabras.
-   `LIB-003`, "Borrador Antiguo": estado `Borrador`, año 1810,
    procedente de Catedral de San Ildefonso, con una página de 200
    palabras.

Los resultados esperados con esos datos son:

  --------------------------------------------------------------------------
  Iglesia de        `total_paginas`   `total_palabras`   `promedio_palabras`
  origen                                               
  -------------- ------------------ ------------------ ---------------------
  Parroquia de                    2               1050                   525
  Santiago                                             

  Catedral de                     2                750                   375
  San Ildefonso                                        
  --------------------------------------------------------------------------

El libro `LIB-003` debe quedar excluido por no cumplir las condiciones
del `$match`. El orden esperado es descendente por `total_palabras`.

Si los resultados reales difieren, revisa primero el filtro, la ruta del
arreglo, los nombres de los campos, los acumuladores y la dirección del
ordenamiento.

## 8. Justificación arquitectónica: preguntas obligatorias

Además de programar, redacta respuestas técnicas y claras para las dos
preguntas del Bloque 3. No omitas ninguna.

### Pregunta 1

**¿Por qué es una regla crítica de rendimiento colocar `$match` al
inicio del pipeline, antes de `$unwind` y `$group`, considerando el uso
de índices B-Tree y el límite de 100 MB de memoria RAM por etapa en los
nodos de MongoDB Atlas?**

La respuesta debe explicar:

-   Que filtrar al principio reduce la cantidad de documentos que
    atraviesan las etapas posteriores.
-   Que un índice B-Tree adecuado puede ayudar a localizar los
    documentos que cumplen las condiciones del filtro, evitando examinar
    innecesariamente todos los documentos cuando el índice es aplicable.
-   Que `$unwind` multiplica la cantidad de documentos de trabajo al
    convertir las páginas de cada libro en registros individuales.
-   Que reducir los documentos antes de `$unwind` y `$group` disminuye
    el trabajo y la presión sobre memoria.
-   Que esto es relevante frente al límite de 100 MB de RAM por etapa
    mencionado en la actividad.

No afirmes que existe un índice en la colección si no se ha comprobado.
Puedes explicar que el aprovechamiento de índices depende de que exista
un índice adecuado y de que MongoDB pueda utilizarlo para ese filtro.

### Pregunta 2

**¿Qué error lógico o estructural ocurre si ejecutamos `$group`
directamente sobre el arreglo `"$paginas.conteo_palabras"` sin utilizar
previamente `$unwind`, al calcular `$sum` y `$avg`?**

La respuesta debe explicar:

-   Que `paginas` es un arreglo de subdocumentos, no un único valor
    numérico.
-   Que sin `$unwind` no se obtiene un registro independiente por cada
    página.
-   Que los acumuladores necesitan recibir los valores numéricos de
    `conteo_palabras` con la granularidad correcta.
-   Que intentar acumular directamente el arreglo puede producir
    resultados incorrectos o no representar el total y promedio por
    página que solicita la actividad.
-   Que `$unwind` aplana el arreglo y permite que `$sum` y `$avg`
    trabajen sobre cada valor individual.

No presentes como equivalentes el promedio por libro y el promedio por
página. La actividad solicita el promedio de `conteo_palabras` de las
páginas procesadas.

## 9. Criterios de evaluación que debes satisfacer

La rúbrica del documento asigna 100 puntos:

### Bloque 1: `$match` y `$unwind` --- 40 %

Para alcanzar el nivel excelente:

-   `$match` debe aparecer al inicio.
-   Debe utilizar correctamente el operador de comparación `$gte`.
-   `$unwind` debe deconstruir correctamente el arreglo embebido.
-   Las rutas de campos deben incluir el prefijo `$` donde corresponda.

### Bloque 2: `$group` y `$sort` --- 40 %

Para alcanzar el nivel excelente:

-   Agrupar por `"$iglesia_origen"`.
-   Calcular correctamente `$sum` y `$avg` sobre los subdocumentos ya
    aplanados.
-   Ordenar por `total_palabras` de forma descendente con `-1`.

### Bloque 3: Justificación teórica --- 20 %

Para alcanzar el nivel excelente:

-   Fundamentar el impacto del filtrado temprano en memoria RAM.
-   Explicar el aprovechamiento potencial de índices.
-   Explicar por qué es necesario aplanar los arreglos.
-   Relacionar las decisiones con el procesamiento en el servidor.

## 10. Forma de trabajo del agente

Sigue este procedimiento:

1.  Lee el código base completo antes de modificarlo.
2.  Identifica el espacio marcado para implementar el pipeline.
3.  Completa las cuatro etapas en el orden exigido.
4.  Asegura que la función ejecute `coleccion.aggregate(pipeline)` y
    devuelva los resultados como una lista.
5.  Comprueba la lógica con los datos de muestra y contrasta los
    resultados con la tabla de validación de este archivo.
6.  Redacta las respuestas de las dos preguntas arquitectónicas.
7.  Revisa el script contra los tres bloques de la rúbrica.
8.  Presenta el código final y explica brevemente qué hace cada etapa.

## 11. Restricciones y reglas de calidad

-   No descargues todos los libros con `find({})` para calcular las
    métricas en Python.
-   No sustituyas el Aggregation Framework por ciclos `for`.
-   No cambies los nombres `libros_historicos`, `paginas`,
    `conteo_palabras`, `iglesia_origen`, `estado` o `anio_publicacion`.
-   No cambies los nombres de las métricas solicitadas.
-   No cambies el orden de las etapas.
-   No omitas ninguna de las dos respuestas teóricas.
-   No inventes resultados de una ejecución real si no se ha conectado a
    MongoDB Atlas.
-   Distingue entre resultados calculados con el dataset de muestra y
    resultados obtenidos de una base de datos real.
-   Explica cualquier supuesto o limitación en lugar de ocultarlo.
-   Mantén las explicaciones en español, con lenguaje técnico
    comprensible para un estudiante.

## 12. Formato de respuesta esperado del agente

Al terminar, entrega:

1.  **Código completo de `analitica_pipeline.py`**, conservando la
    estructura base y completando la función solicitada.
2.  **Explicación del pipeline**, etapa por etapa.
3.  **Tabla de resultados esperados** con el dataset de muestra.
4.  **Respuesta a la Pregunta 1** sobre `$match`, índices B-Tree y
    memoria RAM.
5.  **Respuesta a la Pregunta 2** sobre `$unwind`, `$sum` y `$avg`.
6.  **Lista de verificación de la rúbrica**, indicando si cada requisito
    se cumple.
7.  **Instrucciones de ejecución**, indicando las dependencias y la
    configuración local de `MONGODB_URI` y `DB_NAME`, sin exponer
    credenciales.

El trabajo se considera completo únicamente cuando estén cubiertos los
tres bloques de la actividad: implementación, métricas y justificación
arquitectónica.
