import unittest
from datetime import datetime,timezone,timedelta
from nexus.core.matching_engine import *
from nexus.core.scoring import score
from nexus.core.evaluation import evaluate
from nexus.models import Claim,Company,Record,utcnow
from tests.common import fixture

class MatchingTests(unittest.TestCase):
    def setUp(self): self.repo=fixture()
    def tearDown(self): self.repo.close()
    def test_normalisation(self):
        for text in ["underwater sensor technology","marine environmental sensing","ocean monitoring devices"]:
            self.assertIn("sensing",normalise(text))
    def test_similarity(self):
        self.assertAlmostEqual(similarity("marine sensor","marine sensor"),100,places=3)
        self.assertEqual(similarity("","sensor"),0)
    def test_complementary_not_just_similar(self):
        a=self.repo.company("cleura");b=self.repo.company("malvacom")
        self.assertGreater(complementarity(a,b),0)
        self.assertEqual(complementarity(a,a),0)
    def test_no_domain_no_complement(self):
        a=self.repo.company("cleura");b=self.repo.company("malvacom")
        b.domains=["unrelated"]
        self.assertEqual(complementarity(a,b),0)
    def test_triple_generation(self):
        recs=discover(self.repo.company("baltic"),self.repo.companies(),self.repo.records())
        self.assertTrue(any(len(r["companies"])==3 for r in recs))
        for r in recs:
            if len(r["companies"])==3:
                self.assertGreaterEqual(len({tuple(sorted((e["a"],e["b"]))) for e in r["relationships"]}),2)
    def test_exact_weighted_score(self):
        self.assertEqual(score({"C":100,"O":80,"R":60,"E":40}),75.)
    def test_missing_component_zero(self):
        self.assertEqual(score({"C":100,"O":None,"R":None,"E":100}),55)
    def test_nan_and_invalid_weights(self):
        with self.assertRaises(ValueError): score({"C":float("nan")})
        with self.assertRaises(ValueError): score({},{"C":1})
    def test_different_company_rankings(self):
        a=discover(self.repo.company("baltic"),self.repo.companies(),self.repo.records())
        b=discover(self.repo.company("cleura"),self.repo.companies(),self.repo.records())
        self.assertNotEqual([x["id"] for x in a],[x["id"] for x in b])
        self.assertNotEqual(a[0]["title"],b[0]["title"])
    def test_priority_changes_scores(self):
        c=self.repo.company("dnv")
        before=discover(c,self.repo.companies(),self.repo.records())
        c.priority="Trustworthy industrial data platform"
        c.interests=["cloud software digital"]
        after=discover(c,[c if x.id==c.id else x for x in self.repo.companies()],self.repo.records())
        self.assertNotEqual({r["id"]:r["score"] for r in before},{r["id"]:r["score"] for r in after})
    def test_no_records_missing_coverage(self):
        r=discover(self.repo.company("baltic"),self.repo.companies(),[])[0]
        self.assertIsNone(r["scores"]["O"])
        self.assertIsNone(r["scores"]["R"])
        self.assertEqual(r["coverage"],50)
    def test_funding_closes_at_deadline(self):
        r=next(x for x in self.repo.records() if x.kind=="funding")
        self.assertEqual(r.status(datetime(2027,1,19,13,tzinfo=timezone.utc)),"closed")
    def test_stale_funding_not_open(self):
        r=next(x for x in self.repo.records() if x.kind=="funding")
        r.retrieved_at=(datetime.now(timezone.utc)-timedelta(days=60)).isoformat()
        self.assertTrue(r.status().startswith("unknown"))
    def test_closed_calls_excluded_from_bridge(self):
        r=next(x for x in self.repo.records() if x.kind=="funding")
        r.deadline="2001-01-01T00:00:00+00:00"
        self.assertEqual(bridge([r],"cybersecurity",["cybersecurity"],"funding"),[])
    def test_benchmark_is_reproducible(self):
        e=evaluate()
        self.assertGreaterEqual(e["candidate_count"],20)
        self.assertEqual(e,evaluate())
        self.assertIn("synthetic",e["label_source"])

