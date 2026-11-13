"""Interactive self-contained graph; Plotly/NetworkX used when available."""
from itertools import combinations
from nexus.core.matching_engine import relationships, similarity
import math,json,html

COLORS={"company":"#4d91ff","capability":"#3adacb","research":"#b18bff","funding":"#ffcc71","application":"#f993bd","testbed":"#76cd8c"}
def graph_data(companies,records,recs,focus_id):
    nodes={}; edges=[]
    def node(identity,label,kind,url="",detail=""):
        nodes[identity]={"id":identity,"label":label,"kind":kind,"url":url,"detail":detail}
    def edge(a,b,kind,detail=""):
        edges.append({"a":a,"b":b,"kind":kind,"detail":detail})
    relevant_ids=set([focus_id]+[cid for r in recs[:4] for cid in r["companies"]])
    for c in companies:
        if c.id not in relevant_ids: continue
        node(c.id,c.name,"company",c.website,c.description)
        for cap in c.capabilities():
            cap_id="cap:"+cap
            node(cap_id,cap.replace("_"," "),"capability")
            edge(c.id,cap_id,"HAS_CAPABILITY","Public sourced capability; view Company DNA for evidence.")
    for a,b in combinations([c for c in companies if c.id in relevant_ids],2):
        rels=relationships(a,b)
        if rels:
            edge(a.id,b.id,"COMPLEMENTS","HYPOTHESIS: "+" ".join(e["why"] for e in rels))
        if similarity(a.public_text(),b.public_text())>15:
            edge(a.id,b.id,"SIMILAR_TO","Algorithmic text similarity, not evidence of a partnership.")
    for i,r in enumerate(recs[:4]):
        app_id="hyp:"+r["id"]
        node(app_id,r["title"],"application",detail="HYPOTHESIS: "+r["problem"])
        for cid in r["companies"]:
            edge(cid,app_id,"POTENTIAL_COLLABORATION","Unvalidated proposed combination.")
        for key in ["research","funding","testbeds"]:
            for item in r[key][:2]:
                record=item["record"]; identity="record:"+record["id"]
                node(identity,record["title"],record["kind"],record["source_url"],record["description"])
                edge(app_id,identity,"SUPPORTED_BY" if key=="research" else "RELEVANT_TO","Potential relevance; availability and eligibility unconfirmed.")
    return list(nodes.values()),edges

def graph_html(nodes,edges):
    # Inline SVG and JS only; labels pass through textContent and links through validated records.
    payload=json.dumps({"nodes":nodes,"edges":edges,"colors":COLORS}).replace("<","\\u003c")
    return GRAPH.replace("__PAYLOAD__",payload)

