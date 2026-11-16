import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import validate_campaign as vc  # noqa: E402
import new_campaign  # noqa: E402

import yaml  # noqa: E402

EXAMPLE = HERE.parents[1] / "ejemplos" / "odontologia-sintetico"


def edit_yaml(path, fn):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.c = self.tmp / "camp"
        shutil.copytree(EXAMPLE, self.c)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def errors(self):
        rep, _ = vc.validate(self.c)
        return rep.errors

    def test_example_is_valid(self):
        rep, summary = vc.validate(self.c)
        self.assertEqual(rep.errors, [], rep.errors)
        self.assertTrue(summary["ejemplo"])
        self.assertIn("fallido", summary["ejecuciones"])

    def test_retry_hidden_is_error(self):
        def f(d):
            e = next(x for x in d["ejecuciones"] if x["estado"] == "aprobado")
            e["intentos"], e["inestable"] = 3, False
        edit_yaml(self.c / "ejecuciones.yaml", f)
        self.assertTrue(any("sin marcar inestable" in e for e in self.errors()))

    def test_reproduced_requires_product_failure(self):
        def f(d):
            for x in d["ejecuciones"]:
                if x["estado"] == "fallido":
                    x["clasificacion_fallo"] = "infraestructura"
        edit_yaml(self.c / "ejecuciones.yaml", f)
        errs = self.errors()
        self.assertTrue(any("reproducido" in e for e in errs))
        self.assertTrue(any("bugs/" in e and "producto" in e for e in errs))

    def test_invented_jira_key_is_error(self):
        p = self.c / "bugs" / "BUGD-001.md"
        p.write_text(p.read_text(encoding="utf-8").replace("key: null", "key: DEMO-104"), encoding="utf-8")
        self.assertTrue(any("claves solo existen" in e for e in self.errors()))

    def test_secret_detection(self):
        p = self.c / "evidencias" / "nota.md"
        p.write_text("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\npassword: Hunter2Secret\n", encoding="utf-8")
        errs = self.errors()
        self.assertTrue(any("Bearer literal" in e for e in errs))
        self.assertTrue(any("Password literal" in e for e in errs))

    def test_env_references_are_not_secrets(self):
        p = self.c / "evidencias" / "nota.md"
        p.write_text('curl -H "Authorization: Bearer $QA_TOKEN"\npassword: $QA_USER_ADMIN_PASSWORD\n', encoding="utf-8")
        self.assertFalse(any("nota.md" in e for e in self.errors()))

    def test_blocked_requires_blocker(self):
        def f(d):
            for x in d["ejecuciones"]:
                if x["estado"] == "bloqueado":
                    x["bloqueo"] = "BLK-999"
        edit_yaml(self.c / "ejecuciones.yaml", f)
        self.assertTrue(any("bloqueado requiere" in e for e in self.errors()))

    def test_case_without_trace_is_error(self):
        def f(d):
            d["casos"][0]["requisitos"], d["casos"][0]["riesgos"] = [], []
        edit_yaml(self.c / "casos" / "AGE.yaml", f)
        self.assertTrue(any("≥1 requisito o riesgo" in e for e in self.errors()))

    def test_role_with_literal_value_is_error(self):
        edit_yaml(self.c / "campania.yaml", lambda d: d["roles"][0].update({"env_password": "Secreta.123"}))
        self.assertTrue(any("NOMBRE de variable" in e for e in self.errors()))

    def test_new_campaign_scaffold_validates_in_preparation(self):
        dest = self.tmp / "nueva"
        self.assertEqual(new_campaign.main([str(dest), "--id", "C99", "--nombre", "Prueba"]), 0)
        rep, _ = vc.validate(dest)
        self.assertEqual(rep.errors, [], rep.errors)
        self.assertEqual(new_campaign.main([str(dest), "--id", "C99", "--nombre", "Prueba"]), 1)


if __name__ == "__main__":
    unittest.main()
