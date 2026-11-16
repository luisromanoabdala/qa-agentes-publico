# Referencia: suite E2E contra ambiente desplegado (Playwright Test)

Usar **solo si** la decisión documentada (ver `qa/guias/seleccion-framework.md`) eligió Playwright, y adaptarlo a las
convenciones del repo. Si el repo ya tiene Playwright (p. ej. con la API mockeada), esta suite se agrega como **proyecto
separado** que apunta a un ambiente real; no reemplaza la existente.

Incluye:
- `playwright.ambiente.config.ts`: ambiente por variables, reporte HTML+JUnit, trazas/capturas/video en fallo, reintentos
  visibles (`retries` solo en CI y reportados como *flaky*), autenticación por rol con storage state.
- `fixtures.ts`: `runId` para datos sintéticos, login por rol vía UI con credenciales de entorno, registro de limpieza.
- `smoke.ambiente.spec.ts`: smoke de **solo lectura** (salud del ambiente, login, navegación a módulos), apto para producción.
- `.env.qa.example`: nombres de variables (sin valores reales).

```bash
set -a; source .env.qa; set +a
npx playwright test -c playwright.ambiente.config.ts --project=smoke
npx playwright show-report reports/ambiente
```
Antes de agregar tests que **escriban** datos: confirmar `autorizaciones` de la campaña y usar `runId` + limpieza.
