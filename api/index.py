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
from _lib import venues, bracket, flights, hotels, scores, tickets, costs, matchups  # noqa

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Follow My Team — WC26</title>
<style>
  :root{
    --ink:#0a1f14;            /* deep pitch-night green-black */
    --paper:#f4f7f2;          /* clean off-white field chalk */
    --paper2:#ffffff;
    --pitch:#0f8a4d;          /* vivid grass green */
    --pitch-dark:#0a6e3c;
    --pitch-soft:#d4ede0;
    --grass1:#0e7a45;         /* mowed-stripe greens for hero */
    --grass2:#0c6e3e;
    --flag:#e8472b;           /* signal red-orange */
    --gold:#f4c430;           /* trophy gold accent */
    --muted:#5e7468; --rule:#cdded4;
    --live:#e8112d;
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{
    background:var(--paper);
    color:var(--ink);
    font-family:"Helvetica Neue",Arial,sans-serif; line-height:1.5;
  }
  .wrap{max-width:840px;margin:0 auto;padding:0 16px 80px}

  /* HERO — tournament banner with mowed-pitch stripes */
  header{
    margin:0 -16px 20px; padding:30px 24px 26px; position:relative; overflow:hidden;
    background:
      repeating-linear-gradient(90deg, var(--grass1) 0 46px, var(--grass2) 46px 92px);
    color:#fff;
    border-bottom:4px solid var(--gold);
  }
  header::after{ /* subtle vignette + center-circle hint */
    content:""; position:absolute; inset:0;
    background:
      radial-gradient(circle at 88% 30%, rgba(255,255,255,.10) 0 70px, transparent 72px),
      linear-gradient(180deg, rgba(0,0,0,.05), rgba(0,0,0,.28));
    pointer-events:none;
  }
  header > *{position:relative;z-index:1}
  .kicker{font:800 12px/1 inherit;letter-spacing:.28em;text-transform:uppercase;color:var(--gold);
    display:flex;align-items:center;gap:9px}
  .kicker::before{content:"⚽";font-size:15px;letter-spacing:0}
  h1{font:900 38px/1 inherit;letter-spacing:-.025em;margin:12px 0 6px;text-shadow:0 2px 8px rgba(0,0,0,.25)}
  .sub{color:rgba(255,255,255,.92);font-size:14px;max-width:54ch}

  /* live scores — stadium scoreboard feel */
  .scores{margin:18px 0;border-radius:12px;background:var(--ink);overflow:hidden;
    box-shadow:0 6px 20px rgba(10,31,20,.18)}
  .scores h2{font:800 11px/1 inherit;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);
    margin:0;padding:12px 16px;border-bottom:1px solid rgba(255,255,255,.12);display:flex;align-items:center;gap:9px}
  .live-dot{width:9px;height:9px;border-radius:50%;background:var(--live);display:inline-block;
    box-shadow:0 0 0 0 rgba(232,17,45,.6);animation:pulse 1.6s infinite}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(232,17,45,.6)}70%{box-shadow:0 0 0 7px rgba(232,17,45,0)}100%{box-shadow:0 0 0 0 rgba(232,17,45,0)}}
  @media (prefers-reduced-motion:reduce){.live-dot{animation:none}}
  .score-row{display:flex;justify-content:space-between;gap:10px;padding:11px 16px;
    border-bottom:1px solid rgba(255,255,255,.08);font-size:14px;color:#eaf3ee}
  .score-row:last-child{border-bottom:none}
  .score-row .teams{font-weight:600}
  .score-row .sc{font:800 15px ui-monospace,Menlo,monospace;color:#fff}
  .score-row .st{color:var(--gold);font-size:11px;font-weight:700}
  .empty{padding:14px 16px;font-size:13px;color:rgba(234,243,238,.6);font-style:italic}

  .stub{margin-top:6px;border:none;background:var(--paper2);border-radius:14px;
    padding:18px;display:grid;gap:13px;grid-template-columns:1fr 1fr;
    box-shadow:0 4px 16px rgba(10,31,20,.08);border-top:4px solid var(--pitch)}
  .stub .full{grid-column:1/-1}
  label{display:block;font:800 11px/1 inherit;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
  select,input[type=date]{width:100%;padding:11px 12px;border:1.5px solid var(--rule);border-radius:8px;background:#fff;font-size:15px;color:var(--ink)}
  select:focus,input:focus{outline:3px solid var(--pitch-soft);border-color:var(--pitch)}
  button{padding:13px;border:none;border-radius:9px;background:var(--pitch);color:#fff;font:800 15px/1 inherit;letter-spacing:.03em;cursor:pointer;transition:transform .08s,background .15s}
  button:hover{background:var(--pitch-dark)}
  button:active{transform:translateY(1px)}
  button:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
  .go-row{grid-column:1/-1}
  .go-row button{width:100%}

  .route{margin-top:30px}

  /* visual map */
  :root{--map-sea:#dcebf2;--map-land:#eef4ec;}
  .mapbox{margin:6px 0 22px;border-radius:14px;overflow:hidden;background:#fff;
    box-shadow:0 4px 16px rgba(10,31,20,.10);border:1.5px solid var(--rule)}
  .map-legend{display:flex;flex-wrap:wrap;gap:14px;padding:11px 14px;font:700 11px/1 inherit;
    letter-spacing:.04em;color:var(--muted);text-transform:uppercase;border-bottom:1px solid var(--rule);align-items:center}
  .map-legend span{display:flex;align-items:center;gap:6px}
  .map-hint{margin-left:auto;color:var(--pitch-dark)}
  .lg{width:11px;height:11px;border-radius:50%;display:inline-block}
  .lg-start{background:var(--pitch)}
  .lg-on{background:#6fae8c}
  .lg-final{background:var(--gold)}
  .map-svg{display:block;width:100%;height:auto;background:var(--map-sea)}
  .land{stroke:#fff;stroke-width:1.5;stroke-linejoin:round}
  .land-us{fill:#eaf3ec}
  .land-ca{fill:#e3efe6}
  .land-mx{fill:#f0f1e4}
  .mv-region{fill:#a9c3b6;font:800 15px/1 "Helvetica Neue",Arial;letter-spacing:.22em;text-anchor:middle;text-transform:uppercase;pointer-events:none}
  .mv{cursor:pointer}
  .mv .mvdot{fill:#9fb6aa;stroke:#fff;stroke-width:1.5;transition:transform .12s}
  .mv:hover .mvdot,.mv:focus .mvdot{transform:scale(1.35);transform-origin:center;transform-box:fill-box}
  .mv:focus{outline:none}
  .mv-on .mvdot{fill:#4f9e76}
  .mv-start .mvdot{fill:var(--pitch);stroke:#fff;stroke-width:2.5}
  .mv-final .mvdot{fill:var(--gold);stroke:#fff;stroke-width:2.5}
  .mvlabel{fill:var(--ink);font:800 14px/1 "Helvetica Neue",Arial;paint-order:stroke;stroke:#fff;stroke-width:3.5px;pointer-events:none}
  .map-note{padding:10px 14px;font-size:11px;color:var(--muted);font-style:italic;border-top:1px solid var(--rule)}
  .stop.flash,.candi.flash{animation:flashbg 1.2s ease}
  @keyframes flashbg{0%,100%{background:transparent}30%{background:rgba(244,196,48,.22)}}

  .summary{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:14px}
  .summary .big{font:900 22px/1 inherit;letter-spacing:-.02em}
  .summary .big::before{content:"🏟 ";font-size:18px}
  /* pitch-path timeline */
  .stop{position:relative;padding:18px 0 18px 44px;opacity:0;transform:translateY(8px);animation:rise .45s ease forwards}
  @keyframes rise{to{opacity:1;transform:none}}
  @media (prefers-reduced-motion:reduce){.stop{animation:none;opacity:1;transform:none}}
  .stop:not(:last-child)::before{content:"";position:absolute;left:14px;top:28px;bottom:-12px;width:3px;
    background:repeating-linear-gradient(180deg,var(--pitch) 0 8px,transparent 8px 14px)}
  .dot{position:absolute;left:6px;top:20px;width:18px;height:18px;border-radius:50%;background:#fff;
    border:3px solid var(--pitch);box-shadow:0 0 0 4px var(--pitch-soft)}
  .stop.exact .dot{background:var(--pitch)}
  .stop.exact:last-child .dot{background:var(--gold);border-color:var(--gold);box-shadow:0 0 0 4px rgba(244,196,48,.3)}
  .round{font:800 11px/1 inherit;letter-spacing:.16em;text-transform:uppercase;color:var(--pitch-dark);margin-bottom:8px;display:flex;align-items:center;gap:4px}
  .ri{font-size:13px;letter-spacing:0}
  .city-line{display:flex;flex-wrap:wrap;align-items:baseline;gap:9px}
  .city{font:900 21px/1.05 inherit;letter-spacing:-.01em}
  .stadium{color:var(--muted);font-size:13px}
  .flagtag{font:800 10px/1 inherit;letter-spacing:.08em;border:1.5px solid var(--pitch);border-radius:5px;padding:3px 6px;color:var(--pitch-dark);background:var(--pitch-soft)}
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
  .actions button{padding:8px 12px;font-size:12px;letter-spacing:.04em;font-weight:700;background:#fff;color:var(--pitch-dark);border:1.5px solid var(--pitch);border-radius:8px;cursor:pointer}
  .actions button:hover{background:var(--pitch);color:#fff}
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
  .ghost{flex:1;background:#fff;color:var(--pitch-dark);border:1.5px solid var(--pitch)!important}
  .ghost:hover{background:var(--pitch-soft);color:var(--pitch-dark)}

  /* trip cost estimator */
  .cost-wrap{margin-top:28px;border:1.5px solid var(--ink);border-radius:12px;background:var(--paper2);padding:18px}

  /* possible opponents */
  .foes-wrap{margin-top:24px;border:1.5px solid var(--pitch);border-radius:14px;background:var(--paper2);padding:18px;border-top:4px solid var(--pitch)}
  .foes-head{margin-bottom:14px}
  .foes-title{display:block;font:800 18px/1.1 inherit;letter-spacing:-.01em}
  .foes-sub{display:block;font-size:13px;color:var(--muted);margin-top:3px}
  .foe-stage{padding:13px 0;border-bottom:1px solid var(--rule)}
  .foe-stage:last-of-type{border-bottom:none}
  .foe-stage-head{display:flex;align-items:center;gap:10px;margin-bottom:3px}
  .foe-rd{font:800 13px/1 inherit;letter-spacing:.04em;text-transform:uppercase;color:var(--pitch-dark)}
  .foe-known{font:800 9px/1 inherit;letter-spacing:.08em;text-transform:uppercase;background:var(--pitch);color:#fff;border-radius:20px;padding:3px 8px}
  .foe-maybe{font:800 9px/1 inherit;letter-spacing:.08em;text-transform:uppercase;background:var(--pitch-soft);color:var(--pitch-dark);border-radius:20px;padding:3px 8px}
  .foe-note{font-size:12px;color:var(--muted);margin-bottom:8px}
  .foe-note b{color:var(--ink)}
  .foe-chips{display:flex;flex-wrap:wrap;gap:6px}
  .foe-chip{font:700 12px/1 inherit;background:#fff;border:1.5px solid var(--rule);border-radius:20px;padding:6px 11px;display:inline-flex;align-items:center;gap:5px}
  .foe-chip.foe-tbd{font-style:italic;color:var(--muted);border-style:dashed}
  .foe-foot{font-size:11px;color:var(--muted);margin-top:12px;line-height:1.5;font-style:italic}
  .cost-head{margin-bottom:14px}
  .cost-title{display:block;font:800 18px/1.1 inherit;letter-spacing:-.01em}
  .cost-sub{display:block;font-size:13px;color:var(--muted);margin-top:3px}
  .cost-inputs{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:end}
  .cost-inputs label{display:block;font:700 11px/1 inherit;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
  .cost-inputs select,.cost-inputs input[type=number]{width:100%;padding:10px 11px;border:1.5px solid var(--rule);border-radius:7px;background:#fff;font-size:15px;color:var(--ink)}
  .cost-toggle{font-size:13px;color:var(--ink);display:flex;align-items:center}
  .cost-toggle label{text-transform:none;letter-spacing:0;font-weight:600;color:var(--ink);display:flex;gap:7px;align-items:center;margin:0}
  #calc{grid-column:1/-1;padding:13px;border:none;border-radius:9px;background:var(--gold);color:var(--ink);font:800 14px/1 inherit;letter-spacing:.04em;cursor:pointer}
  #calc:hover{background:#e0b020}
  #cost-result{margin-top:16px}
  .cost-total{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
    background:linear-gradient(135deg,var(--pitch-dark),var(--pitch));color:#fff;border-radius:12px;
    padding:16px 18px;margin-bottom:13px;border-left:5px solid var(--gold);box-shadow:0 6px 18px rgba(15,138,77,.25)}
  .cost-total-lbl{font:700 12px/1.3 inherit;letter-spacing:.04em;max-width:55%}
  .cost-total-amt{font:800 25px/1 ui-monospace,Menlo,monospace;color:var(--gold)}
  .cost-cat{border:1px solid var(--rule);border-radius:9px;background:#fff;padding:12px 14px;margin-bottom:10px}
  .cost-cat-head{display:flex;justify-content:space-between;font:800 15px/1 inherit;margin-bottom:6px}
  .cost-line{display:flex;justify-content:space-between;font-size:13px;color:var(--muted);padding:3px 0}
  .cost-amt{font:700 14px ui-monospace,Menlo,monospace;color:var(--pitch)}
  .cost-line .cost-amt{font-size:12px}
  .cost-basis{font-size:11px;color:var(--muted);font-style:italic;margin-top:6px;border-top:1px solid #f0e8d6;padding-top:6px}
  .cost-foot{font-size:11px;color:var(--muted);margin-top:10px;line-height:1.5}
  .live-pill{display:inline-block;font:800 9px/1 inherit;letter-spacing:.08em;background:var(--pitch);color:#fff;
    border-radius:20px;padding:3px 7px;margin-left:6px;vertical-align:middle;text-transform:uppercase}
  .live-tag{display:inline-block;font:800 9px/1 inherit;letter-spacing:.05em;background:var(--pitch-soft);color:var(--pitch-dark);
    border-radius:4px;padding:2px 5px;margin-left:4px;vertical-align:middle}
  .rate{color:var(--muted);font-weight:600;font-size:11px}
  .maybe-tag{display:inline-block;font:700 9px/1 inherit;color:var(--muted);border:1px solid var(--rule);
    border-radius:4px;padding:2px 4px;margin-left:3px;vertical-align:middle;text-transform:uppercase}
  @media (max-width:520px){.cost-inputs{grid-template-columns:1fr}.cost-total-lbl{max-width:100%}}

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

  <section class="cost-wrap" id="cost-wrap" style="display:none">
    <div class="cost-head">
      <span class="cost-title">What will following your team cost?</span>
      <span class="cost-sub">Estimate the whole journey if they go all the way</span>
    </div>
    <div class="cost-inputs">
      <div>
        <label for="nights">Nights per city</label>
        <select id="nights"><option>1</option><option selected>2</option><option>3</option><option>4</option><option>5</option></select>
      </div>
      <div>
        <label for="budget">Nightly hotel budget — blank = real city rates</label>
        <input type="number" id="budget" placeholder="Use real WC26 rates" min="0" step="10">
      </div>
      <div class="cost-toggle">
        <label><input type="checkbox" id="incflights" checked> Include flights (live fares where available)</label>
      </div>
      <button id="calc">Estimate trip cost</button>
    </div>
    <div id="cost-result"></div>
  </section>

  <section class="foes-wrap" id="foes-wrap" style="display:none">
    <div class="foes-head">
      <span class="foes-title">🤜 Who could you face?</span>
      <span class="foes-sub">Possible opponents at each stage, from the official draw &amp; bracket</span>
    </div>
    <div id="foes-result"></div>
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
let VENUES = [], BYKEY = {}, MAP = null;

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
const ROUND_ICON = {
  group: '🟢', r32: '⚔️', r16: '🔥', qf: '💥', sf: '🏟️', final: '🏆',
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

async function loadFoes(payload){
  const wrap = $('#foes-wrap'), out = $('#foes-result');
  wrap.style.display = 'block';
  out.innerHTML = '<div class="empty">Reading the bracket…</div>';
  try {
    const d = await (await fetch('/api/matchups', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({group: payload.group, finish: payload.finish})})).json();
    if(d.error){ out.innerHTML = `<div class="notcfg">${d.error}</div>`; return; }
    const s = d.stages;
    const order = [['group','Group stage'],['r32','Round of 32'],['r16','Round of 16'],
                   ['qf','Quarter-final'],['sf','Semi-final'],['final','Final']];
    const icon = {group:'🟢',r32:'⚔️',r16:'🔥',qf:'💥',sf:'🏟️',final:'🏆'};
    let html = '';
    for(const [key,label] of order){
      const st = s[key];
      if(!st) continue;
      const chips = st.teams.map(t => {
        const tbd = t.startsWith('TBD');
        return `<span class="foe-chip${tbd?' foe-tbd':''}">${flagFor(t)} ${t}</span>`;
      }).join('');
      const tag = st.known
        ? `<span class="foe-known">confirmed</span>`
        : `<span class="foe-maybe">${st.teams.length} possible</span>`;
      const sub = st.known ? st.note
        : (st.slot_label ? `vs <b>${st.slot_label}</b> — could be:` : st.note);
      html += `<div class="foe-stage">
        <div class="foe-stage-head"><span class="foe-rd">${icon[key]} ${label}</span> ${tag}</div>
        <div class="foe-note">${sub}</div>
        <div class="foe-chips">${chips}</div>
      </div>`;
    }
    out.innerHTML = html +
      `<div class="foe-foot">Group opponents are set by the Dec 5 draw. Knockout names are every nation that could fill that bracket slot — who actually arrives depends on results, so these are possibilities, not predictions.</div>`;
  } catch(e){
    out.innerHTML = `<div class="notcfg">Couldn't load matchups — please try again.</div>`;
  }
}

// Minimal flag emoji lookup for the nations in the draw.
const FLAGS = {
  'Mexico':'🇲🇽','South Korea':'🇰🇷','South Africa':'🇿🇦','Canada':'🇨🇦','Qatar':'🇶🇦',
  'Switzerland':'🇨🇭','Brazil':'🇧🇷','Morocco':'🇲🇦','Scotland':'🏴󠁧󠁢󠁳󠁣󠁴󠁿','Haiti':'🇭🇹',
  'United States':'🇺🇸','Paraguay':'🇵🇾','Australia':'🇦🇺','Germany':'🇩🇪','Ecuador':'🇪🇨',
  'Ivory Coast':'🇨🇮','Curacao':'🇨🇼','Netherlands':'🇳🇱','Japan':'🇯🇵','Tunisia':'🇹🇳',
  'Belgium':'🇧🇪','Iran':'🇮🇷','Egypt':'🇪🇬','New Zealand':'🇳🇿','Spain':'🇪🇸',
  'Uruguay':'🇺🇾','Saudi Arabia':'🇸🇦','Cabo Verde':'🇨🇻','France':'🇫🇷','Senegal':'🇸🇳',
  'Norway':'🇳🇴','Argentina':'🇦🇷','Austria':'🇦🇹','Algeria':'🇩🇿','Jordan':'🇯🇴',
  'Portugal':'🇵🇹','Colombia':'🇨🇴','Uzbekistan':'🇺🇿','England':'🏴󠁧󠁢󠁥󠁮󠁧󠁿','Croatia':'🇭🇷',
  'Panama':'🇵🇦','Ghana':'🇬🇭',
};
function flagFor(team){ return FLAGS[team] || '🏳️'; }

async function estimateCost(){
  const out = $('#cost-result');
  const calcBtn = $('#calc'); const orig = calcBtn.textContent;
  calcBtn.disabled = true; calcBtn.textContent = 'Estimating…';
  const budgetRaw = $('#budget').value.trim();
  const payload = {
    group: $('#group').value, finish: $('#finish').value, group_city: $('#city').value,
    nights_per_stop: parseInt($('#nights').value, 10),
    nightly_budget: budgetRaw === '' ? null : parseFloat(budgetRaw),
    include_flights: $('#incflights').checked,
    travel_date: $('#depart').value,
  };
  try {
    const d = await (await fetch('/api/cost', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})).json();
    if(d.error){ out.innerHTML = `<div class="notcfg">${d.error}</div>`; return; }
    const usd = n => '$' + Math.round(n).toLocaleString();
    const t = d.tickets, h = d.hotels, fl = d.flights, g = d.grand;

    const ticketRows = t.lines.map(l =>
      `<div class="cost-line"><span>${l.round}${l.matches>1?` ×${l.matches}`:''}</span>
       <span class="cost-amt">${usd(l.low)}–${usd(l.high)}</span></div>`).join('');

    // Per-city hotel breakdown
    const hotelRows = (h.lines||[]).map(l =>
      `<div class="cost-line"><span>${l.city} · ${l.nights}n${l.known?'':' <span class="maybe-tag">possible</span>'}</span>
       <span class="cost-amt">${usd(l.cost)} <span class="rate">($${l.rate}/n)</span></span></div>`).join('');

    // Flight legs with LIVE markers
    let flightRows = '';
    if(fl.legs && fl.legs.length){
      flightRows = fl.legs.map(l => {
        const amt = l.low === l.high ? usd(l.low) : `${usd(l.low)}–${usd(l.high)}`;
        const tag = l.live ? `<span class="live-tag">LIVE${l.seen?' · '+l.seen:''}</span>` : '';
        return `<div class="cost-line"><span>→ ${l.to} ${tag}</span><span class="cost-amt">${amt}</span></div>`;
      }).join('');
    }
    const flightBlock = fl.included ? `
      <div class="cost-cat">
        <div class="cost-cat-head"><span>✈️ Flights ${fl.any_live?'<span class="live-pill">LIVE fares</span>':''}</span><span class="cost-amt">${usd(fl.low)}–${usd(fl.high)}</span></div>
        ${flightRows}
        <div class="cost-basis">${fl.basis}</div>
      </div>` : '';

    out.innerHTML = `
      <div class="cost-total">
        <span class="cost-total-lbl">Estimated total if they reach the Final</span>
        <span class="cost-total-amt">${usd(g.low)} – ${usd(g.high)}</span>
      </div>
      <div class="cost-cat">
        <div class="cost-cat-head"><span>🎟️ Tickets</span><span class="cost-amt">${usd(t.low)}–${usd(t.high)}</span></div>
        ${ticketRows}
        <div class="cost-basis">${t.basis}</div>
      </div>
      <div class="cost-cat">
        <div class="cost-cat-head"><span>🏨 Hotels ${h.using_real_rates?'<span class="live-pill">real city rates</span>':''}</span><span class="cost-amt">${usd(h.total)}</span></div>
        ${hotelRows}
        <div class="cost-basis">${h.basis}</div>
      </div>
      ${flightBlock}
      <div class="cost-foot">Tickets use FIFA's published base bands (dynamic pricing). Hotels use ${h.using_real_rates?"real per-city WC26 tournament rates":"your set budget"}. Flights show real cached fares where available (marked LIVE), otherwise a distance-based estimate.</div>`;
  } catch(e){
    out.innerHTML = `<div class="notcfg">Couldn't estimate just now — please try again.</div>`;
  } finally {
    calcBtn.disabled = false; calcBtn.textContent = orig;
  }
}

async function boot(){
  const meta = await (await fetch('/api/meta')).json();
  VENUES = meta.venues; VENUES.forEach(v => BYKEY[v.key] = v);
  MAP = meta.map;

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
  const calcBtn = $('#calc');
  if(calcBtn) calcBtn.addEventListener('click', estimateCost);
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
    $('#cost-wrap').style.display = 'block';
    $('#cost-result').innerHTML = '';
    loadFoes(payload);
    root.scrollIntoView({behavior:'smooth', block:'start'});
  } catch(e) {
    root.innerHTML = `<div class="empty" style="text-align:center;padding:30px">
      Couldn't load the route just now — please try again.</div>`;
  } finally {
    btn.disabled = false; btn.textContent = original;
  }
}

// Simplified country outlines, pre-projected to the map viewBox (same
// projection as the venue dots, so they align). Coarse but recognisable.
const US_PATH = 'M 12.5,39.5 L 38.9,43.2 L 46.7,65.8 L 20.2,140.9 L 17.1,189.8 L 48.3,238.6 L 76.3,302.5 L 130.8,338.2 L 168.2,334.4 L 225.8,360.7 L 269.5,351.3 L 295.9,351.3 L 350.4,403.9 L 375.4,388.9 L 411.2,452.8 L 442.3,462.2 L 437.7,422.7 L 490.6,390.8 L 537.3,400.2 L 568.5,400.2 L 584.1,377.6 L 630.8,390.8 L 665.1,424.6 L 708.7,475.3 L 707.1,445.3 L 685.3,372.0 L 696.2,347.6 L 730.5,311.9 L 778.8,287.5 L 786.5,234.8 L 802.1,187.9 L 848.8,171.0 L 864.4,159.7 L 866.0,127.8 L 911.2,109.0 L 876.9,58.2 L 841.1,103.3 L 786.5,105.2 L 763.2,129.6 L 724.2,135.3 L 671.3,165.3 L 660.4,159.7 L 669.7,103.3 L 635.5,75.2 L 577.8,41.3 L 540.5,43.2 L 471.9,28.2 L 334.9,28.2 L 179.1,28.2 L 38.9,28.2 L 12.5,39.5 Z';
const CA_PATH = 'M 34.3,28.2 L 179.1,28.2 L 334.9,28.2 L 471.9,28.2 L 540.5,43.2 L 577.8,41.3 L 635.5,75.2 L 669.7,103.3 L 660.4,159.7 L 724.2,135.3 L 763.2,129.6 L 786.5,105.2 L 841.1,103.3 L 876.9,58.2 L 942.3,65.8 L 1020.2,65.8 L 1082.5,-9.4 L 957.9,-28.2 L 739.8,-28.2 L 724.2,-84.5 L 490.6,-159.7 L 241.4,-178.5 L 38.9,-159.7 L -70.1,-84.5 L -116.8,-65.8 L -38.9,-9.4 L 34.3,28.2 Z';
const MX_PATH = 'M 130.8,338.2 L 168.2,334.4 L 225.8,360.7 L 269.5,351.3 L 295.9,351.3 L 350.4,403.9 L 375.4,388.9 L 411.2,452.8 L 442.3,462.2 L 433.0,535.5 L 475.0,601.2 L 521.8,601.2 L 579.4,544.8 L 604.3,554.2 L 584.1,601.2 L 552.9,614.4 L 518.7,667.0 L 459.5,653.8 L 381.6,629.4 L 308.4,565.5 L 313.1,516.7 L 250.8,509.2 L 210.3,497.9 L 179.1,441.5 L 179.1,422.7 L 232.1,509.2 L 205.6,403.9 L 166.7,366.4 L 130.8,338.2 Z';

function buildMap(d){
  if(!MAP) return '';
  const W = MAP.w, H = MAP.h, P = MAP.points;
  const PAD = 60; // padding so edge labels (e.g. NYC) aren't clipped

  const groupCity = d.steps.find(s => s.round === 'group');
  const startKey = groupCity ? groupCity.cities[0].key : null;
  const finalStep = d.steps.find(s => s.round === 'final');
  const finalKey = finalStep ? finalStep.cities[0].key : null;
  const touched = new Set();
  d.steps.forEach(s => s.cities.forEach(c => touched.add(c.key)));

  // route arc start -> final
  let routeLine = '';
  if(startKey && finalKey && P[startKey] && P[finalKey]){
    const a = P[startKey], b = P[finalKey];
    routeLine = `<path d="M ${a.x} ${a.y} Q ${(a.x+b.x)/2} ${Math.min(a.y,b.y)-70} ${b.x} ${b.y}"
      fill="none" stroke="var(--gold)" stroke-width="3.5" stroke-dasharray="1 8"
      stroke-linecap="round" opacity="0.95"/>`;
  }

  // dots — every one tappable
  let dots = '';
  Object.entries(P).forEach(([k, p]) => {
    const isStart = k === startKey, isFinal = k === finalKey, isOn = touched.has(k);
    let cls = 'mv';
    if(isFinal) cls += ' mv-final'; else if(isStart) cls += ' mv-start'; else if(isOn) cls += ' mv-on';
    const r = (isStart||isFinal) ? 8.5 : (isOn ? 6.5 : 5);
    // label only the start + final to avoid clutter; place inward if near edge
    let label = '';
    if(isStart || isFinal){
      const nearRight = p.x > W - 140;
      const lx = nearRight ? p.x - 13 : p.x + 13;
      const anchor = nearRight ? 'end' : 'start';
      label = `<text x="${lx}" y="${p.y+4}" class="mvlabel" text-anchor="${anchor}">${p.city}</text>`;
    }
    dots += `<g class="${cls}" onclick="mapTap('${k}')" tabindex="0" role="button"
        aria-label="${p.city}" onkeydown="if(event.key==='Enter')mapTap('${k}')">
      <circle cx="${p.x}" cy="${p.y}" r="16" fill="transparent"></circle>
      <circle cx="${p.x}" cy="${p.y}" r="${r}" class="mvdot"></circle>
      ${label}
    </g>`;
  });

  const labels = `
    <text x="${W*0.52}" y="58" class="mv-region">CANADA</text>
    <text x="${W*0.40}" y="${H*0.46}" class="mv-region">UNITED STATES</text>
    <text x="${W*0.36}" y="${H-20}" class="mv-region">MEXICO</text>`;

  return `<div class="mapbox">
    <div class="map-legend">
      <span><i class="lg lg-start"></i> Group stage</span>
      <span><i class="lg lg-on"></i> Possible venue</span>
      <span><i class="lg lg-final"></i> Final</span>
      <span class="map-hint">tap a city ↗</span>
    </div>
    <svg viewBox="${-PAD} ${-PAD} ${W+PAD*2} ${H+PAD*2}" class="map-svg" preserveAspectRatio="xMidYMid meet"
         role="img" aria-label="Map of your team's possible venues across North America">
      <rect x="${-PAD}" y="${-PAD}" width="${W+PAD*2}" height="${H+PAD*2}" fill="var(--map-sea)"/>
      <path d="${CA_PATH}" class="land land-ca"/>
      <path d="${US_PATH}" class="land land-us"/>
      <path d="${MX_PATH}" class="land land-mx"/>
      ${labels}
      ${routeLine}
      ${dots}
    </svg>
    <div class="map-note">Tap any city to see its travel options below. Dashed gold line marks the confirmed start-to-Final direction.</div>
  </div>`;
}

// Tapping a map dot scrolls to that city and opens it.
function mapTap(cityKey){
  // Prefer the certain stop with this key; else the first candidate card.
  let target = document.getElementById('ph-'+findStopIndex(cityKey)+'-'+cityKey);
  // open a candidate card if present
  const candi = document.querySelector(`[id^="body-"][id$="-${cityKey}"]`);
  if(candi && candi.style.display === 'none'){
    const pid = candi.id.replace('body-','');
    toggleCity(pid);
    target = document.getElementById('ph-'+pid);
  }
  const card = candi ? candi.closest('.candi') : (target ? target.closest('.stop') : null);
  if(card){ card.scrollIntoView({behavior:'smooth', block:'center'});
    card.classList.add('flash'); setTimeout(()=>card.classList.remove('flash'), 1200); }
}
function findStopIndex(cityKey){
  // certain stops use index-key ids; scan for a matching panel host
  const hosts = document.querySelectorAll('[id^="ph-"]');
  for(const h of hosts){ if(h.id.endsWith('-'+cityKey)) return h.id.split('-')[1]; }
  return '';
}


function render(d){
  const root = $('#route');
  let html = `<div class="summary"><span class="big">The road ahead</span>
    <span class="km" style="font:700 13px ui-monospace,Menlo;color:var(--pitch)">tap any city for options</span></div>`;

  html += buildMap(d);

  d.steps.forEach((step, i) => {
    if(step.certain){
      const v = step.cities[0];
      const leg = v.leg;
      const legTxt = leg.same_city ? 'Same city — no travel'
        : `<b>${leg.distance_mi} mi</b> from your last stop${leg.cross_border?' · ✈ cross-border':''}`;
      const cd = countdownHtml(step.round);
      html += `<div class="stop exact" style="animation-delay:${i*70}ms"><span class="dot"></span>
        <div class="round"><span class="ri">${ROUND_ICON[step.round]||""}</span>${step.round_label}${cd}</div>
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
        <div class="round"><span class="ri">${ROUND_ICON[step.round]||""}</span>${step.round_label}${cd}</div>
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
            "groups":bracket.GROUPS,"finishes":bracket.finishes(),
            "map":venues.map_points()}

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

def h_cost(q, b):
    group=b.get("group","A"); finish=b.get("finish","win")
    gc=b.get("group_city","nyc")
    if gc not in venues.VENUES: return {"error":"Unknown city"}
    nights = b.get("nights_per_stop", 2)
    try:
        nights = int(nights)
    except (TypeError, ValueError):
        return {"error":"nights_per_stop must be a number"}
    # budget is OPTIONAL: if omitted/blank, use real per-city WC26 rates.
    budget = b.get("nightly_budget", None)
    if budget in ("", None):
        budget = None
    else:
        try:
            budget = float(budget)
        except (TypeError, ValueError):
            return {"error":"nightly_budget must be a number or blank"}
    include_flights = bool(b.get("include_flights", True))
    travel_date = b.get("travel_date", "")

    # Build the path with legs
    prev=gc; steps=[]
    for st in bracket.path_for_team(group,finish,gc):
        cs=[]
        for ck in st["cities"]:
            v=venues.venue_public(ck); v["leg"]=venues.distance_between(prev,ck); cs.append(v)
        if st["certain"]: prev=st["cities"][0]
        steps.append({**st,"cities":cs})

    # Fetch REAL cached fares for the confirmed legs (only the certain ones,
    # to keep it to a couple of provider calls). Keyed by "origin->dest".
    live_fares = {}
    if include_flights and travel_date:
        seen_keys = set()
        for st in steps:
            if not st["certain"]:
                continue
            leg = st["cities"][0].get("leg") or {}
            o, dst = leg.get("origin_iata"), leg.get("dest_iata")
            if not o or not dst or leg.get("same_city"):
                continue
            fkey = f"{o}->{dst}"
            if fkey in seen_keys:
                continue
            seen_keys.add(fkey)
            try:
                res = flights.search_flights(o, dst, travel_date)
                if res.get("configured") and res.get("cheapest"):
                    c = res["cheapest"]
                    live_fares[fkey] = {
                        "price": c.get("price"),
                        "airline": c.get("airline", ""),
                        "found": (c.get("freshness") or {}).get("label", ""),
                    }
            except Exception:
                pass  # fall back to estimate band; never fabricate

    return costs.estimate(steps, nights, nightly_budget=budget,
                          include_flights=include_flights, live_fares=live_fares)

def h_matchups(q, b):
    group=b.get("group", q.get("group","A"))
    finish=b.get("finish", q.get("finish","win"))
    if group not in matchups.GROUPS:
        return {"error":"Unknown group"}
    return {"group_id":group, "finish":finish,
            "stages":matchups.opponents_for(group, finish)}

ROUTES={"/api/meta":h_meta,"/api/path":h_path,"/api/flights":h_flights,
        "/api/hotels":h_hotels,"/api/scores":h_scores,"/api/tickets":h_tickets,
        "/api/cost":h_cost,"/api/matchups":h_matchups}

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
