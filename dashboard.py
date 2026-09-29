"""Write the self-contained Odds Board v2 dashboard (no external chart libraries)."""
from __future__ import annotations

import json


def write(results: dict, path: str) -> None:
    payload = json.dumps(results, default=str, allow_nan=False).replace("</", "<\\/")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.replace("__DATA__", payload))


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Odds Board</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#f3f5f8; --panel:#ffffff; --ink:#15202e; --ink2:#4a5667; --ink3:#7b8696; --line:#dde2ea; --soft:#eaeef4;
  --accent:#1f5fa8; --up:#17804f; --up-soft:#dff3e8; --down:#c0392b; --down-soft:#fbe4e1; --warn:#b7791f; --warn-soft:#fdf1dc;
  --shadow:0 1px 2px rgba(20,32,46,.06);
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0e141c; --panel:#151d28; --ink:#e6ebf2; --ink2:#aab4c3; --ink3:#7d8898; --line:#253142; --soft:#1c2634;
  --accent:#6aa6ea; --up:#3ccf8a; --up-soft:#133426; --down:#ff7a6b; --down-soft:#3a1c1a; --warn:#f0b454; --warn-soft:#3a2d15;
  --shadow:none; color-scheme:dark;}}
:root[data-theme="dark"]{
  --bg:#0e141c; --panel:#151d28; --ink:#e6ebf2; --ink2:#aab4c3; --ink3:#7d8898; --line:#253142; --soft:#1c2634;
  --accent:#6aa6ea; --up:#3ccf8a; --up-soft:#133426; --down:#ff7a6b; --down-soft:#3a1c1a; --warn:#f0b454; --warn-soft:#3a2d15;
  --shadow:none; color-scheme:dark;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 "IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding-inline:16px;padding-block:20px 48px}
h1,h2,h3{font-family:"IBM Plex Sans Condensed","IBM Plex Sans",system-ui,sans-serif;text-wrap:balance;margin:0}
h1{font-size:26px;font-weight:700;letter-spacing:-.01em}
h2{font-size:18px;font-weight:600}
h3{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--ink3)}
.mono,.num{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
header{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:flex-end;justify-content:space-between;margin-bottom:14px}
.sub{color:var(--ink2);font-size:13px}
.banner{background:var(--warn-soft);color:var(--ink);border:1px solid var(--warn);border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:13px}
.note{color:var(--ink3);font-size:12px}
.strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-bottom:16px}
.tick{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 10px;box-shadow:var(--shadow)}
.tick .n{font-size:12px;color:var(--ink2)} .tick .v{font-size:15px;font-weight:500}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:16px;overflow-x:auto}
.tabs button{appearance:none;background:none;border:0;border-bottom:2px solid transparent;padding:10px 14px;font:600 14px "IBM Plex Sans",sans-serif;color:var(--ink2);cursor:pointer;white-space:nowrap}
.tabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent)}
.tabs button:focus-visible,.seg button:focus-visible,select:focus-visible,th:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--panel)}
.seg button{appearance:none;border:0;background:none;padding:6px 12px;font:500 13px "IBM Plex Sans",sans-serif;color:var(--ink2);cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--accent);color:#fff}
.bar{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin-bottom:12px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;box-shadow:var(--shadow)}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.tbl{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{font-weight:600;color:var(--ink2);font-size:12px;cursor:pointer;user-select:none;position:sticky;top:0;background:var(--panel)}
th:first-child,td:first-child,td.l,th.l{text-align:left}
tbody tr:hover{background:var(--soft)}
tbody tr.clickable{cursor:pointer}
.tk{font-weight:600;font-family:"IBM Plex Mono",monospace}
.pbar{display:inline-flex;align-items:center;gap:8px;min-width:150px;justify-content:flex-end}
.pbar .track{width:90px;height:8px;background:var(--down-soft);border-radius:4px;overflow:hidden;position:relative}
.pbar .fill{position:absolute;left:0;top:0;bottom:0;background:var(--up)}
.pbar .mid{position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--ink3)}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600}
.pill.High{background:var(--up-soft);color:var(--up)} .pill.Medium{background:var(--warn-soft);color:var(--warn)} .pill.Low{background:var(--soft);color:var(--ink2)}
.risk-Low{color:var(--up)} .risk-Medium{color:var(--warn)} .risk-High,.risk-Very{color:var(--down)}
.pos{color:var(--up)} .neg{color:var(--down)}
.hcard{border:1px solid var(--line);border-radius:10px;padding:14px;background:var(--panel)}
.hcard .big{font-size:30px;font-weight:600;line-height:1.1}
.split{display:flex;height:10px;border-radius:5px;overflow:hidden;margin:8px 0}
.split .u{background:var(--up)} .split .d{background:var(--down)}
.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:13px}
.kv dt{color:var(--ink2)} .kv dd{margin:0;text-align:right}
ul.f{margin:6px 0 0;padding-left:18px} ul.f li{margin:3px 0}
.chart{position:relative;height:280px}
.chart.sm{height:220px}
.svgc{position:absolute;inset:0} .svgc svg{width:100%;height:100%;display:block;overflow:visible}
.svgc text{fill:var(--ink2);font:11px "IBM Plex Mono",monospace} .svgc .gl{stroke:var(--line)} .legend{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--ink2);margin-top:6px} .legend i{display:inline-block;width:12px;height:3px;margin-right:5px;vertical-align:middle}
.tip{position:fixed;pointer-events:none;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font:12px "IBM Plex Mono",monospace;color:var(--ink);box-shadow:0 4px 12px rgba(0,0,0,.12);z-index:10;white-space:nowrap}
select{font:500 14px "IBM Plex Sans",sans-serif;padding:7px 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink)}
.lead{font-size:15px;color:var(--ink);max-width:72ch}
.stack{display:flex;flex-direction:column;gap:14px}
a{color:var(--accent)}
.rank li{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid var(--line)}
.rank{list-style:none;margin:8px 0 0;padding:0}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}

.g4{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
tr.dim td{opacity:.5} .dimcard{opacity:.62}
.regime{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;margin-bottom:12px}
.rchip{display:inline-block;padding:3px 10px;border-radius:999px;font-weight:600;font-size:12px;background:var(--soft);color:var(--ink2)}
.r-Bull{background:var(--up-soft);color:var(--up)} .r-Bear{background:var(--down-soft);color:var(--down)} .r-Sideways{background:var(--warn-soft);color:var(--warn)} .r-hv{background:var(--down-soft);color:var(--down)}
.chk{display:inline-flex;gap:6px;align-items:center;font-size:13px;color:var(--ink2)}
input[type=search]{font:14px "IBM Plex Sans",sans-serif;padding:7px 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);min-width:0;width:220px;max-width:100%}
td.nm{max-width:220px;overflow:hidden;text-overflow:ellipsis} td.why{white-space:normal;min-width:240px;max-width:420px;color:var(--ink2)}
.dh{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px}
.dhk{display:flex;flex-wrap:wrap;gap:8px 22px} .dhk div{display:flex;flex-direction:column} .dhk b{font-size:17px}
.hh{display:flex;justify-content:space-between;align-items:center} .pud{display:flex;justify-content:space-between;align-items:baseline;margin-top:6px}
.setup{margin-top:8px;padding:8px;border-radius:8px;background:var(--soft);font-size:12.5px;color:var(--ink2)}
.wrapseg{flex-wrap:wrap} a.tk{text-decoration:none;color:var(--accent)}
.pbar .mid{background:var(--ink)}

