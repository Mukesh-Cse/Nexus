import copy,json,tempfile,unittest
from pathlib import Path
from tests.common import fixture
from nexus.directory import ROOT,canonical,import_directory,reconcile,metadata_rows,FIELDS
from nexus.regional import regional_alignment,in_blekinge
from scripts.crawl_blue_science_park import parse_profile

class DirectoryTests(unittest.TestCase):
    def setUp(self):
        self.seed=json.loads((ROOT/'data/blue_science_park_audited_directory.json').read_text(encoding='utf-8'))
    def test_seed_55_unique_profiles(self):
        rows,summary=reconcile(self.seed)
        self.assertEqual(len(rows),55);self.assertFalse(summary['duplicates'])
        self.assertTrue(all(r['membership_classification']=='member_or_partner_not_individually_disclosed' for r in rows))
    def test_canonical_rejects_untrusted_hosts(self):
        self.assertEqual(canonical('https://bluesciencepark.se/medlem/cleura/?x=1'),'https://www.bluesciencepark.se/medlem/cleura/')
        for bad in ['https://example.org/medlem/foo/','https://www.bluesciencepark.se/','http://bluesciencepark.se/medlem/foo/']:
            with self.assertRaises(ValueError):canonical(bad)
    def test_duplicate_names_keep_alias_and_dont_delete_seed(self):
        data=copy.deepcopy(self.seed);data['records'].append(copy.deepcopy(data['records'][0]))
        data['records'][-1]['organisation_name']='3D Vision!'
        rows,summary=reconcile(data)
        self.assertEqual(len(rows),55);self.assertEqual(len(summary['duplicates']),1)
        self.assertIn('3D Vision!',rows[0]['aliases'])
    def test_failed_live_fetch_preserves_seed_and_old_timestamp(self):
        first=self.seed['records'][0]
        rows,_=reconcile(self.seed,{'records':[{'blue_science_park_profile_url':first['blue_science_park_profile_url'],'profile_fetch_status':'failed'}]})
        self.assertEqual(rows[0]['description_original_sv'],first['description_original_sv'])
        self.assertEqual(rows[0]['last_verified_at'],first['last_verified_date'])
        self.assertEqual(rows[0]['latest_fetch_status'],'failed')
    def test_parser_pairs_separate_attribute_lists_and_keeps_missing(self):
        labels=''.join('<li>'+x+'</li>' for x in ['Bransch','Antal anställda','Grundat','Ort','Webb'])
        values='<li>Cybersäkerhet</li><li></li><li>2001</li><li>Karlskrona, Ronneby</li><li><a href="https://example.org/">example.org</a></li>'
        html='<div class="elementor-location-single"><h1>Synthetic företag</h1><div data-widget_type="text-editor.default">Original svensk text: säkerhet.</div><div data-widget_type="icon-list.default">'+labels+'</div><div data-widget_type="icon-list.default">'+values+'</div></div>'
        row=parse_profile(html,'https://www.bluesciencepark.se/medlem/synthetic/','2026-11-14T12:00:00+00:00')
        self.assertEqual(row['description_original_sv'],'Original svensk text: säkerhet.')
        self.assertEqual(row['locations'],['Karlskrona','Ronneby'])
        self.assertIn('employee_range',row['missing_fields'])
        self.assertNotIn('employee_range',row['field_sources'])
        self.assertEqual(row['official_website'],'https://example.org/')
        self.assertTrue(all(v['url']==row['blue_science_park_profile_url'] for v in row['field_sources'].values()))
    def test_import_idempotence_preserves_refinements_and_existing_evidence(self):
        rows,_=reconcile(self.seed);payload={'directory_snapshot_id':'synthetic-import-test','records':rows}
        repo=fixture()
        try:
            before=repo.companies();original=before[0];original.priority='Retain public priority';repo.save_company(original)
            with tempfile.TemporaryDirectory(dir=ROOT/'data/test_tmp') as tmp:
                p=Path(tmp)/'snapshot.json';p.write_text(json.dumps(payload),encoding='utf-8')
                import_directory(repo,p);count=len(repo.companies());import_directory(repo,p)
                self.assertEqual(count,55);self.assertEqual(len(repo.companies()),55)
                updated=repo.company(original.id)
                self.assertEqual(updated.priority,'Retain public priority')
                self.assertEqual(updated.claims,original.claims)
                self.assertTrue(updated.directory_profile)
                for c in repo.companies():
                    for row in metadata_rows(c.directory_profile):
                        if row['Source value'] not in ('','[]'):
                            self.assertEqual(row['Evidence source'],c.directory_profile['blue_science_park_profile_url'])
        finally:repo.close()
    def test_regional_matching_uses_only_published_places(self):
        from nexus.models import Company
        a=Company('a','A','','',[],directory_profile={'locations':['Karlskrona']})
        b=Company('b','B','','',[],directory_profile={'locations':['Karlshamn']})
        self.assertEqual(regional_alignment(a,b),1)
        b.directory_profile={};self.assertEqual(regional_alignment(a,b),0)
        self.assertTrue(in_blekinge(['Ronneby']));self.assertFalse(in_blekinge(['Stockholm']))
    def test_renamed_canonical_profile_preserves_old_url_and_provenance(self):
        rows,_=reconcile(self.seed)
        live=copy.deepcopy(rows[0]);live['blue_science_park_profile_url']='https://www.bluesciencepark.se/medlem/new-canonical/'
        live['profile_fetch_status']='live_profile_retrieved';live['last_verified_at']='2026-11-14'
        result,summary=reconcile(self.seed,{'records':[live]})
        self.assertEqual(len(result),55)
        revised=next(r for r in result if r['blue_science_park_profile_url']==live['blue_science_park_profile_url'])
        self.assertIn(rows[0]['blue_science_park_profile_url'],revised['alias_profile_urls'])
        self.assertTrue(revised['source_history'])
    def test_live_snapshot_all_displayed_facts_have_exact_sources(self):
        path=ROOT/'data/directory_snapshot.json'
        if not path.exists():self.skipTest('Live snapshot not yet generated')
        data=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(len(data['records']),56)
        self.assertEqual(data['listing_observation']['loaded_card_counts'],[16,32,48,56])
        for r in data['records']:
            for field,source in r['field_sources'].items():
                self.assertEqual(source['url'],r['blue_science_park_profile_url'])
                self.assertEqual(source['excerpt'],r[field])
