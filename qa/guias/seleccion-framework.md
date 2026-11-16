# Selección de framework de automatización

Regla 1: **si el proyecto ya tiene automatización que funciona, se evoluciona.** Cambiar de herramienta requiere un problema
demostrado (no una preferencia).

## Relevamiento (antes de comparar)
| Pregunta | Dónde mirarlo |
|---|---|
| Plataforma: web, PWA, mobile nativa, híbrida, escritorio | README, manifiestos, carpetas `ios/`, `android/`, `electron` |
| Lenguajes y frameworks | `package.json`, `composer.json`, `pyproject`, `go.mod` |
| Tests existentes por nivel | carpetas `tests/`, `e2e/`, configs de Vitest/Jest/PHPUnit/Pytest/Playwright/Cypress |
| CI/CD | `.github/workflows`, GitLab CI, etc. |
| Navegadores/dispositivos reales de los usuarios | analítica, docs del producto, decisión del negocio |
| Experiencia del equipo | lenguaje dominante del repo, quién mantiene los tests |
| Restricciones | CSP, auth por cookie/SSO, 2FA, iframes, canvas/WebGL, archivos grandes |

## Criterios de comparación
Compatibilidad con el stack y plataformas · soporte de navegadores/dispositivos · diagnóstico de fallos (trazas, video, DOM snapshot) ·
estabilidad (auto-wait, aislamiento) · ejecución en CI y paralelismo · costo de mantenimiento · curva del equipo ·
madurez y **documentación oficial vigente** (verificar versión actual y requisitos en el sitio oficial, con fecha de consulta).

## Alternativas habituales (verificar versiones al decidir)
| Contexto | Opciones viables |
|---|---|
| Web (cualquier framework JS) | Playwright Test, Cypress, WebdriverIO |
| Web con equipo Python/Java | Playwright (Python/Java), Selenium |
| Mobile nativa/híbrida | Appium/WebdriverIO, Detox (React Native), Maestro |
| API | Cliente del runner (Playwright `request`, Supertest), Postman/Newman, pytest+httpx |
| Contrato | Validación contra OpenAPI (Schemathesis, Prism, tests del proveedor), Pact (consumer-driven) |
| Unit/componente | El del stack: Vitest/Jest + Testing Library, PHPUnit, Pytest |

## Registro de la decisión
```
Decisión: <herramienta y versión> · Fecha: AAAA-MM-DD · Fuente oficial consultada: <URL>
Alternativas consideradas: A (pros/contras), B (pros/contras)
Motivo: …  · Riesgos/limitaciones: …  · Revisión: cuándo se reconsideraría
```
