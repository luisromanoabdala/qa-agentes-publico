# Estándar de bugs

Aplica a todo bug que se registre (Jira u otro destino). La plantilla de archivo está en
`qa/plantillas/campania/bugs/_plantilla-bug.md`; el mapeo a Jira en `jira-mapping.yaml`.

## Cuándo un hallazgo es un bug

Solo cuando el hallazgo está `reproducido`: existe ≥1 ejecución `fallido` clasificada como `producto`,
con evidencia y con un resultado esperado respaldado por una fuente (requisito, criterio de aceptación,
contrato OpenAPI, especificación, norma o comportamiento previo documentado).
Un hallazgo `estatico` o `hipotesis` **no** se registra como bug; se reporta como riesgo o como tarea de verificación.
Excepción: un hallazgo de seguridad estático grave puede escalarse al Lead para decidir (ver `qa-seguridad`), pero se rotula como "potencial".

## Título

Responde: **¿qué falla, dónde y bajo qué condición?**
Formato orientativo: `[Módulo] Falla observada bajo determinada condición`.

- Bien: `[Agenda] Se permite reservar dos turnos en el mismo sillón y horario al confirmar en simultáneo`
- Mal: `Error en agenda`, `BUG-104 turnos`, `No anda`

No se inventan claves: Jira asigna la clave al crear el issue.

## Campos

| Campo | Contenido | Regla |
|---|---|---|
| Descripción | Contexto breve | 1–3 oraciones |
| Prioridad | P0–P3 | Ver escala; independiente de severidad |
| Severidad | Crítica / Mayor / Menor / Trivial | Ver escala |
| Fecha | Detección real `AAAA-MM-DD` | La de la ejecución que lo reprodujo |
| Entorno | QA / Staging / Prod / otro | Solo si se verificó contra ese ambiente |
| Versión | API, tag, build o commit | Si no se pudo verificar: `No verificada` |
| Test Data | Datos para reproducir, sanitizados | IDs sintéticos, payloads; secretos como `$VARIABLE` |
| Pasos | Numerados, precisos, secuenciales | Reproducibles por otra persona |
| Resultado actual | Lo observado | Incluye HTTP y estado de datos si aplica |
| Resultado esperado | Lo correcto **y su fuente** | Sin fuente → no es bug todavía: pedir aclaración |
| Evidencia | Capturas, video, request/response, logs, queries | Sanitizada |
| Issue de origen | Historia/ticket relacionado | Si existe |
| Observaciones | Frecuencia, alcance, alternativa, hipótesis | Hipótesis rotuladas como tales |

## Prioridad (negocio y planificación)

| Valor | Criterio |
|---|---|
| **P0** — Bloqueante/Urgente | Impide probar o lanzar la aplicación |
| **P1** — Alta | Afecta un flujo crítico sin alternativa temporal |
| **P2** — Media | Error funcional con alternativa temporal |
| **P3** — Baja | Detalle estético, typo o problema menor |

## Severidad (impacto técnico/funcional)

| Valor | Criterio |
|---|---|
| **Crítica** | Caída del servidor, fuga de datos, corrupción o impacto técnico crítico |
| **Mayor** | La función principal falla por completo |
| **Menor** | Falla de validación o mensaje inconsistente con impacto limitado |
| **Trivial** | Inconsistencia cosmética o gráfica |

Un HTTP 500 **no** es Crítico automáticamente: se evalúa por alcance (¿un endpoint con input raro o el login de todos?).
Ejemplos de combinación: typo en la pantalla de consentimiento informado legal → P1/Trivial;
crash en un reporte que nadie usa este mes → P3/Mayor.

Si Jira usa otra escala, el mapeo se documenta en `jira-mapping.yaml` y la clasificación original P0–P3
se conserva (en el campo propio o en la sección "Clasificación y contexto").

## Contenido según tipo

- **UI / mobile:** captura o video, navegador/dispositivo, viewport, rol.
- **API:** método, endpoint, request y response sanitizados, cURL con `$QA_TOKEN`, código HTTP.
- **Backend / datos:** query de verificación y resultado (solo si se consultó la base, con acceso de solo lectura).
- **Seguridad:** ver `qa-seguridad`: sin instrucciones de explotación innecesarias en tickets de acceso amplio.

No completar secciones con información inventada. Si no hay SQL porque no se consultó la base, la sección se omite.
