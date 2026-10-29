# Revisión de interfaz y operación

Revisión del 29 de octubre de 2026. Se conservaron la nueva apariencia y la separación en vistas/componentes.

Se corrigieron estos problemas:

- Configuración y cierre de sesión inaccesibles en móvil; ajustes de ancho y distribución de conversaciones en móvil/tablet.
- Mensajes de la conversación anterior visibles durante la carga de otra.
- Tomar control podía guardar o perder un borrador de notas; ahora preserva el borrador y cambia solo el control.
- El filtro de publicados ocultaba cursos con una edición pendiente. La vista previa ahora aplica todos los campos pendientes, incluso enlaces vacíos.
- Reiniciar el simulador mientras esperaba una respuesta causaba inconsistencias. Ahora se bloquea durante el envío.
- Estado de IA y modelo mostrados como activos solo por tener credenciales. Ahora se distinguen pendiente, sin verificar, llamada correcta y respaldo por error.

La nota de voz investigada sí se había transcrito: su conversación estaba en atención humana. Ahora el worker confirma la recepción y explica que la IA está pausada. Los errores inesperados de mensajes privados también generan un aviso. No se reactivaron automáticamente conversaciones reales.

Validación: 88 pruebas de backend, seis pruebas de navegador, build y migraciones correctos; inspección visual de escritorio y móvil. Gemini y Groq también se probaron con llamadas reales; ver [validación](validation.md).

Los cambios ya están aplicados a los contenedores locales. Abre http://localhost:5173 y actualiza con Ctrl+F5. Para reconstruir después de cambiar código o entorno:

```powershell
docker compose --profile telegram up --build -d
```

Para probar voz: en Conversaciones selecciona tu hilo, pulsa **Reanudar IA** y envía una nota corta al bot. Después pulsa **Tomar control** y envía otra: debe confirmar su transcripción y la pausa. Consulta el [recorrido completo](testing-guide.md).
