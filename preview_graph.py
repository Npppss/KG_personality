import argparse, os
import json
import networkx as nx

def write_html_with_vis(G, out_html):
    nodes, edges, edge_types = [], [], set()
    for n, data in G.nodes(data=True):
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
    for s, t, data in G.edges(data=True):
        rel = data.get("type",""); conf = float(data.get("confidence",0.5)); evid = data.get("evidence","")
        title = f"{rel} | conf={conf:.2f}" + (f" | evidence: {evid}" if evid else "")
        edges.append({"from": s, "to": t, "label": rel, "title": title, "confidence": conf, "width": 1 + 4*conf})
        edge_types.add(rel)
    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Graph Preview</title>
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
var options = {{
  nodes: {{ shape:'dot', size:16 }},
  edges: {{ arrows: {{to:{{enabled:true, scaleFactor:0.7}}}} }},
  physics: {{ stabilization: true }},
  layout: {{ improvedLayout: true }}
}};
var container = document.getElementById('mynetwork');
var network = new vis.Network(container, {{nodes:new vis.DataSet(nodes), edges:new vis.DataSet(edges)}}, options);
function applyFilters() {{
  var minConf = parseFloat(document.getElementById('conf').value);
  document.getElementById('confv').innerText = minConf.toFixed(2);
  var selected = Array.from(document.querySelectorAll('.etype:checked')).map(e => e.value);
  var filteredEdges = edges.filter(e => e.confidence >= minConf && (selected.length===0 || selected.includes(e.label)));
  network.setData({{ nodes: new vis.DataSet(nodes), edges: new vis.DataSet(filteredEdges) }});
}}
document.getElementById('conf').addEventListener('input', applyFilters);
Array.from(document.querySelectorAll('.etype')).forEach(el => el.addEventListener('change', applyFilters));
document.getElementById('search').addEventListener('input', function(ev) {{
  var q = ev.target.value.toLowerCase();
  var hits = nodes.filter(n => n.label.toLowerCase().includes(q)).map(n => n.id);
  network.selectNodes(hits, false);
  if (hits.length) {{ network.focus(hits[0], {{scale:1.2}}); }}
}});
applyFilters();
</script></body></html>"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    G = nx.read_graphml(args.path)
    out_html = args.out or os.path.splitext(args.path)[0] + ".html"

    try:
        from pyvis.network import Network
        net = Network(height="750px", width="100%", directed=True)
        for n, data in G.nodes(data=True):
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
            net.add_node(n, label=label)
        for s, t, data in G.edges(data=True):
            net.add_edge(s, t, label=data.get("type", ""))
        net.write_html(out_html)
    except Exception as e:
        write_html_with_vis(G, out_html)
    print("Saved:", out_html)

if __name__ == "__main__":
    main()