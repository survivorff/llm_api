"""文档中心：快速接入、API 参考、客户端配置、FAQ。侧边栏 + 锚点导航。"""
from .shared import merge_i18n, page

_I18N = {
    "zh": {
        "docs_title": "文档中心", "docs_sub": "五分钟接入，像用 OpenAI 一样调用所有模型。",
        "toc_start": "快速开始", "toc_auth": "认证", "toc_api": "API 参考",
        "toc_clients": "客户端配置", "toc_stream": "流式输出", "toc_errors": "错误码", "toc_faq": "常见问题",
        "h_start": "快速开始", "p_start": "网关完全兼容 OpenAI 接口。三步即可接入：",
        "step1": "在<a href='/portal'>控制台</a>注册并创建 API 令牌（sk- 开头）。",
        "step2": "把客户端的 API 基础地址（base_url）改为下面的网关地址。",
        "step3": "用你的令牌作为 API Key 发起请求，模型名填想调用的模型。",
        "base_label": "网关地址（Base URL）",
        "h_auth": "认证", "p_auth": "所有 /v1 请求通过 Bearer Token 认证，令牌在控制台创建：",
        "h_api": "API 参考", "p_api": "以下端点与 OpenAI 官方语义一致。",
        "ep_chat": "对话补全（支持流式）", "ep_models": "列出可用模型", "ep_embed": "文本向量",
        "ep_img": "图像生成", "ep_msg": "Anthropic 原生消息接口", "ep_me": "查询当前令牌额度/用量",
        "h_clients": "客户端配置", "p_clients": "在常见工具里填写以下三项即可：",
        "cl_field1": "Base URL", "cl_field2": "API Key", "cl_field3": "Model",
        "cl_note": "适用于 Cursor、Cline、Aider、ChatBox、NextChat 等所有 OpenAI 兼容客户端。",
        "sdk_title": "OpenAI Python SDK",
        "h_stream": "流式输出", "p_stream": "设置 stream:true 即可获得 SSE 流式响应，与 OpenAI 一致。",
        "h_errors": "错误码", "p_errors": "网关沿用标准 HTTP 状态码：",
        "err401": "令牌无效、停用或过期", "err402": "余额不足，请充值",
        "err429": "触发限速（RPM）或配额用尽", "err502": "所有上游渠道均不可用",
        "h_faq": "常见问题",
        "faq1_q": "支持哪些模型？", "faq1_a": "取决于管理员配置的渠道，常见有 DeepSeek、Claude、Gemini、GPT 系列。完整清单见<a href='/pricing'>价格页</a>。",
        "faq2_q": "如何计费？", "faq2_a": "按 token 用量实时扣费，采用预扣式结算：请求前冻结预估费用，完成后按实际用量结算并退还差额。",
        "faq3_q": "怎么充值？", "faq3_a": "在控制台充值页支持兑换码与加密货币（USDT）。余额、账单实时可查。",
        "faq4_q": "流式和函数调用支持吗？", "faq4_a": "流式完全支持。函数调用/工具调用取决于上游模型能力，网关透传。",
    },
    "en": {
        "docs_title": "Documentation", "docs_sub": "Integrate in 5 minutes. Call any model like you use OpenAI.",
        "toc_start": "Quickstart", "toc_auth": "Authentication", "toc_api": "API Reference",
        "toc_clients": "Client setup", "toc_stream": "Streaming", "toc_errors": "Error codes", "toc_faq": "FAQ",
        "h_start": "Quickstart", "p_start": "The gateway is fully OpenAI-compatible. Three steps to integrate:",
        "step1": "Sign up and create an API token (starts with sk-) in the <a href='/portal'>console</a>.",
        "step2": "Change your client's API base URL to the gateway URL below.",
        "step3": "Send requests using your token as the API key and the model name you want.",
        "base_label": "Base URL",
        "h_auth": "Authentication", "p_auth": "All /v1 requests use Bearer Token auth. Create tokens in the console:",
        "h_api": "API Reference", "p_api": "These endpoints match OpenAI's semantics.",
        "ep_chat": "Chat completions (streaming supported)", "ep_models": "List available models",
        "ep_embed": "Text embeddings", "ep_img": "Image generation",
        "ep_msg": "Anthropic-native messages", "ep_me": "Query current token quota/usage",
        "h_clients": "Client setup", "p_clients": "Fill in these three fields in common tools:",
        "cl_field1": "Base URL", "cl_field2": "API Key", "cl_field3": "Model",
        "cl_note": "Works with Cursor, Cline, Aider, ChatBox, NextChat and any OpenAI-compatible client.",
        "sdk_title": "OpenAI Python SDK",
        "h_stream": "Streaming", "p_stream": "Set stream:true for an SSE stream, identical to OpenAI.",
        "h_errors": "Error codes", "p_errors": "The gateway uses standard HTTP status codes:",
        "err401": "Invalid, disabled or expired token", "err402": "Insufficient balance, please top up",
        "err429": "Rate limit (RPM) or quota exceeded", "err502": "All upstream channels unavailable",
        "h_faq": "FAQ",
        "faq1_q": "Which models are supported?", "faq1_a": "Depends on channels configured by the admin — commonly DeepSeek, Claude, Gemini and GPT. See the <a href='/pricing'>pricing page</a> for the full list.",
        "faq2_q": "How is billing done?", "faq2_a": "Billed per token in real time with pre-authorized settlement: an estimate is frozen before the request, then settled by actual usage with the difference refunded.",
        "faq3_q": "How do I top up?", "faq3_a": "The console supports redemption codes and crypto (USDT). Balance and invoices are available in real time.",
        "faq4_q": "Streaming and function calling?", "faq4_a": "Streaming is fully supported. Function/tool calling depends on the upstream model; the gateway passes it through.",
    },
}


