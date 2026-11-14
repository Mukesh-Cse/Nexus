"""Refresh official profiles from an observed listing; optional browser listing expansion.

python scripts/crawl_blue_science_park.py --listing data/directory_listing_observation.json
For an independent dynamic crawl: install playwright, playwright install chromium, then use --browser.
Never equates the public listing with all members of the wider ecosystem.
"""
import argparse,asyncio,json,re,sys,time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nexus.directory import canonical,reconcile,FIELDS
from nexus.models import utcnow

DIRECTORY='https://www.bluesciencepark.se/bli-medlem/'
AGENT='NEXUS-DirectoryAudit/1.0'

def parse_profile(html,url,stamp):
    soup=BeautifulSoup(html,'html.parser');root=soup.select_one('.elementor-location-single')
    if root is None or root.find('h1') is None:raise ValueError('Official profile template missing')
    widgets=root.select('[data-widget_type="icon-list.default"]')
    # The five attribute labels and values are separate lists. Do not regex across the full page.
    attributes={};labels=['Bransch','Antal anställda','Grundat','Ort','Webb']
    for i,w in enumerate(widgets[:-1]):
        observed=[x.get_text(' ',strip=True) for x in w.select('li')]
        if observed==labels:
            values=widgets[i+1].select('li')
            if len(values)!=5:raise ValueError('Profile attribute count changed')
            attributes=dict(zip(labels,values));break
    def value(label):
        el=attributes.get(label);return el.get_text(' ',strip=True) if el else ''
    description=root.select_one('[data-widget_type="text-editor.default"]')
    web=attributes.get('Webb');anchor=web.find('a',href=True) if web else None
    website=anchor['href'] if anchor and urlparse(anchor['href']).scheme in {'https','http'} else ''
    year=value('Grundat')
    split=lambda text:[x.strip() for x in re.split(r'[,\n]+',text) if x.strip()]
    row={'organisation_name':root.find('h1').get_text(' ',strip=True),
         'description_original_sv':description.get_text(' ',strip=True) if description else '',
         'industry_original_sv':split(value('Bransch')),'employee_range':value('Antal anställda'),
         'founded_year':int(year) if re.fullmatch(r'\d{4}',year) else None,
         'locations':split(value('Ort')),'official_website':website,
         'blue_science_park_profile_url':canonical(url),
         'membership_classification':'member_or_partner_not_individually_disclosed',
         'last_verified_at':stamp,'profile_fetch_status':'live_profile_retrieved',
         'directory_snapshot_id':'live-'+stamp,'aliases':[]}
    row['missing_fields']=[f for f in FIELDS if row.get(f) in ('',None,[])]
    row['field_sources']={f:{'url':canonical(url),'retrieved_at':stamp,'excerpt':row[f],'provenance':'official_profile_live'} for f in FIELDS if f not in row['missing_fields']}
    return row

async def browser_listing():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page(locale='sv-SE');await page.goto(DIRECTORY,wait_until='domcontentloaded',timeout=60000)
            cards=page.locator('.elementor-loop-container.elementor-grid').filter(has=page.locator(':scope > .e-loop-item')).first
            await cards.locator(':scope > .e-loop-item').first.wait_for()
            counts=[];stable=False
            for _ in range(100):
                count=await cards.locator(':scope > .e-loop-item').count();counts.append(count)
                more=page.get_by_role('button',name=re.compile('ladda mer',re.I))
                if await more.count()==0:
                    await page.wait_for_timeout(1200)
                    stable=await more.count()==0 and await cards.locator(':scope > .e-loop-item').count()==count
                    break
                await more.click(timeout=10000)
                await page.wait_for_function('(n)=>document.querySelectorAll(".elementor-loop-container.elementor-grid > .e-loop-item").length>n',arg=count,timeout=30000)
            urls=await cards.locator('a[href*="/medlem/"]').evaluate_all('(els)=>els.map(a=>a.href)')
            related=await page.locator('a[href*="/medlem/"]').evaluate_all('(els)=>els.map(a=>a.href)')
            return {'source':DIRECTORY,'observed_at':utcnow(),'method':'Playwright dynamic listing expansion','loaded_card_counts':counts,'loaded_card_count':counts[-1],
                    'stable_end':stable,'profile_urls':sorted(set(map(canonical,urls))),
                    'related_profile_urls':sorted(set(map(canonical,related))),'ecosystem_coverage':'unknown'}
        finally:await browser.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--listing',type=Path);parser.add_argument('--browser',action='store_true');parser.add_argument('--retry-failed',action='store_true');args=parser.parse_args()
    if not args.browser and not args.listing:parser.error('Provide --browser or a recorded --listing; static HTML is not proof of a complete listing')
    observation=asyncio.run(browser_listing()) if args.browser else json.loads(args.listing.read_text(encoding='utf-8'))
    urls=sorted(set(canonical(u) for u in observation['profile_urls']+observation.get('related_profile_urls',[])))
    robot=RobotFileParser();r=requests.get('https://www.bluesciencepark.se/robots.txt',headers={'User-Agent':AGENT},timeout=(8,25));r.raise_for_status();robot.parse(r.content.decode('utf-8').splitlines())
    def fetch(url):
        try:
            if not robot.can_fetch(AGENT,url):raise ValueError('robots_disallowed')
            time.sleep(.35)
            r=requests.get(url,headers={'User-Agent':AGENT},timeout=(8,25),allow_redirects=False);r.raise_for_status()
            if r.status_code!=200:raise ValueError('Redirect or non-200 response')
            if len(r.content)>3_000_000:raise ValueError('Oversized page')
            result=parse_profile(r.content.decode('utf-8'),url,utcnow())
        except (requests.RequestException,ValueError) as e:
            result={'blue_science_park_profile_url':url,'profile_fetch_status':'failed','error_type':type(e).__name__,
                    'http_status':getattr(locals().get('r'),'status_code',None)}
        print(result['profile_fetch_status'],url,flush=True);return result
    retained=[];pending=urls
    previous_path=ROOT/'data/directory_snapshot.json'
    if args.retry_failed and previous_path.exists():
        previous=json.loads(previous_path.read_text(encoding='utf-8'))
        retained=[r for r in previous['records'] if r.get('profile_fetch_status')=='live_profile_retrieved' and r['blue_science_park_profile_url'] in urls]
        seen={r['blue_science_park_profile_url'] for r in retained};pending=[url for url in urls if url not in seen]
    with ThreadPoolExecutor(max_workers=3) as pool:live={'records':retained+list(pool.map(fetch,pending))}
    seed=json.loads((ROOT/'data/blue_science_park_audited_directory.json').read_text(encoding='utf-8'))
    rows,audit=reconcile(seed,live);stamp=utcnow()
    snapshot={'directory_snapshot_id':'bsp-'+stamp,'source':DIRECTORY,'observed_at':observation['observed_at'],
              'listing_observation':observation,'records':rows,'scope_note':'Expanded public listing only; entire ecosystem coverage is unknown.'}
    failed=[r for r in live['records'] if r['profile_fetch_status']!='live_profile_retrieved']
    audit.update({'executed_at':stamp,'listing_card_count':observation['loaded_card_count'],'unique_profile_urls':len(urls),
                  'stable_listing_end':observation['stable_end'],'successful_profile_fetches':len(urls)-len(failed),'failed_urls':failed,
                  'missing_fields_by_column':dict(Counter(f for r in rows for f in r.get('missing_fields',[]))),
                  'ecosystem_coverage':'unknown','listing_profiles_checked':not failed and observation['stable_end']})
    (ROOT/'data/directory_snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'docs/directory_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