#evid td[colspan]{white-space:normal}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Odds Board</h1>
      <div class="sub" id="meta"></div>
    </div>
    <div class="note" style="max-width:520px">Model probabilities with backtested track records. Illustrative research, not investment advice. Forecasts below the confidence threshold are shown greyed out.</div>
  </header>
  <div id="demo"></div>
  <div class="regime" id="regime"></div>
  <div class="strip" id="strip"></div>
  <nav class="tabs" role="tablist">
    <button role="tab" aria-selected="true" data-tab="picks">Top lists</button>
    <button role="tab" aria-selected="false" data-tab="screener">Screener</button>
    <button role="tab" aria-selected="false" data-tab="detail">Stock detail</button>
    <button role="tab" aria-selected="false" data-tab="backtest">Backtest</button>
    <button role="tab" aria-selected="false" data-tab="model">Model &amp; method</button>
  </nav>

  <section id="tab-picks">
    <div class="bar"><div class="seg wrapseg" id="listseg"></div></div>
    <p class="lead" id="listdesc"></p>
    <div class="panel tbl"><table id="listt"></table></div>
  </section>

  <section id="tab-screener" hidden>
    <div class="bar">
      <div class="seg" id="hz-scr"></div>
      <select id="f-group" aria-label="Group"></select>
      <select id="f-sort" aria-label="Rank by">
        <option value="p_up">Rank: highest probability</option>
        <option value="risk_adj">Rank: best risk-adjusted return</option>
        <option value="conf">Rank: highest confidence</option>
        <option value="downside">Rank: lowest downside risk</option>
        <option value="quality">Rank: strongest fundamentals</option>
        <option value="gs">Rank: growth + stability</option>
      </select>
      <label class="chk"><input type="checkbox" id="f-pub"> Published forecasts only</label>
      <input id="f-q" type="search" placeholder="Search ticker or name" aria-label="Search">
    </div>
    <div class="note" id="scr-count" style="margin-bottom:6px"></div>
    <div class="panel tbl"><table id="scrt"></table></div>
  </section>

  <section id="tab-detail" hidden>
    <div class="bar"><select id="pick" aria-label="Stock"></select><div class="seg" id="hz-det"></div></div>
    <div class="stack">
      <div class="panel" id="dhead"></div>
      <div class="grid g4" id="hcards"></div>
      <div class="grid g2">
        <div class="panel"><h3>Price, 50/200-day averages, support &amp; resistance</h3><div class="chart"><div class="svgc" id="c-price"></div></div></div>
        <div class="panel"><h3 id="dist-title">Forecast distribution</h3><div class="chart"><div class="svgc" id="c-dist"></div></div><div class="note" id="dist-note"></div></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3 class="pos">Key bullish factors</h3><ul class="f" id="bull"></ul></div>
        <div class="panel"><h3 class="neg">Key bearish factors</h3><ul class="f" id="bear"></ul></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3>Evidence by model component</h3><div class="tbl"><table id="evid"></table></div><p class="note">Each component's own probability and the weight its backtest earned. Weight 0 = switched off for underperforming.</p></div>
        <div class="panel"><h3>Top individual drivers</h3><div class="tbl"><table id="drivers"></table></div></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3>Fundamental quality (0–100, vs universe)</h3><div class="chart sm"><div class="svgc" id="c-qual"></div></div><dl class="kv" id="fundkv" style="margin-top:10px"></dl></div>
        <div class="panel"><h3>Live signals (not backtested, small capped effect)</h3><div id="live"></div></div>
      </div>
    </div>
  </section>

  <section id="tab-backtest" hidden>
    <div class="stack">
      <div class="panel"><h2>Out-of-sample track record</h2><p class="lead" id="bt-lead"></p>
        <div class="tbl"><table id="btt"></table></div>
        <p class="note">Walk-forward: retrained every ~6 months on data up to that point only, with a gap equal to the horizon. Up/down calls are judged against the historical up-rate (not 50%). "Published" = Medium or High confidence. Ranking AUC measures how well it orders stocks against each other on the same day (0.50 = no skill).</p>
      </div>
      <div class="bar"><div class="seg" id="hz-bt"></div></div>
      <div class="panel"><h3>By market condition</h3><div class="tbl"><table id="segt"></table></div></div>
      <div class="grid g2">
        <div class="panel"><h3>Signal portfolio vs equal-weight universe</h3><div class="chart"><div class="svgc" id="c-eq"></div></div><div class="tbl"><table id="stratt"></table></div><p class="note">Long-only, equal-weight published bullish calls, rebalanced every horizon, no costs, risk-free rate 0. Illustrative.</p></div>
        <div class="panel"><h3>Signal portfolio drawdown</h3><div class="chart"><div class="svgc" id="c-dd"></div></div></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3>Components: earned weights (auto-reweighting)</h3><div class="tbl"><table id="compt"></table></div></div>
        <div class="panel"><h3>Component weights over time</h3><div class="chart"><div class="svgc" id="c-wh"></div></div></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3>Calibration: predicted vs actual chance of rising</h3><div class="chart"><div class="svgc" id="c-cal"></div></div></div>
        <div class="panel"><h3>Big-move probabilities: predicted vs actual</h3><div class="tbl"><table id="gaint"></table></div><p class="note">Chance of closing above +5/10/20% at any point within the horizon.</p></div>
      </div>
    </div>
  </section>

  <section id="tab-model" hidden>
    <div class="stack">
      <div class="grid g2">
        <div class="panel"><h3>Feature importance by factor group</h3><div class="chart"><div class="svgc" id="c-impfam"></div></div></div>
        <div class="panel"><h3>How to read confidence and sizing</h3><div id="rules"></div></div>
      </div>
      <div class="panel"><h3>Top 25 features (drop in AUC when shuffled, 1-month model)</h3><div class="chart" style="height:560px"><div class="svgc" id="c-imp"></div></div></div>
      <div class="panel"><h2>Method</h2><ul class="f" id="method"></ul></div>
    </div>
  </section>
</div>

