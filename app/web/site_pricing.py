"""套餐价格页：实时模型价目表（拉 /public/pricing）+ 计费说明 + 充值方式。"""
from .shared import merge_i18n, page

_I18N = {
    "zh": {
        "pricing_title": "套餐价格", "pricing_sub": "按量计费，用多少付多少。无月费、无最低消费。",
        "how_h": "计费如何运作", "how_sub": "透明、可预测、可对账。",
        "how1_h": "按 Token 计费", "how1_p": "每次调用按输入/输出 token 精确计费，价格随模型不同。",
        "how2_h": "预扣式结算", "how2_p": "请求前冻结预估费用，完成后按实际用量结算并退还差额，绝不超扣。",
        "how3_h": "余额充值", "how3_p": "支持兑换码与加密货币（USDT）充值，余额与账单实时可查。",
        "table_h": "模型价目表",
        "col_model": "模型", "col_type": "类型", "col_in": "输入价", "col_out": "输出价", "col_unit": "单位",
        "unit": "/ 百万 tokens",
        "loading": "加载中…", "empty": "管理员尚未配置公开价目。请登录控制台查看可用模型。",
        "note": "价格以人民币计，按实时汇率由内部 credits 结算。实际以调用时价目为准。",
        "cta_h": "现在就开始", "cta_p": "注册即送体验额度，无需绑卡。", "cta_btn": "免费注册",
        "usd_toggle": "按美元显示",
    },
    "en": {
        "pricing_title": "Pricing", "pricing_sub": "Pay as you go. No monthly fees, no minimums.",
        "how_h": "How billing works", "how_sub": "Transparent, predictable, auditable.",
        "how1_h": "Per-token", "how1_p": "Each call is billed by input/output tokens, priced per model.",
        "how2_h": "Pre-authorized", "how2_p": "An estimate is frozen before the request, then settled by actual usage with the remainder refunded — never overcharged.",
        "how3_h": "Prepaid balance", "how3_p": "Top up via redemption codes or crypto (USDT). Balance and invoices in real time.",
        "table_h": "Model price list",
        "col_model": "Model", "col_type": "Type", "col_in": "Input", "col_out": "Output", "col_unit": "Unit",
        "unit": "/ 1M tokens",
        "loading": "Loading…", "empty": "No public pricing configured yet. Sign in to the console to see available models.",
        "note": "Prices settle from internal credits at the live exchange rate. Actual price at call time applies.",
        "cta_h": "Get started now", "cta_p": "Free trial credits on signup. No card required.", "cta_btn": "Sign up free",
        "usd_toggle": "Show in USD",
    },
}


def _body() -> str:
    return r"""
<section class="hero" style="padding:80px 0 40px"><div class="container">
  <h1 style="font-size:42px" data-i18n="pricing_title"></h1>
  <p data-i18n="pricing_sub"></p>
</div></section>

<section class="section" style="padding-top:20px"><div class="container">
  <div class="grid g3">
    <div class="feat"><div class="ic">🎯</div><h3 data-i18n="how1_h"></h3><p data-i18n="how1_p"></p></div>
    <div class="feat"><div class="ic">🔒</div><h3 data-i18n="how2_h"></h3><p data-i18n="how2_p"></p></div>
    <div class="feat"><div class="ic">💰</div><h3 data-i18n="how3_h"></h3><p data-i18n="how3_p"></p></div>
  </div>
</div></section>

<section class="section" style="padding-top:0"><div class="container">
  <div class="card">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
      <h2 style="text-align:left;font-size:22px;margin:0" data-i18n="table_h"></h2>
      <label class="muted" style="font-size:13px;display:flex;align-items:center;gap:8px;cursor:pointer">
        <input type="checkbox" id="usdToggle" onchange="renderPricing()"/> <span data-i18n="usd_toggle"></span>
      </label>
    </div>
    <table style="margin-top:16px">
      <thead><tr>
        <th data-i18n="col_model"></th><th data-i18n="col_type"></th>
        <th style="text-align:right" data-i18n="col_in"></th>
        <th style="text-align:right" data-i18n="col_out"></th>
        <th data-i18n="col_unit"></th>
      </tr></thead>
      <tbody id="priceRows"><tr><td colspan="5" class="muted" data-i18n="loading"></td></tr></tbody>
    </table>
    <p class="muted" style="font-size:13px;margin:16px 0 0" data-i18n="note"></p>
  </div>
</div></section>

<section class="section" style="padding-top:0"><div class="container">
  <div class="card" style="text-align:center;background:var(--grad);border:none;padding:48px 24px">
    <h2 style="color:#fff" data-i18n="cta_h"></h2>
    <p style="color:rgba(255,255,255,.9);font-size:16px;margin:0 auto 24px;max-width:440px" data-i18n="cta_p"></p>
    <a href="/portal" class="btn lg" style="background:#fff;color:#4338ca;font-weight:700" data-i18n="cta_btn"></a>
  </div>
</div></section>
"""


_JS = """
<script>
let PRICING=null;
async function loadPricing(){
  try{ PRICING = await fetch('/public/pricing').then(r=>r.json()); }
  catch(e){ PRICING={pricing:[],credits_per_usd:1000000,usd_cny_rate:7.2}; }
  renderPricing();
}
function fmtMoney(perThousandCredits, usd){
  // 入库单价是 credits / 1K tokens。换算到 / 1M tokens。
  const cpu = PRICING.credits_per_usd||1000000;
  const rate = PRICING.usd_cny_rate||7.2;
  const perMillionCredits = perThousandCredits*1000;
  const usdVal = perMillionCredits / cpu;         // USD / 1M tokens
  if(usd){ return '$'+usdVal.toFixed(2); }
  return '¥'+(usdVal*rate).toFixed(2);
}
function renderPricing(){
  if(!PRICING) return;
  const usd = document.getElementById('usdToggle').checked;
  const rows=document.getElementById('priceRows');
  const list=PRICING.pricing||[];
  if(!list.length){ rows.innerHTML='<tr><td colspan="5" class="muted">'+Portal.t('empty')+'</td></tr>'; return; }
  rows.innerHTML=list.map(p=>`<tr>
    <td class="mono">${p.model}</td>
    <td><span class="pill">${p.group||'default'}</span></td>
    <td style="text-align:right">${fmtMoney(p.input_price,usd)}</td>
    <td style="text-align:right">${fmtMoney(p.output_price,usd)}</td>
    <td class="muted">${Portal.t('unit')}</td>
  </tr>`).join('');
}
document.addEventListener('DOMContentLoaded',loadPricing);
document.addEventListener('langchange',renderPricing);
</script>
"""


def pricing_html() -> str:
    return page("套餐价格 · llm_api", "pricing", _body(), merge_i18n(_I18N), extra_js=_JS)
