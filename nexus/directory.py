"""Auditable directory import. Source facts, taxonomy mappings and user edits stay separate."""
import hashlib,json,re,unicodedata
from pathlib import Path
from urllib.parse import urlparse
from nexus.models import Company,Claim
from nexus.core.matching_engine import normalise

ROOT=Path(__file__).resolve().parents[1]
FIELDS=['organisation_name','description_original_sv','industry_original_sv','employee_range','founded_year','locations','official_website']

def canonical(url):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in {'www.bluesciencepark.se','bluesciencepark.se'} or not re.fullmatch(r'/medlem/[^/]+/?',p.path):
        raise ValueError('Expected an official Blue Science Park profile URL')
    return 'https://www.bluesciencepark.se'+p.path.rstrip('/')+'/'

def name_key(name):
    return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode().lower())

def reconcile(seed,live=None):
    """Seed values survive failed fetches; successful facts keep field-level history."""
    rows={};names={};duplicates=[]
    for r in seed['records']:
        r=dict(r);url=canonical(r['blue_science_park_profile_url']);key=name_key(r['organisation_name'])
        if url in rows or key in names:
            target=url if url in rows else names[key]
            rows[target].setdefault('aliases',[]).append(r['organisation_name']);duplicates.append(url);continue
        r['blue_science_park_profile_url']=url
        r['last_verified_at']=r.get('last_verified_date','')
        r['profile_fetch_status']='supplied_audited_seed'
        r['directory_snapshot_id']='supplied-3.0-audited'
        r['field_sources']={f:{'url':url,'retrieved_at':r['last_verified_at'],'excerpt':r.get(f),'provenance':'supplied_audited_seed'} for f in FIELDS if r.get(f) not in (None,'',[])}
        r['aliases']=[];rows[url]=r;names[key]=url
    matches=0;new=0
    for r in (live or {}).get('records',[]):
        url=canonical(r['blue_science_park_profile_url'])
        previous=rows.get(url)
        if previous: matches+=1
        if r.get('profile_fetch_status')!='live_profile_retrieved':
            if previous: previous['latest_fetch_status']=r.get('profile_fetch_status','failed')
            continue
        if not previous:
            same=names.get(name_key(r['organisation_name']))
            if same:
                previous=rows.pop(same);previous.setdefault('alias_profile_urls',[]).append(same)
                matches+=1;duplicates.append(same)
            else:
                new+=1;previous={}
        merged={**previous,**r}
        merged['source_history']=previous.get('source_history',[])+([previous['field_sources']] if previous.get('field_sources') else [])
        merged['aliases']=sorted(set(previous.get('aliases',[])+r.get('aliases',[])+([previous['organisation_name']] if previous.get('organisation_name') and previous['organisation_name']!=r['organisation_name'] else [])))
        rows[url]=merged;names[name_key(merged['organisation_name'])]=url
    return list(rows.values()),{'seed_records':len(seed['records']),'seed_matches':matches,'new_records':new,'duplicates':duplicates,'total_records':len(rows)}

def import_directory(repo,path=None):
    path=Path(path or ROOT/'data'/'directory_snapshot.json')
    if not path.exists():return {'imported':0}
    data=json.loads(path.read_text(encoding='utf-8'));stamp=data['directory_snapshot_id']
    existing=repo.companies();count=0
    for row in data['records']:
        url=canonical(row['blue_science_park_profile_url'])
        c=next((c for c in existing if c.directory_profile.get('blue_science_park_profile_url')==url or any(cl.source_url.rstrip('/')==url.rstrip('/') for cl in c.claims)),None)
        if c is None:c=next((c for c in existing if name_key(c.name)==name_key(row['organisation_name'])),None)
        if c and c.directory_profile.get('import_snapshot_id')==stamp:continue
        original=row['description_original_sv'];mapped=normalise(original+' '+' '.join(row.get('industry_original_sv',[])))
        # Domains are explicitly machine-mapped application assumptions, not source facts.
        domains=[]
        if set(mapped)&{'software','cloud','ai','cybersecurity','sensing'}:domains.append('digital')
        if set(mapped)&{'marine_operations','robotics'}:domains.append('marine')
        if 'energy' in mapped:domains.append('energy')
        if c is None:
            cid='bsp:'+url.rstrip('/').rsplit('/',1)[-1]
            c=Company(cid,row['organisation_name'],row.get('official_website',''),original,domains,provenance='audited_directory')
            when=row.get('last_verified_at') or row.get('last_verified_date')
            c.claims=[Claim(text=original,category=cat,source_url=url,excerpt=original,retrieved_at=when,provenance='directory_text_taxonomy_mapping') for cat in mapped if original]
        # Keep pre-existing evidence, names, priorities, interests and reviewed capabilities.
        c.directory_profile={**row,'import_snapshot_id':stamp,'domain_mapping_note':'Application domains and capability categories are deterministic taxonomy mappings; source text is retained unchanged.'}
        repo.save_company(c);existing=[x for x in existing if x.id!=c.id]+[c];count+=1
    repo.log('directory_snapshot','directory_import',f'{count} profiles imported or updated; wider ecosystem coverage remains unknown.')
    return {'imported':count,'records':len(data['records'])}

def metadata_rows(profile):
    """One display row per fact, always with its exact source (or explicitly missing)."""
    return [{'Field':f,'Source value':json.dumps(profile.get(f),ensure_ascii=False) if isinstance(profile.get(f),(dict,list)) else str(profile.get(f) if profile.get(f) is not None else ''),
             'Evidence source':profile.get('field_sources',{}).get(f,{}).get('url',''),
             'Verified':profile.get('field_sources',{}).get(f,{}).get('retrieved_at','')} for f in FIELDS]
