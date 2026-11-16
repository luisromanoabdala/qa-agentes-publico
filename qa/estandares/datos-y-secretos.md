# Datos de prueba, datos sensibles y secretos

Las apps de salud (p. ej. odontología) manejan datos personales y **datos de salud**, considerados sensibles
(en Argentina, Ley 25.326 de Protección de Datos Personales y Ley 26.529 de Derechos del Paciente / historia clínica).
QA no necesita datos reales para hacer su trabajo.

## Reglas

1. **Datos sintéticos primero.** Pacientes ficticios con marcador inequívoco (p. ej. nombre `QA-Paciente-<runId>`,
   email `qa+<runId>@example.test`, DNI fuera de rango real `99.000.001`+). Nunca copiar fichas reales a casos o tickets.
2. **Cuentas de prueba** por rol, provistas por el equipo. Nunca usar cuentas personales.
3. **Nada sensible en Git, casos, logs, evidencias o tickets:** contraseñas, tokens, cookies, API keys, service-role keys,
   datos clínicos identificables, DNI/teléfonos reales.
4. **Secretos solo por variables de entorno** o gestor de secretos existente (1Password CLI, Doppler, GitHub Actions secrets, Vercel env…).
   En cURL y pasos: `-H "Authorization: Bearer $QA_TOKEN"`.
5. **Sanitizar antes de adjuntar:** tapar/blurear datos personales en capturas, reemplazar tokens por `<REDACTED>` en HAR/JSON/logs.
6. **Base de datos:** solo lectura cuando alcance (rol read-only o réplica). Escribir solo en ambientes de QA y con autorización.
7. **Limpieza:** todo dato creado por pruebas lleva el `runId` para poder identificarlo y borrarlo. La limpieza se registra en la ejecución.
8. **Producción:** solo smoke de lectura salvo autorización explícita en `campania.yaml → autorizaciones`.

## Variables estándar

| Variable | Uso |
|---|---|
| `QA_ENV` | Nombre del ambiente (`qa`, `staging`, `prod`) |
| `QA_BASE_URL` | URL web del ambiente |
| `QA_API_URL` | Base URL de la API |
| `QA_USER_<ROL>_EMAIL` / `QA_USER_<ROL>_PASSWORD` | Cuenta por rol (p. ej. `QA_USER_ODONTOLOGO_EMAIL`) |
| `QA_TOKEN` | Token de API ya emitido (si se usa) |
| `QA_DB_URL_RO` | Conexión de solo lectura (opcional) |
| `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` | Jira Cloud (o `JIRA_PAT` en Server/DC) |

Archivo local: `.env.qa` (ignorado por Git), a partir de `qa/plantillas/automatizacion/playwright/.env.qa.example`.

## Escaneo automático

`validate_campaign.py` busca patrones de secretos (JWT, `Bearer <valor>`, `password: <valor>`, claves privadas, `sk_live`,
`AKIA…`, `ATATT…`) y emails no sintéticos en toda la carpeta de campaña. Un hallazgo es **error** y bloquea la entrega.
