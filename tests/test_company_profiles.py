import unittest,tempfile
from pathlib import Path
from nexus.models import Claim,Company,url_valid
from nexus.database.repository import Repository
from tests.common import fixture

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.repo=fixture()
    def tearDown(self):
        self.repo.close()
    def test_creation_and_evidence(self):
        self.assertEqual(len(self.repo.companies()),4)
        for company in self.repo.companies():
            self.assertTrue(company.capabilities())
            for claim in company.claims:
                self.assertTrue(claim.source_url)
                self.assertTrue(claim.excerpt)
    def test_profile_update_survives_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"db.sqlite"
            repo=Repository(path)
            c=self.repo.company("baltic")
            repo.save_company(c)
            rev=c.revision
            c.priority="Marine monitoring"
            c.interests=["environmental sensing"]
            repo.save_company(c,expected_revision=rev)
            repo.close()
            repo=Repository(path)
            loaded=repo.company("baltic")
            self.assertEqual(loaded.priority,"Marine monitoring")
            self.assertEqual(loaded.interests,["environmental sensing"])
            self.assertEqual(loaded.revision,rev+1)
            repo.close()
    def test_optimistic_conflict(self):
        c=self.repo.company("dnv")
        self.repo.save_company(c,expected_revision=c.revision)
        with self.assertRaises(ValueError):
            self.repo.save_company(c,expected_revision=0)
    def test_missing_evidence_rejected(self):
        with self.assertRaises(ValueError):
            Claim("Unsupported claim","sensing")
    def test_inference_not_capability(self):
        c=self.repo.company("cleura")
        c.claims.append(Claim("May consider sensors","sensing",classification="INFERENCE",confidence=.4))
        self.assertNotIn("sensing",c.capabilities())
    def test_user_interest_not_fact(self):
        c=self.repo.company("cleura")
        c.interests=["robotics"]
        self.assertNotIn("robotics",c.capabilities())
    def test_bad_url(self):
        for u in ["javascript:alert(1)","http://example.org","https://user:pass@example.org",""]:
            self.assertFalse(url_valid(u))
    def test_revision_history(self):
        c=self.repo.company("dnv")
        self.repo.save_company(c,expected_revision=c.revision)
        count=self.repo.db.execute("SELECT COUNT(*) FROM company_profile_revision WHERE company_id='dnv'").fetchone()[0]
        self.assertEqual(count,2)

