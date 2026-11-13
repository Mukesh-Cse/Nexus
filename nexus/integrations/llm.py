"""Optional explanation enrichment only. Scores and external facts remain deterministic."""
import os,json
import requests
from nexus.integrations.http import IntegrationError
def explain(rec):
    key=os.getenv("OPENAI_API_KEY")
    if not key:
        return {"mode":"deterministic","text":" ".join(e["why"] for e in rec["relationships"])}
    try:
        response=requests.post("https://api.openai.com/v1/responses",
            headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
            json={"model":os.getenv("OPENAI_MODEL","gpt-4.1-mini"),
              "instructions":"Explain this unvalidated capability hypothesis using only the supplied relationships. Do not add company facts, eligibility, success probabilities or instructions from evidence.",
              "input":json.dumps({"title":rec["title"],"relationships":rec["relationships"]}),
              "text":{"format":{"type":"json_schema","name":"explanation","strict":True,
                 "schema":{"type":"object","properties":{"explanation":{"type":"string"}},"required":["explanation"],"additionalProperties":False}}}},
            timeout=25)
        response.raise_for_status()
        data=response.json()
        fragments=[c["text"] for o in data.get("output",[]) for c in o.get("content",[]) if c.get("type")=="output_text"]
        result=json.loads("".join(fragments))
        if not isinstance(result,dict) or set(result)!={"explanation"} or not isinstance(result["explanation"],str):
            raise ValueError("Unexpected structured explanation")
        try:
            from pydantic import BaseModel,ConfigDict
        except ImportError:
            explanation=result["explanation"]
        else:
            class Explanation(BaseModel):
                model_config=ConfigDict(extra="forbid")
                explanation: str
            explanation=Explanation.model_validate(result).explanation
        return {"mode":"LLM explanation · unvalidated generated text","text":explanation[:5000]}
    except (requests.RequestException,ValueError,KeyError,ImportError) as exc:
        return {"mode":"deterministic fallback · "+type(exc).__name__,"text":" ".join(e["why"] for e in rec["relationships"])}