<script>
const R = __DATA__;
const HZ = Object.keys(R.horizons);
const HZNAME = {"1d":"1 day","1w":"1 week","1m":"1 month","3m":"3 months"};
const state = {list:"opportunities_30d", scr:R.primary||"1m", det:R.primary||"1m", bt:R.primary||"1m", pick:(R.predictions[0]||{}).ticker, sortDir:-1};
const $ = s => document.querySelector(s);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const pct = (v,d=1,s=true) => v==null||isNaN(v) ? "n/a" : (s&&v>0?"+":"") + (v*100).toFixed(d) + "%";
const cls = v => v>0 ? "pos" : v<0 ? "neg" : "";
const fmtCap = v => v==null ? "n/a" : v>=1e12 ? "$"+(v/1e12).toFixed(2)+"T" : "$"+(v/1e9).toFixed(0)+"B";
const P = Object.fromEntries(R.predictions.map(p => [p.ticker, p]));
const COMPLABEL = {}; Object.values(R.backtest).forEach(b => (b.components||[]).forEach(c => COMPLABEL[c.key]=c.label));
// ---- tiny SVG chart kit (no external libraries) ----
const NS="http://www.w3.org/2000/svg";
const tip=document.createElement("div"); tip.className="tip"; tip.hidden=true; document.body.appendChild(tip);
function el(tag, attrs, parent){ const e=document.createElementNS(NS,tag); for(const k in attrs) e.setAttribute(k,attrs[k]); parent&&parent.appendChild(e); return e; }
function frame(id){ const host=document.getElementById(id); host.innerHTML=""; const W=host.clientWidth||600, H=host.clientHeight||260; const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,preserveAspectRatio:"none"},host); return {host,svg,W,H}; }
function niceTicks(lo,hi,n=5){ if(lo===hi){lo-=1;hi+=1;} const step0=(hi-lo)/n, mag=10**Math.floor(Math.log10(step0)); const step=[1,2,2.5,5,10].map(m=>m*mag).find(s=>s>=step0); const out=[]; for(let v=Math.ceil(lo/step)*step; v<=hi+1e-12; v+=step) out.push(+v.toFixed(10)); return out; }
function legend(host, items){ const d=document.createElement("div"); d.className="legend"; d.innerHTML=items.map(i=>`<span><i style="background:${i.color}"></i>${esc(i.label)}</span>`).join(""); host.parentElement.insertAdjacentElement("afterend", d); }
function clearLegend(id){ const n=document.getElementById(id).parentElement.nextElementSibling; if(n&&n.classList.contains("legend")) n.remove(); }
function showTip(e, html){ tip.innerHTML=html; tip.hidden=false; const x=Math.min(e.clientX+12, innerWidth-tip.offsetWidth-8); tip.style.left=x+"px"; tip.style.top=(e.clientY+12)+"px"; }
function hideTip(){ tip.hidden=true; }
function lineChart(id, {labels, series, yfmt=v=>v, xfmt=v=>v, ymin, ymax, legendOn=true, hideY=false, xTicks=6, band=null}){
  clearLegend(id); const {host,svg,W,H}=frame(id); const m={l:hideY?8:52,r:10,t:8,b:24};
  const vals=series.flatMap(s=>s.data.filter(v=>v!=null&&!isNaN(v)));
  let lo=ymin??Math.min(...vals), hi=ymax??Math.max(...vals); const pad=(hi-lo)*0.06||1; if(ymin==null)lo-=pad; if(ymax==null)hi+=pad;
  const n=labels.length, X=i=>m.l+(W-m.l-m.r)*i/Math.max(n-1,1), Y=v=>m.t+(H-m.t-m.b)*(1-(v-lo)/(hi-lo));
  if(!hideY) niceTicks(lo,hi,5).forEach(v=>{ el("line",{x1:m.l,x2:W-m.r,y1:Y(v),y2:Y(v),class:"gl"},svg); el("text",{x:m.l-6,y:Y(v)+4,"text-anchor":"end"},svg).textContent=yfmt(v); });
  for(let k=0;k<xTicks;k++){ const i=Math.round((n-1)*k/Math.max(xTicks-1,1)); el("text",{x:X(i),y:H-6,"text-anchor":k===0?"start":k===xTicks-1?"end":"middle"},svg).textContent=xfmt(labels[i]); }
  series.forEach(s=>{
    let d="", open=false; s.data.forEach((v,i)=>{ if(v==null||isNaN(v)){open=false;return;} d+=(open?"L":"M")+X(i).toFixed(1)+","+Y(v).toFixed(1); open=true; });
    if(s.fill){ let a=""; let seg=[]; const flush=()=>{ if(seg.length>1){ a+=`M${X(seg[0]).toFixed(1)},${Y(Math.max(lo,0)).toFixed(1)}`+seg.map(i=>`L${X(i).toFixed(1)},${Y(s.data[i]).toFixed(1)}`).join("")+`L${X(seg[seg.length-1]).toFixed(1)},${Y(Math.max(lo,0)).toFixed(1)}Z`; } seg=[]; };
      s.data.forEach((v,i)=>{ if(v==null||isNaN(v)) flush(); else seg.push(i); }); flush(); el("path",{d:a,fill:s.color,"fill-opacity":.2,stroke:"none"},svg); }
    el("path",{d,fill:"none",stroke:s.color,"stroke-width":s.width||1.6,"stroke-dasharray":s.dash||"","vector-effect":"non-scaling-stroke"},svg);
  });
  if(legendOn) legend(host, series.filter(s=>s.label).map(s=>({label:s.label,color:s.color})));
  const cross=el("line",{y1:m.t,y2:H-m.b,stroke:css("--ink3"),"stroke-dasharray":"3,3",visibility:"hidden"},svg);
  const hit=el("rect",{x:m.l,y:m.t,width:W-m.l-m.r,height:H-m.t-m.b,fill:"transparent"},svg);
  hit.addEventListener("mousemove",e=>{ const r=svg.getBoundingClientRect(); const px=(e.clientX-r.left)*W/r.width; const i=Math.max(0,Math.min(n-1,Math.round((px-m.l)/(W-m.l-m.r)*(n-1))));
    cross.setAttribute("x1",X(i)); cross.setAttribute("x2",X(i)); cross.setAttribute("visibility","visible");
    showTip(e, `<b>${esc(xfmt(labels[i]))}</b><br>`+series.filter(s=>s.label&&s.data[i]!=null).map(s=>`<span style="color:${s.color}">■</span> ${esc(s.label)}: ${yfmt(s.data[i])}`).join("<br>")); });
  hit.addEventListener("mouseleave",()=>{cross.setAttribute("visibility","hidden");hideTip();});
}
function hbarChart(id, {labels, values, colors, xfmt=v=>v.toFixed(2)}){
  clearLegend(id); const {svg,W,H}=frame(id); const lw=Math.min(200, W*0.4), neg=Math.min(0,...values)<0, m={l:lw+(neg?44:8),r:48,t:4,b:18};
  const lo=Math.min(0,...values), hi=Math.max(0,...values)||1, X=v=>m.l+(W-m.l-m.r)*(v-lo)/(hi-lo||1);
  const bh=(H-m.t-m.b)/labels.length;
  el("line",{x1:X(0),x2:X(0),y1:m.t,y2:H-m.b,stroke:css("--ink3")},svg);
  labels.forEach((lab,i)=>{ const y=m.t+i*bh, v=values[i];
    el("text",{x:lw,y:y+bh/2+4,"text-anchor":"end"},svg).textContent=lab.length>30?lab.slice(0,29)+"…":lab;
    const r=el("rect",{x:Math.min(X(0),X(v)),y:y+bh*0.18,width:Math.max(1,Math.abs(X(v)-X(0))),height:bh*0.64,fill:colors[i%colors.length],rx:2},svg);
    el("text",{x:(v>=0?X(v)+4:X(v)-4),y:y+bh/2+4,"text-anchor":v>=0?"start":"end"},svg).textContent=xfmt(v);
    r.addEventListener("mousemove",e=>showTip(e,`${esc(lab)}: ${xfmt(v)}`)); r.addEventListener("mouseleave",hideTip); });
}
function vbarChart(id, {labels, values, colors, yfmt=v=>v.toFixed(2)}){
  clearLegend(id); const {svg,W,H}=frame(id); const m={l:52,r:10,t:10,b:24};
  const lo=Math.min(0,...values), hi=Math.max(0,...values); const pad=(hi-lo)*0.1||1; const L=lo<0?lo-pad:0, Hh=hi+pad;
  const Y=v=>m.t+(H-m.t-m.b)*(1-(v-L)/(Hh-L)); const bw=(W-m.l-m.r)/labels.length;
  niceTicks(L,Hh,5).forEach(v=>{ el("line",{x1:m.l,x2:W-m.r,y1:Y(v),y2:Y(v),class:"gl"},svg); el("text",{x:m.l-6,y:Y(v)+4,"text-anchor":"end"},svg).textContent=yfmt(v); });
  labels.forEach((lab,i)=>{ const v=values[i], x=m.l+i*bw;
    const r=el("rect",{x:x+bw*0.2,y:Math.min(Y(0),Y(v)),width:bw*0.6,height:Math.max(1,Math.abs(Y(v)-Y(0))),fill:colors[i%colors.length],rx:2},svg);
    el("text",{x:x+bw/2,y:H-6,"text-anchor":"middle"},svg).textContent=lab;
    r.addEventListener("mousemove",e=>showTip(e,`${esc(lab)}: ${yfmt(v)}`)); r.addEventListener("mouseleave",hideTip); });
}
function calChart(id, pts){
  clearLegend(id); const {host,svg,W,H}=frame(id); const m={l:44,r:10,t:8,b:34}; const X=v=>m.l+(W-m.l-m.r)*v, Y=v=>m.t+(H-m.t-m.b)*(1-v);
  [0,.25,.5,.75,1].forEach(v=>{ el("line",{x1:m.l,x2:W-m.r,y1:Y(v),y2:Y(v),class:"gl"},svg); el("text",{x:m.l-6,y:Y(v)+4,"text-anchor":"end"},svg).textContent=(v*100)+"%"; el("text",{x:X(v),y:H-18,"text-anchor":"middle"},svg).textContent=(v*100)+"%"; });
  el("text",{x:(W+m.l)/2,y:H-3,"text-anchor":"middle"},svg).textContent="predicted chance of rising";
  el("line",{x1:X(0),y1:Y(0),x2:X(1),y2:Y(1),stroke:css("--ink3"),"stroke-dasharray":"4,4"},svg);
  el("path",{d:pts.map((p,i)=>(i?"L":"M")+X(p.pred)+","+Y(p.actual)).join(""),fill:"none",stroke:css("--accent"),"stroke-width":2},svg);
  pts.forEach(p=>{ const c=el("circle",{cx:X(p.pred),cy:Y(p.actual),r:5,fill:css("--accent")},svg); c.addEventListener("mousemove",e=>showTip(e,`predicted ${(p.pred*100).toFixed(1)}% · actual ${(p.actual*100).toFixed(1)}% · n=${p.n}`)); c.addEventListener("mouseleave",hideTip); });
  legend(host,[{label:"Model",color:css("--accent")},{label:"Perfect calibration",color:css("--ink3")}]);
}


