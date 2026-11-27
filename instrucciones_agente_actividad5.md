# Instrucciones para el agente de IA — Actividad 5
## Tolerancia a Fallos, Exponential Backoff y Resiliencia Cloud

### 1. Rol del agente
Actúa como asistente de desarrollo dentro de VS Code o Antigravity. Tu objetivo es ayudar a completar y verificar el ejercicio de la Actividad 5, respetando los requisitos del documento y explicando los cambios de forma clara para un estudiante.

Trabaja sobre el proyecto abierto en el editor. Antes de modificar archivos:
1. Inspecciona la estructura del proyecto.
2. Localiza `resiliencia_cloud.py` y los archivos de configuración existentes.
3. Lee el código actual y conserva lo que ya funcione.
4. No sobrescribas archivos ajenos al ejercicio ni elimines código sin justificarlo.

### 2. Contexto del ejercicio
La Biblioteca Virtual Eclesiástica digitaliza páginas desde ubicaciones con conexiones inestables. Durante elecciones de Replica Set, puede haber ventanas de aproximadamente 3 a 5 segundos sin un nodo Primario disponible para escrituras.

El microservicio actual falla ante errores como `AutoReconnect` y `NetworkTimeout`, lo que puede obligar a los capturistas a repetir el escaneo.

La tarea es completar el módulo de persistencia para:
- Configurar parámetros de resiliencia en la conexión a MongoDB.
- Reintentar únicamente errores transitorios de red mediante Exponential Backoff.
- Abortar inmediatamente ante errores lógicos o de negocio.

### 3. Alcance y entregables
El entregable principal es completar el script `resiliencia_cloud.py`, resolviendo los bloques marcados con `TODO`.

Debes implementar los siguientes bloques:

#### Bloque 1 — URI resiliente y balanceo (30 puntos)
Construye o completa la URI de conexión para que incluya obligatoriamente:
- `retryWrites=true`
- `w=majority`
- `readPreference=secondaryPreferred`

Respeta la estructura de la URI existente y evita duplicar parámetros. Si se utiliza un archivo `.env`, conserva el uso de la variable `MONGODB_URI` y documenta qué parámetros debe contener.

No escribas credenciales reales en el código ni en archivos versionados. Usa valores de ejemplo o variables de entorno.

#### Bloque 2 — Exponential Backoff en Python (50 puntos)
Completa la función con esta firma:

```python
def guardar_pagina_resiliente(db, documento_pagina, max_intentos=3):
```

Requisitos:
1. Utiliza la colección `paginas_digitalizadas`.
2. Implementa un ciclo de reintentos limitado por `max_intentos`.
3. Utiliza bloques `try...except` diferenciados para errores transitorios y lógicos.
4. Reintenta solamente `AutoReconnect` y `NetworkTimeout`.
5. Ante un error transitorio, imprime una advertencia que indique el intento y el error.
6. Calcula la espera exponencial exactamente con:
   ```python
   time.sleep(2 ** (intento - 1))
   ```
   Para tres intentos, los intervalos calculados deben ser 1, 2 y 4 segundos según la fórmula del documento.
7. Si se agotan los intentos, lanza un `RuntimeError`.
8. Ante `DuplicateKeyError` u `OperationFailure`, registra el fallo lógico y aborta inmediatamente, sin reintentar.
9. No conviertas errores lógicos en errores transitorios ni captures indiscriminadamente todas las excepciones para reintentar.
10. Devuelve el identificador insertado cuando la escritura tenga éxito, de forma compatible con el orquestador incluido en el archivo base.

#### Bloque 3 — Justificación arquitectónica (20 puntos)
El documento incluye dos preguntas de análisis al final. **No las respondas ni las agregues al archivo de código, documentación o entregable generado por el agente.** Las respuestas se entregarán por separado en el chat.

### 4. Código base y elementos que deben conservarse
El script de referencia incluye:
- Importaciones de `os`, `time`, `MongoClient` y excepciones de PyMongo.
- `load_dotenv()` para cargar variables de entorno.
- La variable `URI_RESILIENTE`.
- La función `conectar_cluster()`, que crea el cliente con `serverSelectionTimeoutMS=5000` y `tls=True`, y devuelve la base `biblioteca_virtual`.
- La función `guardar_pagina_resiliente(...)`.
- Un orquestador de prueba bajo `if __name__ == "__main__":`, con un documento de prueba y mensajes de estado.

Conserva estos componentes salvo que exista una razón técnica clara para corregirlos. No cambies el escenario, los nombres de la función, de la base o de la colección sin necesidad.

### 5. Verificación
Después de implementar:
1. Revisa que el archivo no tenga errores de sintaxis.
2. Comprueba que los tres parámetros obligatorios estén presentes en la URI o en la configuración que la construye.
3. Comprueba que los errores de red sean los únicos que activan reintentos.
4. Comprueba que los errores lógicos aborten en el primer intento.
5. Comprueba que el agotamiento de intentos termine en `RuntimeError`.
6. Comprueba que la función devuelva el ID insertado al tener éxito.
7. Si el entorno no tiene acceso a MongoDB Atlas o no cuenta con credenciales, no afirmes que la conexión real fue probada. Explica la limitación y realiza las verificaciones locales que sí sean posibles.

Si es viable, agrega o ejecuta pruebas controladas con mocks para verificar el comportamiento de reintentos sin depender de una conexión real. No introduzcas dependencias nuevas sin necesidad; si agregas alguna, explica por qué.

### 6. Seguridad y configuración
- No solicites ni expongas contraseñas, tokens ni cadenas de conexión reales.
- No imprimas la URI completa si puede contener credenciales.
- No subas secretos al repositorio.
- Mantén la configuración mediante variables de entorno cuando corresponda.
- No realices operaciones destructivas sobre una base de datos real.

### 7. Forma de trabajo y respuesta final del agente
Trabaja en pasos pequeños y explica brevemente cada cambio. Al terminar, informa:
- Qué archivos modificaste.
- Qué requisitos completaste.
- Qué verificaciones o pruebas ejecutaste y sus resultados.
- Qué queda pendiente, si algo depende de credenciales, red o MongoDB Atlas.

No incluyas en el archivo `.md` ni respondas dentro del proyecto las dos preguntas teóricas finales de la actividad.
