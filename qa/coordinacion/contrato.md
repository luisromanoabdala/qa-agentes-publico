# Contrato de intercambio entre agentes QA

Todos los agentes QA leen y escriben **una carpeta de campaña** con archivos versionables.
La carpeta es la única fuente de verdad: lo que no está ahí, no ocurrió.
`python3 qa/scripts/validate_campaign.py <carpeta>` verifica este contrato.

## 1. Estructura de una campaña

```
<campaña>/                      # p. ej. .qa/campanias/C01-2026-11-smoke-agenda/
├── campania.yaml               # contexto, alcance, accesos, requisitos, bloqueos   (dueño: qa-lead)
├── analisis.md                 # análisis técnico y de impacto                      (qa-analista-impacto)
├── riesgos.yaml                # riesgos priorizados                                (qa-analista-impacto → qa-estratega)
├── plan.md                     # estrategia y plan de testing                       (qa-estratega)
├── casos/<MODULO>.yaml         # casos de prueba trazables                          (qa-disenador-casos)
├── ejecuciones.yaml            # registro de ejecuciones                            (qa-ejecutor)
├── hallazgos.yaml              # hallazgos con nivel de confirmación                (todos; qa-lead consolida)
├── bugs/BUGD-NNN.md            # borradores y bugs registrados en Jira               (qa-jira-reporter)
├── jira-mapping.yaml           # mapeo de campos lógicos → campos reales de Jira    (qa-jira-reporter)
├── evidencias/                 # SOLO evidencia sanitizada (raw/ está en .gitignore) (qa-ejecutor, qa-seguridad)
└── informe.md                  # consolidado y recomendación de calidad             (qa-lead)
```

Regla de propiedad: cada agente **agrega o actualiza** sus propios archivos. Para pedir un cambio
en el archivo de otro agente, lo deja como `bloqueos` o `proximos_pasos` en su entrega.
`hallazgos.yaml` es compartido: cualquiera agrega entradas, nadie borra las de otro.

## 2. Identificadores

| Entidad | Formato | Ejemplo | Quién lo asigna |
|---|---|---|---|
| Requisito | El de la fuente (historia, ticket, sección de doc) | `DENT-42`, `DOC-AGENDA-3.2` | Fuente |
| Riesgo | `RSK-NNN` | `RSK-004` | qa-analista-impacto |
| Caso | `TC-<MOD>-NNN` (MOD = 2–6 letras mayúsculas) | `TC-AGE-003` | qa-disenador-casos |
| Ejecución | `EXE-AAAAMMDD-NNN` | `EXE-20261104-007` | qa-ejecutor |
| Hallazgo | `HAL-NNN` | `HAL-012` | quien lo detecta |
| Bug (borrador local) | `BUGD-NNN` | `BUGD-003` | qa-jira-reporter |
| Bug en Jira | Clave real devuelta por Jira | — | **Jira** (nunca se inventa) |
| Bloqueo | `BLK-NNN` | `BLK-002` | quien lo detecta |

Los IDs son estables: no se renumeran ni se reutilizan. Si un caso se descarta, se marca `estado: obsoleto`.

## 3. Vocabulario controlado

**Nivel de confirmación de un hallazgo** (`hallazgos.yaml → confirmacion`):

| Valor | Significa | Requisito mínimo |
|---|---|---|
| `estatico` | Identificado por análisis estático de código/config/contrato | `origen` con archivo:símbolo o documento |
| `hipotesis` | Sospecha razonada pendiente de verificar | `como_verificar` |
| `reproducido` | Confirmado por al menos una ejecución fallida | `ejecuciones` con ≥1 ejecución `fallido` de clasificación `producto` |
| `bloqueado` | No se puede verificar por acceso, datos o dependencias | `bloqueo` (BLK-NNN) |
| `descartado` | Se verificó y no es un problema | `motivo` |

**Estado de una ejecución:** `aprobado`, `fallido`, `bloqueado`, `omitido`. No existe "diseñado" ni "pendiente":
un caso sin ejecución simplemente no tiene filas en `ejecuciones.yaml`.

**Clasificación de un fallo** (`ejecuciones.yaml → clasificacion_fallo`): `producto`, `infraestructura`,
`datos`, `script`, `indeterminado`. Solo `producto` puede originar un bug.

**Estado de un bug en Jira** (`bugs/*.md → jira.estado`): `borrador`, `listo`, `creado`, `duplicado`, `descartado`.

## 4. Trazabilidad obligatoria

```
requisito ─┐
riesgo ────┼─> caso ─> ejecución ─> hallazgo (reproducido) ─> bug ─> issue Jira
análisis ──┘                         ▲
                     hallazgo estático/hipótesis ─(verificación)─┘
```

- Todo caso referencia ≥1 requisito **o** riesgo.
- Toda ejecución referencia un caso existente (las exploratorias usan `TC-EXP-NNN` con su carta en `casos/EXP.yaml`).
- Todo hallazgo tiene `origen` (caso, ejecución o análisis con archivo:símbolo).
- Todo bug referencia ≥1 ejecución `fallido`/`producto`, ≥1 evidencia y un `resultado_esperado` con `fuente`.
- Todo retest es una ejecución nueva con `retest_de: EXE-...` (no se pisa la original).

## 5. Formato de entrega de cada agente (handoff)

Al terminar, cada subagente responde al orquestador **exactamente** con este bloque
(además de haber escrito sus archivos):

```yaml
entrega:
  agente: qa-<rol>
  campania: <ruta de la carpeta>
  hecho:                 # acciones REALMENTE realizadas, verificables
    - "Leí 42 archivos de src/modules/agenda (lista en analisis.md §2)"
  archivos_actualizados: [analisis.md, riesgos.yaml, hallazgos.yaml]
  ids_nuevos: [RSK-001, RSK-002, HAL-001]
  no_hecho:              # lo que se pidió y no se hizo, con motivo
    - "No ejecuté pruebas: no tengo la URL de QA (BLK-001)"
  bloqueos: [BLK-001]
  proximos_pasos:
    - para: qa-disenador-casos
      tarea: "Diseñar casos para RSK-001..RSK-004"
```

`hecho` solo contiene cosas que pasaron. Diseñar una prueba no es ejecutarla; leer código no es probar la app;
preparar un bug no es haberlo creado en Jira.

## 6. Bloqueos

Se registran en `campania.yaml → bloqueos` con: `id`, `descripcion`, `impacta` (IDs de casos/riesgos),
`necesita` (qué y de quién), `detectado` (fecha), `estado` (`abierto`/`resuelto`).
Ante un bloqueo: se registra, se continúa con lo independiente y se reporta en la entrega.
