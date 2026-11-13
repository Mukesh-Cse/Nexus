import json,os,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import Mock,patch
import requests
from tests.common import fixture
from nexus.integrations.http import CachedHTTP,IntegrationError
from nexus.integrations.openalex import OpenAlex
from nexus.integrations.vinnova import parse_call
from nexus.integrations.llm import explain
from nexus.service import refresh_sources,workflow
from nexus.config import load_environment

WORK={"id":"https://openalex.org/W999001","display_name":"Synthetic maritime cybersecurity software study",
 "publication_date":"2026-01-01","abstract_inverted_index":{"marine":[0],"software":[1],"security":[2]},
 "authorships":[{"author":{"display_name":"Synthetic fixture author"}}]}
CALL={"Diarienummer":"2026-12345","Titel":"Synthetic AI cybersecurity innovation call",
 "Beskrivning":"Synthetic funding fixture for marine software and cybersecurity research.",
 "Oppningsdatum":"2020-01-01T00:00:00","Stangningsdatum":"2090-01-01T14:00:00",
 "WebTextLista":[{"TextID":"2","TextEn":"Synthetic consortium eligibility fixture"}]}

def response(payload,status=200,headers=None):
    result=requests.Response()
    result.status_code=status
    result._content=json.dumps(payload).encode()
    result.encoding="utf-8"
    result.headers.update(headers or {})
    return result

