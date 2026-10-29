# Verificación de la V1

Realizada el 29 de octubre de 2026.

- 53 pruebas de backend aprobadas en Windows/Python 3.14 y dentro de Linux/Python 3.12, incluyendo la extensión de voz y su migración a Groq.
- Build de React/TypeScript aprobado en Windows y Docker.
- Prueba de navegador aprobada: login, publicación de ficha real, simulador, frustración, respuesta del asesor, reanudación y actualización por SSE desde una segunda sesión. Captura y comprobación de ancho móvil sin desbordamiento horizontal.
- Imágenes Docker construidas y API, Nginx y PostgreSQL levantados con healthcheck correcto. Migraciones aplicadas y `alembic check` sin diferencias.
- Importación desde Windows: 18 fichas reales sin errores, con versión de respaldo pública en `backend/data/catalog.snapshot.json`. El arranque sin catálogo importa ese respaldo como pendiente de aprobación y conserva la fecha de extracción.
- Credencial de Telegram validada mediante `getMe` para `@asistente_ctt_bot`. No se enviaron mensajes de prueba a terceros.
- Se configuró Gemini nativo con las variables `AI_PROVIDER_*` existentes. El modelo seleccionado devolvió errores temporales 503 (alta demanda) y 504 (plazo agotado); por ello no se afirma una validación satisfactoria en vivo del modelo. El protocolo de herramientas, conservación de firmas nativas y JSON Schema se verificaron con proveedor simulado.
- La importación de la web desde Docker Desktop agotó el tiempo de conexión en este entorno; se conserva el catálogo de respaldo y el flujo de sincronización deja intacta la versión publicada. No se desactivó la verificación TLS.
- Voz: se verificaron multipart, timeout/401/429/503, transcripciones vacías o inválidas, límites de duración/tamaño, errores de descarga, el POST al `ingest` real y el respeto del handover. Las pruebas de regresión simulan STT.
- Groq: clave y modelo verificados por HTTP 200. Se realizó además una transcripción real con `whisper-large-v3-turbo` usando una [muestra OGG pública de python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot/blob/master/tests/data/telegram.ogg), descargada y procesada en memoria (9199 bytes). El proveedor devolvió texto usable. No se enviaron audios de las conversaciones del usuario ni mensajes de prueba a terceros. Falta ensayar una nota propia desde Telegram para comprobar su precisión con el vocabulario de los cursos.

Antes de la presentación: comprobar disponibilidad real del modelo elegido, abrir el bot con una cuenta de Telegram y completar el recorrido de la rúbrica. La calidad conversacional y las políticas comerciales deben evaluarse con ese modelo en vivo. WhatsApp todavía requiere un conector y credenciales de Meta.
