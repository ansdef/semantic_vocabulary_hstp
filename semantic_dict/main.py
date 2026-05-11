import importlib.util
import sys
from pathlib import Path

_BASE = Path(__file__).parent  # semantic_dict/
sys.path.insert(0, str(_BASE))
sys.path.insert(0, str(_BASE / "utils"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Файл называется 07_match_engine.py — имя начинается с цифры, importlib обязателен
_spec = importlib.util.spec_from_file_location("match_engine", _BASE / "07_match_engine.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
search = _mod.search

app = FastAPI(title="Semantic Vocabulary API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Семантический поиск показателей</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f5f7fa; color: #1a1a2e; }
  .wrap { max-width: 920px; margin: 0 auto; padding: 40px 20px; }
  h1 { font-size: 1.6rem; margin-bottom: 6px; }
  .sub { color: #666; margin-bottom: 28px; font-size: .95rem; }
  .search-row { display: flex; gap: 10px; }
  input[type=text] {
    flex: 1; padding: 12px 16px; font-size: 1rem;
    border: 2px solid #d0d5dd; border-radius: 10px; outline: none;
    transition: border-color .2s;
  }
  input[type=text]:focus { border-color: #4f6ef7; }
  button {
    padding: 12px 24px; background: #4f6ef7; color: #fff;
    border: none; border-radius: 10px; font-size: 1rem; cursor: pointer;
    transition: background .2s;
  }
  button:hover { background: #3a55d4; }
  button:disabled { background: #9aabf7; cursor: default; }
  #status { margin-top: 16px; font-size: .9rem; color: #888; min-height: 20px; }
  #results { margin-top: 20px; display: flex; flex-direction: column; gap: 12px; }
  .card {
    background: #fff; border-radius: 12px; padding: 16px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    border-left: 4px solid #4f6ef7;
    display: flex; gap: 16px; align-items: center;
  }
  .card-body { flex: 1; min-width: 0; }
  .indicator { font-size: .97rem; font-weight: 500; }
  .meta { margin-top: 8px; display: flex; gap: 16px; font-size: .82rem; color: #555; flex-wrap: wrap; align-items: center; }
  .badge {
    padding: 2px 8px; border-radius: 5px; font-size: .75rem;
    background: #f0f4ff; color: #4f6ef7;
  }
  .lexemes { margin-top: 8px; font-size: .8rem; color: #888; }
  .euler-wrap { flex-shrink: 0; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Семантический поиск показателей</h1>
  <p class="sub">~1200 статистических показателей регионального развития · метрика Жаккара</p>
  <div class="search-row">
    <input type="text" id="q" placeholder="Например: сколько у нас исследователей в IT"
           onkeydown="if(event.key==='Enter')doSearch()">
    <button id="btn" onclick="doSearch()">Найти</button>
  </div>
  <div id="status"></div>
  <div id="results"></div>
</div>
<script>
const INDEX_LABELS = {economic:'Экономический', personnel:'Кадровый',
                      innovation:'Инновационный', resource:'Ресурсный'};

function eulerSVG(a, b, inter) {
  const W = 190, H = 100;
  const cy = H / 2;
  // Радиусы: логарифмическое масштабирование, чтобы маленький A не терялся
  const maxR = 38, minR = 16;
  const scale = Math.log1p(Math.max(a, b));
  const ra = Math.max(minR, maxR * Math.log1p(a) / scale);
  const rb = Math.max(minR, maxR * Math.log1p(b) / scale);
  // Расстояние между центрами: overlap ratio определяет перекрытие
  const ov = Math.min(inter / Math.min(a, b), 1);
  const dist = Math.max(Math.abs(ra - rb) + 2, (ra + rb) * (1 - ov * 0.75));
  const cx = W / 2;
  const x1 = cx - dist / 2;
  const x2 = cx + dist / 2;
  // Позиции подписей
  const labelA = x1 - ra * 0.45;
  const labelB = x2 + rb * 0.3;
  const labelI = (x1 + x2) / 2;
  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
    <circle cx="${x1.toFixed(1)}" cy="${cy}" r="${ra.toFixed(1)}"
      fill="rgba(79,110,247,0.12)" stroke="#4f6ef7" stroke-width="1.5"/>
    <circle cx="${x2.toFixed(1)}" cy="${cy}" r="${rb.toFixed(1)}"
      fill="rgba(100,116,139,0.1)" stroke="#94a3b8" stroke-width="1.5"/>
    <text x="${labelA.toFixed(1)}" y="${(cy - 4).toFixed(1)}" text-anchor="middle"
      font-size="13" font-weight="700" fill="#4f6ef7">${a}</text>
    <text x="${labelA.toFixed(1)}" y="${(cy + 10).toFixed(1)}" text-anchor="middle"
      font-size="9" fill="#4f6ef7">запрос</text>
    <text x="${labelI.toFixed(1)}" y="${(cy + 5).toFixed(1)}" text-anchor="middle"
      font-size="12" font-weight="700" fill="#6d28d9">${inter}</text>
    <text x="${labelB.toFixed(1)}" y="${(cy - 4).toFixed(1)}" text-anchor="middle"
      font-size="13" font-weight="700" fill="#64748b">${b}</text>
    <text x="${labelB.toFixed(1)}" y="${(cy + 10).toFixed(1)}" text-anchor="middle"
      font-size="9" fill="#64748b">показатель</text>
  </svg>`;
}

async function doSearch() {
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  const btn = document.getElementById('btn');
  const status = document.getElementById('status');
  const results = document.getElementById('results');
  btn.disabled = true;
  status.textContent = 'Ищем…';
  results.innerHTML = '';
  try {
    const t0 = Date.now();
    const r = await fetch('/match', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({query: q})
    });
    const data = await r.json();
    const ms = Date.now() - t0;
    status.textContent = `Найдено: ${data.count} показателей · ${ms} мс`;
    results.innerHTML = data.results.map(item => `
      <div class="card">
        <div class="card-body">
          <div class="indicator">${item.indicator}</div>
          <div class="meta">
            <span>Жаккар: <b>${item.jaccard}</b></span>
            <span>Overlap: <b>${item.overlap}</b></span>
            ${item.indices.map(i => `<span class="badge">${INDEX_LABELS[i]||i}</span>`).join('')}
          </div>
          <div class="lexemes">совпало: ${item.matched_lexemes.slice(0,8).join(', ')}</div>
        </div>
        <div class="euler-wrap">
          ${eulerSVG(item.cloud_A_size, item.cloud_B_size, item.intersection_size)}
        </div>
      </div>`).join('');
  } catch(e) {
    status.textContent = 'Ошибка запроса';
  }
  btn.disabled = false;
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return _HTML


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/match")
def match_endpoint(req: QueryRequest):
    results = search(req.query)
    return {"query": req.query, "count": len(results), "results": results[:50]}