def _body() -> str:
    return r"""
<div class="container" style="display:grid;grid-template-columns:210px 1fr;gap:40px;padding-top:40px;padding-bottom:40px">
  <aside style="position:sticky;top:82px;align-self:start" id="toc">
    <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin-bottom:12px" data-i18n="docs_title"></div>
    <a href="#start" class="toc-link" data-i18n="toc_start"></a>
    <a href="#auth" class="toc-link" data-i18n="toc_auth"></a>
    <a href="#api" class="toc-link" data-i18n="toc_api"></a>
    <a href="#clients" class="toc-link" data-i18n="toc_clients"></a>
    <a href="#stream" class="toc-link" data-i18n="toc_stream"></a>
    <a href="#errors" class="toc-link" data-i18n="toc_errors"></a>
    <a href="#faq" class="toc-link" data-i18n="toc_faq"></a>
  </aside>

  <main style="min-width:0">
    <h1 style="font-size:34px" data-i18n="docs_title"></h1>
    <p class="muted" style="font-size:17px;margin-bottom:36px" data-i18n="docs_sub"></p>

    <section id="start" class="doc-sec">
      <h2 data-i18n="h_start"></h2>
      <p data-i18n="p_start"></p>
      <ol class="steps">
        <li data-i18n="step1"></li>
        <li data-i18n="step2"></li>
        <li data-i18n="step3"></li>
      </ol>
      <div class="muted" style="font-size:13px;margin:16px 0 6px" data-i18n="base_label"></div>
      <div class="code" id="baseUrlBox">https://llmapi.frankfu.cloud/v1</div>
    </section>

    <section id="auth" class="doc-sec">
      <h2 data-i18n="h_auth"></h2>
      <p data-i18n="p_auth"></p>
      <div class="code">Authorization: Bearer <span class="s">sk-your-token</span></div>
    </section>

    <section id="api" class="doc-sec">
      <h2 data-i18n="h_api"></h2>
      <p data-i18n="p_api"></p>
      <table style="margin-top:14px">
        <thead><tr><th>Endpoint</th><th></th></tr></thead>
        <tbody>
          <tr><td class="mono">POST /v1/chat/completions</td><td class="muted" data-i18n="ep_chat"></td></tr>
          <tr><td class="mono">GET /v1/models</td><td class="muted" data-i18n="ep_models"></td></tr>
          <tr><td class="mono">POST /v1/embeddings</td><td class="muted" data-i18n="ep_embed"></td></tr>
          <tr><td class="mono">POST /v1/images/generations</td><td class="muted" data-i18n="ep_img"></td></tr>
          <tr><td class="mono">POST /v1/messages</td><td class="muted" data-i18n="ep_msg"></td></tr>
          <tr><td class="mono">GET /v1/me</td><td class="muted" data-i18n="ep_me"></td></tr>
        </tbody>
      </table>
    </section>

    <section id="clients" class="doc-sec">
      <h2 data-i18n="h_clients"></h2>
      <p data-i18n="p_clients"></p>
      <table style="margin:14px 0">
        <tbody>
          <tr><td class="mono" style="width:120px" data-i18n="cl_field1"></td><td class="mono">https://llmapi.frankfu.cloud/v1</td></tr>
          <tr><td class="mono" data-i18n="cl_field2"></td><td class="mono">sk-your-token</td></tr>
          <tr><td class="mono" data-i18n="cl_field3"></td><td class="mono">deepseek-chat</td></tr>
        </tbody>
      </table>
      <p class="muted" style="font-size:13px" data-i18n="cl_note"></p>
      <div class="muted" style="font-size:13px;margin:20px 0 8px" data-i18n="sdk_title"></div>
      <div class="code"><span class="k">from</span> openai <span class="k">import</span> OpenAI
client = <span class="f">OpenAI</span>(
    base_url=<span class="s">"https://llmapi.frankfu.cloud/v1"</span>,
    api_key=<span class="s">"sk-your-token"</span>,
)
resp = client.chat.completions.<span class="f">create</span>(
    model=<span class="s">"deepseek-chat"</span>,
    messages=[{<span class="s">"role"</span>:<span class="s">"user"</span>,<span class="s">"content"</span>:<span class="s">"Hello"</span>}],
)
<span class="f">print</span>(resp.choices[<span class="s">0</span>].message.content)</div>
    </section>

    <section id="stream" class="doc-sec">
      <h2 data-i18n="h_stream"></h2>
      <p data-i18n="p_stream"></p>
      <div class="code">curl https://llmapi.frankfu.cloud/v1/chat/completions \
  -H <span class="s">"Authorization: Bearer sk-your-token"</span> \
  -d <span class="s">'{"model":"deepseek-chat","stream":true,"messages":[{"role":"user","content":"hi"}]}'</span></div>
    </section>

    <section id="errors" class="doc-sec">
      <h2 data-i18n="h_errors"></h2>
      <p data-i18n="p_errors"></p>
      <table style="margin-top:14px">
        <tbody>
          <tr><td><span class="pill">401</span></td><td class="muted" data-i18n="err401"></td></tr>
          <tr><td><span class="pill">402</span></td><td class="muted" data-i18n="err402"></td></tr>
          <tr><td><span class="pill">429</span></td><td class="muted" data-i18n="err429"></td></tr>
          <tr><td><span class="pill">502</span></td><td class="muted" data-i18n="err502"></td></tr>
        </tbody>
      </table>
    </section>

    <section id="faq" class="doc-sec">
      <h2 data-i18n="h_faq"></h2>
      <div class="card" style="margin-bottom:12px"><h3 style="font-size:16px" data-i18n="faq1_q"></h3><p class="muted" style="margin:0" data-i18n="faq1_a"></p></div>
      <div class="card" style="margin-bottom:12px"><h3 style="font-size:16px" data-i18n="faq2_q"></h3><p class="muted" style="margin:0" data-i18n="faq2_a"></p></div>
      <div class="card" style="margin-bottom:12px"><h3 style="font-size:16px" data-i18n="faq3_q"></h3><p class="muted" style="margin:0" data-i18n="faq3_a"></p></div>
      <div class="card"><h3 style="font-size:16px" data-i18n="faq4_q"></h3><p class="muted" style="margin:0" data-i18n="faq4_a"></p></div>
    </section>
  </main>
</div>
"""


