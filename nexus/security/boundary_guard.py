"""Conservative local scope router. External content is never executable instructions."""
import re
INJECTION = re.compile(r"ignore.{0,50}(rules|instructions|previous)|reveal.{0,60}(private|system|prompt|internal)|system\s*prompt|developer\s*message|bypass|jailbreak|another company.{0,30}private", re.I|re.S)
SCOPE = re.compile(r"collaborat|marine|maritime|funding|research|innovation|technolog|testbed|capabilit|compan|profile|industry|event|cyber|monitoring", re.I)
def route_request(text):
    if len(text) > 3000:
        return {"status":"refused","message":"Please shorten your innovation discovery request."}
    if INJECTION.search(text) or re.search(r"private|confidential|internal interactions",text,re.I):
        return {"status":"refused","message":"I cannot disclose private profiles, internal interactions or system instructions. I can explore public innovation evidence."}
    if not SCOPE.search(text):
        return {"status":"redirected","message":"NEXUS supports company capabilities, research, funding, testbeds and innovation collaboration. Try a discovery request in one of these areas."}
    return {"status":"supported","message":"Searching public, evidence-backed innovation connections."}

def safe_source_text(text):
    # Defence in depth; the deterministic pipeline never interprets any webpage as commands.
    return "\n".join(line for line in text.splitlines() if not INJECTION.search(line))[:100000]

