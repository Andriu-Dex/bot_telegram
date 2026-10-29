# Calidad conversacional: regresiones reportadas

La evaluación detectó dos problemas distintos: un respaldo que devolvía una ficha demasiado amplia y una llamada real a Gemini con HTTP 429. Una clave configurada no garantiza disponibilidad del modelo. Cuando falla el proveedor, el modo de respaldo no debe fingir una conversación generativa ni repetir respuestas ajenas a la pregunta.

En la comprobación posterior del servidor, el entorno apuntaba a `gemini-2.5-flash`. El proveedor devolvió HTTP 404 indicando que ese modelo ya no estaba disponible para usuarios nuevos. Se conservó esa elección de entorno: cambiar el proveedor o modelo requiere una elección explícita; no se sustituye silenciosamente para ocultar el fallo. El recorrido sintético contra la API desplegada confirmó descripción y fecha precisas en modo `fallback`, y rechazo de código en modo `scope`.

## Cambios

- El catálogo se interpreta por campos: descripción, fechas del curso, inscripción, precio, horario, requisitos, objetivos y temario. Se selecciona solo lo solicitado, incluso en el modo sin modelo.
- Se conserva el curso seleccionado para seguimientos como «¿y la fecha?» o «ese curso». Se recuperan menciones del historial y se distingue «el curso anterior». Se reconocen variantes habituales como Git Hub, Gitub y Phyton.
- Se solicita aclaración cuando hay varios niveles y se prefiere una edición abierta frente a otra cerrada del mismo curso. Un curso nuevo desconocido no reutiliza automáticamente la ficha anterior.
- Las solicitudes claras de código o tareas fuera de alcance reciben una explicación breve sin inferencia ni ficha repetida. Consultar si un curso enseña a programar sigue permitido.
- El modelo recibe los campos verificados pertinentes en la primera llamada. Esto evita exigir varios viajes de herramientas para una descripción o fecha. Conserva herramientas para consultas más complejas y no puede modificar precios ni matrículas.
- El prompt exige responder al dato pedido, incluye las intervenciones del asesor en el contexto y prohíbe volcar el catálogo o actuar como asistente general de programación.
- Para `gemini-3.8-flash` se utiliza el nivel de razonamiento `low`, admitido por ese modelo. No se sustituye el modelo configurado. Se rechazan respuestas truncadas antes de enviarlas.
- `/api/status` incluye `llm_runtime`: llamadas exitosas/fallidas, fechas y último código de error. No expone credenciales, prompts ni respuestas. Los contadores pertenecen al proceso y se reinician con él.

## Recorrido de prueba

Con la ficha GitHub aprobada, en una conversación nueva:

| Consulta | Resultado esperado |
| --- | --- |
| De qué trata el curso de GitHub | Descripción, sin precios ni fechas |
| Y la fecha de ese curso | Fechas de GitHub, sin repetir descripción |
| Cuánto cuesta | Precios por categoría, sin temario |
| Escríbeme un código en Python | Límite de alcance, sin repetir la ficha |
| Me interesa Python | Aclaración si hay varios niveles publicados |
| Python 2 | Selección del segundo nivel, no de una edición histórica cerrada |
| Y cuánto dura | Duración de Python 2 |

La suite automatizada prueba estas condiciones con el modelo ausente, respuestas simuladas y HTTP 429. También comprueba que el modelo recibe los campos pedidos y genera una respuesta en modo `llm` cuando el proveedor simulado está disponible. Esto verifica el pipeline; la calidad generativa real requiere repetir el recorrido con cuota disponible en Gemini.

La recuperación por reglas tiene un vocabulario acotado. Para consultas ambiguas o referencias insuficientes debe pedir aclaración, no prometer comprensión universal. El historial comercial y los estados de inscripción siguen siendo independientes de la redacción de las respuestas.

Referencia para la configuración de Gemini: [niveles de razonamiento admitidos](https://ai.google.dev/gemini-api/docs/thinking/).
