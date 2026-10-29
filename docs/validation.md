# Verificación de la V1

Realizada el 29 de octubre de 2026.

- 88 pruebas de backend aprobadas en Windows/Python 3.14 y dentro de Linux/Python 3.12, incluyendo voz/Groq y regresiones de precisión conversacional.
- Build de React/TypeScript aprobado en Windows y Docker.
- Prueba de navegador aprobada: login, publicación de ficha real, simulador, frustración, respuesta del asesor, reanudación y actualización por SSE desde una segunda sesión. Captura y comprobación de ancho móvil sin desbordamiento horizontal.
- Imágenes Docker construidas y API, Nginx y PostgreSQL levantados con healthcheck correcto. Migraciones aplicadas y `alembic check` sin diferencias.
- Importación desde Windows: 18 fichas reales sin errores, con versión de respaldo pública en `backend/data/catalog.snapshot.json`. El arranque sin catálogo importa ese respaldo como pendiente de aprobación y conserva la fecha de extracción.
- Credencial de Telegram validada mediante `getMe` para `@asistente_ctt_bot`. No se enviaron mensajes de prueba a terceros.
- Se configuró Gemini nativo con las variables `AI_PROVIDER_*` existentes. El modelo seleccionado devolvió errores temporales 503 (alta demanda) y 504 (plazo agotado); por ello no se afirma una validación satisfactoria en vivo del modelo. El protocolo de herramientas, conservación de firmas nativas y JSON Schema se verificaron con proveedor simulado.
- La importación de la web desde Docker Desktop agotó el tiempo de conexión en este entorno; se conserva el catálogo de respaldo y el flujo de sincronización deja intacta la versión publicada. No se desactivó la verificación TLS.
- Voz: se verificaron multipart, timeout/401/429/503, transcripciones vacías o inválidas, límites de duración/tamaño, errores de descarga, el POST al `ingest` real y el respeto del handover. Las pruebas de regresión simulan STT.
- Groq: clave y modelo verificados por HTTP 200. Se realizó además una transcripción real con `whisper-large-v3-turbo` usando una [muestra OGG pública de python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot/blob/master/tests/data/telegram.ogg), descargada y procesada en memoria (9199 bytes). El proveedor devolvió texto usable. No se enviaron audios de las conversaciones del usuario ni mensajes de prueba a terceros. Falta ensayar una nota propia desde Telegram para comprobar su precisión con el vocabulario de los cursos.
- Conversación: se reprodujeron descripción, fechas, precio, duración, alcance, referencias al curso, niveles ambiguos y respuestas ante HTTP 429. La comprobación real de Gemini en esta iteración devolvió 429; no se afirma una evaluación satisfactoria en vivo de su lenguaje natural. Ver [pruebas y límites](conversation-quality.md).
- Tras cambiar el entorno a `gemini-2.5-flash`, el proveedor respondió 404 e indicó que ese modelo no estaba disponible para usuarios nuevos. Una prueba sintética sobre la API desplegada verificó descripción sin precios/fechas, seguimiento de fecha del curso y rechazo explícito de código; los dos primeros casos se resolvieron mediante el respaldo. Se retiraron los registros de QA creados por esa prueba.

Antes de la presentación: abrir el bot con una cuenta de Telegram y completar el recorrido de la rúbrica. La calidad conversacional y las políticas comerciales deben evaluarse con ese modelo en vivo. WhatsApp todavía requiere un conector y credenciales de Meta.

## Verificación final de interfaz e IA

- Seis pruebas de navegador aprobadas: un recorrido real completo y cinco pruebas controladas de interfaz. Build de TypeScript/Vite correcto; 88 pruebas de backend aprobadas en Windows y Docker; Alembic sin diferencias.
- Configuración local actual: `gemini-3.1-flash-lite`. Se comprobaron respuestas reales en lenguaje natural, clasificación semántica y un intercambio completo de llamada a herramienta y resultado. En la API desplegada respondió la descripción de GitHub y luego su fecha de inicio conservando el contexto. Estas pruebas sustituyen el diagnóstico histórico de modelos anteriores mencionado arriba.
- Hubo también errores temporales 503/504 del proveedor: el respaldo sigue siendo necesario. Configuración muestra el modelo real, llamadas correctas y fallos; tener una clave configurada no se presenta como prueba de funcionamiento.
- Groq `whisper-large-v3-turbo`: transcripción real dentro del contenedor del worker. El callback real de voz registró la transcripción en una conversación sintética en atención humana y emitió el aviso de IA pausada. Se usó audio público, sin enviar mensajes de prueba a terceros.
- Servicios reconstruidos y levantados. Ver [revisión de interfaz](interface-review.md) y [guía de pruebas](testing-guide.md).
