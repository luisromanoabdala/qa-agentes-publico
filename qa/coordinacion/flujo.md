# Flujo de una campaña: del análisis al retest

Orquesta: skill `qa-lead`. Cada paso indica agente, entradas, salidas y **puerta** (condición para avanzar).
Los pasos sin dependencia entre sí se lanzan en paralelo.

```
0 Intake ─> 1 Análisis ─┬─> 2 Estrategia ─> 3 Casos ─┬─> 4 Automatización ─┐
                        └─> 1b Seguridad (estática)  └──────────────────────┴─> 5 Ejecución
5 Ejecución ─> 6 Triage de fallos ─> 7 Jira ─> 8 Consolidación ─> (fix) ─> 9 Retest + regresión ─> 8
```

| # | Paso | Agente | Entradas | Salidas | Puerta |
|---|---|---|---|---|---|
| 0 | Intake y faltantes | `qa-lead` | Pedido, `campania.yaml` | `campania.yaml` completo o con `pendientes` y `bloqueos` | Alcance y fase definidos. Lo que falta queda como pendiente; no frena lo independiente |
| 1 | Análisis técnico y de impacto | `qa-analista-impacto` | Repos, docs, OpenAPI, diff/PR | `analisis.md`, `riesgos.yaml`, hallazgos `estatico`/`hipotesis` | Módulos reales descubiertos; hechos vs. hipótesis separados |
| 1b | Seguridad estática | `qa-seguridad` | Repos, config, migraciones | Hallazgos `estatico`/`hipotesis` de seguridad | Puede correr en paralelo con 1 |
| 2 | Estrategia y plan | `qa-estratega` | `riesgos.yaml`, `campania.yaml` | `plan.md` | Niveles, suites, criterios entrada/salida y autorizaciones explícitas |
| 3 | Diseño de casos | `qa-disenador-casos` | Plan, requisitos, contratos, riesgos | `casos/*.yaml` (y destino externo si existe) | Cada riesgo alto tiene ≥1 caso; validador sin errores |
| 4 | Automatización | `qa-automatizacion` | Plan, casos candidatos, stack | Framework/tests en el repo de la app (rama), `automatizacion.ref` en casos | Smoke real pasa o su fallo está clasificado |
| 5 | Ejecución | `qa-ejecutor` (+ `qa-seguridad` para pruebas de acceso) | Casos, ambiente, credenciales vía env | `ejecuciones.yaml`, `evidencias/` | Cada ejecución con estado, hora con zona y evidencia |
| 6 | Triage de fallos | `qa-ejecutor` | Ejecuciones `fallido` | `clasificacion_fallo`, frecuencia, hallazgo `reproducido` | Solo `producto` avanza a Jira |
| 7 | Registro en Jira | `qa-jira-reporter` | Hallazgos reproducidos, evidencias | `bugs/BUGD-*.md` con `jira.key`/`url` | Issue verificado con GET; sin duplicados |
| 8 | Consolidación | `qa-lead` | Todo | `informe.md` | Recomendación con evidencia y límites explícitos |
| 9 | Retest y regresión | `qa-ejecutor` | Bug resuelto, build nuevo | Ejecuciones con `retest_de`, regresión relevante | Volver a 8 |

## Reglas transversales

1. **Nada se presenta como ejecutado si solo fue diseñado.** El informe cuenta ejecuciones, no casos.
2. **Pasar E2E no equivale a "listo".** La recomendación pondera riesgos sin cubrir, niveles inferiores, bloqueos y hallazgos abiertos.
3. **Autorización explícita** para pruebas destructivas, de carga o que toquen datos reales (`campania.yaml → autorizaciones`). Una URL de producción no autoriza nada por sí sola.
4. **Ante falta de acceso:** registrar `BLK-NNN`, seguir con lo independiente, nunca simular el resultado.
5. **Validar antes de entregar:** `python3 qa/scripts/validate_campaign.py <campaña>` al cierre de cada paso que escribe archivos.

## Fases del desarrollo → qué corre

| Fase | Pasos típicos | Foco |
|---|---|---|
| Requisitos | 0, 1 (sobre docs), 3 | Ambigüedades, reglas, criterios de aceptación verificables, riesgos |
| Diseño | 1, 1b, 2 | Testabilidad, estados, permisos, integraciones, datos de prueba |
| Desarrollo / PR | 1 (sobre diff), 3, 4 (unit/componente/integración) | Impacto del cambio y pruebas en niveles bajos |
| Integración / QA | 3, 4, 5, 6, 7 | Contratos, API, persistencia, flujos, permisos |
| Prelanzamiento | 5 (smoke + regresión crítica), 8 | Riesgos residuales, decisión |
| Posdespliegue | 5 (smoke autorizado, solo lectura salvo autorización), 8 | Verificación y seguimiento |
