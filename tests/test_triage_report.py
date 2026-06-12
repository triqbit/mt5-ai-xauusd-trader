import os
import unittest

from scripts.generate_triage_report import classify_risk


class TestTriageReport(unittest.TestCase):
    def test_classify_risk_by_file(self):
        # High Risk
        risk, _reason = classify_risk(["src/trading/engine.py"], "Some title")
        self.assertEqual(risk, "High Risk")

        # Medium Risk
        risk, _reason = classify_risk(["src/research/study.py"], "Some title")
        self.assertEqual(risk, "Medium Risk")

        # Safe Surface
        risk, _reason = classify_risk(["docs/README.md"], "Some title")
        self.assertEqual(risk, "Safe Surface")

    def test_classify_risk_by_keyword(self):
        # No files, High Risk keyword
        risk, _reason = classify_risk([], "fix trading logic")
        self.assertEqual(risk, "High Risk")

        # No files, Medium Risk keyword
        risk, _reason = classify_risk([], "improve ux layout")
        self.assertEqual(risk, "Medium Risk")

        # No files, Safe keyword
        risk, _reason = classify_risk([], "fix typo in docs")
        self.assertEqual(risk, "Safe Surface")

    def test_load_cache(self):
        # Create a dummy report in a temporary file
        import tempfile

        from scripts.generate_triage_report import load_cache as load_cache_fn

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "docs/status"), exist_ok=True)
            report_path = os.path.join(tmpdir, "docs/status/PR_TRIAGE_DAILY.md")
            with open(report_path, "w") as f:
                f.write(
                    "| PR # | Title | Author | Branch | Labels | CI Status | Risk Class | Status Flag |\n"
                )
                f.write(
                    "|------|-------|--------|--------|--------|-----------|------------|-------------|\n"
                )
                f.write(
                    "| [9999](https://github.com/repo/pull/9999) | test | user | branch | none | success | High Risk | New |\n"
                )
                f.write(
                    "| [8888](https://github.com/repo/pull/8888) | test | user | branch | none | success | Triage Required | New |\n"
                )

            # Monkeypatch the path in the function's closure or just use a helper that takes a path
            # Since the script is simple, I'll just temporarily change directory
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                cache = load_cache_fn()
                self.assertIn(9999, cache)
                self.assertEqual(cache[9999]["risk"], "High Risk")
                # Updated logic now caches everything for robustness
                self.assertIn(8888, cache)
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
