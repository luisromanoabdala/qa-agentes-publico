#!/usr/bin/env bash
# Instala el equipo de agentes QA para Claude Code.
#
#   ./integracion/instalar.sh                 # para tu usuario (~/.claude): disponible en todos tus repos
#   ./integracion/instalar.sh --repo ../mi-app # dentro de un repo (.claude/ del repo): lo usa todo el equipo de ese repo
#
# No toca credenciales ni configura Jira: eso se hace con variables de entorno (ver README).
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HOME/.claude"
if [[ "${1:-}" == "--repo" ]]; then
  [[ -n "${2:-}" && -d "$2" ]] || { echo "Uso: $0 --repo <ruta-al-repo>"; exit 1; }
  DEST="$(cd "$2" && pwd)/.claude"
fi

mkdir -p "$DEST/agents" "$DEST/skills"
cp "$KIT"/agents/qa-*.md "$DEST/agents/"
rm -rf "$DEST/skills/qa-lead" && cp -R "$KIT/skills/qa-lead" "$DEST/skills/"
echo "✔ Agentes QA y orquestador qa-lead copiados a $DEST"

if command -v python3 >/dev/null; then
  python3 -m pip install --quiet --user -r "$KIT/qa/scripts/requirements.txt" 2>/dev/null \
    || python3 -m pip install --quiet --break-system-packages -r "$KIT/qa/scripts/requirements.txt" 2>/dev/null \
    || echo "⚠ Instalá PyYAML a mano: python3 -m pip install -r $KIT/qa/scripts/requirements.txt"
  python3 -m unittest discover -s "$KIT/qa/scripts/tests" >/dev/null 2>&1 \
    && echo "✔ Scripts QA verificados (22 tests)" \
    || echo "⚠ Los tests de los scripts no pasaron: corré python3 -m unittest discover -s $KIT/qa/scripts/tests -v"
else
  echo "⚠ Falta python3 (necesario para el validador y el reporte a Jira)"
fi

cat <<EOF

Último paso: agregá esta línea a tu ~/.zshrc o ~/.bashrc para que los agentes encuentren el kit:
  export QA_KIT="$KIT"
EOF