// ---------- header
$("#meta").textContent = `Data as of ${R.data_date} · generated ${R.generated} (${R.mode} run) · backtest ${R.backtest_generated||"n/a"} · ${R.predictions.length} stocks · ${R.n_features} features`;
if (R.demo) $("#demo").innerHTML = `<div class="banner"><b>Demo run on synthetic data.</b> Companies and prices are simulated to verify the pipeline and show the layout.</div>`;
const rg = R.regime_now||{};
$("#regime").innerHTML = `<span class="rchip r-${esc(rg.regime)}">${esc(rg.regime)} market</span><span class="rchip ${rg.high_vol?"r-hv":""}">${rg.high_vol?"High volatility":"Normal volatility"}</span>
  <span class="note">S&amp;P 500 ${pct(rg.spx_drawdown,1)} from 1-yr high · ${rg.breadth_above200==null?"":(rg.breadth_above200*100).toFixed(0)+"% of stocks above 200-day avg"} · VIX ${rg.vix==null?"n/a":rg.vix.toFixed(1)} · universe: ${R.universe?.universe??"?"} stocks screened from ${R.universe?.candidates??"?"}</span>`;
$("#strip").innerHTML = (R.market||[]).map(m => `<div class="tick"><div class="n">${esc(m.name)}</div><div class="v num">${m.last.toLocaleString(undefined,{maximumFractionDigits:2})}</div><div class="num" style="font-size:12px"><span class="${cls(m.chg1d)}">${pct(m.chg1d,2)} 1d</span> · <span class="${cls(m.chg1m)}">${pct(m.chg1m,1)} 1m</span></div></div>`).join("");

// ---------- tabs
document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => showTab(b.dataset.tab));
function showTab(t){
  document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab===t));
  ["picks","screener","detail","backtest","model"].forEach(x => $("#tab-"+x).hidden = x!==t);
  ({picks:renderList, screener:renderScreener, detail:renderDetail, backtest:renderBacktest, model:renderModel})[t]();
  try{ history.replaceState(null,"","#"+t) }catch(e){}
}
function seg(id, key, cb, opts=HZ, names=HZNAME){
  const el = $(id);
  el.innerHTML = opts.map(h => `<button aria-pressed="${state[key]===h}" data-h="${h}">${names[h]}</button>`).join("");
  el.querySelectorAll("button").forEach(b => b.onclick = () => { state[key]=b.dataset.h; seg(id,key,cb,opts,names); cb(); });
}
const pill = c => `<span class="pill ${c}">${c}</span>`;
function pbar(p, base){ return `<span class="pbar"><span class="num">${(p*100).toFixed(0)}%</span><span class="track"><span class="fill" style="width:${p*100}%"></span>${base!=null?`<span class="mid" style="left:${base*100}%"></span>`:""}</span></span>`; }
const tickCell = t => `<a href="#detail" class="tk" data-go="${esc(t)}">${esc(t)}</a>`;
function wireGo(root){ root.querySelectorAll("[data-go]").forEach(a => a.onclick = e => { e.preventDefault(); state.pick=a.dataset.go; $("#pick").value=state.pick; showTab("detail"); }); }

