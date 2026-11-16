# Configuración de herramientas y secretos

## 1. Instalar el equipo QA en Claude
```bash
git clone https://github.com/luisromanoabdala/qa-agentes.git ~/qa-agentes
~/qa-agentes/integracion/instalar.sh            # para tu usuario (~/.claude)
~/qa-agentes/integracion/instalar.sh --repo .   # o dentro de un repo (.claude/ versionado)
export QA_KIT="$HOME/qa-agentes"                # agregalo a ~/.zshrc o ~/.bashrc
```
El instalador copia `agents/qa-*.md` y `skills/qa-lead`, instala PyYAML y corre los tests de los scripts.
En Cowork: instalar la skill `qa-lead` (Settings → Capabilities → Skills). Si los subagentes no están disponibles en la
superficie que uses, la skill ejecuta cada rol leyendo `agents/qa-*.md`.

## 2. Secretos de la aplicación bajo prueba
1. Copiá `qa/plantillas/automatizacion/playwright/.env.qa.example` a `.env.qa` **en el repo de la app** (o en una carpeta privada) y completalo.
   `.env.qa` está ignorado por Git (verificá con `git check-ignore .env.qa`).
2. Cargalo solo en la terminal que ejecuta las pruebas: `set -a; source .env.qa; set +a`.
3. Preferible con gestor: `op run --env-file=.env.qa.tpl -- pnpm test:e2e` (1Password CLI) o `doppler run -- …`.
4. CI: GitHub Actions → *Settings → Secrets and variables → Actions*, con los mismos nombres (`QA_USER_ODONTOLOGO_EMAIL`, …).
5. **Cuentas:** una por rol, dedicadas a QA, sin datos reales. Rotar cualquier credencial que haya circulado por chat, mail o tickets.

## 3. Jira
Dos caminos; el agente usa el que esté disponible y lo declara.

**A. Conector Atlassian (MCP) en Claude** — claude.ai → Settings → Connectors → Atlassian → Connect (usa tus permisos de Jira).
Habilitarlo en la sesión donde corre el QA. El agente descubre sitio, proyecto, tipo Bug y campos con las herramientas del conector.

**B. API REST con token** (scripts del kit)
1. Crear token: https://id.atlassian.com/manage-profile/security/api-tokens
2. Variables (en `.env.qa` o gestor, nunca en archivos versionados):
   `JIRA_BASE_URL=https://<sitio>.atlassian.net`, `JIRA_EMAIL=<tu email de Atlassian>`, `JIRA_API_TOKEN=<token>`
   (Server/Data Center: `JIRA_PAT` y `api_version: 2` en el mapeo).
3. Descubrir y mapear:
```bash
C=.qa/campanias/<campaña>
python3 qa/scripts/jira_bug.py discover --project <KEY> --out $C/jira-meta.json
python3 qa/scripts/jira_bug.py suggest-mapping --meta $C/jira-meta.json   # propuesta → revisar y pegar en $C/jira-mapping.yaml
python3 qa/scripts/jira_bug.py check-mapping --meta $C/jira-meta.json --mapping $C/jira-mapping.yaml
python3 qa/scripts/jira_bug.py payload --bug $C/bugs/BUGD-001.md --mapping $C/jira-mapping.yaml --meta $C/jira-meta.json  # dry-run
python3 qa/scripts/jira_bug.py create  --bug $C/bugs/BUGD-001.md --mapping $C/jira-mapping.yaml --meta $C/jira-meta.json --campaign $C
```
El script nunca modifica la configuración de Jira; si un campo requerido no está cubierto, se detiene y lo informa.
Idempotencia: cada bug lleva una etiqueta de huella `qa-fp-<hash>`; ante una respuesta incierta busca esa etiqueta antes de reintentar.

## 4. Navegador y API
- Ejecución exploratoria: el navegador integrado de Claude o Claude in Chrome (el agente `qa-ejecutor` hereda esas herramientas).
- Automatización: la que defina `qa-automatizacion` según `seleccion-framework.md`.
- API: `curl` con `$QA_TOKEN`/cookies de sesión obtenidas en la ejecución, nunca escritas en archivos.

## 5. Base de datos
Solo lectura: usuario con `SELECT` únicamente (MySQL: `GRANT SELECT ON db.* TO 'qa_ro'@'%'`; Postgres: rol `qa_ro` con `pg_read_all_data`
o grants por tabla). Variable `QA_DB_URL_RO`. Cada consulta realizada se registra en la ejecución.

## 6. Validaciones del kit
```bash
python3 qa/scripts/validate_campaign.py <campaña> --resumen       # contrato, trazabilidad, secretos
python3 qa/scripts/validate_campaign.py <campaña> --estricto      # antes de cerrar una campaña
python3 -m unittest discover -s qa/scripts/tests                  # tests del kit
```
El workflow `.github/workflows/qa-kit.yml` de este repo corre los tests y valida el ejemplo; para los repos de las apps, ver `integracion/github-actions/qa-pr.yml`.
