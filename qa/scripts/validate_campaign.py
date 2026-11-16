#!/usr/bin/env python3
"""Valida una carpeta de campaña QA contra el contrato (qa/coordinacion/contrato.md).

Uso:
  python3 qa/scripts/validate_campaign.py <carpeta> [--resumen] [--json] [--estricto]

Salida: errores (rompen el contrato, exit 1), advertencias (revisar) y, con --resumen, la
matriz de trazabilidad/cobertura calculada SOLO a partir de los archivos.
--estricto convierte advertencias en errores (útil en CI antes de cerrar una campaña).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_common import load_yaml, read_front_matter  # noqa: E402

ID_PATTERNS = {
    "riesgo": re.compile(r"^RSK-\d{3,}$"),
    "caso": re.compile(r"^TC-[A-Z]{2,6}-\d{3,}$"),
    "ejecucion": re.compile(r"^EXE-\d{8}-\d{3,}$"),
    "hallazgo": re.compile(r"^HAL-\d{3,}$"),
    "bug": re.compile(r"^BUGD-\d{3,}$"),
    "bloqueo": re.compile(r"^BLK-\d{3,}$"),
}
EXEC_STATES = {"aprobado", "fallido", "bloqueado", "omitido"}
FAIL_CLASSES = {"producto", "infraestructura", "datos", "script", "indeterminado"}
CONFIRMATION = {"estatico", "hipotesis", "reproducido", "bloqueado", "descartado"}
LEVELS = {"unitario", "componente", "integracion", "contrato", "e2e", "exploratorio"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
SEVERITIES = {"Crítica", "Mayor", "Menor", "Trivial"}
JIRA_STATES = {"borrador", "listo", "creado", "duplicado", "descartado"}
FASES = {"requisitos", "diseno", "desarrollo_pr", "integracion_qa", "prelanzamiento", "posdespliegue"}
REQUIRED_BUG_SECTIONS = ["Descripción", "Datos de prueba", "Pasos de reproducción",
                         "Resultado actual", "Resultado esperado", "Evidencia", "Observaciones"]
ISO_TZ = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
JIRA_KEY = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")

SECRET_PATTERNS = [
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Bearer literal", re.compile(r"Bearer\s+(?!\$|<|\{\{|\.\.\.)[A-Za-z0-9._~+/=-]{16,}")),
    ("Clave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Stripe/clave live", re.compile(r"\b(sk|rk)_live_[A-Za-z0-9]{10,}")),
    ("Atlassian token", re.compile(r"ATATT[A-Za-z0-9_\-=]{20,}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("Password literal", re.compile(
        r"(?i)\b(password|passwd|contraseña|clave|secret|api[_-]?key|token)\b\s*[:=]\s*[\"']?"
        r"(?!\$|<|\{\{|null\b|none\b|REDACTED|\*{3,}|QA_|env\b|\"\"|''|ver\b)[^\s\"'#,]{6,}")),
]
SYNTHETIC_EMAIL = re.compile(r"@(example\.(com|org|net|test)|[a-z0-9.-]+\.test|[a-z0-9.-]+\.invalid|[a-z0-9.-]+\.local|"
                             r"[a-z0-9.-]+\.example|mailinator\.com)$", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ALLOWED_EMAIL_ALWAYS = re.compile(r"^(noreply@anthropic\.com)$", re.I)
TEXT_EXT = {".md", ".yaml", ".yml", ".json", ".txt", ".har", ".log", ".csv", ".ts", ".js", ".sh"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _load(path: Path, rep: Report, key: str, required: bool = True):
    if not path.exists():
        if required:
            rep.err(path.name, "archivo obligatorio ausente")
        return []
    try:
        data = load_yaml(path) or {}
    except Exception as exc:  # noqa: BLE001
        rep.err(path.name, f"YAML inválido: {exc}")
        return []
    items = data.get(key) if isinstance(data, dict) else None
    if items is None:
        rep.err(path.name, f"falta la clave raíz '{key}'")
        return []
    if not isinstance(items, list):
        rep.err(path.name, f"'{key}' debe ser una lista")
        return []
    return items


def _check_ids(items, kind, src, rep, seen):
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            rep.err(src, f"elemento #{i} no es un mapa")
            continue
        _id = it.get("id")
        if not _id or not ID_PATTERNS[kind].match(str(_id)):
            rep.err(src, f"ID inválido '{_id}' (formato {ID_PATTERNS[kind].pattern})")
            continue
        if _id in seen:
            rep.err(src, f"ID duplicado {_id} (también en {seen[_id]})")
        seen[_id] = src


def validate(folder: Path):
    rep = Report()
    seen: dict = {}
    camp_path = folder / "campania.yaml"
    camp = {}
    if not camp_path.exists():
        rep.err("campania.yaml", "archivo obligatorio ausente")
    else:
        try:
            camp = load_yaml(camp_path) or {}
        except Exception as exc:  # noqa: BLE001
            rep.err("campania.yaml", f"YAML inválido: {exc}")
    meta = camp.get("campania") or {}
    for k in ("id", "nombre", "estado", "fase", "objetivo", "zona_horaria"):
        if not meta.get(k):
            rep.err("campania.yaml", f"campania.{k} es obligatorio")
    if meta.get("fase") and meta["fase"] not in FASES:
        rep.err("campania.yaml", f"fase '{meta['fase']}' no válida ({sorted(FASES)})")
    estado_camp = meta.get("estado")
    is_example = bool(meta.get("ejemplo"))
    autoriz = camp.get("autorizaciones") or {}
    ambiente = camp.get("ambiente") or {}
    if ambiente.get("es_produccion") and any(autoriz.get(k) for k in ("eliminar_datos", "pruebas_destructivas", "pruebas_carga")):
        rep.warn("campania.yaml", "autorizaciones destructivas/carga sobre PRODUCCIÓN: confirmar que hay autorización escrita")
    req_ids = {str(r.get("id")) for r in as_list(camp.get("requisitos")) if isinstance(r, dict) and r.get("id")}
    bloqueos = as_list(camp.get("bloqueos"))
    _check_ids(bloqueos, "bloqueo", "campania.yaml", rep, seen)
    blk_ids = {b.get("id") for b in bloqueos if isinstance(b, dict)}
    for r in as_list(camp.get("roles")):
        if isinstance(r, dict):
            for k in ("env_email", "env_password"):
                v = r.get(k)
                if v and not re.match(r"^[A-Z][A-Z0-9_]+$", str(v)):
                    rep.err("campania.yaml", f"roles.{r.get('nombre')}.{k} debe ser NOMBRE de variable de entorno, no un valor")
    bugs_proj = ((camp.get("destinos") or {}).get("bugs") or {}).get("proyecto")

    # Riesgos
    riesgos = _load(folder / "riesgos.yaml", rep, "riesgos", required=estado_camp != "preparacion")
    _check_ids(riesgos, "riesgo", "riesgos.yaml", rep, seen)
    rsk = {r["id"]: r for r in riesgos if isinstance(r, dict) and r.get("id")}
    for r in rsk.values():
        p, i, n = r.get("probabilidad"), r.get("impacto"), r.get("nivel")
        if not all(isinstance(x, int) and 1 <= x <= 3 for x in (p, i)):
            rep.err("riesgos.yaml", f"{r['id']}: probabilidad/impacto deben ser 1..3")
        elif n != p * i:
            rep.err("riesgos.yaml", f"{r['id']}: nivel {n} != probabilidad x impacto ({p * i})")
        if r.get("tipo") not in ("hecho", "hipotesis"):
            rep.err("riesgos.yaml", f"{r['id']}: tipo debe ser 'hecho' o 'hipotesis'")
        for q in as_list(r.get("requisitos")):
            if str(q) not in req_ids:
                rep.err("riesgos.yaml", f"{r['id']}: requisito {q} no existe en campania.yaml")

    # Casos
    casos = {}
    casos_dir = folder / "casos"
    case_files = sorted(p for p in casos_dir.glob("*.yaml") if not p.name.startswith("_")) if casos_dir.exists() else []
    for cf in case_files:
        items = _load(cf, rep, "casos")
        src = f"casos/{cf.name}"
        _check_ids(items, "caso", src, rep, seen)
        for c in items:
            if not isinstance(c, dict) or not c.get("id"):
                continue
            casos[c["id"]] = c
            for k in ("titulo", "objetivo", "nivel", "tipo", "prioridad", "esperado"):
                if not c.get(k):
                    rep.err(src, f"{c['id']}: falta '{k}'")
            if c.get("nivel") and c["nivel"] not in LEVELS:
                rep.err(src, f"{c['id']}: nivel '{c['nivel']}' no válido")
            if c.get("nivel") != "exploratorio" and not as_list(c.get("pasos")):
                rep.err(src, f"{c['id']}: faltan pasos")
            if c.get("nivel") != "exploratorio" and not c.get("fuente_esperado"):
                rep.warn(src, f"{c['id']}: sin fuente_esperado (¿de dónde sale el resultado esperado?)")
            reqs, rks = as_list(c.get("requisitos")), as_list(c.get("riesgos"))
            if not reqs and not rks:
                rep.err(src, f"{c['id']}: debe referenciar ≥1 requisito o riesgo")
            for q in reqs:
                if str(q) not in req_ids:
                    rep.err(src, f"{c['id']}: requisito {q} no existe en campania.yaml")
            for k in rks:
                if k not in rsk:
                    rep.err(src, f"{c['id']}: riesgo {k} no existe")
            auto = c.get("automatizacion") or {}
            if auto.get("estado") == "implementada" and not auto.get("ref"):
                rep.err(src, f"{c['id']}: automatización 'implementada' sin ref")

    # Ejecuciones
    ejecs = _load(folder / "ejecuciones.yaml", rep, "ejecuciones", required=estado_camp != "preparacion")
    _check_ids(ejecs, "ejecucion", "ejecuciones.yaml", rep, seen)
    exe = {e["id"]: e for e in ejecs if isinstance(e, dict) and e.get("id")}
    for e in exe.values():
        w = "ejecuciones.yaml"
        eid = e["id"]
        if e.get("caso") not in casos:
            rep.err(w, f"{eid}: caso {e.get('caso')} no existe")
        st = e.get("estado")
        if st not in EXEC_STATES:
            rep.err(w, f"{eid}: estado '{st}' inválido ({sorted(EXEC_STATES)})")
            continue
        fh = str(e.get("fecha_hora") or "")
        if not ISO_TZ.match(fh):
            rep.err(w, f"{eid}: fecha_hora debe ser ISO 8601 con zona (p. ej. 2026-11-04T10:15:00-03:00)")
        elif eid[4:12] != fh[:10].replace("-", ""):
            rep.warn(w, f"{eid}: la fecha del ID no coincide con fecha_hora")
        for k in ("ambiente", "ejecutor", "modo"):
            if not e.get(k):
                rep.err(w, f"{eid}: falta '{k}'")
        if not e.get("version_build"):
            rep.err(w, f"{eid}: version_build obligatorio (usar 'No verificada' si no se pudo verificar)")
        if st in ("aprobado", "fallido"):
            if not e.get("resultado_observado"):
                rep.err(w, f"{eid}: falta resultado_observado")
            if not as_list(e.get("evidencias")):
                (rep.err if st == "fallido" else rep.warn)(w, f"{eid}: {st} sin evidencias")
        if st == "fallido":
            cls = e.get("clasificacion_fallo")
            if cls not in FAIL_CLASSES:
                rep.err(w, f"{eid}: fallido requiere clasificacion_fallo en {sorted(FAIL_CLASSES)}")
        elif e.get("clasificacion_fallo"):
            rep.err(w, f"{eid}: clasificacion_fallo solo aplica a 'fallido'")
        if st == "bloqueado" and e.get("bloqueo") not in blk_ids:
            rep.err(w, f"{eid}: bloqueado requiere 'bloqueo' con un BLK existente en campania.yaml")
        if st == "omitido" and not e.get("motivo_omision"):
            rep.err(w, f"{eid}: omitido requiere motivo_omision")
        intentos, exitos = e.get("intentos", 1), e.get("exitos")
        if isinstance(intentos, int) and intentos > 1 and st == "aprobado" and not e.get("inestable"):
            rep.err(w, f"{eid}: aprobado tras {intentos} intentos sin marcar inestable: true (no ocultar reintentos)")
        if isinstance(intentos, int) and isinstance(exitos, int) and exitos > intentos:
            rep.err(w, f"{eid}: exitos > intentos")
        if e.get("retest_de") and e["retest_de"] not in exe:
            rep.err(w, f"{eid}: retest_de {e['retest_de']} no existe")
        for ev in as_list(e.get("evidencias")):
            if not re.match(r"^(https?://)", str(ev)) and not (folder / str(ev)).exists():
                rep.err(w, f"{eid}: evidencia '{ev}' no existe en la carpeta")
            if "evidencias/raw/" in str(ev):
                rep.err(w, f"{eid}: no referenciar evidencia sin sanitizar (evidencias/raw/)")
        if e.get("bug") and not ID_PATTERNS["bug"].match(str(e["bug"])):
            rep.err(w, f"{eid}: bug debe ser un BUGD-NNN")

    # Hallazgos
    hals = _load(folder / "hallazgos.yaml", rep, "hallazgos", required=estado_camp != "preparacion")
    _check_ids(hals, "hallazgo", "hallazgos.yaml", rep, seen)
    hal = {h["id"]: h for h in hals if isinstance(h, dict) and h.get("id")}
    for h in hal.values():
        w, hid, c = "hallazgos.yaml", h["id"], h.get("confirmacion")
        if c not in CONFIRMATION:
            rep.err(w, f"{hid}: confirmacion '{c}' inválida ({sorted(CONFIRMATION)})")
            continue
        for k in ("titulo", "origen", "detectado_por", "fecha"):
            if not h.get(k):
                rep.err(w, f"{hid}: falta '{k}'")
        if c in ("estatico", "hipotesis") and not h.get("como_verificar"):
            rep.err(w, f"{hid}: {c} requiere 'como_verificar'")
        if c == "reproducido":
            prod_fails = [x for x in as_list(h.get("ejecuciones"))
                          if exe.get(x, {}).get("estado") == "fallido" and exe[x].get("clasificacion_fallo") == "producto"]
            if not prod_fails:
                rep.err(w, f"{hid}: 'reproducido' requiere ≥1 ejecución fallida clasificada 'producto'")
        for x in as_list(h.get("ejecuciones")):
            if x not in exe:
                rep.err(w, f"{hid}: ejecución {x} no existe")
        if c == "bloqueado" and h.get("bloqueo") not in blk_ids:
            rep.err(w, f"{hid}: 'bloqueado' requiere un BLK existente")
        if c == "descartado" and not h.get("motivo"):
            rep.err(w, f"{hid}: 'descartado' requiere motivo")
        if h.get("bug") and c != "reproducido":
            rep.err(w, f"{hid}: solo un hallazgo 'reproducido' puede tener bug (está '{c}')")
        for k in as_list(h.get("riesgos")):
            if k not in rsk:
                rep.err(w, f"{hid}: riesgo {k} no existe")

    # Bugs
    bugs = {}
    bdir = folder / "bugs"
    for bf in sorted(bdir.glob("*.md")) if bdir.exists() else []:
        if bf.name.startswith("_"):
            continue
        src = f"bugs/{bf.name}"
        try:
            b, body = read_front_matter(bf)
        except Exception as exc:  # noqa: BLE001
            rep.err(src, str(exc))
            continue
        _check_ids([b], "bug", src, rep, seen)
        bid = b.get("id")
        bugs[bid] = b
        if bf.stem != bid:
            rep.err(src, f"el nombre del archivo debe ser {bid}.md")
        t = str(b.get("titulo") or "")
        if not re.match(r"^\[[^\]]+\]\s+\S.{10,}", t):
            rep.err(src, "titulo debe seguir '[Módulo] Falla observada bajo condición'")
        if re.search(r"\b[A-Z][A-Z0-9]+-\d+\b", t):
            rep.warn(src, "el título parece contener una clave de issue: Jira asigna la clave, no va en el título")
        if b.get("prioridad") not in PRIORITIES:
            rep.err(src, f"prioridad debe ser {sorted(PRIORITIES)}")
        if b.get("severidad") not in SEVERITIES:
            rep.err(src, f"severidad debe ser {sorted(SEVERITIES)}")
        fd = str(b.get("fecha_deteccion") or "")
        if not DATE.match(fd):
            rep.err(src, "fecha_deteccion debe ser AAAA-MM-DD")
        else:
            try:
                d = dt.date.fromisoformat(fd)
                if d > dt.date.today() + dt.timedelta(days=1):
                    rep.err(src, "fecha_deteccion en el futuro")
            except ValueError:
                rep.err(src, "fecha_deteccion inválida")
        for k in ("entorno", "version", "modulo"):
            if not b.get(k):
                rep.err(src, f"falta '{k}' (version: usar 'No verificada' si no se conoce)")
        ex_ids = as_list(b.get("ejecuciones"))
        prod = [x for x in ex_ids if exe.get(x, {}).get("estado") == "fallido" and exe[x].get("clasificacion_fallo") == "producto"]
        if not prod:
            rep.err(src, "debe referenciar ≥1 ejecución fallida clasificada 'producto'")
        for x in ex_ids:
            if x not in exe:
                rep.err(src, f"ejecución {x} no existe")
        if fd and prod and not any(str(exe[x].get("fecha_hora", ""))[:10] == fd for x in prod):
            rep.warn(src, "fecha_deteccion no coincide con ninguna ejecución que lo reprodujo")
        if b.get("hallazgo"):
            hh = hal.get(b["hallazgo"])
            if not hh:
                rep.err(src, f"hallazgo {b['hallazgo']} no existe")
            elif hh.get("confirmacion") != "reproducido":
                rep.err(src, f"hallazgo {b['hallazgo']} no está 'reproducido'")
        if b.get("caso") and b["caso"] not in casos:
            rep.err(src, f"caso {b['caso']} no existe")
        evs = as_list(b.get("evidencias"))
        if not evs:
            rep.err(src, "sin evidencias")
        for ev in evs:
            if not re.match(r"^https?://", str(ev)) and not (folder / str(ev)).exists():
                rep.err(src, f"evidencia '{ev}' no existe")
        from qa_common import split_sections
        secs = split_sections(body)
        for s in REQUIRED_BUG_SECTIONS:
            if not secs.get(s) or secs[s].strip() in ("...", "[...]"):
                rep.err(src, f"sección '## {s}' ausente o vacía")
        if secs.get("Pasos de reproducción") and not re.search(r"^\s*1\.", secs["Pasos de reproducción"], re.M):
            rep.err(src, "pasos de reproducción deben estar numerados")
        esp = secs.get("Resultado esperado", "")
        if esp and not re.search(r"(?i)fuente", esp):
            rep.err(src, "resultado esperado debe citar su 'Fuente:'")
        if re.search(r"(?i)```sql", body):
            ex_with_db = any("db" in str(exe.get(x, {}).get("modo", "")) or "sql" in json.dumps(exe.get(x, {}), ensure_ascii=False).lower() for x in ex_ids)
            if not ex_with_db:
                rep.warn(src, "incluye SQL: confirmar que la base fue consultada realmente (registrarlo en la ejecución)")
        j = b.get("jira") or {}
        js = j.get("estado")
        if js not in JIRA_STATES:
            rep.err(src, f"jira.estado debe ser {sorted(JIRA_STATES)}")
        if js == "creado":
            if not (j.get("key") and JIRA_KEY.match(str(j["key"])) and str(j.get("url", "")).startswith("http")):
                rep.err(src, "jira.estado=creado requiere key y url devueltas por Jira")
            if is_example:
                rep.err(src, "un ejemplo no puede tener bugs 'creado' en Jira")
        elif j.get("key"):
            rep.err(src, f"jira.key presente con estado '{js}': las claves solo existen tras crear el issue")
        if js == "duplicado" and not j.get("duplicado_de"):
            rep.err(src, "jira.estado=duplicado requiere duplicado_de")
        if js in ("listo", "creado") and not (j.get("proyecto") or bugs_proj):
            rep.err(src, "falta el proyecto Jira (campania.yaml → destinos.bugs.proyecto)")

    # Bloqueos referenciados
    for b in bloqueos:
        if isinstance(b, dict):
            for k in ("descripcion", "necesita", "estado"):
                if not b.get(k):
                    rep.err("campania.yaml", f"{b.get('id')}: falta '{k}'")
            for ref in as_list(b.get("impacta")):
                if ref not in casos and ref not in rsk and ref not in hal and str(ref) not in req_ids:
                    rep.warn("campania.yaml", f"{b.get('id')}: impacta '{ref}' que no existe")

    # Cobertura de riesgos
    cases_by_risk = defaultdict(list)
    for c in casos.values():
        if c.get("estado", "activo") != "obsoleto":
            for k in as_list(c.get("riesgos")):
                cases_by_risk[k].append(c["id"])
    for r in rsk.values():
        if r.get("prioridad") == "alta" and not cases_by_risk.get(r["id"]) and estado_camp != "preparacion":
            rep.warn("riesgos.yaml", f"{r['id']} (alta) sin casos asociados")

    # Escaneo de secretos y PII
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or "raw" in p.relative_to(folder).parts or p.suffix.lower() not in TEXT_EXT:
            continue
        rel = str(p.relative_to(folder))
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for name, rx in SECRET_PATTERNS:
                if rx.search(line):
                    rep.err(rel, f"línea {n}: posible secreto ({name}). Usar $VARIABLE o <REDACTED>")
            for em in EMAIL.findall(line):
                if not SYNTHETIC_EMAIL.search(em) and not ALLOWED_EMAIL_ALWAYS.match(em):
                    rep.warn(rel, f"línea {n}: email no sintético '{em}' — usar @example.test o variable")

    summary = build_summary(camp, rsk, casos, exe, hal, bugs, bloqueos, cases_by_risk)
    return rep, summary


def build_summary(camp, rsk, casos, exe, hal, bugs, bloqueos, cases_by_risk):
    last_by_case = {}
    for e in sorted(exe.values(), key=lambda x: str(x.get("fecha_hora", ""))):
        last_by_case[e.get("caso")] = e
    exec_states = Counter(e.get("estado") for e in exe.values())
    by_risk = []
    for rid, r in sorted(rsk.items()):
        cs = cases_by_risk.get(rid, [])
        st = Counter(last_by_case[c]["estado"] for c in cs if c in last_by_case)
        by_risk.append({
            "riesgo": rid, "prioridad": r.get("prioridad"), "casos": len(cs),
            "ejecutados": sum(st.values()), "aprobados": st.get("aprobado", 0),
            "fallidos": st.get("fallido", 0), "bloqueados": st.get("bloqueado", 0),
            "omitidos": st.get("omitido", 0), "sin_ejecutar": len([c for c in cs if c not in last_by_case]),
        })
    return {
        "campania": (camp.get("campania") or {}).get("id"),
        "ejemplo": bool((camp.get("campania") or {}).get("ejemplo")),
        "casos_activos": len([c for c in casos.values() if c.get("estado", "activo") != "obsoleto"]),
        "casos_sin_ejecutar": sorted(c for c in casos if c not in last_by_case and casos[c].get("estado", "activo") != "obsoleto"),
        "ejecuciones": dict(exec_states),
        "ejecuciones_inestables": sorted(e["id"] for e in exe.values() if e.get("inestable")),
        "hallazgos_por_confirmacion": dict(Counter(h.get("confirmacion") for h in hal.values())),
        "bugs": [{"id": k, "estado_jira": (v.get("jira") or {}).get("estado"), "key": (v.get("jira") or {}).get("key"),
                  "prioridad": v.get("prioridad"), "severidad": v.get("severidad")} for k, v in sorted(bugs.items())],
        "bloqueos_abiertos": sorted(b.get("id") for b in bloqueos if isinstance(b, dict) and b.get("estado") == "abierto"),
        "cobertura_por_riesgo": by_risk,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta", type=Path)
    ap.add_argument("--resumen", action="store_true", help="imprime cobertura y trazabilidad")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--estricto", action="store_true", help="advertencias = errores")
    a = ap.parse_args(argv)
    if not a.carpeta.is_dir():
        print(f"No existe la carpeta {a.carpeta}", file=sys.stderr)
        return 2
    rep, summary = validate(a.carpeta)
    failed = bool(rep.errors) or (a.estricto and bool(rep.warnings))
    if a.json:
        print(json.dumps({"ok": not failed, "errores": rep.errors, "advertencias": rep.warnings,
                          "resumen": summary}, ensure_ascii=False, indent=2))
        return 1 if failed else 0
    for e in rep.errors:
        print(f"ERROR  {e}")
    for w in rep.warnings:
        print(f"AVISO  {w}")
    if a.resumen:
        print("\n== Resumen (calculado desde los archivos) ==")
        if summary["ejemplo"]:
            print("** CAMPAÑA DE EJEMPLO — datos ficticios **")
        print(f"Casos activos: {summary['casos_activos']} | sin ejecutar: {len(summary['casos_sin_ejecutar'])}")
        print(f"Ejecuciones: {summary['ejecuciones']} | inestables: {summary['ejecuciones_inestables']}")
        print(f"Hallazgos: {summary['hallazgos_por_confirmacion']}")
        print(f"Bloqueos abiertos: {summary['bloqueos_abiertos']}")
        print("Bugs:")
        for b in summary["bugs"]:
            print(f"  {b['id']}  {b['prioridad']}/{b['severidad']}  jira={b['estado_jira']} {b['key'] or ''}")
        print("\n| Riesgo | Prio | Casos | Ejecutados | OK | Falla | Bloq | Sin ejecutar |")
        print("|---|---|---|---|---|---|---|---|")
        for r in summary["cobertura_por_riesgo"]:
            print(f"| {r['riesgo']} | {r['prioridad']} | {r['casos']} | {r['ejecutados']} | {r['aprobados']} | "
                  f"{r['fallidos']} | {r['bloqueados']} | {r['sin_ejecutar']} |")
    print(f"\n{'FALLA' if failed else 'OK'}: {len(rep.errors)} errores, {len(rep.warnings)} advertencias")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
