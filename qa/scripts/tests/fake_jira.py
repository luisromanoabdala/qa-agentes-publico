"""Servidor HTTP mínimo que imita la API REST v3 de Jira para tests (sin red externa)."""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class State:
    def __init__(self):
        self.issues = {}
        self.counter = 100
        self.fail_next_create_after_store = 0  # simula timeout/5xx DESPUÉS de crear
        self.links = []
        self.attachments = []
        self.requests = []


FIELDS = [
    {"fieldId": "summary", "name": "Summary", "required": True, "schema": {"type": "string"}},
    {"fieldId": "issuetype", "name": "Issue Type", "required": True, "schema": {"type": "issuetype"}},
    {"fieldId": "project", "name": "Project", "required": True, "schema": {"type": "project"}},
    {"fieldId": "description", "name": "Description", "required": False, "schema": {"type": "string"}},
    {"fieldId": "priority", "name": "Priority", "required": False, "hasDefaultValue": True, "schema": {"type": "priority"},
     "allowedValues": [{"name": n} for n in ["Highest", "High", "Medium", "Low", "Lowest"]]},
    {"fieldId": "labels", "name": "Labels", "required": False, "schema": {"type": "array", "items": "string"}},
    {"fieldId": "environment", "name": "Environment", "required": False, "schema": {"type": "string"}},
    {"fieldId": "customfield_10050", "name": "Severidad", "required": False, "schema": {"type": "option"},
     "allowedValues": [{"value": v} for v in ["Crítica", "Mayor", "Menor", "Trivial"]]},
    {"fieldId": "attachment", "name": "Attachment", "required": False, "schema": {"type": "array", "items": "attachment"}},
]


def make_handler(state):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _auth_ok(self):
            return self.headers.get("Authorization", "").startswith(("Basic ", "Bearer "))

        def do_GET(self):
            state.requests.append(("GET", self.path))
            if not self._auth_ok():
                return self._send(401, {"errorMessages": ["unauthorized"]})
            u = urlparse(self.path)
            p = u.path
            if p == "/rest/api/3/project/DEMO":
                return self._send(200, {"key": "DEMO", "id": "10000", "name": "Demo QA"})
            if p == "/rest/api/3/issue/createmeta/DEMO/issuetypes":
                return self._send(200, {"issueTypes": [{"id": "10001", "name": "Task"}, {"id": "10004", "name": "Bug"}]})
            if p == "/rest/api/3/issue/createmeta/DEMO/issuetypes/10004":
                return self._send(200, {"fields": FIELDS})
            if p == "/rest/api/3/issueLinkType":
                return self._send(200, {"issueLinkTypes": [{"name": "Relates"}, {"name": "Blocks"}]})
            if p == "/rest/api/3/search/jql":
                jql = parse_qs(u.query)["jql"][0]
                res = []
                m = re.search(r'labels = "([^"]+)"', jql)
                t = re.search(r'summary ~ "([^"]+)"', jql)
                for k, i in state.issues.items():
                    f = i["fields"]
                    if m and m.group(1) in f.get("labels", []):
                        res.append({"key": k, "fields": {"summary": f["summary"]}})
                    elif t and all(w.lower() in f["summary"].lower() for w in t.group(1).split()[:3]):
                        res.append({"key": k, "fields": {"summary": f["summary"]}})
                return self._send(200, {"issues": res})
            m = re.match(r"^/rest/api/3/issue/(DEMO-\d+)$", p)
            if m and m.group(1) in state.issues:
                f = state.issues[m.group(1)]["fields"]
                return self._send(200, {"key": m.group(1), "fields": {
                    "summary": f["summary"], "project": {"key": "DEMO"}, "issuetype": f["issuetype"], "labels": f.get("labels", []),
                    "attachment": [{"filename": n} for k2, n in state.attachments if k2 == m.group(1) and isinstance(n, str)]}})
            return self._send(404, {"errorMessages": ["not found " + p]})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n)
            state.requests.append(("POST", self.path))
            if self.path == "/rest/api/3/issue":
                body = json.loads(raw)
                f = body["fields"]
                for k in f:
                    if k not in {x["fieldId"] for x in FIELDS}:
                        return self._send(400, {"errors": {k: "Field cannot be set"}})
                state.counter += 1
                key = f"DEMO-{state.counter}"
                state.issues[key] = body
                if state.fail_next_create_after_store:
                    state.fail_next_create_after_store -= 1
                    return self._send(504, {"errorMessages": ["gateway timeout"]})
                return self._send(201, {"id": str(state.counter), "key": key})
            if self.path == "/rest/api/3/issueLink":
                state.links.append(json.loads(raw))
                return self._send(201, {})
            m = re.match(r"^/rest/api/3/issue/(DEMO-\d+)/attachments$", self.path)
            if m:
                if self.headers.get("X-Atlassian-Token") != "no-check":
                    return self._send(403, {})
                state.attachments.append((m.group(1), len(raw)))
                return self._send(200, [{"filename": "x"}])
            return self._send(404, {})
    return H


def start():
    state = State()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, state, f"http://127.0.0.1:{srv.server_address[1]}"
