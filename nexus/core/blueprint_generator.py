from nexus.models import utcnow
def generate(rec, companies):
    lookup={c.id:c for c in companies}
    for cid,revision in rec["profile_revisions"].items():
        if lookup[cid].revision != revision:
            raise ValueError("Profile changed; regenerate recommendations before exporting")
    lines=["# "+rec["title"],"","**INNOVATION HYPOTHESIS — not a confirmed collaboration**","",
           "Generated: "+utcnow(),"","## Problem",rec["problem"],"",
           "## Potential participating companies",", ".join(rec["names"]),"",
           "## Capability combination",", ".join(rec["capabilities"]),"",
           "## Why these capabilities may work together"]
    lines += ["- "+e["left"]+" + "+e["right"]+": "+e["why"] for e in rec["relationships"]]
    lines += ["","## Missing capabilities",", ".join(rec["missing"]) or "Taxonomy coverage is complete; practical integration capability remains unverified.",
              "","## Research"]
    for key in ["research","funding","testbeds"]:
        if key!="research":
            lines += ["","## "+{"funding":"Potential funding — eligibility unconfirmed","testbeds":"Possible validation environments — access unconfirmed"}[key]]
        if not rec[key]:
            lines += ["No supporting record found. Investigate before proceeding."]
        for item in rec[key]:
            r=item["record"]
            lines += [f"- [{r['title']}]({r['source_url']}) — relevance {item['relevance']}/100; status {item['status']}; retrieved {r['retrieved_at']}; date {r.get('publication_date') or 'not available'}; deadline {r.get('deadline') or 'not available'}.",
                      "  "+r["description"]]
            if r.get("eligibility"):
                lines += ["  Criteria excerpt: "+r["eligibility"]+" Full eligibility has not been checked."]
    lines += ["","## Proposed first experiment",
        "In an isolated test environment, agree one shared use case and one synthetic or consented data schema. Connect a small data producer to an integration service, host the service, and review its threat model. Measure ingestion latency, data completeness and detection false positives against a documented baseline. These are proposed measurements, not achieved outcomes.",
        "","## Technical requirements",
        "Documented APIs; data ownership agreement; isolated infrastructure; representative sample data; monitoring; security review; named technical owners.",
        "","## Risks and unknowns",*["- "+x for x in rec["uncertainty"]],
        "","## Score and evidence coverage",
        str(rec["scores"])+f"; weighted score {rec['score']}/100; component coverage {rec['coverage']}%. This is a ranking heuristic, not a probability of success.",
        "","Ranking weights: "+str(rec.get("weights",{"C":0.35,"O":0.25,"R":0.20,"E":0.20})),
        "","## Company evidence"]
    for cid in rec["companies"]:
        c=lookup[cid]
        lines += ["","### "+c.name]
        for cl in c.claims:
            if cl.supported():
                lines += [f"- {cl.text} — [{cl.category}]({cl.source_url}); retrieved {cl.retrieved_at}.",
                          "  Evidence: "+cl.excerpt]
        lines += ["User-supplied public priorities: "+(c.priority or "none"),
                  "User-supplied interests (not verified capabilities): "+(", ".join(c.interests) or "none")]
    lines += ["","## Suggested next steps","1. Ask each company to validate its profile and interest.",
              "2. Review the cited publications and the full funding criteria.",
              "3. Contact the testbed to confirm facilities, access and scheduling.",
              "4. Agree scope, data permissions and a measurable pilot before committing resources.",""]
    return "\n".join(lines)