// ---------- top lists
const LISTS = {
  opportunities_30d: ["Next 30 days", "Published bullish 1-month forecasts (Medium/High confidence), ranked by edge over the base rate × confidence, adjusted for risk. Empty means nothing cleared the bar today."],
  highest_probability: ["Highest probability", "Highest chance of a higher price in 1 month. Published forecasts come first; greyed rows are below the confidence threshold."],
  low_risk_growth: ["Low-risk growth", "Risk rating ≤ 4/10 with above-median growth, ranked by growth, quality and low risk, nudged by the 3-month outlook."],
  momentum: ["Momentum", "Stocks in uptrends ranked by 12-1 month momentum, 3-month relative strength, distance above the 200-day average and 6-month Sharpe. A factual screen, not a forecast."],
  compounders: ["Long-term compounders", "Ranked by fundamental quality (growth, profitability, cash flow, balance sheet, stability) and 5-year compounded return."],
};
function renderList(){
  seg("#listseg","list",renderList,Object.keys(LISTS),Object.fromEntries(Object.entries(LISTS).map(([k,v])=>[k,v[0]])));
  $("#listdesc").textContent = LISTS[state.list][1];
  const rows = R.rankings[state.list] || [];
  $("#listt").innerHTML = `<thead><tr><th class="l">#</th><th class="l">Stock</th><th class="l">Company</th><th class="l">Why it's here</th><th>P(up) 1m</th><th>Median 1m</th><th>Confidence</th><th>Risk</th><th>Quality</th></tr></thead><tbody>` +
    (rows.length ? rows.map((r,i) => { const p = P[r.ticker], pub = p?.horizons[R.primary]?.published;
      return `<tr class="${pub?"":"dim"}"><td class="l">${i+1}</td><td class="l">${tickCell(r.ticker)}</td><td class="l nm">${esc(r.name)}</td><td class="l why">${esc(r.why)}</td><td>${pbar(r.p_up, p?.horizons[R.primary]?.base_rate)}</td><td class="num ${cls(r.exp_move)}">${pct(r.exp_move)}</td><td>${pill(r.conf)}</td><td class="num">${r.risk}/10</td><td class="num">${r.quality==null?"–":r.quality.toFixed(0)}</td></tr>`; }).join("")
    : `<tr><td colspan="9" class="l note">No stock clears the confidence threshold for this list today. That's the model declining to guess, by design.</td></tr>`) +
    (state.list==="opportunities_30d" && (R.rankings.near_threshold||[]).length ? `<tr><td colspan="9" class="l"><h3 style="margin-top:10px">Closest to the threshold (not published)</h3></td></tr>` +
      R.rankings.near_threshold.map((r,i)=>`<tr class="dim"><td class="l">–</td><td class="l">${tickCell(r.ticker)}</td><td class="l nm">${esc(r.name)}</td><td class="l why">${esc(r.why)}</td><td>${pbar(r.p_up, P[r.ticker]?.horizons[R.primary]?.base_rate)}</td><td class="num ${cls(r.exp_move)}">${pct(r.exp_move)}</td><td>${pill(r.conf)}</td><td class="num">${r.risk}/10</td><td class="num">${r.quality==null?"–":r.quality.toFixed(0)}</td></tr>`).join("") : "") + "</tbody>";
  wireGo($("#listt"));
}

// ---------- screener
const groups = ["All","Watchlist","S&P 500","Nasdaq-100","Dow 30","Global blue chip"];
$("#f-group").innerHTML = groups.map(g=>`<option>${g}</option>`).join("");
["#f-group","#f-sort","#f-pub","#f-q"].forEach(id => $(id).addEventListener("input", renderScreener));
function renderScreener(){
  seg("#hz-scr","scr",renderScreener);
  const h = state.scr, g = $("#f-group").value, q = $("#f-q").value.trim().toLowerCase(), pub = $("#f-pub").checked, key = $("#f-sort").value;
  let rows = R.predictions.filter(p => (g==="All" || p.groups.includes(g)) && (!pub || p.horizons[h].published) && (!q || p.ticker.toLowerCase().includes(q) || String(p.name).toLowerCase().includes(q)));
  const cn = {High:3, Medium:2, Low:1};
  const val = p => { const x=p.horizons[h], f=p.fundamentals||{};
    return {p_up:x.p_up, risk_adj:x.risk_adj, conf:cn[x.confidence]*10+Math.abs(x.edge), downside:x.band[0], quality:f.quality??0, gs:Math.sqrt(Math.max(f.growth??0,0)*Math.max(f.stability??0,0))}[key]; };
  rows.sort((a,b) => val(b)-val(a));
  $("#scr-count").textContent = `${rows.length} stocks · ${rows.filter(p=>p.horizons[h].published).length} with published ${HZNAME[h]} forecasts`;
  $("#scrt").innerHTML = `<thead><tr><th class="l">Stock</th><th class="l">Company</th><th class="l">Trend</th><th>P(up)</th><th>P(down)</th><th>Exp. change</th><th>80% band</th><th>Confidence</th><th>Similar setups</th><th>Risk</th><th>Size*</th><th>R/R</th><th>Quality</th></tr></thead><tbody>` +
    rows.map(p => { const x=p.horizons[h], s=x.setup;
      return `<tr class="${x.published?"":"dim"}"><td class="l">${tickCell(p.ticker)}</td><td class="l nm">${esc(p.name)}</td><td class="l">${esc(p.trend)}</td><td>${pbar(x.p_up,x.base_rate)}</td><td class="num">${(x.p_down*100).toFixed(0)}%</td>
      <td class="num ${cls(x.exp_move)}">${pct(x.exp_move)}</td><td class="num">${pct(x.band[0])} / ${pct(x.band[1])}</td><td>${pill(x.confidence)}</td>
      <td class="num">${s?`${(s.hit*100).toFixed(0)}% <span class="note">n=${s.n.toLocaleString()}</span>`:"–"}</td><td class="num">${p.risk_rating}/10</td><td class="num">${h===R.primary?pct(p.position.weight,1,false):"–"}</td><td class="num">${x.rr==null?"–":x.rr.toFixed(2)}</td><td class="num">${p.fundamentals?.quality==null?"–":p.fundamentals.quality.toFixed(0)}</td></tr>`; }).join("") + "</tbody>";
  wireGo($("#scrt"));
}

