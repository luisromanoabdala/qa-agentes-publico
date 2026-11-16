# ⚠️ EJEMPLO — Plan de testing (campaña ficticia EJ01)

## 1. Objetivo, alcance y exclusiones
- Decide: pasar 1.4.0-rc2 a Staging para la demo con consultorios piloto.
- Incluye: Agenda, permisos de ficha clínica, alta de pacientes.
- Excluye: Pagos (sandbox no disponible → riesgo residual declarado), mobile.

## 3. Riesgos y prioridades
RSK-003 (9), RSK-001 (6), RSK-002 (6) altos; RSK-004 y RSK-005 medios.

## 4. Niveles y tipos de prueba
| Riesgo | Unit | Comp | Integración | Contrato | E2E | Explor. | Seguridad |
|---|---|---|---|---|---|---|---|
| RSK-001 | regla de superposición | – | concurrencia en DB (TC-AGE-004) | – | smoke agendar (TC-AGE-001) | sí | – |
| RSK-002 | – | – | API con 2 consultorios (TC-HC-003) | – | – | – | IDOR |
| RSK-003 | – | – | API por rol (TC-HC-002) | – | UI recepción | – | autorización |
| RSK-004 | límites 14/15/240/241 (TC-AGE-002) | formulario | – | OpenAPI min/max | – | – | – |
| RSK-005 | transición estado | – | liberar slot (TC-AGE-003) | – | – | – | – |

## 5. Suites
- **Smoke:** TC-AGE-001, TC-HC-001.
- **Regresión crítica:** smoke + TC-AGE-003, TC-AGE-004, TC-HC-002, TC-HC-003.
- **Focalizada (diff release/1.4):** TC-AGE-002..004.

## 7. Datos
Pacientes sintéticos `QA-Paciente-<runId>`, sillones del seed de QA, limpieza por `runId` al final de cada test.

## 8–9. Entrada / salida
Entrada: build verificado en `/api/health` ✔, cuentas odontólogo y recepción ✔, cuenta consultorio B ✘ (BLK-001).
Salida: smoke 100% ejecutado, 0 P0/P1 abiertos sin decisión, riesgos altos ejecutados o aceptados.

## 10. Bloqueos
BLK-001 → RSK-002 sin evidencia dinámica.
