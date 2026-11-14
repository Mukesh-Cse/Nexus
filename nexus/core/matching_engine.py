"""Deterministic complementary capability paths with public evidence gating."""
from itertools import combinations
import re
from nexus.core.embeddings import similarity
from nexus.core.scoring import score,WEIGHTS
from nexus.models import freshness
from nexus.regional import regional_alignment

TAXONOMY = {
 "sensing": ["sensor","sensing","monitoring","iot","ocean monitoring devices"],
 "robotics": ["robot","rov","autonomous navigation"],
 "software": ["software","mjukvara","systemintegration","embedded","firmware"],
 "ai": ["artificial intelligence","ai automation","ai-automation","machine learning","artificiell intelligens"],
 "cloud": ["cloud","iaas","openstack","hosting"],
 "cybersecurity": ["cyber","security","säkerhet","threat","cybersäkerhet","cybersakerhet","resiliens"],
 "marine_operations": ["subsea","underwater","undervatten","marine operations","cable installation"],
 "energy": ["energy","power cable","kraftöverföring"]
}
# Input/output dependencies, not arbitrary dissimilarity.
RELATIONSHIPS = [
 ("sensing","software","Sensor output needs ingestion and integration."),
 ("sensing","ai","Sensor observations can become model inputs."),
 ("robotics","sensing","A mobile platform can carry sensing payloads."),
 ("robotics","software","A robotic platform needs control and data interfaces."),
 ("marine_operations","software","Field workflows can supply requirements for an integration prototype."),
 ("marine_operations","cybersecurity","Operational maritime systems can benefit from threat modelling."),
 ("marine_operations","robotics","Subsea operations can provide a validation context for robotics."),
 ("software","cloud","Software services require deployment and data infrastructure."),
 ("software","cybersecurity","Software interfaces need security review and monitoring."),
 ("software","ai","Integrated data pipelines can support AI applications."),
 ("ai","cloud","Models need compute and managed data pipelines."),
 ("ai","cybersecurity","AI pipelines need threat analysis and trustworthy inputs."),
 ("cloud","cybersecurity","Cloud infrastructure requires security controls and monitoring."),
 ("energy","cybersecurity","Energy operations can provide requirements for OT security.")
]
CONCEPTS = {
 "marine": {"title":"Secure maritime operations intelligence","problem":"Explore whether fragmented maritime operational data can support more resilient monitoring.","requires":{"marine_operations","software","cybersecurity"},"domains":{"marine","digital","energy"}},
 "digital": {"title":"Trustworthy industrial data platform","problem":"Explore whether deployment, integration and security capabilities can support a trustworthy industrial data service.","requires":{"software","cloud","cybersecurity"},"domains":{"digital","energy"}},
 "monitoring": {"title":"Connected environmental monitoring prototype","problem":"Explore whether sensing, integration and analytics can turn environmental observations into usable monitoring.","requires":{"sensing","software","ai"},"domains":{"marine","digital","environment"}}
}
def normalise(text):
    t = re.sub(r"[^\w\s]"," ",text.lower())
    return sorted({name for name,terms in TAXONOMY.items() if any(re.search(r"\b"+re.escape(term)+r"\b",t) for term in [name.replace("_"," "),*terms])})

def relationships(a,b):
    ca, cb = set(a.capabilities()),set(b.capabilities())
    return [{"a":a.id,"b":b.id,"left":x,"right":y,"why":why}
            for x,y,why in RELATIONSHIPS if (x in ca and y in cb) or (y in ca and x in cb)]

def complementarity(a,b):
    rels = relationships(a,b)
    if not rels or not set(a.domains)&set(b.domains):
        return 0.
    return min(100.,45+15*len(rels))

def evidence_quality(companies):
    claims=[cl for c in companies for cl in c.claims if cl.category!="membership"]
    if not claims:
        return 0.
    return round(100*sum(cl.supported()*(1 if freshness(cl.retrieved_at) else .4) for cl in claims)/len(claims),2)

def relevance(record, query, tags):
    lexical = similarity(query,record.title+" "+record.description+" "+" ".join(record.tags))
    overlap = len(set(record.tags)&set(tags))/max(1,len(set(record.tags)))
    return round(min(100.,.55*lexical+45*overlap),2)