// ---------- detail
$("#pick").innerHTML = [...R.predictions].sort((a,b)=>a.ticker.localeCompare(b.ticker)).map(p => `<option value="${esc(p.ticker)}">${esc(p.ticker)} · ${esc(p.name)}</option>`).join("");
$("#pick").onchange = e => { state.pick = e.target.value; renderDetail(); };
function renderDetail(){
  seg("#hz-det","det",renderDetail);
  const p = P[state.pick] || R.predictions[0]; $("#pick").value = p.ticker;
  const f = p.fundamentals||{}, rs = p.risk_stats||{};
  $("#dhead").innerHTML = `<div class="dh"><div><h2>${esc(p.ticker)} · ${esc(p.name)}</h2><div class="sub">${esc(p.sector||"")} ${f.industry?"· "+esc(f.industry):""} · ${p.groups.map(esc).join(", ")}</div></div>
    <div class="dhk"><div><span class="note">Price</span><b class="num">${p.price.toFixed(2)}</b></div><div><span class="note">Trend</span><b>${esc(p.trend)}</b></div><div><span class="note">Risk rating</span><b class="num">${p.risk_rating}/10</b></div>
    <div><span class="note">Illustrative size*</span><b class="num">${pct(p.position.weight,1,false)}</b></div><div><span class="note">Momentum</span><b class="num">${p.momentum_score==null?"–":p.momentum_score.toFixed(0)}/100</b></div></div></div>
    <p class="lead" style="margin:10px 0 0">${esc(p.summary)}</p><p class="note">${esc(p.explanation)} *Size basis: ${esc(p.position.basis)}.</p>`;
  $("#hcards").innerHTML = HZ.map(h => { const x = p.horizons[h], s = x.setup;
    return `<div class="hcard ${x.published?"":"dimcard"}"><div class="hh"><h3>${HZNAME[h]}</h3>${pill(x.confidence)}</div>
      <div class="pud"><span class="big num pos">${(x.p_up*100).toFixed(0)}%</span><span class="num neg">${(x.p_down*100).toFixed(0)}% down</span></div>
      <div class="split"><span class="u" style="width:${x.p_up*100}%"></span><span class="d" style="width:${x.p_down*100}%"></span></div>
      <dl class="kv"><dt>Typical up-rate</dt><dd class="num">${(x.base_rate*100).toFixed(0)}%</dd>
      <dt>Expected change</dt><dd class="num ${cls(x.exp_move)}">${pct(x.exp_move)}</dd>
      <dt>80% band</dt><dd class="num">${pct(x.band[0])} to ${pct(x.band[1])}</dd>
      <dt>Risk / reward</dt><dd class="num">${x.rr==null?"–":x.rr.toFixed(2)}</dd>
      <dt>P(&gt;+5 / +10 / +20%)</dt><dd class="num">${["5","10","20"].map(k=>pct(x.p_gain[k],0,false)).join(" / ")}</dd></dl>
      <div class="setup">Ranks in the <b>${esc(x.bucket)}</b> of the universe (${(x.rank*100).toFixed(0)}th pct).<br>${s?(x.bucket.startsWith("Middle")?`Past stocks in this bucket (${esc(s.scope.toLowerCase())}) rose ${(s.hit*100).toFixed(0)}% of the time · n=${s.n.toLocaleString()}`:`Similar past calls (${esc(s.scope.toLowerCase())}): <b>${(s.hit*100).toFixed(0)}% right</b> vs ${(s.side_base*100).toFixed(0)}% base rate · n=${s.n.toLocaleString()}`):"No comparable history yet."}</div>
      ${x.published?"":`<div class="note">Below the confidence threshold. Shown for reference, not published.</div>`}
      ${x.earnings_in_window?`<div class="note">Earnings inside this window: band widened.</div>`:""}</div>`; }).join("");
  const c = p.chart, up=css("--up"), down=css("--down"), acc=css("--accent"), ink3=css("--ink3");
  const lvl = (v,col,lab) => ({label:lab, data:c.dates.map(()=>v), color:col, dash:"5,4", width:1});
  lineChart("c-price", {labels:c.dates, xTicks:5, xfmt:d=>new Date(d+"T00:00").toLocaleDateString(undefined,{month:"short",day:"numeric"}), yfmt:v=>(+v).toFixed(2), series:[
    {label:"Close", data:c.close, color:acc, width:2}, {label:"50-day", data:c.sma50, color:css("--warn"), width:1.2}, {label:"200-day", data:c.sma200, color:ink3, width:1.2},
    ...(c.support||[]).slice(0,1).map(v=>lvl(v,up,"Support")), ...(c.resistance||[]).slice(0,1).map(v=>lvl(v,down,"Resistance"))]});
  const x = p.horizons[state.det], mu = x.exp_move, s = (x.band[1]-x.band[0])/(2*1.2816);
  const xs=[], ys=[]; for (let i=0;i<=120;i++){ const v=mu-3.5*s+7*s*i/120; xs.push(v); ys.push(Math.exp(-0.5*((v-mu)/s)**2)); }
  lineChart("c-dist", {labels:xs, xfmt:v=>(v*100).toFixed(1)+"%", hideY:true, ymin:0, legendOn:false, xTicks:7, yfmt:v=>(+v).toFixed(2), series:[
    {label:"Up", data:ys.map((y,i)=>xs[i]>=0?y:null), color:up, fill:true, width:1.5}, {label:"Down", data:ys.map((y,i)=>xs[i]<=0?y:null), color:down, fill:true, width:1.5}]});
  $("#dist-title").textContent = `Forecast distribution · ${HZNAME[state.det]}`;
  $("#dist-note").textContent = `Centre ${pct(mu)}; shaded band holds ~80% of outcomes in backtests (${pct(x.band[0])} to ${pct(x.band[1])}).`;
  $("#bull").innerHTML = p.bullish.map(b=>`<li>${esc(b)}</li>`).join("") || "<li>None stand out.</li>";
  $("#bear").innerHTML = p.bearish.map(b=>`<li>${esc(b)}</li>`).join("") || "<li>None stand out.</li>";
  $("#evid").innerHTML = `<thead><tr><th class="l">Component</th><th>Its probability</th><th>Earned weight</th></tr></thead><tbody>` +
    x.evidence.map(e => `<tr class="${e.weight>0?"":"dim"}"><td class="l">${esc(COMPLABEL[e.component]||e.component)}</td><td class="num">${(e.p*100).toFixed(1)}%</td><td class="num">${e.weight>0?e.weight.toFixed(2):"off"}</td></tr>`).join("") +
    (Object.keys(x.overlay||{}).length ? `<tr><td class="l">Live overlays (log-odds)</td><td class="num" colspan="2">${Object.entries(x.overlay).map(([k,v])=>`${k.replace("_"," ")} ${v>=0?"+":""}${v.toFixed(2)}`).join(" · ")}</td></tr>` : "") + "</tbody>";
  $("#drivers").innerHTML = `<thead><tr><th class="l">Feature</th><th>Value</th><th>Push</th></tr></thead><tbody>` + (p.top_drivers||[]).map(d=>`<tr><td class="l">${esc(d.feature)}</td><td class="num">${esc(d.value)}</td><td class="num ${cls(d.impact)}">${d.impact>0?"▲":"▼"} ${Math.abs(d.impact).toFixed(3)}</td></tr>`).join("") + "</tbody>";
  const qk = [["growth","Growth"],["profitability","Profitability"],["cash_flow","Cash flow"],["balance_sheet","Balance sheet"],["stability","Stability"],["valuation","Valuation"],["quality","Overall quality"]];
  hbarChart("c-qual", {labels:qk.map(q=>q[1]), values:qk.map(q=>f[q[0]]??50), colors:qk.map(q=>q[0]==="quality"?acc:css("--ink3")), xfmt:v=>v.toFixed(0)});
  $("#fundkv").innerHTML = [["Market cap",fmtCap(f.marketCap)],["Revenue growth",pct(f.revenueGrowth,0)],["Earnings growth",pct(f.earningsGrowth,0)],["Return on equity",pct(f.returnOnEquity,0,false)],
    ["Operating margin",pct(f.operatingMargins,0,false)],["FCF margin",pct(f.fcf_margin,0,false)],["Debt / equity",f.debtToEquity==null?"n/a":(f.debtToEquity/100).toFixed(2)+"x"],["Forward P/E",f.forwardPE==null?"n/a":f.forwardPE.toFixed(1)],
    ["1-yr volatility",pct(rs.vol_1y,0,false)],["Max drawdown (3y)",pct(rs.max_dd_3y,0)],["5-yr CAGR",pct(rs.cagr_5y,1)],["Beta",rs.beta==null?"n/a":rs.beta.toFixed(2)]].map(([k,v])=>`<dt>${k}</dt><dd class="num">${v}</dd>`).join("");
  const L = p.live;
  if (!L){ $("#live").innerHTML = `<p class="note">Not collected for this stock in this run (live signals are fetched for the watchlist and the strongest model calls).</p>`; return; }
  const sc = v => `<span class="num ${cls(v)}">${v>=0?"+":""}${(v||0).toFixed(2)}</span>`; const n=L.news||{}, a=L.analyst||{}, o=L.options||{}, ins=L.institutional||{};
  $("#live").innerHTML = `<h3 style="margin-top:6px">News ${sc(n.score)}</h3><ul class="f">${(n.headlines||[]).map(hd=>`<li>${hd.url?`<a href="${esc(hd.url)}" target="_blank" rel="noopener">${esc(hd.title)}</a>`:esc(hd.title)} <span class="note">${esc(hd.source||"")} ${sc(hd.score)}</span></li>`).join("")||"<li>No recent headlines.</li>"}</ul>
    <dl class="kv" style="margin-top:8px"><dt>Analyst consensus ${sc(a.score)}</dt><dd>${esc(a.rating||"n/a")}</dd><dt>Target vs price</dt><dd class="num">${pct(a.target_upside,0)}</dd><dt>Net up/downgrades (30d)</dt><dd class="num">${a.net_upgrades_30d??"n/a"}</dd>
    <dt>Options ${sc(o.score)}: put/call vol</dt><dd class="num">${o.put_call_vol?.toFixed(2)??"n/a"}</dd><dt>Implied ÷ realised vol</dt><dd class="num">${o.iv_vs_rv?.toFixed(2)??"n/a"}</dd><dt>Unusual options activity</dt><dd>${o.unusual?"Yes":"No"}</dd>
    <dt>Institutions ${sc(ins.score)}: held</dt><dd class="num">${pct(ins.inst_pct,0,false)}</dd><dt>Net insider $ (6m)</dt><dd class="num ${cls(ins.insider_net_6m)}">${ins.insider_net_6m==null?"n/a":(ins.insider_net_6m/1e6).toFixed(1)+"M"}</dd></dl>`;
}

