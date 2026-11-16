#!/usr/bin/env python3
"""Crea una carpeta de campaña a partir de qa/plantillas/campania.

Uso:
  python3 qa/scripts/new_campaign.py <destino> --id C01 --nombre "Smoke agenda" [--fase integracion_qa]
Ejemplo:
  python3 qa/scripts/new_campaign.py .qa/campanias/C01-smoke-agenda --id C01 --nombre "Smoke agenda"
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_common import load_yaml  # noqa: E402

import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "plantillas" / "campania"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("destino", type=Path)
    ap.add_argument("--id", required=True)
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--fase", default="integracion_qa")
    ap.add_argument("--objetivo", default="Pendiente de definir con el QA Lead")
    a = ap.parse_args(argv)
    if a.destino.exists() and any(a.destino.iterdir()):
        print(f"{a.destino} ya existe y no está vacía; no se sobrescribe.", file=sys.stderr)
        return 1
    shutil.copytree(TEMPLATE, a.destino, dirs_exist_ok=True)
    camp_path = a.destino / "campania.yaml"
    header = "".join(l for l in camp_path.read_text(encoding="utf-8").splitlines(True) if l.startswith("#"))
    data = load_yaml(camp_path)
    data["campania"].update({"id": a.id, "nombre": a.nombre, "fase": a.fase, "objetivo": a.objetivo,
                             "inicio": dt.date.today().isoformat()})
    camp_path.write_text(header + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    # riesgos de la plantilla son de ejemplo: se dejan vacíos
    (a.destino / "riesgos.yaml").write_text("riesgos: []\n", encoding="utf-8")
    (a.destino / "evidencias" / "raw").mkdir(parents=True, exist_ok=True)
    print(f"Campaña creada en {a.destino}. Próximo paso: completar campania.yaml y correr validate_campaign.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
