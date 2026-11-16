# Agentes QA

Equipo de agentes de QA para Claude Code. Un **orquestador** (`qa-lead`) coordina a siete especialistas que analizan el código, arman la estrategia por riesgo, escriben y ejecutan casos, revisan seguridad y **reportan los bugs en Jira**. Cada afirmación queda respaldada por archivos verificables: nada se da por probado sin una ejecución registrada con evidencia.

Sirve para cualquier repo: una app web, una API o un panel. Copialo, adaptalo y usalo en tus proyectos o en los de tu equipo.

---

## Índice
1. [El equipo](#1-el-equipo)
2. [Instalación (5 minutos)](#2-instalación-5-minutos)
3. [Cómo usarlo: un pedido por caso](#3-cómo-usarlo-un-pedido-por-caso)
4. [Reportar bugs en Jira](#4-reportar-bugs-en-jira)
5. [QA automático en PR y antes de pushear](#5-qa-automático-en-pr-y-antes-de-pushear)
6. [Dónde quedan los resultados](#6-dónde-quedan-los-resultados)
7. [Reglas del equipo QA](#7-reglas-del-equipo-qa)
8. [Comandos útiles y problemas comunes](#8-comandos-útiles-y-problemas-comunes)

---

## 1. El equipo

| Agente | Qué hace | Cuándo entra |
|---|---|---|
| **`qa-lead`** (skill, orquestador) | Recibe el pedido, arma la campaña, pide solo lo que falta, reparte el trabajo, verifica lo que devuelve cada agente y emite la recomendación final | Siempre: es con quien hablás |
| `qa-analista-impacto` | Lee el código y el diff: módulos reales, reglas de negocio, permisos, integraciones e impacto directo e indirecto del cambio | Inicio de campaña y cada PR |
| `qa-estratega` | Plan por riesgo: qué niveles probar (unitario, integración, e2e), qué no y por qué | Después del análisis |
| `qa-disenador-casos` | Casos de prueba trazables (requisito/riesgo → caso), con datos, pasos y resultado esperado con fuente | Después del plan |
| `qa-automatizacion` | Elige o mejora el framework y automatiza los casos candidatos | Cuando conviene automatizar |
| `qa-ejecutor` | Ejecuta en el ambiente (navegador y API), registra evidencia, clasifica fallos y hace retest | Con ambiente y cuentas |
| `qa-seguridad` | Autenticación, permisos por rol, aislamiento entre clientes, secretos, cabeceras | En paralelo al análisis |
| **`qa-jira-reporter`** | Convierte bugs reproducidos en issues de Jira: descubre los campos reales del proyecto, evita duplicados, crea, verifica y adjunta evidencia | Cuando hay bugs confirmados |

No hace falta llamarlos uno por uno. Le pedís el trabajo a Claude y `qa-lead` decide quién interviene.

## 2. Instalación (5 minutos)

**Requisitos:** [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) instalado, `git` y `python3` (3.9 o más).

```bash
git clone https://github.com/luisromanoabdala/qa-agentes.git ~/qa-agentes
cd ~/qa-agentes
./integracion/instalar.sh                  # instala los agentes para tu usuario
echo 'export QA_KIT="$HOME/qa-agentes"' >> ~/.zshrc && source ~/.zshrc   # o ~/.bashrc
```

Para que **todo el equipo de un repo** los tenga sin instalar nada (quedan versionados en `.claude/` de ese repo):

```bash
~/qa-agentes/integracion/instalar.sh --repo ~/ruta/a/mi-app
cd ~/ruta/a/mi-app && git add .claude && git commit -m "Agentes QA"
```

### Tener tu propia copia

- **Fork:** botón *Fork* en GitHub. Te quedás con una copia en tu cuenta u organización y podés traer mejoras de este repo con *Sync fork*.
- **Copia independiente:**
  ```bash
  git clone https://github.com/luisromanoabdala/qa-agentes.git ~/qa-agentes
  cd ~/qa-agentes && git remote remove origin
  gh repo create <tu-usuario-u-org>/qa-agentes --private --source . --push
  ```
  Si tu copia queda en otro lugar, cargá la variable `QA_AGENTES_REPO` (ver §5.1) para que el workflow de PR la use.

Comprobá que quedó bien: abrí Claude Code en cualquier repo (`claude`) y escribí `/agents`. Tienen que aparecer los siete `qa-*`.

**Recomendado:** copiá `integracion/contexto-ejemplo.md` a `.qa/contexto.md` en cada repo y completalo con ambientes, roles, flujos prioritarios y proyecto Jira. Con eso el orquestador no te pregunta lo mismo en cada campaña.

> En Claude Desktop (Cowork) podés instalar `skills/qa-lead` desde *Settings → Capabilities → Skills*. Si los subagentes no están disponibles en esa superficie, el orquestador ejecuta cada rol leyendo su archivo de `agents/`.

## 3. Cómo usarlo: un pedido por caso

Abrí Claude Code **en el repo de la app** (`cd mi-app && claude`) y pedí en lenguaje natural. Ejemplos listos para copiar:

| Necesitás… | Pedido |
|---|---|
| **QA completo** de una versión | `Corré un QA de punta a punta de esta app sobre https://test.miapp.com. Flujos prioritarios: login, alta de cliente y pagos. Bugs en Jira proyecto ABC.` |
| **Revisar un PR o una rama** antes de mergear | `Analizá para QA el impacto de la rama feature/pagos contra main: riesgos, qué se puede romper indirectamente y qué casos correr.` |
| **Smoke antes de un deploy** | `Smoke test de https://test.miapp.com antes de pasar a producción: lo mínimo para decidir si se puede deployar.` |
| **Retest** de bugs arreglados | `Retest de ABC-12, ABC-15 y ABC-20 en test. Si pasan, comentá cada ticket con la evidencia; si alguno falla, volvelo a "En curso" con la causa.` |
| **Regresión** después de arreglos | `Regresión de los módulos que tocaron los commits desde v1.4 hasta main, en test.` |
| **Seguridad** | `Revisá permisos por rol y aislamiento entre clientes de la API. Solo lectura, sin pruebas destructivas.` |
| **Automatizar** | `Automatizá los casos críticos de la campaña C02 con el framework que ya usa el repo.` |
| **Solo reportar** bugs ya encontrados | `Reportá en Jira ABC los bugs reproducidos de la campaña C02.` |

Qué esperar:
1. `qa-lead` crea la campaña en `.qa/campanias/Cnn-nombre/` y te pide **una sola vez** lo que no puede sacar del repo: URL, cuentas, alcance y permisos para crear o borrar datos.
2. Avanza en paralelo con lo que no depende de vos (análisis de código, plan, casos).
3. Te entrega `informe.md` con una recomendación: **Apta**, **Apta con riesgos aceptados**, **No apta** o **Sin evidencia suficiente**, más la lista de bugs con su clave real de Jira.

**Cuentas de prueba:** nunca pegues contraseñas en el chat. Cargalas como variables de entorno (ver §4.1) o iniciá sesión vos en el navegador de Claude y avisale.

## 4. Reportar bugs en Jira

El agente `qa-jira-reporter` crea los issues **en el proyecto que le indiques** y solo con bugs reproducidos (con ejecución fallida y evidencia). Antes de crear, lee la configuración real del proyecto: tipos de issue, campos obligatorios y valores permitidos. Nunca inventa claves, campos ni valores, y nunca cambia la configuración de Jira.

### 4.1 Configuración (una vez)

**Opción A — conector de Atlassian en Claude:** *Settings → Connectors → Atlassian → Connect*. El agente usa tus permisos de Jira.

**Opción B — API con token** (la que usan los scripts y la CI):
1. Creá un token en https://id.atlassian.com/manage-profile/security/api-tokens
2. Creá un archivo `.env.qa` en el repo de la app. Está en `.gitignore`: verificalo con `git check-ignore .env.qa`.
   ```bash
   JIRA_BASE_URL=https://<sitio>.atlassian.net
   JIRA_EMAIL=<tu email de Atlassian>
   JIRA_API_TOKEN=<token>
   # cuentas de la app bajo prueba, una por rol
   QA_USER_ADMIN_EMAIL=...
   QA_USER_ADMIN_PASSWORD=...
   ```
3. Cargalo en la terminal donde vas a trabajar: `set -a; source .env.qa; set +a`

### 4.2 Flujo

Lo hace el agente solo cuando le pedís "reportá los bugs en Jira <PROYECTO>". Si querés hacerlo a mano (`C` = carpeta de la campaña):

```bash
C=.qa/campanias/C01-smoke
python3 $QA_KIT/qa/scripts/jira_bug.py discover --project ABC --out $C/jira-meta.json        # lee los campos reales
python3 $QA_KIT/qa/scripts/jira_bug.py suggest-mapping --meta $C/jira-meta.json              # propone el mapeo → $C/jira-mapping.yaml
python3 $QA_KIT/qa/scripts/jira_bug.py check-mapping --meta $C/jira-meta.json --mapping $C/jira-mapping.yaml
python3 $QA_KIT/qa/scripts/jira_bug.py payload --bug $C/bugs/BUGD-001.md --mapping $C/jira-mapping.yaml --meta $C/jira-meta.json   # vista previa, no crea nada
python3 $QA_KIT/qa/scripts/jira_bug.py create  --bug $C/bugs/BUGD-001.md --mapping $C/jira-mapping.yaml --meta $C/jira-meta.json --campaign $C
python3 $QA_KIT/qa/scripts/jira_bug.py attach  --campaign $C                                  # sube las evidencias de todos los bugs
```

- **Sin duplicados:** cada bug lleva una etiqueta `qa-fp-<hash>`. Antes de reintentar una creación dudosa, el script busca esa etiqueta.
- **Adjuntos:** `attach` es idempotente. Sube solo los archivos que el issue todavía no tiene, así que lo podés correr cuantas veces quieras.
- **Formato del bug:** título `[Módulo] Falla observada bajo condición`, prioridad P0–P3 y severidad por separado, pasos, resultado actual y esperado con fuente, y evidencia sanitizada. Estándar completo en `qa/estandares/bugs.md`.

## 5. QA automático en PR y antes de pushear

La idea: **antes de que algo entre a una rama principal**, el orquestador revisa el cambio, deja un reporte y, si querés, frena el merge cuando la recomendación es "No apta".

### 5.1 En cada Pull Request (GitHub Actions) — recomendado

1. En el repo de la app, copiá el workflow:
   ```bash
   mkdir -p .github/workflows && cp $QA_KIT/integracion/github-actions/qa-pr.yml .github/workflows/
   ```
2. En *Settings → Secrets and variables → Actions* del repo de la app (o de tu organización):
   - Secret `ANTHROPIC_API_KEY`: clave de la API de Anthropic.
   - Variable `QA_AGENTES_REPO` (opcional): `usuario/repo` de tu copia de los agentes. Sin ella usa `luisromanoabdala/qa-agentes`.
   - Secret `QA_AGENTES_TOKEN` (opcional): solo si tu copia de los agentes es privada. Es un token de **solo lectura** con acceso a ella.
3. Para que bloquee el merge: *Settings → Branches* → regla de `main` (y de `test`) → **Require status checks** → `QA / revisión`.

Qué pasa en cada PR hacia `main`, `master`, `test` o `develop`:
- Se instalan los agentes y se validan las campañas QA del repo, si hay.
- `qa-analista-impacto` y `qa-seguridad` revisan el diff.
- Se suman los casos sugeridos y el reporte queda **comentado en el PR**.
- Si la primera línea dice `Recomendación: No apta`, el check queda en rojo.

El modo PR es de **solo lectura**: no ejecuta contra ambientes ni crea issues en Jira. Para eso, pedí un QA completo (§3).

### 5.2 Antes de pushear (hook local)

Para quien prefiera enterarse antes de abrir el PR:

```bash
mkdir -p .githooks && cp $QA_KIT/integracion/hooks/pre-push .githooks/ && chmod +x .githooks/pre-push
git config core.hooksPath .githooks
```

- Corre solo al pushear a `main`, `master`, `test` o `develop`; se cambia con `QA_RAMAS="main test"`.
- Deja el reporte en `.qa/reportes/push-<rama>-<commit>.md` y muestra la recomendación.
- Es **informativo** por defecto. Con `QA_BLOQUEAR=1` cancela el push si la recomendación es "No apta".
- Para saltearlo una vez con el riesgo aceptado: `QA_SALTEAR=1 git push`.
- Si el repo ya tiene un `pre-push` (por ejemplo, un build), agregá el contenido de este al final del existente en lugar de reemplazarlo.

> **¿Y en cada commit?** No lo recomendamos: el análisis tarda minutos y frena el trabajo diario. Lo útil es revisar en el **push a ramas principales** y en el **PR**, que es donde se decide qué se mergea.

### 5.3 Flujo sugerido por rama

| Momento | Qué corre | Bloquea |
|---|---|---|
| Commit en tu rama | Tus tests y linters de siempre | — |
| Push a `test` / `main` | Hook `pre-push` (análisis de impacto) | Opcional (`QA_BLOQUEAR=1`) |
| PR hacia `test` / `main` | Workflow `qa-pr.yml` | Sí, con la regla de rama |
| Antes de pasar `test` → `main` | Pedido "Smoke de test antes de producción" (§3) | Decisión del equipo con el `informe.md` |
| Después del deploy | Pedido "Retest de …" y "Regresión de …" | Reabre tickets que fallen |

## 6. Dónde quedan los resultados

En el repo de la app:

```
.qa/
├── contexto.md                  # ambientes, roles, flujos, Jira (lo completás una vez)
├── reportes/                    # reportes de PR y de pre-push
└── campanias/C01-smoke/         # una carpeta por campaña
    ├── campania.yaml            # alcance, ambiente, autorizaciones, bloqueos
    ├── analisis.md · riesgos.yaml · plan.md
    ├── casos/*.yaml             # casos de prueba
    ├── ejecuciones.yaml         # lo que realmente se ejecutó, con fecha, versión y evidencia
    ├── hallazgos.yaml           # estático · hipótesis · reproducido · bloqueado
    ├── bugs/BUGD-001.md         # borrador → clave real de Jira
    ├── evidencias/              # capturas y logs sanitizados
    └── informe.md               # recomendación final
```

Versioná `.qa/` junto con el código, salvo que contenga datos sensibles: las evidencias se sanitizan, pero revisalas antes del commit. El contrato completo de archivos e IDs está en `qa/coordinacion/contrato.md`. Hay una campaña de ejemplo completa, con datos ficticios, en `qa/ejemplos/odontologia-sintetico/`.

## 7. Reglas del equipo QA

- **Cuatro estados, nunca mezclados:** hallazgo estático (leído en el código), hipótesis, bug reproducido (ejecución fallida con evidencia) y prueba bloqueada.
- **Nada se presenta como probado si no se ejecutó.** El informe sale de `ejecuciones.yaml`.
- **Producción:** solo lectura, salvo autorización explícita. Las pruebas destructivas o de carga necesitan alcance escrito.
- **Secretos:** nunca en Git, casos, logs, tickets ni chat. Van en variables de entorno o en un gestor (1Password, Doppler…). Si una credencial circuló por chat, se rota.
- **Datos:** sintéticos. En apps con datos personales o de salud, nada identificable en evidencias.
- **Jira:** sin claves, campos ni valores inventados, y sin tocar la configuración del proyecto.

## 8. Comandos útiles y problemas comunes

```bash
python3 $QA_KIT/qa/scripts/new_campaign.py .qa/campanias/C02-regresion --id C02 --nombre "Regresión v1.5"
python3 $QA_KIT/qa/scripts/validate_campaign.py .qa/campanias/C02-regresion --resumen    # estado y números del informe
python3 $QA_KIT/qa/scripts/validate_campaign.py .qa/campanias/C02-regresion --estricto   # antes de cerrar una campaña
python3 -m unittest discover -s $QA_KIT/qa/scripts/tests                                 # tests del kit
```

| Problema | Solución |
|---|---|
| `/agents` no muestra los `qa-*` | Volvé a correr `integracion/instalar.sh` y reiniciá Claude Code |
| Los agentes no encuentran `qa/…` | Falta `export QA_KIT=…` en tu shell |
| `jira_bug.py` responde 401 | Revisá `JIRA_EMAIL` y `JIRA_API_TOKEN`, y que hayas hecho `source .env.qa` en esa terminal |
| `check-mapping` marca un campo obligatorio | El proyecto exige un campo sin valor en el bug: completalo en el bug o pedí el valor a quien administra Jira |
| El workflow de PR no encuentra los agentes | Revisá la variable `QA_AGENTES_REPO`; si tu copia es privada, falta el secret `QA_AGENTES_TOKEN` |
| El reporte de PR dice "Sin evidencia suficiente" | El diff necesita pruebas en un ambiente: pedí un smoke o un QA completo (§3) |

Más detalle: `qa/README.md` (estructura del kit), `qa/coordinacion/flujo.md` (etapas), `qa/estandares/` (bugs, evidencia, secretos, pirámide de pruebas) y `qa/guias/` (herramientas y elección de framework).
