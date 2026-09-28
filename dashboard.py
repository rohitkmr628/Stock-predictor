"""Write a self-contained HTML dashboard from results.json data."""
from __future__ import annotations

import json


def write(results: dict, path: str) -> None:
    payload = json.dumps(results, default=str).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", payload)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)


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
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Odds Board</h1>
      <div class="sub" id="meta"></div>
    </div>
    <div class="note" style="max-width:480px">Probabilities from a backtested model, not advice. Stock moves are mostly noise; read the Backtest tab before trusting any number.</div>
  </header>
  <div id="demo"></div>
  <div class="strip" id="strip"></div>
  <nav class="tabs" role="tablist">
    <button role="tab" aria-selected="true" data-tab="overview">Overview</button>
    <button role="tab" aria-selected="false" data-tab="detail">Stock detail</button>
    <button role="tab" aria-selected="false" data-tab="scanner">Big-move scanner</button>
    <button role="tab" aria-selected="false" data-tab="backtest">Backtest &amp; model</button>
  </nav>

  <section id="tab-overview">
    <div class="bar">
      <div class="seg" id="hz-overview"></div>
      <span class="note">Click a column to sort · click a row for details</span>
    </div>
    <div class="panel tbl"><table id="ovt"></table></div>
  </section>

  <section id="tab-detail" hidden>
    <div class="bar">
      <select id="pick" aria-label="Stock"></select>
      <div class="seg" id="hz-detail"></div>
    </div>
    <div class="stack">
      <div class="grid g3" id="hcards"></div>
      <div class="grid g2">
        <div class="panel"><h3>Price, moving averages, support &amp; resistance</h3><div class="chart"><div class="svgc" id="c-price"></div></div></div>
        <div class="panel"><h3 id="dist-title">Probability distribution</h3><div class="chart"><div class="svgc" id="c-dist"></div></div><div class="note" id="dist-note"></div></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3>Outlook</h3><p class="lead" id="o-short"></p><p class="lead" id="o-med"></p><p class="note" id="o-why"></p></div>
        <div class="panel"><h3>Risk assessment</h3><div id="risk"></div></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3 class="pos">Bullish factors</h3><ul class="f" id="bull"></ul></div>
        <div class="panel"><h3 class="neg">Bearish factors</h3><ul class="f" id="bear"></ul></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3>What moved this prediction (factor groups)</h3><div class="chart sm"><div class="svgc" id="c-fam"></div></div></div>
        <div class="panel"><h3>Top individual drivers</h3><div class="tbl"><table id="drivers"></table></div></div>
      </div>
      <div class="panel"><h3>Live signals (not backtested)</h3><div class="grid g2" id="live" style="margin-top:8px"></div></div>
    </div>
  </section>

  <section id="tab-scanner" hidden>
    <div class="bar"><div class="seg" id="hz-scanner"></div><span class="note">Chance the price closes above each threshold at any point within the period</span></div>
    <div class="grid g3" id="gainlists"></div>
    <div class="panel tbl" style="margin-top:14px"><h3 style="margin-bottom:8px">Ranked by risk-adjusted expected return (median move ÷ predicted volatility)</h3><table id="rat"></table></div>
  </section>

  <section id="tab-backtest" hidden>
    <div class="stack">
      <div class="panel"><h2>How well did it work out of sample?</h2>
        <p class="lead" id="bt-summary"></p>
        <div class="tbl"><table id="btt"></table></div>
        <p class="note">Walk-forward test: the model is retrained every quarter and only ever predicts dates it has not seen, with a gap equal to the horizon so outcomes never leak. "Naive" always guesses the more common direction.</p>
      </div>
      <div class="bar"><div class="seg" id="hz-bt"></div></div>
      <div class="grid g2">
        <div class="panel"><h3>Calibration: predicted vs actual chance of rising</h3><div class="chart"><div class="svgc" id="c-cal"></div></div></div>
        <div class="panel"><h3>Average forward return by prediction quintile</h3><div class="chart"><div class="svgc" id="c-quint"></div></div><div class="note">If the model ranks well, quintile 5 (most bullish) should beat quintile 1.</div></div>
      </div>
      <div class="grid g2">
        <div class="panel"><h3>Signal check: names with P(up) &gt; 55% vs equal-weight all</h3><div class="chart"><div class="svgc" id="c-eq"></div></div><div class="note">Non-overlapping periods, no costs or slippage. Illustrative only.</div></div>
        <div class="panel"><h3>Feature importance by factor group</h3><div class="chart"><div class="svgc" id="c-impfam"></div></div></div>
      </div>
      <div class="panel"><h3>Top 20 features (drop in AUC when shuffled)</h3><div class="chart" style="height:460px"><div class="svgc" id="c-imp"></div></div></div>
      <div class="panel"><h2>Method</h2>
        <ul class="f">
          <li><b>Data:</b> daily OHLCV, sector ETFs, S&amp;P 500 / Nasdaq / Dow / Russell, VIX, Treasury yields, oil, gold, dollar, credit, and FRED macro (CPI, unemployment, fed funds, consumer sentiment, GDP) lagged to release dates.</li>
          <li><b>Features:</b> <span id="nfeat"></span> indicators including RSI, MACD, Bollinger Bands, moving averages, stochastics, ATR, ADX, volume flow, trend-line regressions, rule-based chart patterns (double tops/bottoms, head &amp; shoulders, cup &amp; handle, flags, triangles, breakouts, support/resistance), relative strength vs sector and market, and an EWMA volatility forecast.</li>
          <li><b>Models:</b> gradient-boosted trees + logistic regression for direction (isotonic-calibrated), gradient-boosted quantile regression for the 10th/50th/90th percentile move, and one classifier per gain threshold.</li>
          <li><b>Honesty controls:</b> each prediction is shrunk toward the historical base rate in proportion to the model's out-of-sample AUC, and the move range is rescaled so it would have held 80% of outcomes in the backtest.</li>
          <li><b>Live overlays:</b> news sentiment, analyst targets and rating changes, options put/call and unusual activity, and insider/institutional data nudge the probability by a small capped amount. They are not backtested.</li>
        </ul>
      </div>
    </div>
  </section>
