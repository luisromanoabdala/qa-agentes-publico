"""Utilidades compartidas por los scripts QA (carga de YAML y front matter)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Falta PyYAML: pip install -r qa/scripts/requirements.txt") from exc

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def read_front_matter(path: Path) -> Tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: falta front matter YAML delimitado por '---'")
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"{path}: el front matter debe ser un mapa")
    return meta, m.group(2)


def write_front_matter(path: Path, meta: dict, body: str) -> None:
    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    path.write_text(f"---\n{dumped}\n---\n{body}", encoding="utf-8")


def split_sections(body: str) -> dict:
    """Devuelve {titulo_seccion: contenido} para encabezados '## '."""
    sections: dict = {}
    current = None
    buf: list = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections
