import unittest,tempfile
from pathlib import Path
from nexus.service import workflow
from nexus.core.blueprint_generator import generate
from nexus.core.graph_engine import graph_data,graph_html
from tests.common import fixture

class EndToEndTests(unittest.TestCase):
    def setUp(self):self.repo=fixture()
    def tearDown(self):self.repo.close()
    def test_complete_discovery_and_export(self):
        output=workflow(self.repo,"baltic","Find potential collaborators for a marine environmental monitoring project.")
        self.assertEqual(output["boundary"]["status"],"supported")
        rec=output["recommendations"][0]
        self.assertTrue(rec["research"])
        self.assertTrue(rec["funding"])
        self.assertTrue(rec["testbeds"])
        report=generate(rec,self.repo.companies())
        self.assertIn("HYPOTHESIS",report)
        self.assertIn("## Proposed first experiment",report)
        self.assertIn("https://",report)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"blueprint.md";p.write_text(report,encoding="utf-8")
            self.assertEqual(p.read_text(encoding="utf-8"),report)
        self.assertGreater(self.repo.db.execute("SELECT COUNT(*) FROM recommendation").fetchone()[0],0)
    def test_stale_blueprint_rejected(self):
        rec=workflow(self.repo,"dnv")["recommendations"][0]
        c=self.repo.company("dnv");c.priority="A new priority"
        self.repo.save_company(c,expected_revision=c.revision)
        with self.assertRaises(ValueError):generate(rec,self.repo.companies())
        self.assertEqual(self.repo.db.execute("SELECT COUNT(*) FROM recommendation").fetchone()[0],0)
    def test_graph_source_links_and_escaping(self):
        recs=workflow(self.repo,"baltic")["recommendations"]
        nodes,edges=graph_data(self.repo.companies(),self.repo.records(),recs,"baltic")
        self.assertTrue(any(e["kind"]=="POTENTIAL_COLLABORATION" for e in edges))
        self.assertTrue(any(n["kind"]=="funding" for n in nodes))
        nodes[0]["label"]="</script><script>alert(1)</script>"
        document=graph_html(nodes,edges)
        self.assertNotIn(nodes[0]["label"],document)
        self.assertIn("textContent",document)
    def test_unrelated_flow_has_no_recommendations(self):
        self.assertEqual(workflow(self.repo,"dnv","Write a romantic poem")["recommendations"],[])
    def test_feedback_persists(self):
        self.repo.feedback("dnv","sample",4,"Useful test")
        self.assertEqual(self.repo.feedback_rows()[0]["rating"],4)