</div>

<script>
const R = __DATA__;
const HZ = Object.keys(R.horizons);
const HZNAME = {"1d":"1 day","1w":"1 week","1m":"1 month"};
const state = {ov:"1w", det:"1w", scan:"1m", bt:"1w", sort:{k:"p_up", dir:-1}, pick: R.predictions[0]?.ticker};
const $ = s => document.querySelector(s);
const pct = (v,d=1,s=true) => v==null||isNaN(v) ? "n/a" : (s&&v>0?"+":"") + (v*100).toFixed(d) + "%";
const cls = v => v>0 ? "pos" : v<0 ? "neg" : "";
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

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
// header
$("#meta").textContent = `Data as of ${R.data_date} · generated ${R.generated} · ${R.predictions.length} stocks · ${R.n_features} features`;
if (R.demo) $("#demo").innerHTML = `<div class="banner"><b>Demo run on synthetic data.</b> Tickers and prices are simulated to show the layout and verify the pipeline. Run <span class="mono">python run.py</span> (or the GitHub workflow) for real predictions.</div>`;
$("#strip").innerHTML = (R.market||[]).map(m => `<div class="tick"><div class="n">${esc(m.name)}</div><div class="v num">${m.last.toLocaleString(undefined,{maximumFractionDigits:2})}</div><div class="num ${cls(m.chg1d)}" style="font-size:12px">${pct(m.chg1d,2)} 1d · <span class="${cls(m.chg1m)}">${pct(m.chg1m,1)} 1m</span></div></div>`).join("");
$("#nfeat").textContent = R.n_features;

// tabs
document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => showTab(b.dataset.tab));
function showTab(t){
  document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab===t));
  ["overview","detail","scanner","backtest"].forEach(x => $("#tab-"+x).hidden = x!==t);
  if (t==="detail") renderDetail(); if (t==="backtest") renderBacktest(); if (t==="scanner") renderScanner();
  try{ history.replaceState(null,"","#"+t) }catch(e){}
}
function seg(id, key, cb){
  const el = $(id);
  el.innerHTML = HZ.map(h => `<button aria-pressed="${state[key]===h}" data-h="${h}">${HZNAME[h]}</button>`).join("");
  el.querySelectorAll("button").forEach(b => b.onclick = () => { state[key]=b.dataset.h; seg(id,key,cb); cb(); });
}

