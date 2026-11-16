#!/usr/bin/env python3
"""Verifica el frontmatter de los agentes QA y de la skill qa-lead, y que las rutas del kit que citan existan."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_common import read_front_matter  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VALID_TOOLS = {"Read", "Write", "Edit", "Grep", "Glob", "Bash", "WebFetch", "WebSearch", "NotebookEdit"}
VALID_MODELS = {"opus", "sonnet", "haiku", "inherit"}
errors = []
files = sorted((ROOT / "agents").glob("qa-*.md")) + [ROOT / "skills" / "qa-lead" / "SKILL.md"]
for f in files:
    rel = f.relative_to(ROOT)
    try:
        meta, body = read_front_matter(f)
    except ValueError as e:
        errors.append(str(e))
        continue
    if not meta.get("name") or not re.match(r"^[a-z0-9-]+$", str(meta["name"])):
        errors.append(f"{rel}: name inválido")
    if f.parent.name == "agents" and meta.get("name") != f.stem:
        errors.append(f"{rel}: name '{meta.get('name')}' debe coincidir con el archivo")
    if not meta.get("description") or len(meta["description"]) < 80:
        errors.append(f"{rel}: description ausente o demasiado corta para enrutar")
    if "tools" in meta:
        bad = {t.strip() for t in str(meta["tools"]).split(",")} - VALID_TOOLS
        if bad:
            errors.append(f"{rel}: herramientas desconocidas {bad}")
    if "model" in meta and meta["model"] not in VALID_MODELS:
        errors.append(f"{rel}: model '{meta['model']}' inválido")
    for ref in set(re.findall(r"(qa/[\w./-]+\.(?:md|yaml|py))", body)):
        if not (ROOT / ref).exists():
            errors.append(f"{rel}: referencia inexistente {ref}")
    if "contrato" not in body:
        errors.append(f"{rel}: no referencia el contrato de coordinación")
for e in errors:
    print("ERROR", e)
print(f"{'FALLA' if errors else 'OK'}: {len(files)} archivos revisados")
sys.exit(1 if errors else 0)
