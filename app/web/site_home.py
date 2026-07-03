"""门户首页（landing）：品牌介绍 + 特性 + 快速上手引导 + CTA。"""
from .shared import merge_i18n, page

_I18N = {
    "zh": {
        "badge": "服务运行中 · OpenAI 兼容",
        "hero_h": "一个 API，接入<span class=\"grad\">所有大模型</span>",
        "hero_p": "统一 OpenAI 兼容端点，聚合 DeepSeek、Claude、Gemini、GPT 等主流模型。按量计费、多渠道自动故障转移、开箱即用。",
        "cta_start": "免费开始", "cta_docs": "查看文档",
        "trust": "兼容你已在用的一切工具",
        "feat_eyebrow": "核心能力", "feat_h": "为生产而生的网关",
        "feat_sub": "不只是转发。计费、路由、限流、可观测，运营一个 AI 服务需要的都在这。",
        "f1_h": "OpenAI 兼容", "f1_p": "无缝替换 base_url 即可。Chat、流式、embeddings、images 全支持，现有代码零改动。",
        "f2_h": "多模型聚合", "f2_p": "DeepSeek、Claude、Gemini、GPT 一个 key 全调用。协议自动互转，模型名智能路由。",
        "f3_h": "按量计费", "f3_p": "预扣式精确结算，按 token 实时扣费。余额、账单、用量全透明可对账。",
        "f4_h": "故障转移", "f4_p": "多渠道加权路由，上游异常自动熔断切换。同渠道多 key 轮询，稳定不中断。",
        "f5_h": "多租户令牌", "f5_p": "配额、有效期、RPM 限速、模型白名单，逐令牌精细管控。适合团队与转售。",
        "f6_h": "可观测运营", "f6_p": "Prometheus 指标、审计日志、渠道健康巡检。设置热更新，无需重启。",
        "start_eyebrow": "三步上手", "start_h": "五分钟接入",
        "s1_h": "注册领取 Key", "s1_p": "邮箱或 GitHub/Google 一键登录，在控制台自助创建 API 令牌。",
        "s2_h": "配置 base_url", "s2_p": "把客户端的 API 地址指向网关，密钥填你的令牌即可。",
        "s3_h": "开始调用", "s3_p": "用熟悉的 OpenAI SDK 直接调用，支持流式与非流式。",
        "code_title": "cURL 示例",
        "cta2_h": "准备好了吗？", "cta2_p": "免费注册，立即获取你的 API 密钥。",
        "cta2_btn": "进入控制台",
    },
    "en": {
        "badge": "Operational · OpenAI-compatible",
        "hero_h": "One API for <span class=\"grad\">every LLM</span>",
        "hero_p": "A unified OpenAI-compatible endpoint aggregating DeepSeek, Claude, Gemini, GPT and more. Usage-based billing, multi-channel failover, ready out of the box.",
        "cta_start": "Start free", "cta_docs": "Read the docs",
        "trust": "Works with the tools you already use",
        "feat_eyebrow": "Core features", "feat_h": "A gateway built for production",
        "feat_sub": "More than a proxy. Billing, routing, rate limiting and observability — everything you need to run an AI service.",
        "f1_h": "OpenAI-compatible", "f1_p": "Just swap the base_url. Chat, streaming, embeddings and images all supported. Zero code changes.",
        "f2_h": "Multi-model", "f2_p": "DeepSeek, Claude, Gemini, GPT with one key. Automatic protocol translation and smart model routing.",
        "f3_h": "Usage billing", "f3_p": "Precise pre-authorized settlement, billed per token in real time. Transparent balance, invoices and usage.",
        "f4_h": "Failover", "f4_p": "Weighted multi-channel routing with automatic circuit breaking. Multi-key rotation keeps you online.",
        "f5_h": "Multi-tenant keys", "f5_p": "Quota, expiry, RPM limits, model allowlists — fine-grained control per token. Great for teams and resale.",
        "f6_h": "Observability", "f6_p": "Prometheus metrics, audit logs, channel health checks. Hot-reload settings, no restart needed.",
        "start_eyebrow": "Three steps", "start_h": "Integrate in 5 minutes",
        "s1_h": "Sign up for a key", "s1_p": "Log in with email or GitHub/Google, then create an API token in the console.",
        "s2_h": "Set the base_url", "s2_p": "Point your client's API base to the gateway and use your token as the key.",
        "s3_h": "Start calling", "s3_p": "Use the OpenAI SDK you already know. Streaming and non-streaming supported.",
        "code_title": "cURL example",
        "cta2_h": "Ready to go?", "cta2_p": "Sign up free and get your API key instantly.",
        "cta2_btn": "Open console",
    },
}