// ---------- backtest
function renderBacktest(){
  const B = R.backtest, f3 = v => v==null||isNaN(v) ? "–" : v.toFixed(3);
  $("#btt").innerHTML = `<thead><tr><th class="l">Horizon</th><th>Test period</th><th>Predictions</th><th>Accuracy</th><th>Naive</th><th>Precision</th><th>Recall</th><th>AUC</th><th>Ranking AUC</th><th>Brier skill</th><th>Published</th><th>Published accuracy</th><th>80% band held</th></tr></thead><tbody>` +
    HZ.filter(h=>B[h]).map(h=>{ const m=B[h].metrics; return `<tr><td class="l">${HZNAME[h]}</td><td class="num">${m.start} → ${m.end}</td><td class="num">${m.n.toLocaleString()}</td><td class="num">${pct(m.accuracy,1,false)}</td><td class="num">${pct(m.naive_accuracy,1,false)}</td><td class="num">${pct(m.precision,1,false)}</td><td class="num">${pct(m.recall,1,false)}</td><td class="num">${f3(m.auc)}</td><td class="num ${m.ranking_auc>0.51?"pos":m.ranking_auc<0.5?"neg":""}">${f3(m.ranking_auc)}</td><td class="num ${cls(m.brier_skill)}">${pct(m.brier_skill,1)}</td><td class="num">${pct(m.published_share,0,false)}</td><td class="num">${pct(m.published_accuracy,1,false)}</td><td class="num">${pct(m.band_coverage,0,false)}</td></tr>`; }).join("") + "</tbody>";
  const best = HZ.filter(h=>B[h]).sort((a,b)=>(B[b].metrics.ranking_auc||0)-(B[a].metrics.ranking_auc||0))[0];
  const bm = B[best].metrics;
  $("#bt-lead").textContent = bm.ranking_auc < 0.51
    ? `No horizon shows a meaningful out-of-sample edge (best ranking AUC ${f3(bm.ranking_auc)} at ${HZNAME[best]}). The model therefore publishes few or no forecasts and keeps probabilities near the base rate.`
    : `Strongest evidence is at ${HZNAME[best]}: ranking AUC ${f3(bm.ranking_auc)}; published calls were right ${pct(bm.published_accuracy,1,false)} of the time vs ${pct(bm.naive_accuracy,1,false)} naive, on ${pct(bm.published_share,0,false)} of opportunities. Small edges like this are normal and can fade.`;
  seg("#hz-bt","bt",renderBacktest);
  const b = B[state.bt] || B[best]; const acc=css("--accent"), ink3=css("--ink3"), up=css("--up"), down=css("--down");
  $("#segt").innerHTML = `<thead><tr><th class="l">Condition</th><th>Predictions</th><th>Up-rate</th><th>Accuracy</th><th>Naive</th><th>Precision</th><th>Recall</th><th>AUC</th><th>Ranking AUC</th><th>Published</th><th>Published accuracy</th></tr></thead><tbody>` +
    b.segments.map(s=>`<tr><td class="l">${esc(s.segment)}</td><td class="num">${s.n.toLocaleString()}</td><td class="num">${pct(s.base_rate,0,false)}</td><td class="num">${pct(s.accuracy,1,false)}</td><td class="num">${pct(s.naive_accuracy,1,false)}</td><td class="num">${pct(s.precision,1,false)}</td><td class="num">${pct(s.recall,1,false)}</td><td class="num">${f3(s.auc)}</td><td class="num">${f3(s.ranking_auc)}</td><td class="num">${pct(s.published_share,0,false)}</td><td class="num">${pct(s.published_accuracy,1,false)}</td></tr>`).join("") + "</tbody>";
  const S = b.strategy;
  lineChart("c-eq", {labels:S.curve.map(e=>e.date), xTicks:4, xfmt:d=>new Date(d+"T00:00").toLocaleDateString(undefined,{month:"short",year:"2-digit"}), yfmt:v=>(+v).toFixed(2)+"×", series:[
    {label:"Published bullish calls", data:S.curve.map(e=>e.strategy), color:acc, width:2}, {label:"Equal-weight universe", data:S.curve.map(e=>e.benchmark), color:ink3, width:1.5}]});
  lineChart("c-dd", {labels:S.curve.map(e=>e.date), xTicks:4, xfmt:d=>new Date(d+"T00:00").toLocaleDateString(undefined,{month:"short",year:"2-digit"}), yfmt:v=>(v*100).toFixed(0)+"%", ymax:0, legendOn:false, series:[{label:"Drawdown", data:S.curve.map(e=>e.dd), color:down, fill:true, width:1.2}]});
  const row = (n,o) => `<tr><td class="l">${n}</td><td class="num ${cls(o.ann_return)}">${pct(o.ann_return,1)}</td><td class="num">${pct(o.ann_vol,1,false)}</td><td class="num">${o.sharpe.toFixed(2)}</td><td class="num neg">${pct(o.max_drawdown,1)}</td><td class="num">${pct(o.win_rate,0,false)}</td></tr>`;
  $("#stratt").innerHTML = `<thead><tr><th class="l">Portfolio</th><th>Ann. return</th><th>Volatility</th><th>Sharpe</th><th>Max drawdown</th><th>Win rate</th></tr></thead><tbody>${row("Published bullish calls",S.strategy)}${row("Equal-weight universe",S.benchmark)}${row("Top-minus-bottom quintile",S.long_short)}</tbody>` +
    `<caption class="note" style="caption-side:bottom;text-align:left;padding-top:6px">Invested ${pct(S.invested_share,0,false)} of periods · avg ${S.avg_positions.toFixed(1)} positions · position hit rate ${pct(S.position_hit_rate,0,false)}</caption>`;
  $("#compt").innerHTML = `<thead><tr><th class="l">Component</th><th>Weight now</th><th>Recent AUC</th><th>Full-history AUC</th><th class="l">Status</th></tr></thead><tbody>` +
    b.components.map(c=>`<tr class="${c.weight>0?"":"dim"}"><td class="l">${esc(c.label)}</td><td class="num">${c.weight.toFixed(2)}</td><td class="num">${f3(c.recent_auc)}</td><td class="num">${f3(c.full_auc)}</td><td class="l"><span class="pill ${c.status==="Active"?"High":c.status==="Reduced"?"Medium":"Low"}">${esc(c.status)}</span></td></tr>`).join("") + "</tbody>";
  const wh = b.weights_history||[], keys = b.components.map(c=>c.key), pal=[acc,up,css("--warn"),down,ink3,"#7a68b3"];
  if (wh.length) lineChart("c-wh", {labels:wh.map(w=>w.start), xTicks:4, yfmt:v=>(+v).toFixed(2), ymin:0, series:keys.map((k,i)=>({label:COMPLABEL[k]||k, data:wh.map(w=>+w[k]||0), color:pal[i%pal.length], width:1.6}))});
  calChart("c-cal", b.calibration);
  $("#gaint").innerHTML = `<thead><tr><th class="l">Threshold</th><th>Formula (avg)</th><th>Actual</th><th>Correction applied</th></tr></thead><tbody>` + b.gain_calibration.map(g=>`<tr><td class="l">+${g.threshold}%</td><td class="num">${pct(g.predicted,1,false)}</td><td class="num">${pct(g.actual,1,false)}</td><td class="num">×${(g.scale??1).toFixed(2)}</td></tr>`).join("") + "</tbody>";
}

