"""report.html — одна страница, удобная на телефоне: фильтры, карточки, бейджи."""
from __future__ import annotations

import json
from pathlib import Path

KEEP = ["uid", "platform", "kind", "url", "title", "price_listed", "price_net", "price_gross", "invoice_vat",
        "real_price_net", "real_price_gross", "real_price_note", "fleet_flag", "fleet_phrases", "year",
        "model_year", "mileage", "engine", "power_hp", "gearbox", "version", "trim", "seats", "city",
        "seller_type", "seller_name", "posted_at", "vin", "first_seen", "price_history", "duplicates",
        "match_score", "match_why", "cost_for_me", "cost_basis", "is_new", "price_dropped",
        "monthly_rate_net", "lease_terms", "condition"]


def _slim(rows):
    return [{k: r.get(k) for k in KEEP} for r in rows]


def write_report(path: Path, sale, lease, top, meta):
    data = {"sale": _slim(sale), "lease": _slim(lease), "top": [r["uid"] for r in top], "meta": meta}
    blob = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    Path(path).write_text(TEMPLATE.replace("/*DATA*/null", blob), encoding="utf-8")


TEMPLATE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VW Caddy — поиск</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#16181d;--mute:#5d6470;--line:#e2e5ea;--acc:#0b5cd5;
--fleet:#b54708;--fleet-bg:#fff4e5;--drop:#067647;--drop-bg:#e7f6ee;--new:#5b21b6;--new-bg:#efe9fd;--warn-bg:#fdecec;--warn:#b42318}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111317;--card:#1a1d23;--ink:#e8eaee;--mute:#9aa1ad;--line:#2b3038;
--acc:#6ea8ff;--fleet:#ffb86b;--fleet-bg:#3a2a14;--drop:#5fd39a;--drop-bg:#123124;--new:#c4b5fd;--new-bg:#2a2140;--warn-bg:#3b1a1a;--warn:#ff8a80}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:4px 0 2px}h2{font-size:17px;margin:22px 0 8px}
.sub{color:var(--mute);font-size:13px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.chip{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:3px 10px;font-size:12px}
.chip.ok{border-color:var(--drop)}.chip.bad{border-color:var(--warn);color:var(--warn)}
.filters{background:var(--bg);padding:8px 0;display:grid;gap:8px;
grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border-bottom:1px solid var(--line)}
.filters input,.filters select{width:100%;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
.filters label{display:flex;align-items:center;gap:6px;font-size:13px}
.filters label input{width:auto}
.list,.top{display:grid;grid-template-columns:minmax(0,1fr);gap:10px;margin-top:10px}
.row1>div:first-child{min-width:0;flex:1}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:grid;gap:6px}
.row1{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.price{font-size:20px;font-weight:700;white-space:nowrap;text-align:right}
.price small{display:block;font-size:12px;font-weight:400;color:var(--mute)}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.title{font-weight:600;overflow-wrap:anywhere}
.specs,.meta{color:var(--mute);font-size:13px}
.badges{display:flex;flex-wrap:wrap;gap:5px}
.b{font-size:11px;font-weight:600;padding:2px 7px;border-radius:6px;background:var(--line);color:var(--ink)}
.b.fleet{background:var(--fleet-bg);color:var(--fleet)}.b.drop{background:var(--drop-bg);color:var(--drop)}
.b.new{background:var(--new-bg);color:var(--new)}.b.nofv{background:var(--warn-bg);color:var(--warn)}
.note{font-size:13px;background:var(--fleet-bg);color:var(--ink);border-radius:8px;padding:6px 8px}
details{font-size:13px}summary{cursor:pointer;color:var(--mute)}
.top .card{grid-template-columns:auto 1fr auto;align-items:center}
.score{font-weight:700;font-size:15px;min-width:44px;text-align:center;border-radius:8px;padding:4px;background:var(--new-bg);color:var(--new)}
.empty{color:var(--mute);padding:20px;text-align:center}
@media (min-width:700px){.filters{position:sticky;top:0;z-index:5}}
@media (max-width:560px){.row1{flex-direction:column}.price{font-size:18px;text-align:left}.top .card{grid-template-columns:auto 1fr}.top .price{grid-column:2;text-align:left}}
</style>
</head>
<body>
<div class="wrap">
<h1>VW Caddy — поиск для JDG</h1>
<div class="sub" id="sub"></div>
<div class="chips" id="sources"></div>
<div class="sub" id="changes"></div>

<h2>Топ-10 по совпадению с ориентиром</h2>
<div class="top" id="top"></div>

<section>
<h2>Все объявления о продаже <span class="sub" id="count"></span></h2>
<div class="filters">
  <input id="q" type="search" placeholder="Поиск: TSI, Life, Warszawa…">
  <select id="plat"><option value="">Все площадки</option></select>
  <select id="ver"><option value="">Все версии</option></select>
  <input id="pmax" type="number" inputmode="numeric" placeholder="Макс. цена для меня">
  <select id="sort">
    <option value="cost">Сорт.: реальная цена ↑</option>
    <option value="match">Совпадение ↓</option>
    <option value="new">Новые сначала</option>
    <option value="km">Пробег ↑</option>
  </select>
  <label><input type="checkbox" id="nofleet"> скрыть флот/финанс.</label>
  <label><input type="checkbox" id="fv"> только с FV 23%</label>
  <label><input type="checkbox" id="tsi"> только 1.5 TSI</label>
</div>
<div class="list" id="list"></div>
</section>

<h2>Najem / leasing — оферты со ставкой</h2>
<div class="list" id="lease"></div>
<p class="sub">Цены и ставки — как опубликованы площадками; «реальная цена» = без флотовых условий/финансирования.
brutto = netto × 1,23. Проверяйте условия у продавца.</p>
</div>
<script>
const D = /*DATA*/null;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pln = v => v == null ? "—" : Math.round(v).toLocaleString("pl-PL").replace(/,/g," ") + " zł";
const m = D.meta, unit = m.vat_status === "czynny" ? "netto" : "brutto";
$("#sub").innerHTML = `Сформировано ${esc(m.generated.replace("T"," ").slice(0,16))} UTC · VAT: <b>${esc(m.vat_status)}</b> (сравнение по ${unit}) ·
 ориентир 1.5 TSI 116 KM MY${m.reference.model_year}: ${pln(m.reference.fleet_price_net)} netto / ${pln(m.reference.fleet_price_gross)} brutto (флот) · запросов: ${m.pages_fetched}`;
$("#sources").innerHTML = Object.entries(m.statuses).map(([k,s]) =>
  `<span class="chip ${s.status==="ok"?"ok":"bad"}" title="${esc(s.note||"")}">${esc(k)}: ${esc(s.status)}${s.status==="ok"?" · "+s.found:""}${s.note?" ⓘ":""}</span>`).join("");
const blocked = Object.entries(m.statuses).filter(([k,s]) => s.status!=="ok");
const ch = m.changes;
$("#changes").innerHTML = (m.prev_run ? `С прошлого запуска: новых <b>${ch.new}</b>, подешевели <b>${ch.price_down}</b>, подорожали ${ch.price_up}, исчезли ${ch.gone}.` : "Первый запуск — бейдж «новое» и история цен появятся со следующего.")
 + (blocked.length ? "<br>Недоступно: " + blocked.map(([k,s]) => `${esc(k)} — ${esc(s.note)}`).join("; ") : "");

function badges(r){
  const b = [];
  if (r.fleet_flag) b.push(`<span class="b fleet" title="${esc((r.fleet_phrases||[]).join(" · "))}">флотовая цена / финанс.</span>`);
  if (r.price_dropped) b.push(`<span class="b drop">снижение цены</span>`);
  if (r.is_new) b.push(`<span class="b new">новое</span>`);
  if (r.kind==="sale") b.push(r.invoice_vat ? `<span class="b">FV 23%</span>` : `<span class="b nofv">без FV</span>`);
  if (r.condition==="new") b.push(`<span class="b">nowy</span>`);
  if (r.model_year) b.push(`<span class="b">MY${r.model_year}</span>`);
  if ((r.duplicates||[]).length) b.push(`<span class="b">+${r.duplicates.length} площ.</span>`);
  return b.join("");
}
const host = u => { try { return new URL(u).hostname.replace("www.",""); } catch(e) { return u; } };
function card(r){
  const specs = [r.year && `rok ${r.year}`, r.engine, r.power_hp && r.power_hp+" KM", r.gearbox, r.version, r.trim,
    r.seats && r.seats+" miejsc", r.mileage!=null && r.mileage.toLocaleString("pl-PL")+" km"].filter(Boolean).map(esc).join(" · ");
  const listed = r.kind==="lease" ? "" : `${pln(r.price_gross)} brutto${r.price_net?" / "+pln(r.price_net)+" netto":""}`;
  const hist = (r.price_history||[]).filter(h=>h[1]);
  const fleet = r.fleet_flag ? `<div class="note"><b>Условия:</b> ${esc((r.fleet_phrases||[]).join(" · "))}<br>${esc(r.real_price_note||"")}</div>` : "";
  const dups = (r.duplicates||[]).map(u => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(host(u))}</a>`).join(", ");
  const main = r.kind==="lease" ? `${pln(r.monthly_rate_net)}<small>netto / мес.</small>` : `${pln(r.cost_for_me)}<small>для меня: ${esc(r.cost_basis||"")}</small>`;
  return `<div class="card">
   <div class="row1"><div><a class="title" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>
   <div class="meta">${[r.platform, [r.seller_type, r.seller_name].filter(Boolean).join(" "), r.city, r.posted_at && r.posted_at.slice(0,10)].filter(Boolean).map(esc).join(" · ")}</div></div>
   <div class="price">${main}</div></div>
   <div class="specs">${specs}</div>
   <div class="badges">${badges(r)}</div>
   ${listed?`<div class="meta">Цена в объявлении: ${listed}${r.kind==="lease"&&r.price_net?"":""}</div>`:""}
   ${r.kind==="lease"?`<div class="meta">${r.price_net?"Цена авто: "+pln(r.price_net)+" netto · ":""}${esc(r.lease_terms||"")}</div>`:""}
   ${fleet}
   <details><summary>подробнее</summary>
    <div>Впервые замечено: ${esc((r.first_seen||"").slice(0,10))}${r.vin?" · VIN "+esc(r.vin):""}</div>
    ${hist.length>1?`<div>История цены: ${hist.map(h=>esc(h[0].slice(0,10))+" "+pln(h[1])).join(" → ")}</div>`:""}
    ${dups?`<div>Это же авто: ${dups}</div>`:""}
    <div>Совпадение с ориентиром: ${r.match_score}/100 ${esc((r.match_why||[]).join(", "))}</div>
   </details></div>`;
}
const byId = Object.fromEntries(D.sale.map(r=>[r.uid,r]));
$("#top").innerHTML = D.top.map(u=>byId[u]).filter(Boolean).map(r =>
 `<div class="card"><div class="score">${r.match_score}</div>
  <div><a class="title" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>
  <div class="meta">${esc((r.match_why||[]).join(" · "))} · ${esc(r.seller_name||"")} ${esc(r.city||"")}</div>
  <div class="badges">${badges(r)}</div></div>
  <div class="price">${pln(r.cost_for_me)}<small>${esc(r.cost_basis||"")}</small></div></div>`).join("") || `<div class="empty">Нет данных</div>`;

for (const p of [...new Set(D.sale.map(r=>r.platform))]) $("#plat").insertAdjacentHTML("beforeend", `<option>${esc(p)}</option>`);
for (const v of [...new Set(D.sale.map(r=>r.version).filter(Boolean))].sort()) $("#ver").insertAdjacentHTML("beforeend", `<option>${esc(v)}</option>`);
const ids = ["q","plat","ver","pmax","sort","nofleet","fv","tsi"];
try { const s = JSON.parse(localStorage.getItem("caddyFilters")||"{}");
  ids.forEach(i => { if (s[i]!==undefined) { const e=$("#"+i); e.type==="checkbox" ? e.checked=s[i] : e.value=s[i]; } }); } catch(e) {}
function render(){
  const f = Object.fromEntries(ids.map(i => { const e=$("#"+i); return [i, e.type==="checkbox"?e.checked:e.value]; }));
  try { localStorage.setItem("caddyFilters", JSON.stringify(f)); } catch(e) {}
  const q = f.q.toLowerCase().trim();
  let rows = D.sale.filter(r => (!f.plat || r.platform===f.plat) && (!f.ver || r.version===f.ver)
    && (!f.pmax || (r.cost_for_me||0) <= +f.pmax) && (!f.nofleet || !r.fleet_flag) && (!f.fv || r.invoice_vat)
    && (!f.tsi || /1\.5 TSI/.test(r.engine||""))
    && (!q || [r.title,r.city,r.seller_name,r.version,r.trim,r.engine].join(" ").toLowerCase().includes(q)));
  const k = {cost:r=>r.cost_for_me??9e9, match:r=>-r.match_score, new:r=>-(Date.parse(r.posted_at)||0), km:r=>r.mileage??9e9}[f.sort];
  rows.sort((a,b)=>k(a)-k(b));
  $("#count").textContent = `(${rows.length} из ${D.sale.length})`;
  $("#list").innerHTML = rows.map(card).join("") || `<div class="empty">Ничего не найдено под фильтры</div>`;
}
ids.forEach(i => $("#"+i).addEventListener("input", render));
render();
$("#lease").innerHTML = D.lease.sort((a,b)=>(a.monthly_rate_net??9e9)-(b.monthly_rate_net??9e9)).map(card).join("")
  || `<div class="empty">Оферт со ставкой не найдено</div>`;
</script>
</body>
</html>
"""