_HEAD = """
<style>
.toc-link{display:block;color:var(--muted);padding:7px 12px;border-radius:8px;font-size:14px;margin-bottom:2px;border-left:2px solid transparent}
.toc-link:hover,.toc-link.active{color:var(--text);background:var(--panel2);border-left-color:var(--primary)}
.doc-sec{padding:26px 0;border-bottom:1px solid var(--border);scroll-margin-top:80px}
.doc-sec h2{font-size:23px;text-align:left;margin-bottom:12px}
.doc-sec p{color:var(--muted)}
.steps{color:var(--muted);padding-left:20px;line-height:2}
.steps li{margin-bottom:4px}
@media(max-width:820px){.container[style*=grid]{grid-template-columns:1fr!important}#toc{display:none}}
</style>
"""

_JS = """
<script>
// 滚动高亮当前章节
const secs=[...document.querySelectorAll('.doc-sec')];
const links=[...document.querySelectorAll('.toc-link')];
function onScroll(){
  let cur=secs[0]?.id;
  for(const s of secs){ if(window.scrollY>=s.offsetTop-100) cur=s.id; }
  links.forEach(a=>a.classList.toggle('active', a.getAttribute('href')==='#'+cur));
}
window.addEventListener('scroll',onScroll); onScroll();
</script>
"""


def docs_html() -> str:
    return page("文档中心 · llm_api", "docs", _body(), merge_i18n(_I18N),
                extra_head=_HEAD, extra_js=_JS)
