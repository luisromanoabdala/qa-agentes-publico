# Estrategia y plan de testing — <campaña>

> Dueño: `qa-estratega`. Adaptar la extensión al tamaño/fase: una campaña de PR puede ser media página.
> Cada sección responde una decisión; si no aporta, se elimina.

## 1. Objetivo, alcance y exclusiones
- Objetivo / decisión que habilita:
- Incluye:
- Excluye (y por qué):

## 2. Funcionalidades y roles
| Módulo | Funcionalidad | Roles | Requisitos |
|---|---|---|---|

## 3. Riesgos y prioridades
Resumen de `riesgos.yaml` (alta primero). Riesgos aceptados sin prueba: listar con motivo.

## 4. Niveles y tipos de prueba
| Riesgo | Unitario | Componente | Integración | Contrato | E2E | Exploratorio | Seguridad | Otros |
|---|---|---|---|---|---|---|---|---|

## 5. Suites
- **Smoke** (≤15 min, bloqueante): casos …
- **Regresión crítica:** casos …
- **Focalizadas** (impacto del cambio): casos …

## 6. Automatización vs. exploración manual
- A automatizar (y en qué nivel):
- Exploratorio (cartas `TC-EXP-*`):

## 7. Ambientes, datos y dependencias
- Ambiente(s): | Datos: sintéticos con `runId` | Limpieza: | Dependencias externas (pagos, email, WhatsApp, storage):

## 8. Criterios de entrada
- [ ] Build desplegado y versión verificable
- [ ] Cuentas por rol disponibles
- [ ] Autorizaciones de datos definidas

## 9. Criterios de salida
- [ ] Smoke 100% ejecutado; 0 P0/P1 abiertos sin decisión
- [ ] Riesgos altos: ejecutados o aceptados explícitamente
- [ ] Bloqueos y riesgo residual informados

## 10. Bloqueos y supuestos pendientes
| ID | Descripción | Impacta | Necesita |
|---|---|---|---|