// overview
function pbar(p){ return `<span class="pbar"><span class="num">${(p*100).toFixed(0)}%</span><span class="track"><span class="fill" style="width:${p*100}%"></span><span class="mid"></span></span></span>`; }
function renderOverview(){
  const h = state.ov;
  const rows = R.predictions.map(p => ({t:p.ticker, price:p.price, ...p.horizons[h], risk:p.risk.level, g5:p.horizons[h].p_gain["5"]}));
  const k = state.sort.k, d = state.sort.dir;
  rows.sort((a,b) => { const x=a[k], y=b[k]; return (typeof x==="string" ? x.localeCompare(y) : (x-y)) * d; });
  const cols = [["t","Stock","l"],["price","Price"],["p_up","P(up)"],["exp_move","Median move"],["range","80% range"],["confidence","Confidence"],["lean","Lean","l"],["risk","Risk"],["g5","P(>+5%)"]];
  $("#ovt").innerHTML = `<thead><tr>${cols.map(c=>`<th class="${c[2]||""}" data-k="${c[0]}" tabindex="0">${c[1]}${state.sort.k===c[0]?(d>0?" ▲":" ▼"):""}</th>`).join("")}</tr></thead><tbody>` +
    rows.map(r => `<tr class="clickable" data-t="${esc(r.t)}"><td class="tk">${esc(r.t)}</td><td class="num">${r.price.toFixed(2)}</td><td>${pbar(r.p_up)}</td>
      <td class="num ${cls(r.exp_move)}">${pct(r.exp_move)}</td><td class="num">${pct(r.range[0])} to ${pct(r.range[1])}</td>
      <td><span class="pill ${r.confidence}">${r.confidence}</span></td><td class="l">${esc(r.lean)}</td><td class="risk-${r.risk.split(" ")[0]}">${esc(r.risk)}</td><td class="num">${pct(r.g5,0,false)}</td></tr>`).join("") + "</tbody>";
  $("#ovt").querySelectorAll("th").forEach(th => { const go = () => { const k=th.dataset.k; state.sort = {k, dir: state.sort.k===k ? -state.sort.dir : -1}; renderOverview(); }; th.onclick = go; th.onkeydown = e => { if(e.key==="Enter") go(); }; });
  $("#ovt").querySelectorAll("tr.clickable").forEach(tr => tr.onclick = () => { state.pick = tr.dataset.t; $("#pick").value = state.pick; showTab("detail"); });
}