def _body() -> str:
    return r"""
<section class="hero"><div class="container">
  <span class="badge"><span class="dot"></span><span data-i18n="badge"></span></span>
  <h1 data-i18n="hero_h"></h1>
  <p data-i18n="hero_p"></p>
  <div class="hero-cta">
    <a href="/portal" class="btn primary lg" data-i18n="cta_start"></a>
    <a href="/docs" class="btn lg" data-i18n="cta_docs"></a>
  </div>
</div></section>

<section class="section" style="padding-top:20px"><div class="container">
  <div class="grid g4" style="gap:14px">
    <div class="feat" style="padding:18px 20px"><div style="font-size:15px;font-weight:600">DeepSeek</div><div class="muted" style="font-size:13px">deepseek-chat / reasoner</div></div>
    <div class="feat" style="padding:18px 20px"><div style="font-size:15px;font-weight:600">Claude</div><div class="muted" style="font-size:13px">claude-3.5 / sonnet</div></div>
    <div class="feat" style="padding:18px 20px"><div style="font-size:15px;font-weight:600">Gemini</div><div class="muted" style="font-size:13px">gemini-1.5 / 2.0</div></div>
    <div class="feat" style="padding:18px 20px"><div style="font-size:15px;font-weight:600">OpenAI</div><div class="muted" style="font-size:13px">gpt-4o / o-series</div></div>
  </div>
</div></section>

<section class="section"><div class="container">
  <div class="eyebrow" data-i18n="feat_eyebrow"></div>
  <h2 data-i18n="feat_h"></h2>
  <p class="sub" data-i18n="feat_sub"></p>
  <div class="grid g3">
    <div class="feat"><div class="ic">🔌</div><h3 data-i18n="f1_h"></h3><p data-i18n="f1_p"></p></div>
    <div class="feat"><div class="ic">🧩</div><h3 data-i18n="f2_h"></h3><p data-i18n="f2_p"></p></div>
    <div class="feat"><div class="ic">💳</div><h3 data-i18n="f3_h"></h3><p data-i18n="f3_p"></p></div>
    <div class="feat"><div class="ic">🔀</div><h3 data-i18n="f4_h"></h3><p data-i18n="f4_p"></p></div>
    <div class="feat"><div class="ic">🎟️</div><h3 data-i18n="f5_h"></h3><p data-i18n="f5_p"></p></div>
    <div class="feat"><div class="ic">📊</div><h3 data-i18n="f6_h"></h3><p data-i18n="f6_p"></p></div>
  </div>
</div></section>

<section class="section" style="background:var(--bg2)"><div class="container">
  <div class="eyebrow" data-i18n="start_eyebrow"></div>
  <h2 data-i18n="start_h"></h2>
  <div class="grid g3" style="margin-top:40px">
    <div class="feat"><div class="ic">1</div><h3 data-i18n="s1_h"></h3><p data-i18n="s1_p"></p></div>
    <div class="feat"><div class="ic">2</div><h3 data-i18n="s2_h"></h3><p data-i18n="s2_p"></p></div>
    <div class="feat"><div class="ic">3</div><h3 data-i18n="s3_h"></h3><p data-i18n="s3_p"></p></div>
  </div>
  <div class="card" style="margin-top:30px;max-width:760px;margin-left:auto;margin-right:auto">
    <div class="muted" style="font-size:13px;margin-bottom:12px" data-i18n="code_title"></div>
    <div class="code" data-base><span class="c"># chat completions</span>
curl __BASE__/v1/chat/completions \
  -H <span class="s">"Authorization: Bearer sk-your-token"</span> \
  -H <span class="s">"Content-Type: application/json"</span> \
  -d <span class="s">'{"model":"deepseek-chat","messages":[{"role":"user","content":"Hello"}]}'</span></div>
  </div>
</div></section>

<section class="section"><div class="container">
  <div class="card" style="text-align:center;background:var(--grad);border:none;padding:56px 24px">
    <h2 style="color:#fff" data-i18n="cta2_h"></h2>
    <p style="color:rgba(255,255,255,.9);font-size:17px;margin:0 auto 26px;max-width:480px" data-i18n="cta2_p"></p>
    <a href="/portal" class="btn lg" style="background:#fff;color:#4338ca;font-weight:700" data-i18n="cta2_btn"></a>
  </div>
</div></section>
"""


def home_html() -> str:
    return page("llm_api · 多模型 API 网关", "home", _body(), merge_i18n(_I18N))