GRAPH = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#0d1728;color:#dce8fb;font:13px system-ui}#toolbar{padding:12px;display:flex;gap:12px;align-items:center}select,button{background:#162840;color:#dce8fb;border:1px solid #365072;border-radius:6px;padding:6px}svg{width:100%;height:470px;cursor:grab}#detail{padding:14px;min-height:75px;background:#132238;border-top:1px solid #28405d}a{color:#55dbe7}.node{cursor:pointer}.node:hover circle{stroke:#fff;stroke-width:3}text{fill:#e4edfc;font-size:11px;pointer-events:none}
</style></head><body><div id="toolbar"><b>CONNECTION MAP</b><select id="filter"><option value="all">All relationships</option></select><button id="reset">Reset view</button><span>Scroll to zoom · drag to pan · select a node or edge</span></div>
<svg id="svg" viewBox="0 0 1000 470" role="img" aria-label="Innovation connection graph"><g id="view"></g></svg><div id="detail">Select a node to inspect its evidence. Pink application nodes are hypotheses.</div>
<script>
const data=__PAYLOAD__,NS="http://www.w3.org/2000/svg",view=document.getElementById("view"),svg=document.getElementById("svg"),detail=document.getElementById("detail");
let scale=1,dx=0,dy=0,drag=null;
const pos={};const groups=[...new Set(data.nodes.map(n=>n.kind))];
groups.forEach((kind,gi)=>{const group=data.nodes.filter(n=>n.kind===kind); group.forEach((n,i)=>{const angle=2*Math.PI*i/group.length+gi*.4;const radius=kind==="company"?100:170+gi*12;pos[n.id]={x:500+radius*Math.cos(angle),y:225+(radius*.7)*Math.sin(angle)};});});
function element(name,attrs){const e=document.createElementNS(NS,name);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));return e;}
function show(label,text,url){detail.replaceChildren();const b=document.createElement("b");b.textContent=label;detail.append(b,document.createElement("br"),document.createTextNode(text));if(url&&url.startsWith("https://")){const a=document.createElement("a");a.textContent=" Open source ↗";a.href=url;a.target="_blank";a.rel="noopener noreferrer";detail.append(a);}}
function draw(){view.replaceChildren(); const selected=document.getElementById("filter").value;
data.edges.filter(e=>selected==="all"||e.kind===selected).forEach(e=>{const a=pos[e.a],b=pos[e.b];if(!a||!b)return;const line=element("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:e.kind==="HAS_CAPABILITY"?"#237d82":"#40526e","stroke-width":e.kind==="COMPLEMENTS"?2:1.2,"stroke-dasharray":e.kind==="POTENTIAL_COLLABORATION"?"5 5":""});line.style.cursor="pointer";line.addEventListener("click",()=>show(e.kind,e.detail));view.append(line);});
data.nodes.forEach(n=>{const p=pos[n.id],g=element("g",{class:"node",tabindex:"0",role:"button","aria-label":n.label});const c=element("circle",{cx:p.x,cy:p.y,r:n.kind==="company"?12:7,fill:data.colors[n.kind]||"#aaa",stroke:"#102039","stroke-width":2});const t=element("text",{x:p.x+15,y:p.y+4});t.textContent=n.label.length>30?n.label.slice(0,29)+"…":n.label;const title=element("title",{});title.textContent=n.label+" · "+n.kind;g.append(c,t,title);g.addEventListener("click",()=>show(n.label,n.kind+" · "+n.detail,n.url));g.addEventListener("keydown",e=>{if(e.key==="Enter")show(n.label,n.detail,n.url)});view.append(g);});}
[...new Set(data.edges.map(e=>e.kind))].forEach(kind=>{const o=document.createElement("option");o.value=kind;o.textContent=kind;document.getElementById("filter").append(o);});
document.getElementById("filter").onchange=draw;
function transform(){view.setAttribute("transform","translate("+dx+","+dy+") scale("+scale+")");}
svg.addEventListener("wheel",e=>{e.preventDefault();scale=Math.max(.4,Math.min(3,scale*(e.deltaY<0?1.1:.9)));transform();},{passive:false});
svg.addEventListener("pointerdown",e=>{if(e.target===svg){drag={x:e.clientX,y:e.clientY,dx,dy};svg.setPointerCapture(e.pointerId);}});
svg.addEventListener("pointermove",e=>{if(drag){dx=drag.dx+(e.clientX-drag.x);dy=drag.dy+(e.clientY-drag.y);transform();}});
svg.addEventListener("pointerup",()=>drag=null);
document.getElementById("reset").onclick=()=>{scale=1;dx=dy=0;transform();};draw();
</script></body></html>"""

def plotly_figure(nodes,edges):
    import networkx as nx
    import plotly.graph_objects as go
    g=nx.Graph()
    g.add_nodes_from(n["id"] for n in nodes)
    g.add_edges_from((e["a"],e["b"]) for e in edges)
    pos=nx.spring_layout(g,seed=42)
    traces=[]
    for edge in edges:
        a,b=pos[edge["a"]],pos[edge["b"]]
        traces.append(go.Scatter(x=[a[0],b[0]],y=[a[1],b[1]],mode="lines",line=dict(color="#334860",width=1),hoverinfo="skip",showlegend=False))
    traces.append(go.Scatter(x=[pos[n["id"]][0] for n in nodes],y=[pos[n["id"]][1] for n in nodes],mode="markers+text",text=[n["label"] for n in nodes],hovertext=[n["detail"] for n in nodes],marker=dict(size=13,color=[COLORS.get(n["kind"],"#aaa") for n in nodes]),textposition="top center",showlegend=False))
    fig=go.Figure(traces)
    fig.update_layout(paper_bgcolor="#0d1728",plot_bgcolor="#0d1728",font_color="#dce8fb",height=550,xaxis=dict(visible=False),yaxis=dict(visible=False),margin=dict(l=15,r=15,t=15,b=15))
    return fig

