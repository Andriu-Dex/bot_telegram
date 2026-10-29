# Evaluación de la propuesta y siguientes mejoras

La propuesta de `instruction.md` es apropiada para esta V1. Aporta valor visible en la demostración y mantiene la lógica de negocio independiente del formato y canal de entrada. STT produce texto, y el agente conserva un único contrato. El mismo módulo podrá recibir bytes desde un adaptador WhatsApp.

Se implementa como extensión del worker: notas privadas, un minuto/2 MB, procesamiento en memoria, transcripción de un intento y envío al `ingest` existente con prefijo de micrófono. No se añade una modalidad al dashboard ni se alteran prompts, SQL, outbox o handover.

El ajuste de configuración a tener presente es el proveedor: el contrato de voz usa **Grok STT de xAI**, mientras la conversación usa Gemini. Se reutilizan `OPENAI_API_KEY`/`OPENAI_BASE_URL` tal como pide el documento; esos nombres no convierten el servicio en OpenAI ni permiten usar una clave de Gemini para xAI. Son credenciales de servicios diferentes, aunque no se añada otro campo secreto.

Si prefieres reducir proveedores, una alternativa de siguiente iteración sería sustituir únicamente la implementación de `transcribe()` por una transcripción con Gemini y evaluar su precisión con notas reales. El audio seguiría terminando en texto en el borde; el agente comercial no tendría que ser multimodal. En esta entrega se respeta el contrato xAI solicitado.

## Prioridades recomendadas después de voz

1. **Visibilidad del proveedor y de entregas fallidas.** Mostrar la última inferencia exitosa, cuándo se usó el respaldo y errores de envío con una acción de reintento controlada. Es la mejora más útil antes de una demostración porque evita confundir una clave configurada con un servicio disponible. Un futuro modelo alternativo debe configurarse explícitamente.
2. **Vigencia de las ofertas.** Separar etiqueta de la web, fechas de inscripción y fecha de revisión. Avisar sobre datos vencidos o pendientes de revisión en el dashboard, conservando las condiciones oficiales. Importar un curso marcado abierto no garantiza que acepte matrículas hoy.
3. **Seguimiento con responsables y vencimientos.** Convertir la próxima acción en una tarea fechada, filtrar pendientes y medir tiempo hasta la primera respuesta humana. Los recordatorios internos aportan valor antes de añadir mensajes automáticos a prospectos.
4. **WhatsApp como siguiente canal.** Implementar el adaptador, firmas del webhook, ventana de atención, plantillas y estados de entrega. Mantener STT y el pipeline compartidos; no fusionar identidades entre canales automáticamente.
5. **Escalado cuando haya carga real.** Identidades y permisos por asesor, paginación, cola de trabajo, locks distribuidos y eventos por PubSub antes de ejecutar varias réplicas. La V1 requiere un proceso API y un worker de polling.

Estas son propuestas de siguiente iteración; no se presentan como funcionalidades ya implementadas. Para esta entrega conviene estabilizar los proveedores, completar la prueba real de voz y ensayar el recorrido de la rúbrica.
