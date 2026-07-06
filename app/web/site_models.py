"""模型目录页 /models（v2.5，借鉴 OpenRouter）：搜索 + 排序 + 价格 + 类型。"""
from .shared import merge_i18n, page

_I18N = {
    "zh": {
        "models_title": "模型目录", "models_sub": "一个 key 调用所有模型。价格透明，按量计费。",
        "search_ph": "搜索模型…",
        "sort_name": "名称", "sort_price_low": "价格 低→高", "sort_price_high": "价格 高→低",
        "col_model": "模型", "col_type": "类型", "col_in": "输入", "col_out": "输出", "col_action": "",
        "per_m": "/ 百万 tokens", "free": "未计费", "use": "调用",
        "loading": "加载中…", "empty": "暂无可用模型",
        "count": "个模型", "usd_toggle": "美元",
        "modal_title": "调用示例", "modal_close": "关闭",
    },
    "en": {
        "models_title": "Models", "models_sub": "One key for every model. Transparent pricing, pay as you go.",
        "search_ph": "Search models…",
        "sort_name": "Name", "sort_price_low": "Price low→high", "sort_price_high": "Price high→low",
        "col_model": "Model", "col_type": "Type", "col_in": "Input", "col_out": "Output", "col_action": "",
        "per_m": "/ 1M tokens", "free": "Free", "use": "Use",
        "loading": "Loading…", "empty": "No models available",
        "count": "models", "usd_toggle": "USD",
        "modal_title": "Usage example", "modal_close": "Close",
    },
}


def _body() -> str:
    return r"""
<section class="hero" style="padding:64px 0 30px"><div class="container">
  <h1 style="font-size:38px" data-i18n="models_title"></h1>
  <p data-i18n="models_sub"></p>
</div></section>

<section style="padding:0 0 64px"><div class="container">
  <div class="card" style="padding:0">
    <div style="display:flex;gap:12px;padding:16px 18px;border-bottom:1px solid var(--border);flex-wrap:wrap;align-items:center">
      <div class="search" style="flex:1;min-width:200px"><input class="input" id="mSearch" oninput="renderModels()" data-i18n-ph="search_ph"/></div>
      <select class="input" id="mSort" onchange="renderModels()" style="width:auto">
        <option value="name" data-i18n="sort_name"></option>
        <option value="plow" data-i18n="sort_price_low"></option>
        <option value="phigh" data-i18n="sort_price_high"></option>
      </select>
      <label class="muted" style="font-size:13px;display:flex;align-items:center;gap:6px;cursor:pointer">
        <input type="checkbox" id="mUsd" onchange="renderModels()"/> <span data-i18n="usd_toggle"></span>
      </label>
      <span class="pill gray" id="mCount">–</span>
    </div>
    <table>
      <thead><tr>
        <th data-i18n="col_model"></th><th data-i18n="col_type"></th>
        <th style="text-align:right" data-i18n="col_in"></th>
        <th style="text-align:right" data-i18n="col_out"></th>
        <th style="width:80px"></th>
      </tr></thead>
      <tbody id="mRows"><tr><td colspan="5"><div class="empty" data-i18n="loading"></div></td></tr></tbody>
    </table>
  </div>
</div></section>

<div id="mModal" class="hidden" style="position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:60">
  <div class="card" style="width:640px;max-width:94vw">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="margin:0" id="mModalTitle"></h3>
      <button class="btn sm ghost" onclick="document.getElementById('mModal').classList.add('hidden')" data-i18n="modal_close"></button>
    </div>
    <div class="code" id="mModalCode" data-base></div>
  </div>
</div>
"""


_JS = """
<script>
let MODELS=[], PRICING={}, RATE={cpu:1000000,cny:7.2};
async function loadModels(){
  try{
    const [m,p]=await Promise.all([
      fetch('/public/models').then(r=>r.json()),
      fetch('/public/pricing').then(r=>r.json()),
    ]);
    MODELS=m.models||[];
    RATE.cpu=p.credits_per_usd||1000000; RATE.cny=p.usd_cny_rate||7.2;
    (p.pricing||[]).forEach(x=>{ if(x.group==='default'||!PRICING[x.model]) PRICING[x.model]=x; });
    renderModels();
  }catch(e){ document.getElementById('mRows').innerHTML='<tr><td colspan="5"><div class="empty">'+Portal.t('empty')+'</div></td></tr>'; }
}
function priceOf(model,which){ const p=PRICING[model]; if(!p)return null; return which==='in'?p.input_price:p.output_price; }
function fmtPrice(perK,usd){ if(perK==null) return '<span class="muted">'+Portal.t('free')+'</span>';
  const perM=perK*1000, usdVal=perM/RATE.cpu;
  const v = usd ? ('$'+usdVal.toFixed(2)) : ('¥'+(usdVal*RATE.cny).toFixed(2));
  return v+' <span class="muted" style="font-size:11px">'+Portal.t('per_m')+'</span>'; }
function typeChip(t){ const map={openai:'OpenAI',claude:'Claude',anthropic:'Claude',gemini:'Gemini',google:'Gemini',deepseek:'DeepSeek',qwen:'Qwen'};
  return '<span class="pill gray">'+(map[t]||t)+'</span>'; }
function renderModels(){
  const q=(document.getElementById('mSearch').value||'').toLowerCase();
  const sort=document.getElementById('mSort').value;
  const usd=document.getElementById('mUsd').checked;
  let list=MODELS.filter(m=>m.model.toLowerCase().includes(q));
  list.sort((a,b)=>{
    if(sort==='name') return a.model.localeCompare(b.model);
    const pa=priceOf(a.model,'out')??1e18, pb=priceOf(b.model,'out')??1e18;
    return sort==='plow'?pa-pb:pb-pa;
  });
  document.getElementById('mCount').textContent=list.length+' '+Portal.t('count');
  const rows=document.getElementById('mRows');
  if(!list.length){ rows.innerHTML='<tr><td colspan="5"><div class="empty">'+Portal.t('empty')+'</div></td></tr>'; return; }
  rows.innerHTML=list.map(m=>`<tr>
    <td><span class="mono" style="font-weight:600">${m.model}</span></td>
    <td>${typeChip(m.type)}</td>
    <td style="text-align:right">${fmtPrice(priceOf(m.model,'in'),usd)}</td>
    <td style="text-align:right">${fmtPrice(priceOf(m.model,'out'),usd)}</td>
    <td style="text-align:right"><button class="btn sm" onclick="showUse('${m.model}')">${Portal.t('use')}</button></td>
  </tr>`).join('');
}
function showUse(model){
  const base=window.__BASE__||location.origin;
  document.getElementById('mModalTitle').textContent=Portal.t('modal_title')+' · '+model;
  document.getElementById('mModalCode').innerHTML=
    'curl '+base+'/v1/chat/completions \\\\\\n'+
    '  -H <span class="s">"Authorization: Bearer sk-your-token"</span> \\\\\\n'+
    '  -H <span class="s">"Content-Type: application/json"</span> \\\\\\n'+
    '  -d <span class="s">\\'{"model":"'+model+'","messages":[{"role":"user","content":"Hello"}]}\\'</span>';
  document.getElementById('mModal').classList.remove('hidden');
}
document.addEventListener('DOMContentLoaded',loadModels);
document.addEventListener('langchange',()=>{ if(MODELS.length)renderModels(); });
</script>
"""


def models_html() -> str:
    return page("模型目录 · llm_api", "models", _body(), merge_i18n(_I18N), extra_js=_JS)