class LiveAPITests(unittest.TestCase):
    def setUp(self):
        self.repo=fixture()
        self.session=Mock()
    def tearDown(self): self.repo.close()
    def test_anonymous_search_avoids_authenticated_cursor(self):
        self.session.get.return_value=response({"results":[WORK],"meta":{"next_cursor":"next"}})
        with patch.dict(os.environ,{"OPENALEX_API_KEY":""}):
            result=OpenAlex(CachedHTTP(self.repo,self.session)).search("marine",pages=3)
        self.assertEqual(len(result),1)
        self.assertEqual(self.session.get.call_count,1)
        self.assertNotIn("cursor",self.session.get.call_args.kwargs["params"])
    def test_key_is_header_only(self):
        self.session.get.return_value=response({"results":[WORK],"meta":{}})
        with patch.dict(os.environ,{"OPENALEX_API_KEY":"synthetic-test-secret"}):
            OpenAlex(CachedHTTP(self.repo,self.session)).search("marine")
        request=self.session.get.call_args
        self.assertEqual(request.kwargs["headers"]["Authorization"],"Bearer synthetic-test-secret")
        self.assertNotIn("api_key",request.kwargs["params"])
        self.assertNotIn("synthetic-test-secret",json.dumps(self.repo.logs()))
    def test_cached_research_preserves_original_time(self):
        self.session.get.return_value=response({"results":[WORK],"meta":{}})
        http=CachedHTTP(self.repo,self.session)
        with patch.dict(os.environ,{"OPENALEX_API_KEY":""}):
            first=OpenAlex(http).search("marine")
            second=OpenAlex(http).search("marine")
        self.assertEqual(first[0].retrieved_at,second[0].retrieved_at)
        self.assertEqual(second[0].provenance,"cached_api")
        self.assertEqual(self.session.get.call_count,1)
    def test_force_refresh_bypasses_cache(self):
        self.session.get.return_value=response({"results":[]})
        http=CachedHTTP(self.repo,self.session)
        http.json("https://api.openalex.org/works")
        http.json("https://api.openalex.org/works",refresh=True)
        self.assertEqual(self.session.get.call_count,2)
    def test_http_auth_error_is_actionable_and_redacted(self):
        self.session.get.return_value=response({"error":"denied"},403)
        with self.assertRaises(IntegrationError) as error:
            CachedHTTP(self.repo,self.session).json("https://api.openalex.org/works",headers={"Authorization":"Bearer synthetic-secret"})
        self.assertEqual(error.exception.code,"http_403")
        self.assertIn("key activation",str(error.exception))
        self.assertNotIn("synthetic-secret",json.dumps(self.repo.logs()))
    def test_rate_limit_does_not_block_for_long_retry(self):
        self.session.get.return_value=response({},429,{"Retry-After":"120"})
        with patch("nexus.integrations.http.time.sleep") as sleep:
            with self.assertRaises(IntegrationError) as error:
                CachedHTTP(self.repo,self.session).json("https://api.openalex.org/works")
        self.assertEqual(error.exception.retry_after,120)
        sleep.assert_not_called()
    def test_short_retry_is_bounded(self):
        self.session.get.side_effect=[response({},503,{"Retry-After":"0"}),response({"results":[]})]
        self.assertEqual(CachedHTTP(self.repo,self.session).json("https://api.openalex.org/works"),{"results":[]})
        self.assertEqual(self.session.get.call_count,2)
    def test_vinnova_metadata_and_topic_tags(self):
        item={**CALL,"LankLista":[{"URL":"https://www.vinnova.se/e/synthetic-test-call"}]}
        record=parse_call(item)
        self.assertIn("cybersecurity",record.tags)
        self.assertEqual(record.source_url,"https://www.vinnova.se/e/synthetic-test-call")
    def test_partial_failure_retains_snapshots(self):
        before={r.id for r in self.repo.records()}
        http=CachedHTTP(self.repo,self.session)
        def route(url,**kwargs):
            if "openalex" in url:return response({"results":[WORK],"meta":{}})
            return response({},503,{"Retry-After":"60"})
        self.session.get.side_effect=route
        with patch("nexus.service.CachedHTTP",return_value=http),patch.dict(os.environ,{"OPENALEX_API_KEY":""}):
            result=refresh_sources(self.repo,"marine")
        self.assertEqual(result["OpenAlex"]["status"],"live")
        self.assertEqual(result["Vinnova"]["status"],"unavailable")
        self.assertTrue(before<={r.id for r in self.repo.records()})
    def test_live_workflow_feeds_rankings_and_storage(self):
        def route(url,**kwargs):
            return response({"results":[WORK],"meta":{}}) if "openalex" in url else response([CALL])
        self.session.get.side_effect=route
        http=CachedHTTP(self.repo,self.session)
        with patch("nexus.service.CachedHTTP",return_value=http),patch.dict(os.environ,{"OPENALEX_API_KEY":""}):
            result=workflow(self.repo,"baltic","Find marine cybersecurity research collaborators",live=True)
        self.assertTrue(result["recommendations"])
        self.assertEqual(result["refresh"]["Vinnova"]["status"],"live")
        self.assertIn(WORK["id"].split("/")[-1],{r.id for r in self.repo.records()})
    def test_public_refresh_requires_host_opt_in(self):
        with patch.dict(os.environ,{"NEXUS_ALLOW_PUBLIC_REFRESH":"0"}):
            result=refresh_sources(self.repo,"marine",public_demo=True)
        self.assertTrue(all(v["status"]=="disabled" for v in result.values()))
    def test_public_refresh_cooldown(self):
        http=CachedHTTP(self.repo,self.session)
        self.session.get.return_value=response({"results":[],"meta":{}})
        with patch("nexus.service.CachedHTTP",return_value=http),patch("nexus.service._public_next_refresh",0),patch.dict(os.environ,{"NEXUS_ALLOW_PUBLIC_REFRESH":"1","OPENALEX_API_KEY":""}):
            refresh_sources(self.repo,"marine",sources=["OpenAlex"],public_demo=True)
            again=refresh_sources(self.repo,"marine",sources=["OpenAlex"],public_demo=True)
        self.assertEqual(again["OpenAlex"]["status"],"cooldown")
        self.assertEqual(self.session.get.call_count,1)
    def test_env_loader_keeps_existing_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"example.env"
            path.write_text('OPENALEX_API_KEY="synthetic-from-file"\nUNRELATED=ignored\n',encoding="utf-8")
            with patch.dict(os.environ,{"OPENALEX_API_KEY":"already-configured"}):
                load_environment(path)
                self.assertEqual(os.environ["OPENALEX_API_KEY"],"already-configured")
    def test_env_loader_does_not_execute_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"example.env"
            path.write_text('OPENALEX_API_KEY="$(do-not-execute)"',encoding="utf-8")
            with patch.dict(os.environ,{"OPENALEX_API_KEY":""}):
                load_environment(path)
                self.assertEqual(os.environ["OPENALEX_API_KEY"],"$(do-not-execute)")
    def test_optional_llm_structured_response(self):
        rec={"title":"Synthetic hypothesis","relationships":[{"why":"Synthetic dependency"}]}
        payload={"output":[{"content":[{"type":"output_text","text":json.dumps({"explanation":"Synthetic explanation"})}]}]}
        with patch.dict(os.environ,{"OPENAI_API_KEY":"synthetic-key"}),patch("nexus.integrations.llm.requests.post",return_value=response(payload)):
            result=explain(rec)
        self.assertEqual(result["text"],"Synthetic explanation")
        self.assertIn("LLM explanation",result["mode"])

