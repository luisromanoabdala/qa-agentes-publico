#!/usr/bin/env bash
# EJEMPLO FICTICIO. Requiere QA_API_URL, QA_TOKEN_ODONTOLOGO, QA_TOKEN_RECEPCION y PACIENTE_ID en el entorno.
set -euo pipefail
body='{"sillonId":"S3","pacienteId":"'"$PACIENTE_ID"'","inicio":"2026-11-04T12:00:00-03:00","duracionMin":30}'
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$QA_API_URL/turnos" -H "Authorization: Bearer $QA_TOKEN_ODONTOLOGO" -H "Content-Type: application/json" -d "$body" &
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$QA_API_URL/turnos" -H "Authorization: Bearer $QA_TOKEN_RECEPCION" -H "Content-Type: application/json" -d "$body" &
wait
curl -sS "$QA_API_URL/turnos?sillon=S3&fecha=2026-11-04" -H "Authorization: Bearer $QA_TOKEN_ODONTOLOGO"
