---
id: BUGD-001
titulo: "[Agenda] Se crean dos turnos superpuestos en el mismo sillón al confirmar en simultáneo"
modulo: Agenda
tipo: api
prioridad: P1
severidad: Mayor
fecha_deteccion: 2026-11-03
entorno: QA
version: 1.4.0-rc2 (commit e4f5a6b)
issue_origen: DEMO-21
caso: TC-AGE-004
ejecuciones: [EXE-20261103-004]
hallazgo: HAL-001
evidencias: [evidencias/EXE-20261103-004/request-response.json, evidencias/EXE-20261103-004/curl.sh]
etiquetas: [qa-agentico, agenda]
jira:
  estado: borrador
  proyecto: null
  key: null
  url: null
  fingerprint: null
  duplicado_de: null
---
## Descripción
⚠️ EJEMPLO FICTICIO. Cuando dos usuarios confirman al mismo tiempo un turno para el mismo sillón y horario, la API acepta ambos y la agenda queda con dos turnos superpuestos.

## Clasificación y contexto
<!-- completado por jira_bug.py con los campos sin campo propio en Jira -->

## Datos de prueba
- Base URL: `$QA_API_URL`
- Endpoint: `POST /turnos`
- Método HTTP: POST
- Rol utilizado: odontólogo y recepción (dos sesiones)
- Precondiciones: sillón S3 libre el 2026-11-04 12:00-12:30
- IDs de datos sintéticos: paciente `QA-Paciente-r7f6`, sillón `S3`
- Payload: `{"sillonId":"S3","pacienteId":"<id QA-Paciente-r7f6>","inicio":"2026-11-04T12:00:00-03:00","duracionMin":30}`
- Referencia segura a credenciales: `$QA_USER_ODONTOLOGO_*`, `$QA_USER_RECEPCION_*`

## Pasos de reproducción
1. Obtener un token para cada rol (`$QA_TOKEN_ODONTOLOGO`, `$QA_TOKEN_RECEPCION`).
2. Enviar en paralelo los dos `POST /turnos` con el payload indicado (script `curl.sh` adjunto).
3. Consultar `GET /turnos?sillon=S3&fecha=2026-11-04`.

## Resultado actual
Ambas solicitudes responden `201 Created` y el GET lista dos turnos para S3 12:00-12:30 (4 de 5 corridas).

## Resultado esperado
Una solicitud responde `201` y la otra `409 TURNO_SUPERPUESTO`; el GET lista un único turno. Fuente: DEMO-21 criterio 1 y `openapi.yaml` (POST /turnos → 409).

## Evidencia
- Request/response sanitizados: `request-response.json`
- cURL reproducible: `curl.sh` (usa `$QA_API_URL` y tokens por variable)

## Observaciones
- Frecuencia de reproducción: 4/5 corridas con 2 solicitudes en paralelo.
- Alcance observado: cualquier sillón; secuencialmente la validación funciona (TC-AGE-001).
- Alternativa temporal: recepción revisa y cancela manualmente el duplicado.
- Hipótesis técnica (pendiente de confirmar): `crearTurno` hace SELECT + INSERT sin transacción ni constraint de exclusión (`turnos.service.ts:58`).
- Caso y ejecución relacionados: TC-AGE-004 / EXE-20261103-004.