def bridge(records,query,tags,kind):
    ranked=[]
    for record in records:
        if record.kind != kind or (kind=="funding" and record.status() in {"closed","upcoming"}):
            continue
        val = relevance(record,query,tags)
        # An unknown/stale call is context only, never positive eligibility evidence.
        if kind=="funding" and record.status()!="open":
            val*=.4
        if val>5:
            ranked.append({"record":record.to_dict(),"relevance":round(val,2),"status":record.status()})
    return sorted(ranked,key=lambda r:(-r["relevance"],r["record"]["id"]))[:3]

def discover(focus, companies, records, limit=15, weights=None):
    score({},weights)
    others=sorted([c for c in companies if c.id!=focus.id],key=lambda c:(-complementarity(focus,c),-regional_alignment(focus,c),c.id))[:12]
    groups=[(focus,c) for c in others]
    groups += [(focus,a,b) for a,b in combinations(others[:8],2)]
    results=[]
    for group in groups:
        edges=[r for a,b in combinations(group,2) for r in relationships(a,b) if set(a.domains)&set(b.domains)]
        # Every participating company must be connected; triple requires >=2 distinct company links.
        links={tuple(sorted((e["a"],e["b"]))) for e in edges}
        if len(links)<len(group)-1 or set(c.id for c in group)!={v for link in links for v in link}:
            continue
        caps=set(v for c in group for v in c.capabilities())
        common=set.intersection(*(set(c.domains) for c in group))
        if not common:
            continue
        for concept_id,concept in CONCEPTS.items():
            if not common&concept["domains"] or len(caps&concept["requires"])<2:
                continue
            # Concept needs a supporting capability relationship, and focus must contribute.
            if not set(focus.capabilities())&concept["requires"]:
                continue
            priority_text=" ".join([focus.priority,*focus.interests])
            alignment=similarity(priority_text,concept["title"]+" "+concept["problem"]+" "+concept_id) if priority_text else 0
            pair_scores=[complementarity(a,b) for a,b in combinations(group,2)]
            base=sum(pair_scores)/len(pair_scores)
            cscore=min(100.,.65*base+25*len(caps&concept["requires"])/len(concept["requires"])+.1*alignment)
            tags=sorted(caps|common|{concept_id})
            query=concept["title"]+" "+" ".join(tags)+" "+priority_text
            research=bridge(records,query,tags,"research")
            funding=bridge(records,query,tags,"funding")
            testbeds=bridge(records,query,tags,"testbed")
            components={"C":round(cscore,2),"O":funding[0]["relevance"] if funding else None,"R":research[0]["relevance"] if research else None,"E":evidence_quality(group)}
            missing=sorted(concept["requires"]-caps)
            rec={
                "id":concept_id+":"+":".join(sorted(c.id for c in group)),
                "title":concept["title"],"problem":concept["problem"],"companies":[c.id for c in group],
                "names":[c.name for c in group],"capabilities":sorted(caps),"relationships":edges,
                "missing":missing,"scores":components,"score":score(components,weights),
                "weights":dict(WEIGHTS if weights is None else weights),
                "coverage":round(100*sum(v is not None for v in components.values())/4),
                "research":research,"funding":funding,"testbeds":testbeds,
                "classification":"HYPOTHESIS","shared_domains":sorted(common),
                "uncertainty":["Commercial interest and willingness to collaborate are unverified.","Interface compatibility, access to data, budgets and eligibility require review."],
                "profile_revisions":{c.id:c.revision for c in group}
            }
            results.append(rec)
    lookup={c.id:c for c in companies}
    return sorted(results,key=lambda r:(-r["score"],-sum(regional_alignment(focus,lookup[cid]) for cid in r['companies'] if cid!=focus.id),r["id"]))[:limit]

def baseline(focus,companies):
    return sorted([{"company":c.name,"id":c.id,"score":similarity(focus.public_text(),c.public_text())} for c in companies if c.id!=focus.id],key=lambda r:(-r["score"],r["id"]))

