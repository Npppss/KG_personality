import os
import networkx as nx
from typing import Dict, List, Tuple
from .models import Entity, Relation, ExtractionResult, PersonalityResult
from .normalization import canon_name, canon_relation

class KGBuilder:
    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def add_entities(self, entities: List[Entity]):
        for e in entities:
            key = canon_name(e.name)
            self.graph.add_node(
                key,
                name=e.name,
                type=e.type,
                **(e.attributes or {}),
            )

    def add_relations(self, relations: List[Relation]):
        for r in relations:
            meta = getattr(r, "meta", {}) or {}
            s = canon_name(meta.get("source_name", r.source_id))
            t = canon_name(meta.get("target_name", r.target_id))
            rel_type = canon_relation(r.type)
            self.graph.add_edge(
                s, t, key=rel_type, type=rel_type, confidence=r.confidence, evidence=r.evidence
            )

    def add_personality(self, personality: PersonalityResult):
        for person_name, scores in personality.traits.items():
            key = canon_name(person_name)
            if key in self.graph.nodes:
                for trait, val in scores.items():
                    self.graph.nodes[key][trait] = float(val)

    def export(self, out_dir: str, base_name: str) -> Tuple[str, str]:
        import json
        os.makedirs(out_dir, exist_ok=True)
        gml = os.path.join(out_dir, f"{base_name}.graphml")
        nx.write_graphml(self.graph, gml)
        html = os.path.join(out_dir, f"{base_name}.html")
        try:
            from pyvis.network import Network
            net = Network(height="750px", width="100%", directed=True)
            color_map = {
                "Person":"#1f77b4","Organization":"#ff7f0e","Event":"#2ca02c",
                "Location":"#d62728","Concept":"#9467bd"
            }
            # nodes with labels, colors, and trait tooltip
            for n, data in self.graph.nodes(data=True):
                name = data.get("name", n)
                typ = data.get("type", "")
                label = f"{name} ({typ})"
                traits = []
                for t in ["openness","conscientiousness","extraversion","agreeableness","neuroticism"]:
                    v = data.get(t)
                    if v is not None:
                        traits.append(f"{t[:3]}={float(v):.2f}")
                if traits:
                    label += " [" + ", ".join(traits) + "]"
                title = f"type={typ}"
                if traits:
                    title += " | " + ", ".join(traits)
                net.add_node(n, label=label, title=title, color=color_map.get(typ, "#888"))
            # edges with label, width by confidence, tooltip evidence
            for s, t, data in self.graph.edges(data=True):
                rel = data.get("type","")
                conf = float(data.get("confidence", 0.5))
                evid = data.get("evidence","")
                title = f"{rel} | conf={conf:.2f}" + (f" | evidence: {evid}" if evid else "")
                width = 1 + 4 * conf
                # pyvis uses 'value' or 'width' to scale edge thickness
                net.add_edge(s, t, label=rel, title=title, width=width)
            # write HTML (avoid net.show to reduce template issues)
            net.write_html(html)
        except Exception:
            # robust local fallback using vis-network CDN
            color_map = {
                "Person":"#1f77b4","Organization":"#ff7f0e","Event":"#2ca02c",
                "Location":"#d62728","Concept":"#9467bd"
            }
            nodes, edges = [], []
            for n, data in self.graph.nodes(data=True):
                name = data.get("name", n); typ = data.get("type","")
                label = f"{name} ({typ})"
                traits = []
                for t in ["openness","conscientiousness","extraversion","agreeableness","neuroticism"]:
                    v = data.get(t)
                    if v is not None:
                        traits.append(f"{t[:3]}={float(v):.2f}")
                if traits: label += " [" + ", ".join(traits) + "]"
                title = f"type={typ}" + ((" | " + ", ".join(traits)) if traits else "")
                nodes.append({"id": n, "label": label, "group": typ, "color": color_map.get(typ, "#888"), "title": title})
            edge_types = set()
            for s, t, data in self.graph.edges(data=True):
                rel = data.get("type",""); conf = float(data.get("confidence",0.5)); evid = data.get("evidence","")
                title = f"{rel} | conf={conf:.2f}" + (f" | evidence: {evid}" if evid else "")
                edges.append({"from": s, "to": t, "label": rel, "title": title, "confidence": conf, "width": 1 + 4*conf})
                edge_types.add(rel)
            html_str = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>KG Preview</title>
<link rel="stylesheet" href="c:/Assigment/lib/vis-9.1.2/vis-network.css">
<script src="c:/Assigment/lib/vis-9.1.2/vis-network.min.js"></script>
<style>
body {{ margin:0; font-family: Arial, sans-serif; }}
#toolbar {{ padding:10px; border-bottom:1px solid #ddd; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }}
#legend span {{ display:inline-block; padding:4px 8px; border-radius:4px; margin-right:6px; color:#fff; font-size:12px; }}
#mynetwork {{ height: calc(100vh - 54px); }}
</style></head><body>
<div id="toolbar">
  <div><strong>Search:</strong> <input id="search" placeholder="type to search..." style="width:220px;"></div>
  <div><strong>Min confidence:</strong> <input id="conf" type="range" min="0" max="1" step="0.05" value="0"><span id="confv">0.00</span></div>
  <div id="filters"><strong>Edge types:</strong> {" ".join([f'<label><input class="etype" type="checkbox" value="{et}" checked> {et}</label>' for et in sorted(edge_types)])}</div>
  <div id="legend"><strong>Legend:</strong> {" ".join([f'<span style="background:{color_map[t]}">{t}</span>' for t in color_map])}</div>
</div>
<div id='mynetwork'></div>
<script>
var nodes = {json.dumps(nodes)};
var edges = {json.dumps(edges)};
var container = document.getElementById('mynetwork');
var options = {{
  nodes: {{ shape:'dot', size:16 }},
  edges: {{ arrows: {{to:{{enabled:true, scaleFactor:0.7}}}} }},
  physics: {{ stabilization: true }},
  layout: {{ improvedLayout: true }}
}};
var network = new vis.Network(container, {{nodes:new vis.DataSet(nodes), edges:new vis.DataSet(edges)}}, options);

// filters
function applyFilters() {{
  var minConf = parseFloat(document.getElementById('conf').value);
  document.getElementById('confv').innerText = minConf.toFixed(2);
  var selected = Array.from(document.querySelectorAll('.etype:checked')).map(e => e.value);
  var filteredEdges = edges.filter(e => e.confidence >= minConf && (selected.length===0 || selected.includes(e.label)));
  var data = {{ nodes: new vis.DataSet(nodes), edges: new vis.DataSet(filteredEdges) }};
  network.setData(data);
}}
document.getElementById('conf').addEventListener('input', applyFilters);
Array.from(document.querySelectorAll('.etype')).forEach(el => el.addEventListener('change', applyFilters));

// search
document.getElementById('search').addEventListener('input', function(ev) {{
  var q = ev.target.value.toLowerCase();
  var hits = nodes.filter(n => n.label.toLowerCase().includes(q)).map(n => n.id);
  network.selectNodes(hits, false);
  if (hits.length) {{ network.focus(hits[0], {{scale:1.2}}); }}
}});

// initial
applyFilters();
</script></body></html>"""
            with open(html, "w", encoding="utf-8") as f:
                f.write(html_str)
        return gml, html