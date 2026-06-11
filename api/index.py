"""
WC26 — single self-contained Vercel entrypoint.
Frontend HTML is embedded (no disk reads). All /api/* routes dispatch to the
providers in api/_lib. Pure stdlib.
"""
import json, os, sys
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import venues, bracket, flights, hotels, scores, tickets  # noqa

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Follow My Team — WC26</title>
<style>
  :root{
    --ink:#13243b; --paper:#f3ede1; --paper2:#fff8ec; --pitch:#1f7a4d;
    --pitch-soft:#d6e8dc; --flag:#e4572e; --muted:#6b7a8d; --rule:#c9bfa8;
    --live:#d12d2d;
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{
    background:
      repeating-linear-gradient(90deg,transparent 0 38px,rgba(19,36,59,.025) 38px 39px),
      var(--paper);
    color:var(--ink); font-family:"Helvetica Neue",Arial,sans-serif; line-height:1.5;
  }
  .wrap{max-width:820px;margin:0 auto;padding:24px 16px 80px}
  header{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:18px}
  .kicker{font:600 12px/1 inherit;letter-spacing:.32em;text-transform:uppercase;color:var(--flag)}
  h1{font:800 32px/1.02 inherit;letter-spacing:-.02em;margin:10px 0 4px}
  .sub{color:var(--muted);font-size:14px;max-width:56ch}

  /* live scores ticker */
  .scores{margin:18px 0;border:1.5px solid var(--ink);border-radius:10px;background:var(--paper2);overflow:hidden}
  .scores h2{font:700 11px/1 inherit;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);
    margin:0;padding:11px 14px;border-bottom:1px solid var(--rule);display:flex;align-items:center;gap:8px}
  .live-dot{width:8px;height:8px;border-radius:50%;background:var(--live);display:inline-block;
    animation:pulse 1.6s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  @media (prefers-reduced-motion:reduce){.live-dot{animation:none}}
  .score-row{display:flex;justify-content:space-between;gap:10px;padding:9px 14px;border-bottom:1px solid #eadfc8;font-size:14px}
  .score-row:last-child{border-bottom:none}
  .score-row .teams{font-weight:600}
  .score-row .sc{font:700 14px ui-monospace,Menlo,monospace}
  .score-row .st{color:var(--muted);font-size:12px}
  .empty{padding:14px;font-size:13px;color:var(--muted);font-style:italic}

  .stub{margin-top:6px;border:1.5px solid var(--ink);background:var(--paper2);border-radius:10px;
    padding:16px;display:grid;gap:13px;grid-template-columns:1fr 1fr}
  .stub .full{grid-column:1/-1}
  label{display:block;font:700 11px/1 inherit;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
  select,input[type=date]{width:100%;padding:11px 12px;border:1.5px solid var(--rule);border-radius:7px;background:#fff;font-size:15px;color:var(--ink)}
  select:focus,input:focus{outline:3px solid var(--pitch-soft);border-color:var(--pitch)}
  button{padding:13px;border:none;border-radius:8px;background:var(--ink);color:var(--paper2);font:800 15px/1 inherit;letter-spacing:.04em;cursor:pointer}
  button:hover{background:#0c1929}
  button:focus-visible{outline:3px solid var(--flag);outline-offset:2px}
  .go-row{grid-column:1/-1}
  .go-row button{width:100%}

  .route{margin-top:28px}
  .summary{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px dashed var(--rule);padding-bottom:8px;margin-bottom:6px}
  .summary .big{font:800 18px/1 inherit}
  .stop{position:relative;padding:18px 0 18px 42px;opacity:0;transform:translateY(8px);animation:rise .45s ease forwards}
  @keyframes rise{to{opacity:1;transform:none}}
  @media (prefers-reduced-motion:reduce){.stop{animation:none;opacity:1;transform:none}}
  .stop:not(:last-child)::before{content:"";position:absolute;left:13px;top:26px;bottom:-12px;width:2px;background:var(--pitch)}
  .dot{position:absolute;left:6px;top:20px;width:16px;height:16px;border-radius:50%;background:#fff;border:3px solid var(--pitch)}
  .stop.exact .dot{background:var(--pitch)}
  .round{font:700 11px/1 inherit;letter-spacing:.18em;text-transform:uppercase;color:var(--flag);margin-bottom:7px}
  .city-line{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px}
  .city{font:800 19px/1.1 inherit}
  .stadium{color:var(--muted);font-size:13px}
  .flagtag{font:700 10px/1 inherit;letter-spacing:.1em;border:1px solid var(--rule);border-radius:4px;padding:3px 6px;color:var(--muted)}
  .meta{margin-top:8px;font-size:13px;color:var(--muted)}
  .meta b{color:var(--ink)}
  .pills{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}
  .pill{font:600 12px/1 inherit;border:1px solid var(--rule);border-radius:20px;padding:6px 11px;background:var(--paper2)}

  /* tappable candidate-city cards for knockout rounds */
  .candi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:9px}
  .candi{border:1.5px solid var(--rule);border-radius:9px;background:var(--paper2);overflow:hidden}
  .candi-head{width:100%;display:flex;align-items:center;gap:7px;padding:10px 11px;background:none;border:none;
    cursor:pointer;font:700 13px/1.1 inherit;color:var(--ink);text-align:left}
  .candi-head:hover{background:#fff}
  .candi-city{flex:1}
  .candi-flag{font:700 9px/1 inherit;letter-spacing:.06em;border:1px solid var(--rule);border-radius:4px;padding:2px 5px;color:var(--muted)}
  .candi-caret{color:var(--pitch);font-size:11px}
  .candi-body{padding:0 11px 11px;border-top:1px solid var(--rule)}

  /* countdown chip */
  .cd{font:700 10px/1 inherit;letter-spacing:.04em;color:var(--pitch);margin-left:6px;text-transform:none}
  .cd-live{color:var(--live)}

  .actions{margin-top:10px;display:flex;flex-wrap:wrap;gap:8px}
  .actions button{padding:8px 12px;font-size:12px;letter-spacing:.06em;background:#fff;color:var(--ink);border:1.5px solid var(--ink);border-radius:7px;cursor:pointer}
  .actions button:hover{background:var(--ink);color:var(--paper2)}
  .panel{margin-top:10px;border:1px solid var(--rule);border-radius:8px;background:#fff;padding:11px 13px;font-size:13px}
  .panel h4{margin:0 0 7px;font:700 11px/1 inherit;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
  .offer{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid #f0e8d6}
  .offer:last-child{border-bottom:none}
  .price{font:700 13px ui-monospace,Menlo,monospace;color:var(--pitch)}
  .notcfg{color:var(--muted);font-style:italic}
  .subnote{color:var(--muted);font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin:9px 0 4px}
  .fresh{display:inline-block;font:700 10px/1 inherit;letter-spacing:.04em;padding:3px 7px;border-radius:20px;
    background:var(--pitch-soft);color:var(--pitch);vertical-align:middle;margin-left:4px}
  .fresh.stale{background:#f6e3c8;color:#9a6a16}
  .ticket-links{display:flex;flex-wrap:wrap;gap:8px;margin-top:4px}
  .ticket-links a{font:600 13px inherit;color:var(--ink);text-decoration:underline;text-underline-offset:3px}

  /* stadium facts grid */
  .sfacts{display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;margin:4px 0 8px}
  .sfacts span{font-size:13px}
  .sfacts .lbl{display:block;font:700 9px/1 inherit;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:2px}
  .snote{font-size:13px;color:var(--ink);line-height:1.5;border-top:1px solid #f0e8d6;padding-top:8px}

  /* share button + button pair */
  .btn-pair{display:flex;gap:8px}
  .btn-pair #go{flex:2}
  .ghost{flex:1;background:#fff;color:var(--ink);border:1.5px solid var(--ink)!important}
  .ghost:hover{background:var(--ink);color:var(--paper2)}

  footer{margin-top:36px;border-top:1px solid var(--rule);padding-top:14px;font-size:12px;color:var(--muted)}
  .foot-sources{display:block;margin-top:9px;font-size:11px;opacity:.8}
  @media (max-width:520px){.stub{grid-template-columns:1fr}h1{font-size:26px}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">World Cup 2026 · USA · Canada · Mexico</div>
    <h1>Follow My Team</h1>
    <p class="sub">Track your team's path through the tournament — every city they
      could play in, with flight prices, hotel and ticket search for your dates,
      and kickoff times in your own time zone. Live scores update as you watch.</p>
  </header>

  <section class="scores">
    <h2><span class="live-dot"></span> Live &amp; recent scores</h2>
    <div id="scores-body"><div class="empty">Loading…</div></div>
  </section>

  <div class="stub">
    <div>
      <label for="group">Your team's group</label>
      <select id="group"></select>
    </div>
    <div>
      <label for="finish">They finish…</label>
      <select id="finish"></select>
    </div>
    <div>
      <label for="city">Watching the group stage in</label>
      <select id="city"></select>
    </div>
    <div>
      <label for="tz">Show kickoffs in</label>
      <select id="tz"></select>
    </div>
    <div>
      <label for="depart">Travel date (for live prices)</label>
      <input type="date" id="depart" value="2026-06-28" min="2026-06-11" max="2026-07-19">
    </div>
    <div>
      <label for="adults">Travellers</label>
      <select id="adults"><option>1</option><option>2</option><option>3</option><option>4</option></select>
    </div>
    <div class="go-row btn-pair"><button id="go">Plot the road ahead</button><button id="share" class="ghost">Share route</button></div>
  </div>

  <section class="route" id="route">
    <div class="empty" style="text-align:center;padding:36px">Pick your team above to see the route.</div>
  </section>

  <footer id="foot">
    Knockout-round cities are confirmed once the bracket draw is complete; until
    then, each round shows every possible venue your team could reach. Confirmed
    by FIFA: quarter-finals in LA, Miami, Kansas City &amp; Boston; semi-finals in
    Dallas &amp; Atlanta; Final at MetLife Stadium, New York / NJ.
    <span class="foot-sources">Flight prices via Travelpayouts · hotels via Booking.com &amp; Hotels.com · tickets via FIFA, SeatGeek &amp; StubHub · scores via football-data.org</span>
  </footer>
</div>

<script>
const $ = s => document.querySelector(s);
let VENUES = [], BYKEY = {};

const HOME_ZONES = [
  ['London (UK)','Europe/London'], ['Madrid · Paris · Berlin','Europe/Paris'],
  ['Lisbon','Europe/Lisbon'], ['Buenos Aires','America/Argentina/Buenos_Aires'],
  ['São Paulo','America/Sao_Paulo'], ['Bogotá · Lima','America/Bogota'],
  ['Lagos · Casablanca','Africa/Lagos'], ['Tokyo · Seoul','Asia/Tokyo'],
  ['Sydney','Australia/Sydney'],
];

// Approximate first-match date per round (WC26 schedule). Used for countdowns.
const ROUND_DATES = {
  group: '2026-06-11', r32: '2026-06-28', r16: '2026-07-04',
  qf: '2026-07-09', sf: '2026-07-14', final: '2026-07-19',
};

function countdownHtml(round){
  const d = ROUND_DATES[round];
  if(!d) return '';
  return ` <span class="cd" data-date="${d}"></span>`;
}

let cdTimer = null;
function startCountdowns(){
  if(cdTimer) clearInterval(cdTimer);
  const tick = () => {
    document.querySelectorAll('.cd').forEach(el => {
      const target = new Date(el.dataset.date + 'T18:00:00Z').getTime();
      const diff = target - Date.now();
      if(diff <= 0){ el.textContent = '· live window'; el.classList.add('cd-live'); return; }
      const days = Math.floor(diff/86400000);
      const hrs = Math.floor((diff%86400000)/3600000);
      el.textContent = days > 0 ? `· in ${days}d ${hrs}h` : `· in ${hrs}h`;
    });
  };
  tick();
  cdTimer = setInterval(tick, 60000);
}

function shareRoute(){
  const params = new URLSearchParams({
    g: $('#group').value, f: $('#finish').value, c: $('#city').value,
    tz: $('#tz').value, d: $('#depart').value, a: $('#adults').value,
  });
  const url = location.origin + location.pathname + '?' + params.toString();
  navigator.clipboard.writeText(url).then(() => {
    const btn = $('#share'); const orig = btn.textContent;
    btn.textContent = 'Link copied ✓';
    setTimeout(() => btn.textContent = orig, 1800);
  }).catch(() => prompt('Copy your route link:', url));
}

function applyShared(){
  const p = new URLSearchParams(location.search);
  if(!p.has('g')) return false;
  const set = (id, key) => { const el = $(id); if(el && p.get(key)!=null) el.value = p.get(key); };
  set('#group','g'); set('#finish','f'); set('#city','c');
  set('#tz','tz'); set('#depart','d'); set('#adults','a');
  return true;
}

async function boot(){
  const meta = await (await fetch('/api/meta')).json();
  VENUES = meta.venues; VENUES.forEach(v => BYKEY[v.key] = v);

  const g = $('#group'); meta.groups.forEach(x => g.add(new Option('Group ' + x, x)));
  const f = $('#finish'); meta.finishes.forEach(x => f.add(new Option(x.label, x.key)));
  const city = $('#city'); VENUES.forEach(v => city.add(new Option(v.city + ' — ' + v.country_name, v.key)));

  const tz = $('#tz'); const seen = new Set();
  VENUES.forEach(v => { if(seen.has(v.tz)) return; seen.add(v.tz);
    tz.add(new Option('Host · ' + v.tz_label + ' (' + v.city + ')', v.tz)); });
  HOME_ZONES.forEach(([l,z]) => tz.add(new Option('Home · ' + l, z)));

  $('#go').addEventListener('click', plot);
  const shareBtn = $('#share');
  if(shareBtn) shareBtn.addEventListener('click', shareRoute);
  loadScores();
  setInterval(loadScores, 60000); // refresh scores each minute

  // If opened from a shared link, restore selections and plot automatically.
  if(applyShared()) plot();
}

async function loadScores(){
  const body = $('#scores-body');
  try{
    const d = await (await fetch('/api/scores')).json();
    if(!d.configured){ body.innerHTML = `<div class="empty">${d.message}</div>`; return; }
    if(d.error){ body.innerHTML = `<div class="empty">${d.message}</div>`; return; }
    const ms = (d.matches || []).slice(0, 8);
    if(!ms.length){ body.innerHTML = `<div class="empty">No matches to show right now.</div>`; return; }
    body.innerHTML = ms.map(m => {
      const sc = (m.home_score==null||m.away_score==null) ? '–' : `${m.home_score}–${m.away_score}`;
      return `<div class="score-row">
        <span class="teams">${m.home} <span class="st">v</span> ${m.away}</span>
        <span class="sc">${sc} <span class="st">${m.status||''}</span></span>
      </div>`;
    }).join('');
  }catch(e){ body.innerHTML = `<div class="empty">Couldn't reach the score service.</div>`; }
}

async function plot(){
  const btn = $('#go');
  const original = btn.textContent;
  btn.disabled = true; btn.textContent = 'Plotting…';
  const root = $('#route');
  const payload = {
    group: $('#group').value, finish: $('#finish').value,
    group_city: $('#city').value, home_tz: $('#tz').value,
  };
  try {
    const d = await (await fetch('/api/path', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})).json();
    render(d);
    root.scrollIntoView({behavior:'smooth', block:'start'});
  } catch(e) {
    root.innerHTML = `<div class="empty" style="text-align:center;padding:30px">
      Couldn't load the route just now — please try again.</div>`;
  } finally {
    btn.disabled = false; btn.textContent = original;
  }
}

function render(d){
  const root = $('#route');
  let html = `<div class="summary"><span class="big">The road ahead</span>
    <span class="km" style="font:700 13px ui-monospace,Menlo;color:var(--pitch)">tap any city for options</span></div>`;

  d.steps.forEach((step, i) => {
    if(step.certain){
      const v = step.cities[0];
      const leg = v.leg;
      const legTxt = leg.same_city ? 'Same city — no travel'
        : `<b>${leg.distance_mi} mi</b> from your last stop${leg.cross_border?' · ✈ cross-border':''}`;
      const cd = countdownHtml(step.round);
      html += `<div class="stop exact" style="animation-delay:${i*70}ms"><span class="dot"></span>
        <div class="round">${step.round_label}${cd}</div>
        <div class="city-line"><span class="city">${v.city}</span>
          <span class="stadium">${v.stadium}</span><span class="flagtag">${v.country}</span></div>
        <div class="meta">${legTxt}${v.sample_kickoff_home?` · sample kickoff in your zone <b>${v.sample_kickoff_home}</b>`:''}</div>
        ${cityActions(v, leg, step.round_label, i+'-'+v.key)}
        <div class="panel-host" id="ph-${i}-${v.key}"></div>
      </div>`;
    } else {
      const cd = countdownHtml(step.round);
      // Every candidate city is now its own tappable mini-card.
      const cards = step.cities.map(c => {
        const pid = i+'-'+c.key;
        return `<div class="candi">
          <button class="candi-head" onclick="toggleCity('${pid}')">
            <span class="candi-city">${c.city}</span>
            <span class="candi-flag">${c.country}</span>
            <span class="candi-caret" id="caret-${pid}">▸</span>
          </button>
          <div class="candi-body" id="body-${pid}" style="display:none">
            <div class="meta" style="margin:2px 0 8px">${c.stadium}</div>
            ${cityActions(c, c.leg, step.round_label, pid)}
            <div class="panel-host" id="ph-${pid}"></div>
          </div>
        </div>`;
      }).join('');
      html += `<div class="stop" style="animation-delay:${i*70}ms"><span class="dot"></span>
        <div class="round">${step.round_label}${cd}</div>
        <div class="meta">Exact city set by the bracket draw — tap a possible venue to explore it:</div>
        <div class="candi-grid">${cards}</div></div>`;
    }
  });
  root.innerHTML = html;
  startCountdowns();
}

function toggleCity(pid){
  const body = document.getElementById('body-'+pid);
  const caret = document.getElementById('caret-'+pid);
  const open = body.style.display !== 'none';
  body.style.display = open ? 'none' : 'block';
  caret.textContent = open ? '▸' : '▾';
}

function cityActions(v, leg, roundLabel, pid){
  const canFly = leg && !leg.same_city && leg.origin_iata && leg.dest_iata;
  const si = v.stadium_info || {};
  return `<div class="actions">
    ${canFly?`<button onclick="lookupFlights('${leg.origin_iata}','${leg.dest_iata}','${pid}')">Flight prices</button>`:''}
    <button onclick="lookupHotels('${v.key}','${pid}')">Find hotels</button>
    <button onclick="lookupTickets('${v.key}','${roundLabel}','${pid}')">Tickets</button>
    ${si.capacity?`<button onclick="showStadium('${v.key}','${pid}')">Stadium info</button>`:''}
  </div>`;
}

function panel(pid){ return document.getElementById('ph-'+pid); }
function setPanel(pid, html){ const p = panel(pid); if(p) p.innerHTML = `<div class="panel">${html}</div>`; }

function showStadium(cityKey, pid){
  const v = BYKEY[cityKey]; const si = (v && v.stadium_info) || {};
  if(!si.capacity){ return setPanel(pid, `<div class="notcfg">No stadium details available.</div>`); }
  setPanel(pid, `<h4>${v.stadium}</h4>
    <div class="sfacts">
      <span><span class="lbl">FIFA name</span> ${si.fifa_name||v.stadium}</span>
      <span><span class="lbl">Capacity</span> ${si.capacity.toLocaleString()}</span>
      <span><span class="lbl">Usual tenant</span> ${si.tenant||'—'}</span>
      <span><span class="lbl">Roof</span> ${si.roof||'—'}</span>
      <span><span class="lbl">Region</span> ${si.region||'—'}</span>
    </div>
    <div class="snote">${si.note||''}</div>`);
}

async function lookupFlights(origin, dest, pid){
  setPanel(pid, `<h4>Flights ${origin} → ${dest}</h4><div class="empty">Checking fares…</div>`);
  const date = $('#depart').value, adults = $('#adults').value;
  const d = await (await fetch(`/api/flights?origin=${origin}&dest=${dest}&date=${date}&adults=${adults}`)).json();
  let priceHtml = '';
  if(d.configured && d.offers && d.offers.length){
    priceHtml = `<div class="subnote">Cached recent fares — real prices people saw, not a live quote:</div>` +
      d.offers.map(o => {
        const seg = `${o.airline||'—'} · ${o.transfers===0?'nonstop':o.transfers+' stop'} · seen ${o.departure_at||date}`;
        const label = o.link ? `<a href="${o.link}" target="_blank" rel="noopener">${seg} ↗</a>` : seg;
        const fresh = o.freshness ? `<span class="fresh ${o.freshness.days>4?'stale':''}">${o.freshness.label}</span>` : '';
        return `<div class="offer"><span>${label} ${fresh}</span>
          <span class="price">$${Math.round(o.price)} ${o.currency}</span></div>`;
      }).join('');
  } else {
    priceHtml = `<div class="notcfg">${d.message||'No cached fares — check the live search below.'}</div>`;
  }
  const links = (d.live_links||[]).map(l =>
    `<a href="${l.url}" target="_blank" rel="noopener">${l.site} ↗</a>`).join('');
  setPanel(pid, `<h4>Flights ${origin} → ${dest} · ${date}</h4>
    ${priceHtml}
    <div class="subnote">See live fares:</div>
    <div class="ticket-links">${links}</div>`);
}

async function lookupHotels(cityKey, pid){
  setPanel(pid, `<h4>Hotels</h4><div class="empty">Finding searches…</div>`);
  const ci = $('#depart').value;
  const co = new Date(new Date(ci).getTime()+86400000).toISOString().slice(0,10);
  const adults = $('#adults').value;
  const d = await (await fetch(`/api/hotels?city=${cityKey}&check_in=${ci}&check_out=${co}&adults=${adults}`)).json();
  const links = (d.links||[]).map(l =>
    `<a href="${l.url}" target="_blank" rel="noopener">${l.site} ↗</a>`).join('');
  setPanel(pid, `<h4>Hotels · ${ci} → ${co}</h4>
    <div class="subnote">${d.note||'Live listings for your dates:'}</div>
    <div class="ticket-links">${links}</div>`);
}

async function lookupTickets(cityKey, roundLabel, pid){
  setPanel(pid, `<h4>Tickets</h4><div class="empty">Finding listings…</div>`);
  const d = await (await fetch(`/api/tickets?city=${cityKey}&round=${encodeURIComponent(roundLabel)}`)).json();
  let html = `<h4>Tickets · ${roundLabel}</h4>`;
  if(d.events && d.events.length){
    html += d.events.map(e => `<div class="offer">
      <span><a href="${e.url}" target="_blank" rel="noopener">${e.title}</a></span>
      <span class="price">${e.lowest_price!=null?('$'+e.lowest_price):'see site'}</span></div>`).join('');
  }
  html += `<div class="ticket-links">` +
    d.links.map(l => `<a href="${l.url}" target="_blank" rel="noopener">${l.site} ↗</a>`).join('') +
    `</div>`;
  setPanel(pid, html);
}

boot();
</script>
</body>
</html>
"""

def kickoff_in_zone(stadium_tz, home_tz, local_hhmm="20:00"):
    try:
        s, h = ZoneInfo(stadium_tz), ZoneInfo(home_tz)
    except Exception:
        return None
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    dt = datetime(2026, 7, 4, hh, mm, tzinfo=s)
    return dt.astimezone(h).strftime("%a %H:%M")

def h_meta(q, b):
    return {"venues":[venues.venue_public(k) for k in venues.VENUES],
            "groups":bracket.GROUPS,"finishes":bracket.finishes()}

def h_path(q, b):
    group=b.get("group","A"); finish=b.get("finish","win")
    gc=b.get("group_city","nyc"); htz=b.get("home_tz","America/New_York")
    if gc not in venues.VENUES: return {"error":"Unknown city"}
    prev=gc; steps=[]
    for st in bracket.path_for_team(group,finish,gc):
        cs=[]
        for ck in st["cities"]:
            v=venues.venue_public(ck); v["leg"]=venues.distance_between(prev,ck)
            v["sample_kickoff_home"]=kickoff_in_zone(v["tz"],htz); cs.append(v)
        if st["certain"]: prev=st["cities"][0]
        steps.append({**st,"cities":cs})
    return {"group":group,"finish":finish,"steps":steps}

def h_flights(q, b):
    o=q.get("origin","").upper(); d=q.get("dest","").upper(); dt=q.get("date","")
    if not (o and d and dt): return {"error":"origin, dest, date required"}
    return flights.search_flights(o,d,dt,adults=int(q.get("adults",1)))

def h_hotels(q, b):
    c=q.get("city",""); ci=q.get("check_in",""); co=q.get("check_out","")
    if c not in venues.VENUES or not (ci and co): return {"error":"valid city, check_in, check_out required"}
    v=venues.VENUES[c]
    return hotels.search_hotels(v.city, venues.COUNTRY_NAMES[v.country], ci, co, adults=int(q.get("adults",1)))

def h_scores(q, b):
    return scores.live_scores()

def h_tickets(q, b):
    c=q.get("city",""); rl=q.get("round","Match")
    cl=venues.VENUES[c].city if c in venues.VENUES else c
    return tickets.tickets_for(cl, rl)

ROUTES={"/api/meta":h_meta,"/api/path":h_path,"/api/flights":h_flights,
        "/api/hotels":h_hotels,"/api/scores":h_scores,"/api/tickets":h_tickets}

def _body(environ):
    try: n=int(environ.get("CONTENT_LENGTH",0) or 0)
    except ValueError: n=0
    if n<=0: return {}
    try: return json.loads(environ["wsgi.input"].read(n).decode())
    except Exception: return {}

def app(environ, start_response):
    path=urlparse(environ.get("PATH_INFO","/")).path
    q={k:v[0] for k,v in parse_qs(environ.get("QUERY_STRING","")).items()}
    if path in ROUTES:
        b=_body(environ) if environ.get("REQUEST_METHOD")=="POST" else {}
        try: payload=ROUTES[path](q,b); status="200 OK"
        except Exception as e: payload={"error":str(e)}; status="500 Internal Server Error"
        data=json.dumps(payload).encode()
        start_response(status,[("Content-Type","application/json"),("Cache-Control","no-store")])
        return [data]
    start_response("200 OK",[("Content-Type","text/html; charset=utf-8")])
    return [INDEX_HTML.encode("utf-8")]