// detail
$("#pick").innerHTML = R.predictions.map(p => `<option value="${esc(p.ticker)}">${esc(p.ticker)}</option>`).join("");
$("#pick").onchange = e => { state.pick = e.target.value; renderDetail(); };
function erf(x){ const t=1/(1+0.3275911*Math.abs(x)); const y=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-x*x); return x>=0?y:-y; }
function renderDetail(){
  const p = R.predictions.find(x => x.ticker===state.pick) || R.predictions[0];
  $("#hcards").innerHTML = HZ.map(h => { const x = p.horizons[h];
    return `<div class="hcard"><h3>${HZNAME[h]}</h3>
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:6px"><span class="big num pos">${(x.p_up*100).toFixed(0)}%</span><span class="num neg" style="font-size:18px">${(x.p_down*100).toFixed(0)}% down</span></div>
      <div class="split"><span class="u" style="width:${x.p_up*100}%"></span><span class="d" style="width:${x.p_down*100}%"></span></div>
      <dl class="kv"><dt>Median move</dt><dd class="num ${cls(x.exp_move)}">${pct(x.exp_move)}</dd>
      <dt>80% range</dt><dd class="num">${pct(x.range[0])} to ${pct(x.range[1])}</dd>
      <dt>Confidence</dt><dd><span class="pill ${x.confidence}">${x.confidence}</span></dd>
      <dt>P(&gt;+5% / +10% / +20%)</dt><dd class="num">${["5","10","20"].map(k=>pct(x.p_gain[k],0,false)).join(" / ")}</dd>
      <dt>Model → with live signals</dt><dd class="num">${(x.p_model*100).toFixed(1)}% → ${(x.p_up*100).toFixed(1)}%</dd></dl>
      ${x.earnings_in_window ? `<div class="note" style="margin-top:6px">Earnings fall inside this window; range widened.</div>`:""}</div>`; }).join("");
  // price chart
  const c = p.chart, up=css("--up"), down=css("--down"), acc=css("--accent"), ink3=css("--ink3");
  const lvl = (v,col,lab) => ({label:lab, data:c.dates.map(()=>v), color:col, dash:"5,4", width:1});
  lineChart("c-price", {labels:c.dates, xfmt:d=>new Date(d+"T00:00").toLocaleDateString(undefined,{month:"short",day:"numeric"}), xTicks:5, yfmt:v=>(+v).toFixed(2), series:[
    {label:"Close", data:c.close, color:acc, width:2},
    {label:"20-day MA", data:c.sma20, color:css("--warn"), width:1.2},
    {label:"50-day MA", data:c.sma50, color:ink3, width:1.2},
    ...(c.support||[]).slice(0,1).map(v=>lvl(v,up,"Support")), ...(c.resistance||[]).slice(0,1).map(v=>lvl(v,down,"Resistance"))]});
  // distribution: split-normal fitted to the 10th/50th/90th percentiles
  const x = p.horizons[state.det], q10=x.range[0], q50=x.exp_move, q90=x.range[1];
  const sl = Math.max((q50-q10)/1.2816,1e-4), sr = Math.max((q90-q50)/1.2816,1e-4);
  const lo = q50-3.2*sl, hi = q50+3.2*sr, N=120, xs=[], ys=[];
  for (let i=0;i<=N;i++){ const v=lo+(hi-lo)*i/N, s=v<q50?sl:sr; xs.push(v); ys.push(Math.exp(-0.5*((v-q50)/s)**2)*2/(Math.sqrt(2*Math.PI)*(sl+sr))); }
  lineChart("c-dist", {labels:xs, xfmt:v=>(v*100).toFixed(1)+"%", yfmt:v=>(+v).toFixed(2), hideY:true, ymin:0, legendOn:false, xTicks:7, series:[
    {label:"Up", data:ys.map((y,i)=>xs[i]>=0?y:null), color:up, fill:true, width:1.5},
    {label:"Down", data:ys.map((y,i)=>xs[i]<=0?y:null), color:down, fill:true, width:1.5}]});
  $("#dist-title").textContent = `Probability distribution · ${HZNAME[state.det]}`;
  $("#dist-note").textContent = `Shape from the model's 10th/50th/90th percentile forecast (${pct(q10)} / ${pct(q50)} / ${pct(q90)}). The shaded split is only a sketch; the headline P(up) comes from the calibrated direction model.`;
  $("#o-short").textContent = p.short_outlook; $("#o-med").textContent = p.medium_outlook; $("#o-why").textContent = p.explanation;
  const r = p.risk;
  $("#risk").innerHTML = `<dl class="kv"><dt>Risk level</dt><dd class="risk-${r.level.split(" ")[0]}"><b>${r.level}</b></dd>
    <dt>Annualised volatility (3m)</dt><dd class="num">${pct(r.vol_annual,0,false)}</dd><dt>Average daily range (ATR)</dt><dd class="num">${pct(r.atr_pct,1,false)}</dd>
    <dt>Beta to S&amp;P 500</dt><dd class="num">${isNaN(r.beta)||r.beta==null?"n/a":r.beta.toFixed(2)}</dd><dt>1-week downside (10th pct)</dt><dd class="num neg">${pct(r.downside_q10)}</dd></dl>
    <ul class="f">${r.notes.map(n=>`<li>${esc(n)}</li>`).join("") || "<li>No special risk flags.</li>"}</ul>`;
  $("#bull").innerHTML = p.bullish.map(b=>`<li>${esc(b)}</li>`).join("") || "<li>None stand out.</li>";
  $("#bear").innerHTML = p.bearish.map(b=>`<li>${esc(b)}</li>`).join("") || "<li>None stand out.</li>";
  const fam = [...p.family_contrib].sort((a,b)=>b.value-a.value);
  hbarChart("c-fam", {labels:fam.map(f=>f.family), values:fam.map(f=>f.value), colors:fam.map(f=>f.value>=0?up:down), xfmt:v=>(v>=0?"+":"")+v.toFixed(2)});
  $("#drivers").innerHTML = `<thead><tr><th class="l">Feature</th><th>Value</th><th>Push</th></tr></thead><tbody>` + p.top_drivers.map(d=>`<tr><td class="l">${esc(d.feature)}</td><td class="num">${esc(d.value)}</td><td class="num ${cls(d.impact)}">${d.impact>0?"▲":"▼"} ${Math.abs(d.impact).toFixed(3)}</td></tr>`).join("") + "</tbody>";
  const L = p.live;
  if (!L){ $("#live").innerHTML = `<p class="note">Live signals were not collected in this run.</p>`; return; }
  const n=L.news||{}, a=L.analyst||{}, o=L.options||{}, ins=L.institutional||{};
  const sc = v => `<span class="num ${cls(v)}">${v>=0?"+":""}${(v||0).toFixed(2)}</span>`;
  $("#live").innerHTML = `
    <div><h3>News sentiment ${sc(n.score)}</h3><ul class="f">${(n.headlines||[]).map(hd=>`<li>${hd.url?`<a href="${esc(hd.url)}" target="_blank" rel="noopener">${esc(hd.title)}</a>`:esc(hd.title)} <span class="note">${esc(hd.source||"")} · ${sc(hd.score)}</span></li>`).join("")||"<li>No recent headlines.</li>"}</ul></div>
    <div class="stack" style="gap:10px">
      <div><h3>Analysts ${sc(a.score)}</h3><dl class="kv"><dt>Consensus</dt><dd>${esc(a.rating||"n/a")}</dd><dt>Target vs price</dt><dd class="num">${pct(a.target_upside,0)}</dd><dt>Net up/downgrades (30d)</dt><dd class="num">${a.net_upgrades_30d??"n/a"}</dd></dl></div>
      <div><h3>Options ${sc(o.score)}</h3><dl class="kv"><dt>Put/call volume</dt><dd class="num">${o.put_call_vol?.toFixed(2)??"n/a"}</dd><dt>Put/call open interest</dt><dd class="num">${o.put_call_oi?.toFixed(2)??"n/a"}</dd><dt>ATM implied vol</dt><dd class="num">${pct(o.iv_atm,0,false)}</dd><dt>Implied ÷ realised vol</dt><dd class="num">${o.iv_vs_rv?.toFixed(2)??"n/a"}</dd><dt>Unusual activity</dt><dd>${o.unusual?"Yes":"No"}</dd></dl></div>
      <div><h3>Institutions &amp; insiders ${sc(ins.score)}</h3><dl class="kv"><dt>Held by institutions</dt><dd class="num">${pct(ins.inst_pct,0,false)}</dd><dt>Net insider $ (6m)</dt><dd class="num ${cls(ins.insider_net_6m)}">${ins.insider_net_6m==null?"n/a":(ins.insider_net_6m/1e6).toFixed(1)+"M"}</dd></dl></div>
    </div>`;
}

