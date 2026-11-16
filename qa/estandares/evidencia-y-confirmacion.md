# Evidencia, confirmación y honestidad de resultados

## Las cuatro categorías que nunca se mezclan

| Categoría | Cómo se escribe | Ejemplo |
|---|---|---|
| Hallazgo por análisis estático | "El código en `X:símbolo` **permite**…" | "`createAppointment` no valida solapamiento por sillón" |
| Hipótesis pendiente | "**Hipótesis:** … Se verifica con …" | "Podría duplicarse el turno si dos usuarios confirman a la vez" |
| Bug reproducido | "**Reproducido** en EXE-… (3/3 intentos)" | "Se crearon 2 turnos para el mismo slot" |
| Prueba bloqueada | "**Bloqueado** por BLK-…: falta …" | "No se probó el rol Recepción: no hay cuenta" |

## Qué cuenta como evidencia

- UI: captura o video con URL visible (o anotada), timestamp y rol; traza de Playwright si existe.
- API: request + response sanitizados, código HTTP, headers relevantes sin secretos.
- Datos: query de solo lectura + resultado (IDs sintéticos).
- Logs: extracto relevante con hora y zona.
- Análisis estático: `ruta/archivo.ext:línea` y símbolo, commit analizado.

Cada evidencia vive en `evidencias/` (sanitizada) o como enlace a un artefacto de CI.
Los originales sin sanitizar van a `evidencias/raw/` (ignorado por Git) y se borran al cerrar la campaña.

## Afirmaciones prohibidas sin respaldo

- "Se ejecutó / pasó / falló" sin fila en `ejecuciones.yaml`.
- "Se consultó Jira / se creó el issue" sin clave y URL devueltas por Jira.
- "Se abrió la URL / se probó en el ambiente" sin evidencia con timestamp.
- "No hay bugs" (correcto: "no se encontraron fallos en el alcance ejecutado: …").
- "La app está lista" basado solo en E2E.

## Intermitencia y reintentos

- Registrar `intentos` y `exitos` por ejecución. Un test que pasó solo tras reintentos se registra con
  `inestable: true` y **no** se informa como aprobado limpio.
- Reproducir los fallos cuando sea viable y declarar la frecuencia (`3/3`, `2/10`).
- No configurar reintentos para "hacer pasar" una suite. Si el framework reintenta, el reporte debe conservar el intento fallido.

## Fallo del producto vs. fallo de otra cosa

Antes de clasificar `producto`, descartar: ambiente caído o lento (`infraestructura`), datos faltantes o sucios (`datos`),
locator roto o espera mal hecha (`script`). Si no se puede distinguir: `indeterminado` y se investiga; no va a Jira.
