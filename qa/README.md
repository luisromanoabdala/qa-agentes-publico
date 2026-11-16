# QA agéntico — equipo de agentes QA reutilizable

Equipo de agentes QA con criterio senior para cualquier proyecto: analiza código e impacto, diseña la estrategia
por riesgo, escribe casos trazables, automatiza, ejecuta sobre ambientes reales, revisa seguridad y registra bugs en Jira,
con un **contrato de archivos** que hace verificable cada afirmación.

## Equipo

| Rol lógico | Implementación | Archivo |
|---|---|---|
| A. QA Lead / Orquestador | Skill | `skills/qa-lead/SKILL.md` |
| B. Analista técnico y de impacto | Subagente | `agents/qa-analista-impacto.md` |
| C. Automatización y framework E2E | Subagente | `agents/qa-automatizacion.md` |
| D. Estrategia y planes | Subagente | `agents/qa-estratega.md` |
| E. Diseño y registro de casos | Subagente | `agents/qa-disenador-casos.md` |
| F. Ejecución, triage y retest | Subagente | `agents/qa-ejecutor.md` |
| G. Seguridad QA | Subagente | `agents/qa-seguridad.md` |
| H. Bugs en Jira | Subagente + script | `agents/qa-jira-reporter.md`, `qa/scripts/jira_bug.py` |

El orquestador es una skill porque corre en la conversación principal y es quien puede lanzar subagentes;
los subagentes no se lanzan entre sí: devuelven su `entrega:` al Lead.

## Estructura

```
qa/
├── coordinacion/   contrato.md (archivos, IDs, vocabulario, handoff) · flujo.md (análisis → retest)
├── estandares/     bugs.md · evidencia-y-confirmacion.md · datos-y-secretos.md · piramide-y-fases.md
├── guias/          configuracion-herramientas.md (instalación, secretos, Jira) · seleccion-framework.md
├── plantillas/
│   ├── campania/   campania.yaml (contexto inicial) · analisis.md · riesgos.yaml · plan.md · casos/ ·
│   │               ejecuciones.yaml · hallazgos.yaml · bugs/_plantilla-bug.md · jira-mapping.yaml · informe.md
│   └── automatizacion/playwright/   referencia de suite contra ambiente (si la decisión es Playwright)
├── scripts/        validate_campaign.py · new_campaign.py · jira_bug.py · tests/
└── ejemplos/odontologia-sintetico/   ⚠️ EJEMPLO con datos ficticios, campaña completa
```

Las campañas reales viven en el repo de cada app: `.qa/campanias/<Cnn-nombre>/`.

## Uso rápido

1. Instalar (una vez): `integracion/instalar.sh` (ver el README principal).
2. Pedirle a Claude, por ejemplo:
   - `corré un QA de <app> sobre <URL>, flujos prioritarios: <flujos>, bugs en Jira <PROYECTO>`
   - `analizá el impacto de este PR para QA` · `retest de BUGD-003 en la versión 1.5.1`
3. El Lead crea/actualiza la campaña, pide solo lo que falta, coordina a los subagentes y entrega `informe.md`.

```bash
python3 qa/scripts/new_campaign.py .qa/campanias/C02-regresion --id C02 --nombre "Regresión v1.5"
python3 qa/scripts/validate_campaign.py .qa/campanias/C02-regresion --resumen
```

## Garantías que da el kit (y cómo se verifican)

| Regla | Mecanismo |
|---|---|
| Nada "ejecutado" sin registro | Informe se arma desde `ejecuciones.yaml`; validador exige fecha con zona, ambiente, versión y evidencia |
| Hallazgo ≠ bug | `confirmacion` controlada; un bug exige ejecución `fallido` clasificada `producto` |
| Reintentos visibles | Aprobado con `intentos > 1` sin `inestable: true` es error |
| Sin claves Jira inventadas | `jira.key` solo con `estado: creado` + URL; el script escribe la clave devuelta por Jira |
| Sin campos/valores inventados en Jira | `discover` + `check-mapping` contra la metadata real; requeridos sin cubrir detienen la creación |
| Sin duplicados por reintento | Huella `qa-fp-*` en etiquetas + búsqueda antes de reintentar |
| Sin secretos ni PII | Escaneo de patrones de secretos y emails no sintéticos en la campaña |
| Trazabilidad | Referencias cruzadas validadas (requisito/riesgo → caso → ejecución → hallazgo → bug) |
