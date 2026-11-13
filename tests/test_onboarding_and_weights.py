import unittest
from tests.common import fixture
from nexus.company_profiles import register_company,add_reviewed_capability
from nexus.core.matching_engine import discover
from nexus.core.scoring import score
from nexus.core.blueprint_generator import generate

class OnboardingTests(unittest.TestCase):
    def setUp(self): self.repo=fixture()
    def tearDown(self): self.repo.close()
    def new_company(self):
        return register_company(self.repo,"Synthetic Onboarding Company","https://example.org",
            "A synthetic profile used only to verify onboarding.",["digital"])
    def test_registration_is_not_verified_capability(self):
        c=self.new_company()
        self.assertEqual(c.capabilities(),[])
        loaded=self.repo.company(c.id)
        self.assertEqual(loaded.provenance,"user_supplied")
        self.assertEqual(loaded.claims[0].classification,"USER_INPUT")
    def test_duplicate_registration_rejected(self):
        self.new_company()
        with self.assertRaises(ValueError):self.new_company()
    def test_invalid_registration(self):
        for url,domains in [("http://example.org",["digital"]),("https://example.org",[])]:
            with self.assertRaises(ValueError):
                register_company(self.repo,"Synthetic company",url,"Public profile description",domains)
    def test_reviewed_capability_enables_discovery(self):
        c=self.new_company()
        before=discover(c,self.repo.companies(),self.repo.records())
        self.assertEqual(before,[])
        updated=add_reviewed_capability(self.repo,c.id,"software","Synthetic software test claim",
            "https://example.org/fixture","Synthetic evidence excerpt for automated tests.",True)
        self.assertIn("software",updated.capabilities())
        self.assertTrue(discover(updated,self.repo.companies(),self.repo.records()))
    def test_confirmation_required(self):
        c=self.new_company()
        with self.assertRaises(ValueError):
            add_reviewed_capability(self.repo,c.id,"software","Claim","https://example.org","Excerpt",False)
    def test_duplicate_evidence_rejected(self):
        c=self.new_company()
        args=(self.repo,c.id,"software","Synthetic claim","https://example.org","Synthetic excerpt",True)
        add_reviewed_capability(*args)
        with self.assertRaises(ValueError):add_reviewed_capability(*args)
    def test_custom_weights_and_export(self):
        weights={"C":1.,"O":0.,"R":0.,"E":0.}
        recs=discover(self.repo.company("baltic"),self.repo.companies(),self.repo.records(),weights=weights)
        self.assertTrue(recs)
        for rec in recs:self.assertEqual(rec["score"],rec["scores"]["C"])
        self.assertEqual(recs[0]["weights"],weights)
        self.assertIn("Ranking weights",generate(recs[0],self.repo.companies()))
    def test_invalid_weight_values(self):
        for weights in [{},{"C":float("nan"),"O":0,"R":0,"E":0},{"C":-1,"O":2,"R":0,"E":0}]:
            with self.assertRaises(ValueError):score({},weights)

