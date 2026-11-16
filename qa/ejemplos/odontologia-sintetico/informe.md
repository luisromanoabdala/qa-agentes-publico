# ⚠️ EJEMPLO — Informe de calidad EJ01 (datos ficticios)

## 1. Recomendación
**No apta** para Staging de demo con consultorios piloto, todavía.
- BUGD-001 (P1/Mayor, reproducido 4/5): doble reserva por concurrencia en Agenda — RSK-001.
- RSK-002 (aislamiento entre consultorios) **sin evidencia dinámica** por BLK-001; HAL-003 sigue como hipótesis.
- Smoke 2/2 ejecutado: TC-AGE-001 aprobado; TC-HC-001 aprobado **inestable** (pasó al 2º intento).
Límites: no se probaron pagos (excluidos), mobile, rendimiento ni accesibilidad completa.

## 2. Contexto verificado
QA · https://qa.dentapp.example.test · 1.4.0-rc2 (verificada en /api/health) · commit e4f5a6b · 2026-11-03 (UTC-3) · roles odontólogo y recepción.

## 3. Cobertura (de `validate_campaign.py --resumen`)
| Riesgo | Prio | Casos | Ejecutados | OK | Falla | Bloq | Sin ejecutar |
|---|---|---|---|---|---|---|---|
| RSK-001 | alta | 2 | 2 | 1 | 1 | 0 | 0 |
| RSK-002 | alta | 1 | 1 | 0 | 0 | 1 | 0 |
| RSK-003 | alta | 2 | 2 | 2 | 0 | 0 | 0 |
| RSK-004 | media | 1 | 0 | 0 | 0 | 0 | 1 |
| RSK-005 | media | 1 | 0 | 0 | 0 | 0 | 1 |

Diseñados sin ejecutar: TC-AGE-002, TC-AGE-003 (no cuentan como cobertura).

## 5. Bugs
| Borrador | Jira | Título | P | Sev | Estado |
|---|---|---|---|---|---|
| BUGD-001 | — (falta proyecto Jira) | [Agenda] Se crean dos turnos superpuestos… | P1 | Mayor | borrador |

## 6. Hallazgos no confirmados
HAL-003 (bloqueado), HAL-004 (estático, testabilidad/accesibilidad).

## 7. Bloqueos y riesgo residual
| BLK | Falta | No probado | Riesgo residual |
|---|---|---|---|
| BLK-001 | Cuenta consultorio B | TC-HC-003 | Posible fuga de datos clínicos entre consultorios (alto) |

## 8. Próximos pasos
1. Proyecto Jira → crear BUGD-001. 2. Cuenta consultorio B → ejecutar TC-HC-003. 3. Estabilizar TC-HC-001 (espera por la pestaña, no por tiempo). 4. Retest BUGD-001 + regresión de Agenda tras el fix.
