import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import fake_jira  # noqa: E402
import jira_bug  # noqa: E402
from qa_common import read_front_matter  # noqa: E402

EXAMPLE = HERE.parents[1] / "ejemplos" / "odontologia-sintetico"


class JiraBugTests(unittest.TestCase):
    def setUp(self):
        self.srv, self.state, self.base = fake_jira.start()
        os.environ.update({"JIRA_BASE_URL": self.base, "JIRA_EMAIL": "qa@example.test", "JIRA_API_TOKEN": "x" * 8})
        os.environ.pop("JIRA_PAT", None)
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(EXAMPLE, self.tmp / "camp")
        self.camp = self.tmp / "camp"
        self.bug = self.camp / "bugs" / "BUGD-001.md"
        self.j = jira_bug.Jira()
        self.meta = jira_bug.discover(self.j, "DEMO")
        self.mapping = {
            "proyecto": "DEMO", "tipo_issue": "Bug", "api_version": 3,
            "campos": {"prioridad": {"jira_field": "priority", "valores": {"P0": "Highest", "P1": "High", "P2": "Medium", "P3": "Low"}},
                       "severidad": {"jira_field": "customfield_10050", "valores": {}},
                       "entorno": {"jira_field": "environment"}, "version": {"jira_field": None},
                       "fecha_deteccion": {"jira_field": None}, "modulo": {"jira_field": None},
                       "etiquetas": {"jira_field": "labels"}},
            "issue_origen": {"tipo_vinculo": "Relates"}, "adjuntar_evidencias": True, "etiquetas_fijas": ["qa-agentico"]}

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.tmp)

    def test_discover_reads_real_fields(self):
        self.assertEqual(self.meta["tipo_issue"]["id"], "10004")
        self.assertIn("customfield_10050", self.meta["campos"])
        self.assertEqual(self.meta["campos"]["customfield_10050"]["valores_permitidos"], ["Crítica", "Mayor", "Menor", "Trivial"])
        self.assertIn("Relates", self.meta["tipos_vinculo"])

    def test_discover_rejects_missing_issuetype(self):
        with self.assertRaises(SystemExit):
            jira_bug.discover(self.j, "DEMO", "Defecto")

    def test_suggest_mapping_finds_candidates_without_inventing_values(self):
        s = jira_bug.suggest_mapping(self.meta)
        self.assertEqual(s["campos"]["severidad"]["jira_field"], "customfield_10050")
        self.assertEqual(s["campos"]["severidad"]["valores"], {})
        self.assertEqual(s["campos"]["prioridad"]["jira_field"], "priority")
        self.assertIsNone(s["campos"]["fecha_deteccion"]["jira_field"])

    def test_check_mapping_rejects_invented_field_and_value(self):
        bad = json.loads(json.dumps(self.mapping))
        bad["campos"]["version"]["jira_field"] = "customfield_99999"
        bad["campos"]["prioridad"]["valores"]["P0"] = "Blocker"
        errs, _ = jira_bug.check_mapping(self.meta, bad)
        self.assertTrue(any("customfield_99999" in e for e in errs))
        self.assertTrue(any("Blocker" in e for e in errs))
        self.assertEqual(jira_bug.check_mapping(self.meta, self.mapping)[0], [])

    def test_payload_uses_fields_and_moves_unmapped_to_description(self):
        bug, body = read_front_matter(self.bug)
        bug["_fp"] = jira_bug.fingerprint(bug)
        payload, unmapped, link = jira_bug.build_payload(bug, body, self.mapping, self.meta)
        f = payload["fields"]
        self.assertEqual(f["priority"], {"name": "High"})
        self.assertEqual(f["customfield_10050"], {"value": "Mayor"})
        self.assertIn(bug["_fp"], f["labels"])
        desc = json.dumps(f["description"], ensure_ascii=False)
        self.assertIn("Versión", desc)            # sin campo → descripción
        self.assertIn("Fecha de detección", desc)
        self.assertNotIn("Severidad:", desc)     # tiene campo propio → no se repite
        self.assertIn("P1 → High", desc)          # se conserva la clasificación del estándar
        self.assertEqual(f["description"]["type"], "doc")
        self.assertEqual(link, "Relates")

    def test_create_verifies_links_attaches_and_writes_key(self):
        res = jira_bug.create(self.j, self.bug, self.mapping, self.meta, self.camp)
        self.assertEqual(res["resultado"], "creado")
        self.assertEqual(res["verificacion"], "ok")
        self.assertTrue(res["url"].endswith("/browse/" + res["key"]))
        meta, _ = read_front_matter(self.bug)
        self.assertEqual(meta["jira"]["key"], res["key"])
        self.assertEqual(meta["jira"]["estado"], "creado")
        self.assertEqual(len(self.state.links), 1)
        self.assertGreaterEqual(len(self.state.attachments), 1)

    def test_create_is_idempotent(self):
        first = jira_bug.create(self.j, self.bug, self.mapping, self.meta, self.camp)
        second = jira_bug.create(self.j, self.bug, self.mapping, self.meta, self.camp)
        self.assertEqual(second["resultado"], "ya_creado")
        self.assertEqual(first["key"], second["key"])
        self.assertEqual(len(self.state.issues), 1)

    def test_uncertain_response_does_not_duplicate(self):
        self.state.fail_next_create_after_store = 1  # Jira crea pero responde 504
        res = jira_bug.create(self.j, self.bug, self.mapping, self.meta, self.camp)
        self.assertEqual(res["resultado"], "creado")
        self.assertEqual(len(self.state.issues), 1)

    def test_similar_issue_blocks_creation_until_reviewed(self):
        jira_bug.create(self.j, self.bug, self.mapping, self.meta, self.camp)
        other = self.camp / "bugs" / "BUGD-099.md"
        meta, body = read_front_matter(self.bug)
        meta.update({"id": "BUGD-099", "caso": "TC-AGE-999", "jira": {"estado": "listo"}})
        from qa_common import write_front_matter
        write_front_matter(other, meta, body)
        res = jira_bug.create(self.j, other, self.mapping, self.meta, self.camp)
        self.assertEqual(res["resultado"], "posibles_duplicados")
        self.assertEqual(len(self.state.issues), 1)

    def test_required_field_not_covered_blocks(self):
        meta = json.loads(json.dumps(self.meta))
        meta["campos"]["customfield_20000"] = {"nombre": "Cliente", "requerido": True, "tiene_default": False,
                                               "schema": {"type": "string"}, "operaciones": [], "valores_permitidos": []}
        with self.assertRaises(SystemExit):
            jira_bug.create(self.j, self.bug, self.mapping, meta, self.camp)
        self.assertEqual(len(self.state.issues), 0)

    def test_attach_campaign_uploads_once(self):
        res = jira_bug.create(self.j, self.bug, self.mapping, self.meta, self.camp)
        n_before = len(self.state.attachments)
        rep = jira_bug.attach_campaign(self.j, self.camp)
        self.assertEqual(rep[0]["key"], res["key"])
        self.assertGreaterEqual(len(self.state.attachments), n_before)

    def test_wiki_render_for_server(self):
        out = jira_bug.md_to_wiki([("Pasos", "1. a\n2. b"), ("Evidencia", "```bash\ncurl $QA_API_URL\n```")])
        self.assertIn("# a", out)
        self.assertIn("{code:bash}", out)


if __name__ == "__main__":
    unittest.main()
