# ⚠️ EJEMPLO — Análisis técnico y de impacto (datos ficticios)

> Commit analizado: web `a1b2c3d`, api `e4f5a6b` (ficticios) — 2026-11-03.

## 1. Stack y arquitectura
| Capa | Tecnología (evidencia) |
|---|---|
| Frontend | React 19 + Vite **[Hecho]** `web/package.json` |
| Backend / API | Node 22 + Fastify, OpenAPI 3.1 **[Hecho]** `api/openapi.yaml` |
| Persistencia | PostgreSQL 16 con `consultorio_id` en cada tabla **[Hecho]** `api/db/migrations/0003_agenda.sql` |
| Auth | JWT con claims `rol` y `consultorio_id` **[Hecho]** `api/src/auth/jwt.ts:verify` |
| Tests existentes | 41 unitarias (Vitest) en `api/src/**`, 0 integración, 0 E2E **[Hecho]** |

## 2. Módulos reales descubiertos
| Módulo | Pantallas | Endpoints | Tablas | Archivos clave |
|---|---|---|---|---|
| Agenda | `/agenda` | `POST/PATCH /turnos` | `turnos`, `sillones` | `api/src/agenda/turnos.service.ts:crearTurno` |
| Pacientes | `/pacientes` | `/pacientes` | `pacientes` | `api/src/pacientes/*.ts` |
| Ficha clínica | `/pacientes/:id/ficha` | `GET /pacientes/:id/evoluciones` | `evoluciones` | `api/src/ficha/evoluciones.controller.ts:listar` |

(No se detectaron módulos de pagos ni archivos/radiografías en este repo ficticio: no se generan riesgos para ellos.)

## 3. Reglas de negocio, estados y cálculos
- **[Hecho]** `crearTurno` verifica superposición con un `SELECT` y luego hace `INSERT` sin transacción ni constraint de exclusión (`turnos.service.ts:58-74`). → HAL-001, RSK-001.
- **[Hecho]** Estados del turno: `pendiente → confirmado → atendido | cancelado | ausente` (`turnos.estado.ts`).

## 4. Autorización y aislamiento
- **[Hecho]** `evoluciones.controller.ts:listar` filtra por `consultorio_id` del token pero **no** por rol. → HAL-002, RSK-003.
- **[Hipótesis]** El endpoint `GET /pacientes/:id` podría no validar `consultorio_id` (el filtro está en un middleware que no aparece aplicado a esa ruta). Se verifica con dos cuentas de consultorios distintos. → HAL-003, RSK-002.

## 7. Impacto del cambio (release/1.4)
| Archivo | Símbolos | Directo | Indirecto | Riesgo |
|---|---|---|---|---|
| `turnos.service.ts` | `crearTurno`, `reprogramar` | Agenda | Recordatorios por email (usa `turnos`) | RSK-001 |

## 8. Testabilidad
Los botones de agenda no tienen nombre accesible estable (`<div onClick>`): se pidió `aria-label`/rol (HAL-004, categoría testabilidad).