// ---------- model
function renderModel(){
  const I = R.importance||{}; const acc=css("--accent"), pal=[acc,css("--up"),css("--warn"),css("--down"),css("--ink3"),"#5b8fa8","#8a6fb0","#9c8b5e","#6f9a6a","#b07a5a","#5a7ab0","#a0a05a","#7aa0a0","#a07aa0"];
  if (I.families){ hbarChart("c-impfam", {labels:I.families.map(f=>f.family), values:I.families.map(f=>f.share*100), colors:I.families.map((_,i)=>pal[i%pal.length]), xfmt:v=>v.toFixed(0)+"%"});
    hbarChart("c-imp", {labels:I.features.map(f=>f.label||f.feature), values:I.features.map(f=>f.importance), colors:[acc], xfmt:v=>v.toFixed(4)}); }
  const C = R.rules.confidence, Ps = R.rules.position;
  $("#rules").innerHTML = `<ul class="f">
    <li><b>High</b>: the stock ranks in the top (or bottom) 10% of the universe, its probability is ≥ ${(C.high.min_edge*100).toFixed(0)} pts above (below) the typical up-rate, and past calls from the same bucket beat their base rate by ≥ ${(C.high.setup_edge*100).toFixed(1)} pts on ≥ ${C.high.min_n} cases.</li>
    <li><b>Medium</b>: top/bottom 25%, ≥ ${(C.medium.min_edge*100).toFixed(0)} pt edge, and the bucket beat its base rate by ≥ ${(C.medium.setup_edge*100).toFixed(1)} pts on ≥ ${C.medium.min_n} cases.</li>
    <li><b>Low</b>: anything else. Not published; shown greyed for reference. High is capped at Medium when earnings fall inside the window.</li>
    <li><b>Uncertainty band</b>: sized so ${(R.rules.band*100).toFixed(0)}% of backtest outcomes landed inside it.</li>
    <li><b>Illustrative size</b>: ${(Ps.risk_per_idea*100).toFixed(1)}% portfolio risk ÷ the band's 1-month downside, × ${Ps.conf_mult.High} (High) or ${Ps.conf_mult.Medium} (Medium), capped at ${(Ps.max_weight*100).toFixed(0)}%. Zero without a published bullish forecast. A sizing rule, not advice.</li>
    <li><b>Risk rating 1–10</b>: universe percentile of volatility, drawdown, downside beta, forecast downside and leverage.</li></ul>`;
  $("#method").innerHTML = `
    <li><b>Universe:</b> S&amp;P 500, Nasdaq-100, Dow 30 and global blue chips, screened for market cap ≥ $30B, profitability, positive free cash flow and moderate debt, then ranked by quality. Your watchlist is always included.</li>
    <li><b>Evidence:</b> ${R.n_features} point-in-time features: price and volume, RSI/MACD/Bollinger/ATR/ADX/moving averages, chart patterns and support/resistance, momentum, sector and relative strength, sector rotation, market regime (bull/bear/sideways, volatility), breadth, rates, inflation, unemployment/recession signals, GDP, and earnings surprises.</li>
    <li><b>Ensemble:</b> five stock-selection components (technical, relative strength, earnings, time-series, linear all-factor) predict whether a stock beats the average stock; one market-timing component predicts market direction. Each earns a weight from its out-of-sample record (the worse of recent and full-history AUC), and components below the bar are switched off automatically.</li>
    <li><b>Calibration:</b> the blend is isotonic-calibrated on earlier out-of-sample results; expected change and bands come from an EWMA volatility forecast calibrated to hold 80% of outcomes; big-move odds use a drift-diffusion formula checked against actual hit rates.</li>
    <li><b>Backtest:</b> walk-forward across the whole history (bull, bear, high-volatility, earnings-season and downturn periods), with accuracy, precision, recall, AUC, ranking AUC, Brier skill, and a signal portfolio's Sharpe, drawdown and win rate.</li>
    <li><b>Fundamentals</b> (quality, growth, balance sheet) come from today's snapshot and drive the universe screen and the quality lists. They are not in the backtested model, to avoid look-ahead bias.</li>
    <li><b>Live overlays</b> (news, analysts, options, insiders) can't be backtested with free data; they nudge probabilities by a small capped amount.</li>
    <li><b>Limits:</b> short-term returns are mostly noise; expect small edges, no costs or taxes modelled, and past performance may not repeat.</li>`;
}

renderList();
const start = (location.hash||"").slice(1);
if (["screener","detail","backtest","model"].includes(start)) showTab(start);
const rerender = () => { const t=document.querySelector('.tabs [aria-selected="true"]').dataset.tab; showTab(t); };
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", rerender);
let rz; addEventListener("resize", () => { clearTimeout(rz); rz=setTimeout(rerender, 200); });

</script>
</body>
</html>
"""
