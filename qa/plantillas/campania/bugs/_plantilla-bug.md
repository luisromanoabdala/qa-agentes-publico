---
id: BUGD-001
titulo: "[Módulo] Falla observada bajo determinada condición"
modulo: "<Módulo>"
tipo: ui                       # ui | api | mobile | backend | seguridad
prioridad: P2                  # P0 | P1 | P2 | P3
severidad: Menor               # Crítica | Mayor | Menor | Trivial
fecha_deteccion: AAAA-MM-DD
entorno: QA
version: No verificada
issue_origen: null             # clave Jira de la historia, si existe
caso: TC-MOD-001
ejecuciones: [EXE-AAAAMMDD-001]
hallazgo: HAL-001
evidencias: []
etiquetas: [qa-agentico]
jira:
  estado: borrador             # borrador | listo | creado | duplicado | descartado
  proyecto: null
  key: null                    # SOLO la devuelta por Jira
  url: null
  fingerprint: null            # lo calcula jira_bug.py
  duplicado_de: null
---
## Descripción
[Contexto breve del fallo.]

## Clasificación y contexto
<!-- jira_bug.py incluye aquí SOLO los campos que no tienen campo propio en Jira -->

## Datos de prueba
- Base URL: `$QA_BASE_URL`
- Pantalla o endpoint:
- Método HTTP, si aplica:
- Rol utilizado:
- Precondiciones:
- IDs de datos sintéticos:
- Payload / parámetros:
- Referencia segura a credenciales: `$QA_USER_<ROL>_EMAIL` / `$QA_USER_<ROL>_PASSWORD`

## Pasos de reproducción
1. ...
2. ...
3. ...

## Resultado actual
[Comportamiento observado, código HTTP y estado de datos cuando corresponda.]

## Resultado esperado
[Comportamiento esperado.] Fuente: [requisito / contrato / especificación]

## Evidencia
- Captura / video:
- Request y response sanitizados:
- cURL:
```bash
curl -sS -X GET "$QA_API_URL/..." -H "Authorization: Bearer $QA_TOKEN"
```
<!-- Incluir query SQL SOLO si se consultó la base de datos -->

## Observaciones
- Frecuencia de reproducción:
- Alcance observado:
- Alternativa temporal:
- Hipótesis técnica (pendiente de confirmar):
- Caso y ejecución relacionados:
