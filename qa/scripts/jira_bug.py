#!/usr/bin/env python3
"""Registro de bugs en Jira con mapeo dinámico de campos, sin inventar campos ni valores.

Credenciales SOLO por entorno:
  JIRA_BASE_URL   p. ej. https://<sitio>.atlassian.net
  JIRA_EMAIL + JIRA_API_TOKEN   (Jira Cloud, Basic)   |   JIRA_PAT (Server/Data Center, Bearer)

Subcomandos:
  discover        --project KEY [--issuetype Bug] --out jira-meta.json
                  Consulta tipos de issue, campos (requeridos/editables) y valores permitidos.
  suggest-mapping --meta jira-meta.json
                  Propone un jira-mapping.yaml a partir de los nombres de campos (para revisar).
  check-mapping   --meta jira-meta.json --mapping jira-mapping.yaml
                  Verifica que cada campo/valor del mapeo exista y que los requeridos estén cubiertos.
  payload         --bug bugs/BUGD-001.md --mapping ... --meta ... [--campaign DIR]
                  Arma el payload (dry-run, no llama a Jira).
  duplicates      --bug ... --mapping ...
                  Busca duplicados (huella del bug y JQL por texto del título).
  attach          --campaign DIR [--bug bugs/BUGD-001.md]
                  Sube a Jira las evidencias (archivos locales) de los bugs ya creados (jira.key),
                  sin repetir adjuntos que ya existan con el mismo nombre.
  create          --bug ... --mapping ... --meta ... [--campaign DIR] [--allow-similar]
                  Verifica duplicados, crea el issue, comprueba con GET, adjunta evidencias,
                  y escribe key/url en el bug. Ante respuesta incierta, busca por huella antes de reintentar.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_common import load_yaml, read_front_matter, split_sections, write_front_matter  # noqa: E402

import yaml  # noqa: E402

LOGICAL_FIELDS = ["prioridad", "severidad", "entorno", "version", "fecha_deteccion", "modulo", "etiquetas"]
LABELS_HUMAN = {"prioridad": "Prioridad", "severidad": "Severidad", "fecha_deteccion": "Fecha de detección",
                "entorno": "Entorno", "version": "Versión", "modulo": "Módulo", "issue_origen": "Issue de origen"}
NAME_HINTS = {
    "prioridad": [r"^priority$", r"prioridad"],
    "severidad": [r"severi"],
    "entorno": [r"^environment$", r"entorno", r"ambiente"],
    "version": [r"^versions$", r"affects? version", r"versi[oó]n", r"build"],
    "fecha_deteccion": [r"detec", r"found date", r"fecha"],
    "modulo": [r"^components$", r"componente", r"m[oó]dulo"],
    "etiquetas": [r"^labels$"],
}
BODY_ORDER = ["Descripción", "Clasificación y contexto", "Datos de prueba", "Pasos de reproducción",
              "Resultado actual", "Resultado esperado", "Evidencia", "Observaciones"]


def load_env_file():
    """Carga variables desde $QA_ENV_FILE o <raíz del kit>/.env.qa si existen, sin pisar las ya definidas.
    El archivo está ignorado por Git; nunca se imprime su contenido."""
    candidates = [os.environ.get("QA_ENV_FILE"), str(Path(__file__).resolve().parents[2] / ".env.qa")]
    for c in candidates:
        if c and Path(c).expanduser().is_file():
            for line in Path(c).expanduser().read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip().removeprefix("export ").strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
            return c
    return None


class JiraError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status, self.body = status, body


class Uncertain(Exception):
    """La operación pudo o no haberse aplicado (timeout, 5xx, conexión cortada)."""


# ------------------------------------------------------------------ cliente HTTP
class Jira:
    def __init__(self, base=None, api_version=3, timeout=30):
        self.base = (base or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
        if not self.base:
            raise SystemExit("Falta JIRA_BASE_URL en el entorno")
        self.api = f"/rest/api/{api_version}"
        self.api_version = api_version
        self.timeout = timeout
        if os.environ.get("JIRA_PAT"):
            self.auth = f"Bearer {os.environ['JIRA_PAT']}"
        elif os.environ.get("JIRA_EMAIL") and os.environ.get("JIRA_API_TOKEN"):
            raw = f"{os.environ['JIRA_EMAIL']}:{os.environ['JIRA_API_TOKEN']}".encode()
            self.auth = "Basic " + base64.b64encode(raw).decode()
        else:
            raise SystemExit("Faltan credenciales: JIRA_EMAIL + JIRA_API_TOKEN, o JIRA_PAT")

    def req(self, method, path, body=None, headers=None, raw=None):
        url = self.base + path
        h = {"Authorization": self.auth, "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        if raw is not None:
            data = raw
        h.update(headers or {})
        r = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, timeout=self.timeout) as resp:
                txt = resp.read().decode() or "null"
                return json.loads(txt)
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="ignore")
            if e.code >= 500:
                raise Uncertain(f"HTTP {e.code}: {txt[:300]}") from e
            raise JiraError(e.code, txt) from e
        except (socket.timeout, TimeoutError, urllib.error.URLError, ConnectionError) as e:
            raise Uncertain(str(e)) from e

    def search(self, jql, fields=("summary", "status"), max_results=20):
        q = urllib.parse.urlencode({"jql": jql, "fields": ",".join(fields), "maxResults": max_results})
        # Jira Cloud migró a /search/jql; Server/DC usa /search
        try:
            res = self.req("GET", f"{self.api}/search/jql?{q}")
        except JiraError as e:
            if e.status not in (404, 405, 410):
                raise
            res = self.req("GET", f"{self.api}/search?{q}")
        return res.get("issues", [])


# ------------------------------------------------------------------ discover / mapping
def discover(j: Jira, project, issuetype="Bug"):
    proj = j.req("GET", f"{j.api}/project/{urllib.parse.quote(project)}")
    its = j.req("GET", f"{j.api}/issue/createmeta/{urllib.parse.quote(project)}/issuetypes")
    types = its.get("issueTypes") or its.get("values") or []
    it = next((t for t in types if t.get("name", "").lower() == issuetype.lower()), None)
    if not it:
        raise SystemExit(f"El proyecto {project} no tiene el tipo '{issuetype}'. Disponibles: {[t.get('name') for t in types]}")
    fields_res = j.req("GET", f"{j.api}/issue/createmeta/{urllib.parse.quote(project)}/issuetypes/{it['id']}?maxResults=200")
    fields = fields_res.get("fields") or fields_res.get("values") or []
    out_fields = {}
    for f in fields:
        fid = f.get("fieldId") or f.get("key")
        out_fields[fid] = {
            "nombre": f.get("name"),
            "requerido": bool(f.get("required")),
            "tiene_default": bool(f.get("hasDefaultValue")),
            "schema": f.get("schema", {}),
            "operaciones": f.get("operations", []),
            "valores_permitidos": [v.get("name") or v.get("value") for v in f.get("allowedValues", []) or []
                                   if (v.get("name") or v.get("value"))],
        }
    link_types = []
    try:
        link_types = [lt["name"] for lt in j.req("GET", f"{j.api}/issueLinkType").get("issueLinkTypes", [])]
    except (JiraError, Uncertain):
        pass
    return {"proyecto": {"key": proj.get("key"), "id": proj.get("id"), "nombre": proj.get("name")},
            "tipo_issue": {"id": it["id"], "nombre": it["name"]},
            "campos": out_fields, "tipos_vinculo": link_types, "api_version": j.api_version,
            "base_url": j.base}


def suggest_mapping(meta):
    campos = meta["campos"]
    mapping = {"proyecto": meta["proyecto"]["key"], "tipo_issue": meta["tipo_issue"]["nombre"],
               "api_version": meta.get("api_version", 3), "campos": {}, "issue_origen": {"tipo_vinculo": None},
               "adjuntar_evidencias": "attachment" in campos, "etiquetas_fijas": ["qa-agentico"]}
    for logical, pats in NAME_HINTS.items():
        found = None
        for fid, f in campos.items():
            if any(re.search(p, fid, re.I) or re.search(p, f.get("nombre") or "", re.I) for p in pats):
                found = (fid, f)
                break
        entry = {"jira_field": found[0] if found else None}
        if found and found[1]["valores_permitidos"]:
            entry["valores"] = {}
            entry["_opciones_reales"] = found[1]["valores_permitidos"]
        mapping["campos"][logical] = entry
    for lt in meta.get("tipos_vinculo", []):
        if lt.lower() in ("relates", "relaciona", "relacionado"):
            mapping["issue_origen"]["tipo_vinculo"] = lt
    mapping["_requeridos_en_jira"] = [fid for fid, f in campos.items() if f["requerido"] and not f["tiene_default"]]
    mapping["_nota"] = ("PROPUESTA automática: confirmar cada jira_field y completar 'valores' usando SOLO "
                        "'_opciones_reales'. Borrar claves que empiezan con '_' al confirmar.")
    return mapping


STANDARD_FIELDS = {"summary", "description", "project", "issuetype"}
STANDARD_VALUES = {"prioridad": ["P0", "P1", "P2", "P3"], "severidad": ["Crítica", "Mayor", "Menor", "Trivial"]}


def check_mapping(meta, mapping):
    errors, warnings = [], []
    campos = meta["campos"]
    if mapping.get("proyecto") and mapping["proyecto"] != meta["proyecto"]["key"]:
        errors.append(f"mapping.proyecto={mapping['proyecto']} pero meta es de {meta['proyecto']['key']}")
    if (mapping.get("tipo_issue") or "").lower() != meta["tipo_issue"]["nombre"].lower():
        errors.append(f"tipo_issue '{mapping.get('tipo_issue')}' no coincide con meta '{meta['tipo_issue']['nombre']}'")
    covered = set(STANDARD_FIELDS)
    for logical, cfg in (mapping.get("campos") or {}).items():
        if logical.startswith("_") or not cfg:
            continue
        fid = cfg.get("jira_field")
        if not fid:
            continue
        if fid not in campos:
            errors.append(f"{logical}: el campo '{fid}' no existe o no es editable al crear en este proyecto/tipo")
            continue
        covered.add(fid)
        allowed = campos[fid]["valores_permitidos"]
        for k, v in (cfg.get("valores") or {}).items():
            if allowed and v not in allowed:
                errors.append(f"{logical}: valor '{v}' (para {k}) no está entre los permitidos {allowed}")
        if allowed and not cfg.get("valores"):
            std = STANDARD_VALUES.get(logical)
            if std and not set(std) <= set(allowed):
                errors.append(f"{logical}: '{fid}' tiene opciones cerradas {allowed} que no coinciden con el "
                              f"estándar {std}; definir 'valores' usando solo opciones reales")
            elif not std and logical in ("entorno",):
                warnings.append(f"{logical}: '{fid}' tiene opciones cerradas; valores no listados irán a la descripción")
    for fid, f in campos.items():
        if f["requerido"] and not f["tiene_default"] and fid not in covered and fid not in ("reporter",):
            errors.append(f"Jira exige '{fid}' ({f['nombre']}) y el mapeo no lo cubre: pedir el dato, no inventarlo")
    lt = (mapping.get("issue_origen") or {}).get("tipo_vinculo")
    if lt and meta.get("tipos_vinculo") and lt not in meta["tipos_vinculo"]:
        errors.append(f"tipo de vínculo '{lt}' no existe ({meta['tipos_vinculo']})")
    if any(k.startswith("_") for k in mapping):
        warnings.append("el mapeo contiene claves '_...' de una propuesta automática sin confirmar")
    return errors, warnings


# ------------------------------------------------------------------ armado del payload
def fingerprint(bug):
    base = f"{bug.get('modulo','')}|{bug.get('titulo','')}|{bug.get('caso','')}".lower()
    base = re.sub(r"\s+", " ", base).strip()
    return "qa-fp-" + hashlib.sha1(base.encode()).hexdigest()[:10]


def _field_value(meta_field, value, cfg):
    schema = (meta_field or {}).get("schema", {})
    t, items = schema.get("type"), schema.get("items")
    mapped = (cfg.get("valores") or {}).get(value, value) if cfg.get("valores") else value
    if t == "priority":
        return {"name": mapped}
    if t == "option":
        return {"value": mapped}
    if t == "array" and items in ("version", "component"):
        return [{"name": v} for v in (mapped if isinstance(mapped, list) else [mapped])]
    if t == "array" and items == "option":
        return [{"value": v} for v in (mapped if isinstance(mapped, list) else [mapped])]
    if t == "array" and items == "string":
        return mapped if isinstance(mapped, list) else [mapped]
    if t == "date":
        return str(mapped)
    return str(mapped)


def build_payload(bug, body, mapping, meta):
    campos_meta = meta["campos"]
    fields = {"project": {"key": mapping.get("proyecto") or meta["proyecto"]["key"]},
              "issuetype": {"id": meta["tipo_issue"]["id"]},
              "summary": bug["titulo"][:255]}
    in_description = []
    unmapped_values = []
    labels = list(dict.fromkeys((mapping.get("etiquetas_fijas") or []) + (bug.get("etiquetas") or []) + [bug["_fp"]]))
    for logical in LOGICAL_FIELDS:
        cfg = (mapping.get("campos") or {}).get(logical) or {}
        fid = cfg.get("jira_field")
        if logical == "etiquetas":
            if fid == "labels" and "labels" in campos_meta:
                fields["labels"] = [re.sub(r"\s+", "-", l) for l in labels]
            else:
                in_description.append(("Etiquetas", ", ".join(labels)))
            continue
        val = bug.get(logical)
        if val in (None, ""):
            continue
        if fid and fid in campos_meta:
            allowed = campos_meta[fid]["valores_permitidos"]
            mapped = (cfg.get("valores") or {}).get(val, val)
            if allowed and mapped not in allowed:
                unmapped_values.append(f"{logical}={val}")
                in_description.append((LABELS_HUMAN.get(logical, logical), str(val)))
                continue
            fields[fid] = _field_value(campos_meta[fid], val, cfg)
            if logical == "prioridad" and cfg.get("valores"):
                # conservar la clasificación solicitada aunque la escala de Jira sea otra
                in_description.append(("Prioridad (estándar QA)", f"{val} → {mapped} en Jira"))
        else:
            in_description.append((LABELS_HUMAN.get(logical, logical), str(val)))
    link_type = (mapping.get("issue_origen") or {}).get("tipo_vinculo")
    if bug.get("issue_origen") and not link_type:
        in_description.append(("Issue de origen", str(bug["issue_origen"])))
    trace = f"Caso {bug.get('caso') or '-'} · Ejecuciones {', '.join(bug.get('ejecuciones') or [])} · Hallazgo {bug.get('hallazgo') or '-'} · Borrador {bug['id']}"
    sections = split_sections(body)
    sections["Clasificación y contexto"] = "\n".join(f"- {k}: {v}" for k, v in in_description) or ""
    obs = sections.get("Observaciones", "")
    sections["Observaciones"] = (obs + "\n" if obs else "") + f"- Trazabilidad QA: {trace}"
    ordered = [(k, sections[k]) for k in BODY_ORDER if sections.get(k, "").strip()]
    ordered += [(k, v) for k, v in sections.items() if k not in BODY_ORDER and v.strip()]
    if mapping.get("api_version", 3) == 3:
        fields["description"] = md_to_adf(ordered)
    else:
        fields["description"] = md_to_wiki(ordered)
    return {"fields": fields}, unmapped_values, link_type


def _strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def _inline(text):
    nodes, pos = [], 0
    for m in re.finditer(r"`([^`]+)`|\*\*([^*]+)\*\*", text):
        if m.start() > pos:
            nodes.append({"type": "text", "text": text[pos:m.start()]})
        if m.group(1):
            nodes.append({"type": "text", "text": m.group(1), "marks": [{"type": "code"}]})
        else:
            nodes.append({"type": "text", "text": m.group(2), "marks": [{"type": "strong"}]})
        pos = m.end()
    if pos < len(text):
        nodes.append({"type": "text", "text": text[pos:]})
    return nodes or [{"type": "text", "text": " "}]


def md_to_adf(sections):
    content = []
    for title, md in sections:
        content.append({"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": title}]})
        lines = _strip_comments(md).splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("```"):
                lang = line.strip()[3:] or None
                code = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code.append(lines[i])
                    i += 1
                node = {"type": "codeBlock", "content": [{"type": "text", "text": "\n".join(code) or " "}]}
                if lang:
                    node["attrs"] = {"language": lang}
                content.append(node)
                i += 1
                continue
            m_ol, m_ul = re.match(r"^\s*\d+\.\s+(.*)", line), re.match(r"^\s*[-*]\s+(.*)", line)
            if m_ol or m_ul:
                kind = "orderedList" if m_ol else "bulletList"
                rx = r"^\s*\d+\.\s+(.*)" if m_ol else r"^\s*[-*]\s+(.*)"
                items = []
                while i < len(lines) and re.match(rx, lines[i]):
                    items.append({"type": "listItem", "content": [
                        {"type": "paragraph", "content": _inline(re.match(rx, lines[i]).group(1))}]})
                    i += 1
                content.append({"type": kind, "content": items})
                continue
            if line.strip():
                para = [line.strip()]
                i += 1
                while i < len(lines) and lines[i].strip() and not re.match(r"^\s*(\d+\.|[-*]|```)", lines[i]):
                    para.append(lines[i].strip())
                    i += 1
                content.append({"type": "paragraph", "content": _inline(" ".join(para))})
                continue
            i += 1
    return {"type": "doc", "version": 1, "content": content}


def md_to_wiki(sections):
    out = []
    for title, md in sections:
        out.append(f"h3. {title}")
        md = _strip_comments(md)
        md = re.sub(r"```(\w*)\n(.*?)```", lambda m: "{code" + (f":{m.group(1)}" if m.group(1) else "") + "}\n" + m.group(2) + "{code}", md, flags=re.S)
        md = re.sub(r"^\s*\d+\.\s+", "# ", md, flags=re.M)
        md = re.sub(r"^\s*-\s+", "* ", md, flags=re.M)
        md = re.sub(r"`([^`]+)`", r"{{\1}}", md)
        md = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", md)
        out.append(md.strip())
    return "\n\n".join(out)


# ------------------------------------------------------------------ duplicados / creación
def _jql_text(s):
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"[^\w\sáéíóúñÁÉÍÓÚÑ]", " ", s)
    words = [w for w in s.split() if len(w) > 3][:8]
    return " ".join(words)


def find_duplicates(j, project, bug):
    by_fp = j.search(f'project = "{project}" AND labels = "{bug["_fp"]}"')
    text = _jql_text(bug["titulo"])
    similar = []
    if text:
        similar = j.search(f'project = "{project}" AND issuetype = Bug AND statusCategory != Done AND summary ~ "{text}"')
    return by_fp, [s for s in similar if s["key"] not in {x["key"] for x in by_fp}]


def issue_url(j, key):
    return f"{j.base}/browse/{key}"


def attach(j, key, paths):
    done = []
    for p in paths:
        p = Path(p)
        boundary = uuid.uuid4().hex
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{p.name}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n").encode() + p.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        j.req("POST", f"{j.api}/issue/{key}/attachments", raw=body,
              headers={"X-Atlassian-Token": "no-check", "Content-Type": f"multipart/form-data; boundary={boundary}"})
        done.append(p.name)
    return done


def create(j, bug_path, mapping, meta, campaign, allow_similar=False, retries=2):
    bug, body = read_front_matter(bug_path)
    bug["_fp"] = (bug.get("jira") or {}).get("fingerprint") or fingerprint(bug)
    jira_state = bug.get("jira") or {}
    if jira_state.get("estado") == "creado" and jira_state.get("key"):
        return {"resultado": "ya_creado", "key": jira_state["key"], "url": jira_state.get("url")}
    errs, _ = check_mapping(meta, mapping)
    if errs:
        raise SystemExit("Mapeo inválido, no se crea nada:\n- " + "\n- ".join(errs))
    project = mapping.get("proyecto") or meta["proyecto"]["key"]
    by_fp, similar = find_duplicates(j, project, bug)
    if by_fp:
        key = by_fp[0]["key"]
        _save(bug_path, bug, body, estado="creado", key=key, url=issue_url(j, key), proyecto=project)
        return {"resultado": "existente_por_huella", "key": key, "url": issue_url(j, key)}
    if similar and not allow_similar:
        return {"resultado": "posibles_duplicados", "candidatos": [{"key": s["key"], "summary": s["fields"]["summary"]} for s in similar],
                "accion": "Revisar. Si es duplicado: marcar jira.estado=duplicado y duplicado_de. Si no: re-ejecutar con --allow-similar."}
    payload, unmapped, link_type = build_payload(bug, body, mapping, meta)
    created = None
    for attempt in range(retries + 1):
        try:
            created = j.req("POST", f"{j.api}/issue", body=payload)
            break
        except Uncertain as e:
            time.sleep(min(2 ** attempt, 5))
            again, _ = find_duplicates(j, project, bug)  # ¿se creó igual?
            if again:
                created = {"key": again[0]["key"]}
                break
            if attempt == retries:
                raise SystemExit(f"Respuesta incierta de Jira y el issue no aparece: {e}. No se reintenta más.")
    key = created["key"]
    check = j.req("GET", f"{j.api}/issue/{key}?fields=summary,issuetype,project,labels")
    f = check.get("fields", {})
    problems = []
    if f.get("summary") != payload["fields"]["summary"]:
        problems.append("summary distinto")
    if (f.get("project") or {}).get("key") != project:
        problems.append("proyecto distinto")
    if (f.get("issuetype") or {}).get("id") not in (None, meta["tipo_issue"]["id"]):
        problems.append("tipo de issue distinto")
    linked = None
    if link_type and bug.get("issue_origen"):
        try:
            j.req("POST", f"{j.api}/issueLink", body={"type": {"name": link_type}, "inwardIssue": {"key": key},
                                                     "outwardIssue": {"key": bug["issue_origen"]}})
            linked = bug["issue_origen"]
        except (JiraError, Uncertain) as e:
            problems.append(f"no se pudo vincular {bug['issue_origen']}: {e}")
    attached = []
    if mapping.get("adjuntar_evidencias") and campaign:
        files = [Path(campaign) / e for e in bug.get("evidencias") or [] if not re.match(r"^https?://", str(e))]
        try:
            attached = attach(j, key, [p for p in files if p.exists()])
        except (JiraError, Uncertain) as e:
            problems.append(f"adjuntos: {e}")
    _save(bug_path, bug, body, estado="creado", key=key, url=issue_url(j, key), proyecto=project)
    return {"resultado": "creado", "key": key, "url": issue_url(j, key), "verificacion": problems or "ok",
            "valores_sin_mapear_en_descripcion": unmapped, "vinculado_a": linked, "adjuntos": attached}


ATTACHABLE = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".json", ".log", ".txt", ".diff", ".har", ".mp4", ".webm", ".zip"}


def attach_campaign(j, campaign, only=None):
    campaign = Path(campaign)
    files = [Path(only)] if only else sorted((campaign / "bugs").glob("BUGD-*.md"))
    report = []
    for bf in files:
        bug, body = read_front_matter(bf)
        key = (bug.get("jira") or {}).get("key")
        if (bug.get("jira") or {}).get("estado") != "creado" or not key:
            report.append({"bug": bug.get("id"), "resultado": "sin clave Jira: se omite"})
            continue
        existing = {a.get("filename") for a in (j.req("GET", f"{j.api}/issue/{key}?fields=attachment").get("fields", {}).get("attachment") or [])}
        paths = [campaign / e for e in bug.get("evidencias") or [] if not re.match(r"^https?://", str(e))]
        todo = [p for p in paths if p.exists() and p.suffix.lower() in ATTACHABLE and p.name not in existing]
        done = attach(j, key, todo) if todo else []
        report.append({"bug": bug.get("id"), "key": key, "subidos": done, "ya_estaban": sorted(existing & {p.name for p in paths}),
                       "faltantes": [str(p) for p in paths if not p.exists()]})
        if done or existing:
            bug.setdefault("jira", {})["adjuntos"] = sorted(set(done) | (existing & {p.name for p in paths}))
            write_front_matter(bf, bug, body)
    return report


def _save(path, bug, body, **jira):
    bug = {k: v for k, v in bug.items() if not k.startswith("_")}
    j = bug.get("jira") or {}
    j.update({k: v for k, v in jira.items()})
    j["fingerprint"] = j.get("fingerprint") or fingerprint(bug)
    bug["jira"] = j
    write_front_matter(path, bug, body)


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover"); d.add_argument("--project", required=True); d.add_argument("--issuetype", default="Bug")
    d.add_argument("--out", type=Path, required=True); d.add_argument("--api-version", type=int, default=3)
    s = sub.add_parser("suggest-mapping"); s.add_argument("--meta", type=Path, required=True)
    c = sub.add_parser("check-mapping"); c.add_argument("--meta", type=Path, required=True); c.add_argument("--mapping", type=Path, required=True)
    at = sub.add_parser("attach"); at.add_argument("--campaign", type=Path, required=True); at.add_argument("--bug", type=Path)
    for name in ("payload", "duplicates", "create"):
        p = sub.add_parser(name)
        p.add_argument("--bug", type=Path, required=True)
        p.add_argument("--mapping", type=Path, required=True)
        p.add_argument("--meta", type=Path, required=name != "duplicates")
        p.add_argument("--campaign", type=Path)
        if name == "create":
            p.add_argument("--allow-similar", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd not in ("suggest-mapping", "check-mapping", "payload"):
        load_env_file()

    if a.cmd == "suggest-mapping":
        print(yaml.safe_dump(suggest_mapping(json.loads(a.meta.read_text())), allow_unicode=True, sort_keys=False))
        return 0
    if a.cmd == "check-mapping":
        errs, warns = check_mapping(json.loads(a.meta.read_text()), load_yaml(a.mapping))
        for w in warns:
            print("AVISO ", w)
        for e in errs:
            print("ERROR ", e)
        print("OK" if not errs else "FALLA")
        return 1 if errs else 0
    if a.cmd == "payload":
        meta, mapping = json.loads(a.meta.read_text()), load_yaml(a.mapping)
        bug, body = read_front_matter(a.bug)
        bug["_fp"] = fingerprint(bug)
        errs, _ = check_mapping(meta, mapping)
        payload, unmapped, link = build_payload(bug, body, mapping, meta)
        print(json.dumps({"errores_mapeo": errs, "payload": payload, "valores_sin_mapear": unmapped,
                          "vinculo": link, "huella": bug["_fp"]}, ensure_ascii=False, indent=2))
        return 1 if errs else 0

    if a.cmd == "attach":
        j = Jira(api_version=3)
        print(json.dumps(attach_campaign(j, a.campaign, a.bug), ensure_ascii=False, indent=2))
        return 0
    mapping = load_yaml(a.mapping) if a.cmd != "discover" else None
    api_version = a.api_version if a.cmd == "discover" else (mapping.get("api_version") or 3)
    j = Jira(api_version=api_version)
    if a.cmd == "discover":
        meta = discover(j, a.project, a.issuetype)
        a.out.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        req = [k for k, f in meta["campos"].items() if f["requerido"]]
        print(f"OK: {meta['proyecto']['key']} / {meta['tipo_issue']['nombre']} — {len(meta['campos'])} campos, requeridos: {req}")
        return 0
    if a.cmd == "duplicates":
        bug, _ = read_front_matter(a.bug)
        bug["_fp"] = fingerprint(bug)
        by_fp, similar = find_duplicates(j, mapping["proyecto"], bug)
        print(json.dumps({"por_huella": [x["key"] for x in by_fp],
                          "similares": [{"key": x["key"], "summary": x["fields"]["summary"]} for x in similar]},
                         ensure_ascii=False, indent=2))
        return 0
    if a.cmd == "create":
        res = create(j, a.bug, mapping, json.loads(a.meta.read_text()), a.campaign, a.allow_similar)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["resultado"] in ("creado", "ya_creado", "existente_por_huella") else 3
    return 1


if __name__ == "__main__":
    sys.exit(main())
