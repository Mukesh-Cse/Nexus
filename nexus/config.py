"""Small server-side configuration loader. Values are never rendered or logged."""
import os
from pathlib import Path

CONFIG_KEYS={
 "OPENALEX_API_KEY","OPENAI_API_KEY","OPENAI_MODEL","NEXUS_DB","NEXUS_PUBLIC_DEMO",
 "NEXUS_ALLOW_PUBLIC_REFRESH","NEXUS_SOURCE_HOSTS","NEXUS_EMBEDDINGS","NEXUS_EMBEDDING_MODEL"
}
def load_environment(path):
    path=Path(path)
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line=raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key,value=line.split("=",1)
        key=key.strip().removeprefix("export ").strip()
        value=value.strip()
        if len(value)>1 and value[0]==value[-1] and value[0] in {"'",'"'}:
            value=value[1:-1]
        if key in CONFIG_KEYS and value and not os.getenv(key):
            os.environ[key]=value

def credential_status():
    return {"OpenAlex key":bool(os.getenv("OPENALEX_API_KEY")),
            "OpenAI key":bool(os.getenv("OPENAI_API_KEY"))}