// scanner
function renderScanner(){
  const h = state.scan, rk = R.rankings[h];
  $("#gainlists").innerHTML = R.thresholds.map(t => `<div class="panel"><h3>Chance of +${t}% within ${HZNAME[h]}</h3><ol class="rank">${rk[String(t)].slice(0,8).map(r=>`<li><span class="tk">${esc(r.ticker)}</span><span class="num">${pct(r.p_gain,0,false)} <span class="note">· median ${pct(r.exp_move)}</span></span></li>`).join("")}</ol></div>`).join("");
  $("#rat").innerHTML = `<thead><tr><th class="l">#</th><th class="l">Stock</th><th>Risk-adj. score</th><th>Median move</th><th>80% range</th><th>P(up)</th></tr></thead><tbody>` +
    rk.risk_adjusted.map((r,i)=>`<tr><td class="l">${i+1}</td><td class="tk l">${esc(r.ticker)}</td><td class="num ${cls(r.risk_adj)}">${r.risk_adj.toFixed(2)}</td><td class="num ${cls(r.exp_move)}">${pct(r.exp_move)}</td><td class="num">${pct(r.range[0])} to ${pct(r.range[1])}</td><td>${pbar(r.p_up)}</td></tr>`).join("") + "</tbody>";
}

// backtest
function renderBacktest(){
  const B = R.backtest || {};
  if (!Object.keys(B).length){ $("#bt-summary").textContent = "The backtest was skipped in this run."; return; }
  const f = v => v==null||isNaN(v) ? "n/a" : v.toFixed(3);
  $("#btt").innerHTML = `<thead><tr><th class="l">Horizon</th><th>Test period</th><th>Predictions</th><th>Accuracy</th><th>Naive</th><th>AUC</th><th>Brier skill</th><th>Accuracy when ≥60/≤40%</th><th>Share of calls</th><th>80% range held</th></tr></thead><tbody>` +
    HZ.filter(h=>B[h]).map(h=>{ const m=B[h]; return `<tr><td class="l">${HZNAME[h]}</td><td class="num">${m.start} → ${m.end}</td><td class="num">${m.n.toLocaleString()}</td><td class="num">${pct(m.accuracy,1,false)}</td><td class="num">${pct(m.naive_accuracy,1,false)}</td><td class="num ${m.auc>0.52?"pos":m.auc<0.5?"neg":""}">${f(m.auc)}</td><td class="num ${cls(m.brier_skill)}">${pct(m.brier_skill,1)}</td><td class="num">${pct(m.high_conf_accuracy,1,false)}</td><td class="num">${pct(m.high_conf_share,0,false)}</td><td class="num">${pct(m.range_coverage_80,0,false)}</td></tr>`; }).join("") + "</tbody>";
  const best = HZ.filter(h=>B[h]).sort((a,b)=>B[b].auc-B[a].auc)[0];
  const edge = B[best].auc - 0.5;
  $("#bt-summary").textContent = edge < 0.02
    ? `Out of sample the model shows essentially no directional edge (best AUC ${B[best].auc.toFixed(3)} at ${HZNAME[best]}; 0.5 is a coin flip). Its probabilities are therefore held close to the base rate. Treat it as a structured summary of signals, not a forecast.`
    : `Best out-of-sample edge is at ${HZNAME[best]} (AUC ${B[best].auc.toFixed(3)}, accuracy ${pct(B[best].accuracy,1,false)} vs ${pct(B[best].naive_accuracy,1,false)} naive). Modest edges like this are typical and can fade; probabilities are shrunk toward the base rate to match the evidence.`;
  seg("#hz-bt","bt",renderBacktest);
  const m = B[state.bt] || B[best]; const up=css("--up"), down=css("--down"), acc=css("--accent"), ink3=css("--ink3");
  calChart("c-cal", m.calibration);
  vbarChart("c-quint", {labels:m.quintile_returns.map(q=>"Q"+q.q), values:m.quintile_returns.map(q=>q.avg_ret*100), colors:m.quintile_returns.map(q=>q.avg_ret>=0?up:down), yfmt:v=>v.toFixed(2)+"%"});
  lineChart("c-eq", {labels:m.equity_curve.map(e=>e.date), xTicks:4, xfmt:d=>new Date(d+"T00:00").toLocaleDateString(undefined,{month:"short",year:"2-digit"}), yfmt:v=>(+v).toFixed(2)+"×", series:[
    {label:"P(up) > 55%", data:m.equity_curve.map(e=>e.model), color:acc, width:2},
    {label:"Equal-weight all", data:m.equity_curve.map(e=>e.equal_weight), color:ink3, width:1.5}]});
  const I = R.importance[state.bt] || R.importance["1w"];
  const pal = [acc, css("--up"), css("--warn"), css("--down"), ink3, "#5b8fa8", "#8a6fb0", "#9c8b5e"];
  hbarChart("c-impfam", {labels:I.families.map(f=>f.family), values:I.families.map(f=>f.share*100), colors:I.families.map((_,i)=>pal[i%pal.length]), xfmt:v=>v.toFixed(0)+"%"});
  hbarChart("c-imp", {labels:I.features.map(f=>f.label), values:I.features.map(f=>f.importance), colors:[acc], xfmt:v=>v.toFixed(4)});
}

seg("#hz-overview","ov",renderOverview); seg("#hz-detail","det",renderDetail); seg("#hz-scanner","scan",renderScanner);
renderOverview();
const start = (location.hash||"").slice(1);
if (["detail","scanner","backtest"].includes(start)) showTab(start);
const rerender = () => { const t=document.querySelector('.tabs [aria-selected="true"]').dataset.tab; showTab(t); };
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", rerender);
let rz; addEventListener("resize", () => { clearTimeout(rz); rz=setTimeout(rerender, 200); });
</script>
</body>
</html>
"""
