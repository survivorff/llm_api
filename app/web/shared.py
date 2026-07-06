"""门户网站共享基座：设计系统（明暗双主题）、导航、页脚、i18n 运行时。

v2.5 重设计：借鉴 OpenRouter —— 明暗双主题（默认跟随系统）、克制配色、
数据前置、模型目录。零构建，纯内联 HTML/CSS/JS。
"""


def base_css() -> str:
    return r"""
/* ============ 设计系统 v2.5：明暗双主题 ============ */
:root{
  /* 亮色（默认） */
  --bg:#fafafb; --bg2:#f3f4f7; --panel:#ffffff; --panel2:#f6f7f9; --border:#e5e7ee;
  --text:#16181f; --muted:#5b6472; --dim:#8b94a3;
  --primary:#4f46e5; --primary2:#6366f1; --accent:#0ea5e9;
  --green:#16a34a; --red:#dc2626; --amber:#d97706;
  --radius:12px; --radius-sm:9px; --maxw:1200px;
  --grad:linear-gradient(135deg,#4f46e5,#0ea5e9);
  --shadow:0 1px 3px rgba(16,18,31,.06),0 1px 2px rgba(16,18,31,.04);
  --shadow-md:0 6px 24px rgba(16,18,31,.10);
  --code-bg:#f6f7f9;
}
:root[data-theme="dark"]{
  --bg:#0b0d13; --bg2:#0f1219; --panel:#141824; --panel2:#1b2130; --border:#262d3d;
  --text:#e8eaf0; --muted:#98a1b3; --dim:#6b7488;
  --primary:#6366f1; --primary2:#818cf8; --accent:#22d3ee;
  --green:#22c55e; --red:#ef4444; --amber:#f59e0b;
  --grad:linear-gradient(135deg,#6366f1,#22d3ee);
  --shadow:0 1px 3px rgba(0,0,0,.4);
  --shadow-md:0 8px 30px rgba(0,0,0,.5);
  --code-bg:#0a0c11;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--text);font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;
  transition:background .2s,color .2s}
a{color:var(--primary);text-decoration:none}
a:hover{color:var(--accent)}
.hidden{display:none!important}
.container{max-width:var(--maxw);margin:0 auto;padding:0 24px}
h1,h2,h3,h4{line-height:1.25;margin:0 0 .5em;font-weight:700}
.muted{color:var(--muted)}
.dim{color:var(--dim)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}

/* ---- 顶部导航 ---- */
.nav{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg) 85%,transparent);
  backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
.nav-in{display:flex;align-items:center;justify-content:space-between;height:60px;max-width:var(--maxw);margin:0 auto;padding:0 24px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;color:var(--text)}
.brand .logo{width:28px;height:28px;border-radius:8px;background:var(--grad);display:flex;align-items:center;justify-content:center;font-size:15px;color:#fff}
.nav-links{display:flex;align-items:center;gap:2px}
.nav-links a{color:var(--muted);padding:7px 13px;border-radius:8px;font-weight:500;font-size:14px}
.nav-links a:hover,.nav-links a.active{color:var(--text);background:var(--panel2)}
.nav-right{display:flex;align-items:center;gap:8px}
.icon-toggle{width:34px;height:34px;border-radius:8px;border:1px solid var(--border);background:var(--panel);
  color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:15px}
.icon-toggle:hover{color:var(--text);border-color:var(--primary)}
.langsel{background:var(--panel);border:1px solid var(--border);color:var(--text);padding:7px 9px;border-radius:8px;font-size:13px;cursor:pointer}
.menu-btn{display:none;background:var(--panel);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:7px 11px;cursor:pointer}

/* ---- 按钮 ---- */
.btn{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--border);background:var(--panel);
  color:var(--text);padding:9px 16px;border-radius:9px;cursor:pointer;font-size:14px;font-weight:500;
  transition:.15s;white-space:nowrap;box-shadow:var(--shadow)}
.btn:hover{border-color:var(--primary);color:var(--text)}
.btn.primary{background:var(--primary);border-color:var(--primary);color:#fff;font-weight:600}
.btn.primary:hover{filter:brightness(1.06);color:#fff}
.btn.grad{background:var(--grad);border:none;color:#fff;font-weight:600}
.btn.grad:hover{filter:brightness(1.06);color:#fff}
.btn.lg{padding:12px 24px;font-size:15px}
.btn.sm{padding:6px 11px;font-size:13px;box-shadow:none}
.btn.ghost{background:transparent;box-shadow:none}
.btn.danger{color:var(--red);border-color:color-mix(in srgb,var(--red) 40%,var(--border))}
.btn.danger:hover{background:color-mix(in srgb,var(--red) 12%,transparent);border-color:var(--red)}

/* ---- 卡片/栅格 ---- */
.card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:22px;box-shadow:var(--shadow)}
.grid{display:grid;gap:18px}
.g2{grid-template-columns:repeat(2,1fr)}
.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}

/* ---- 章节 ---- */
.section{padding:64px 0}
.section h2{font-size:28px;text-align:center;margin-bottom:10px}
.section .sub{text-align:center;color:var(--muted);max-width:620px;margin:0 auto 40px;font-size:16px}
.eyebrow{color:var(--primary);font-weight:600;font-size:12px;letter-spacing:.09em;text-transform:uppercase;text-align:center;margin-bottom:10px}

/* ---- Hero ---- */
.hero{position:relative;padding:96px 0 64px;text-align:center;overflow:hidden}
.hero::before{content:"";position:absolute;top:-40%;left:50%;transform:translateX(-50%);
  width:1000px;height:640px;background:radial-gradient(ellipse,color-mix(in srgb,var(--primary) 16%,transparent),transparent 60%);pointer-events:none}
.hero h1{font-size:48px;font-weight:800;letter-spacing:-.02em;margin-bottom:18px;position:relative}
.hero h1 .grad{background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero p{font-size:18px;color:var(--muted);max-width:640px;margin:0 auto 30px;position:relative}
.hero-cta{display:flex;gap:12px;justify-content:center;position:relative;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;gap:8px;background:var(--panel);border:1px solid var(--border);
  color:var(--muted);padding:6px 14px;border-radius:999px;font-size:13px;margin-bottom:24px;position:relative;box-shadow:var(--shadow)}
.badge .dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}

/* ---- 统计条（数据前置）---- */
.statbar{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;position:relative}
.statbar .s{text-align:center;padding:8px}
.statbar .n{font-size:34px;font-weight:800;letter-spacing:-.02em;background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.statbar .l{color:var(--muted);font-size:13px;margin-top:4px}

/* ---- 特性卡 ---- */
.feat{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:24px;transition:.18s;box-shadow:var(--shadow)}
.feat:hover{border-color:var(--primary);box-shadow:var(--shadow-md)}
.feat .ic{width:42px;height:42px;border-radius:10px;background:color-mix(in srgb,var(--primary) 12%,transparent);
  display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:14px}
.feat h3{font-size:16px;margin-bottom:7px}
.feat p{color:var(--muted);font-size:14px;margin:0}

/* ---- logo 墙 ---- */
.logowall{display:flex;flex-wrap:wrap;gap:10px;justify-content:center}
.logowall .chip{display:inline-flex;align-items:center;gap:7px;background:var(--panel);border:1px solid var(--border);
  border-radius:999px;padding:7px 15px;font-size:13px;font-weight:500;color:var(--muted);box-shadow:var(--shadow)}

/* ---- 代码 ---- */
.code{background:var(--code-bg);border:1px solid var(--border);border-radius:10px;padding:16px 18px;overflow-x:auto;
  font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;line-height:1.7;color:var(--text)}
.code .k{color:#a855f7}.code .s{color:#0891b2}.code .c{color:var(--dim)}.code .f{color:#2563eb}
:root[data-theme="dark"] .code .k{color:#c792ea}
:root[data-theme="dark"] .code .s{color:#89dceb}
:root[data-theme="dark"] .code .f{color:#82aaff}

/* ---- 表格 ---- */
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:13px 16px;border-bottom:1px solid var(--border);font-size:14px}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em;background:var(--bg2)}
tbody tr:hover{background:var(--panel2)}

/* ---- 搜索/输入 ---- */
.input{width:100%;padding:10px 14px;background:var(--panel);border:1px solid var(--border);border-radius:9px;
  color:var(--text);font-size:14px}
.input:focus{outline:none;border-color:var(--primary)}
.search{position:relative}
.search input{padding-left:38px}
.search::before{content:"🔍";position:absolute;left:13px;top:50%;transform:translateY(-50%);font-size:14px;opacity:.6}

/* ---- 杂项 ---- */
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;
  background:color-mix(in srgb,var(--primary) 12%,transparent);color:var(--primary)}
.pill.gray{background:var(--panel2);color:var(--muted);border:1px solid var(--border)}
.msg{padding:11px 15px;border-radius:10px;margin:10px 0;font-size:14px}
.msg.err{background:color-mix(in srgb,var(--red) 12%,transparent);color:var(--red);border:1px solid color-mix(in srgb,var(--red) 30%,transparent)}
.msg.ok{background:color-mix(in srgb,var(--green) 12%,transparent);color:var(--green);border:1px solid color-mix(in srgb,var(--green) 30%,transparent)}
.empty{padding:30px;text-align:center;color:var(--muted)}

/* ---- 页脚 ---- */
.footer{border-top:1px solid var(--border);padding:44px 0 30px;margin-top:48px;color:var(--muted)}
.footer-in{display:flex;justify-content:space-between;gap:30px;flex-wrap:wrap}
.footer h4{color:var(--text);font-size:14px;margin-bottom:12px}
.footer a{display:block;color:var(--muted);font-size:14px;margin-bottom:8px}
.footer a:hover{color:var(--text)}
.footer .cols{display:flex;gap:60px;flex-wrap:wrap}
.footer .copy{margin-top:26px;padding-top:20px;border-top:1px solid var(--border);font-size:13px;color:var(--dim)}

@media(max-width:860px){
  .nav-links{display:none;position:absolute;top:60px;left:0;right:0;flex-direction:column;background:var(--bg);
    border-bottom:1px solid var(--border);padding:10px;gap:2px}
  .nav-links.open{display:flex}
  .menu-btn{display:block}
  .g2,.g3,.g4{grid-template-columns:1fr}
  .statbar{grid-template-columns:repeat(2,1fr)}
  .hero h1{font-size:34px}.hero p{font-size:16px}
  .section{padding:48px 0}.section h2{font-size:23px}
}
"""


def theme_js() -> str:
    """主题切换：默认跟随系统，localStorage 记忆，切换按钮。"""
    return """
<script>
(function(){
  const KEY='theme';
  function sysDark(){return window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;}
  function resolve(){const s=localStorage.getItem(KEY); if(s==='dark'||s==='light')return s; return sysDark()?'dark':'light';}
  function applyTheme(t){document.documentElement.setAttribute('data-theme',t);
    const b=document.getElementById('themeBtn'); if(b)b.textContent = t==='dark'?'☀':'🌙';}
  window.__toggleTheme=function(){const cur=document.documentElement.getAttribute('data-theme')||resolve();
    const next=cur==='dark'?'light':'dark'; localStorage.setItem(KEY,next); applyTheme(next);};
  // 立即应用，避免闪烁
  applyTheme(resolve());
  document.addEventListener('DOMContentLoaded',()=>applyTheme(resolve()));
  if(window.matchMedia){window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{
    if(!localStorage.getItem(KEY))applyTheme(resolve());});}
})();
</script>
"""


def nav_html(active: str = "") -> str:
    def cls(name):
        return ' class="active"' if active == name else ""
    return f"""
<nav class="nav">
  <div class="nav-in">
    <a href="/" class="brand"><span class="logo">⚡</span><span data-i18n="brand">llm_api</span></a>
    <div class="nav-links" id="navLinks">
      <a href="/"{cls('home')} data-i18n="nav_home">首页</a>
      <a href="/models"{cls('models')} data-i18n="nav_models">模型</a>
      <a href="/pricing"{cls('pricing')} data-i18n="nav_pricing">价格</a>
      <a href="/docs"{cls('docs')} data-i18n="nav_docs">文档</a>
    </div>
    <div class="nav-right">
      <button class="icon-toggle" id="themeBtn" onclick="__toggleTheme()" title="切换主题">🌙</button>
      <select class="langsel" id="langSel" onchange="Portal.setLang(this.value)">
        <option value="zh">中文</option><option value="en">EN</option>
      </select>
      <a href="/portal" class="btn sm primary" data-i18n="nav_console">控制台</a>
      <button class="menu-btn" onclick="document.getElementById('navLinks').classList.toggle('open')">☰</button>
    </div>
  </div>
</nav>
"""


def footer_html() -> str:
    return """
<footer class="footer"><div class="container footer-in">
  <div>
    <div class="brand" style="margin-bottom:10px"><span class="logo">⚡</span><span data-i18n="brand">llm_api</span></div>
    <div class="muted" style="max-width:280px;font-size:14px" data-i18n="footer_tag">OpenAI 兼容的多模型 API 网关，一个 key 调用主流大模型。</div>
  </div>
  <div class="cols">
    <div>
      <h4 data-i18n="footer_product">产品</h4>
      <a href="/" data-i18n="nav_home">首页</a>
      <a href="/models" data-i18n="nav_models">模型</a>
      <a href="/pricing" data-i18n="nav_pricing">价格</a>
      <a href="/portal" data-i18n="nav_console">控制台</a>
    </div>
    <div>
      <h4 data-i18n="footer_dev">开发者</h4>
      <a href="/docs" data-i18n="nav_docs">文档</a>
      <a href="/docs#api" data-i18n="footer_api">API 参考</a>
      <a href="/healthz" data-i18n="footer_status">服务状态</a>
    </div>
  </div>
</div>
<div class="container copy"><span data-i18n="footer_copy">© 2026 llm_api · 基于 MIT 许可开源</span></div>
</footer>
"""


def i18n_js(dict_json: str) -> str:
    return """
<script>
window.Portal = (function(){
  const DICT = %s;
  let lang = localStorage.getItem('lang') || (navigator.language||'zh').slice(0,2);
  if(!DICT[lang]) lang = 'zh';
  function t(k){ return (DICT[lang]&&DICT[lang][k]) || (DICT.zh&&DICT.zh[k]) || k; }
  function apply(){
    document.documentElement.lang = lang;
    const sel=document.getElementById('langSel'); if(sel) sel.value=lang;
    document.querySelectorAll('[data-i18n]').forEach(el=>{ el.innerHTML = t(el.getAttribute('data-i18n')); });
    document.querySelectorAll('[data-i18n-ph]').forEach(el=>{ el.placeholder = t(el.getAttribute('data-i18n-ph')); });
  }
  function setLang(l){ lang=l; localStorage.setItem('lang',l); apply(); document.dispatchEvent(new CustomEvent('langchange',{detail:l})); }
  async function injectBase(){
    let base='';
    try{ const s=await fetch('/public/settings').then(r=>r.json()); base=(s&&s.base_url)||''; }catch(e){}
    if(!base) base=location.origin;
    const host=base.replace(/^https?:\\/\\//,'');
    document.querySelectorAll('[data-base]').forEach(el=>{
      el.innerHTML = el.innerHTML.split('__BASE__').join(base).split('__HOST__').join(host);
    });
    window.__BASE__=base;
    document.dispatchEvent(new CustomEvent('baseready',{detail:base}));
  }
  document.addEventListener('DOMContentLoaded', function(){ apply(); injectBase(); });
  return { t, setLang, apply, get lang(){return lang;}, get base(){return window.__BASE__||location.origin;} };
})();
</script>
""" % dict_json


SHARED_I18N = {
    "zh": {
        "brand": "llm_api", "nav_home": "首页", "nav_models": "模型", "nav_docs": "文档",
        "nav_pricing": "价格", "nav_console": "控制台",
        "footer_tag": "OpenAI 兼容的多模型 API 网关，一个 key 调用主流大模型。",
        "footer_product": "产品", "footer_dev": "开发者", "footer_api": "API 参考",
        "footer_status": "服务状态", "footer_copy": "© 2026 llm_api · 基于 MIT 许可开源",
    },
    "en": {
        "brand": "llm_api", "nav_home": "Home", "nav_models": "Models", "nav_docs": "Docs",
        "nav_pricing": "Pricing", "nav_console": "Console",
        "footer_tag": "An OpenAI-compatible multi-model API gateway. One key for all major LLMs.",
        "footer_product": "Product", "footer_dev": "Developers", "footer_api": "API Reference",
        "footer_status": "Status", "footer_copy": "© 2026 llm_api · Open source under MIT",
    },
}


def merge_i18n(*dicts) -> str:
    import json
    out: dict = {}
    for d in (SHARED_I18N, *dicts):
        for lang, kv in d.items():
            out.setdefault(lang, {}).update(kv)
    return json.dumps(out, ensure_ascii=False)


def page(title: str, active: str, body: str, i18n_json: str, extra_head: str = "",
         extra_js: str = "") -> str:
    return f"""<!doctype html>
<html lang="zh" data-theme="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<style>{base_css()}</style>
{theme_js()}
{extra_head}
</head>
<body>
{nav_html(active)}
{body}
{footer_html()}
{i18n_js(i18n_json)}
{extra_js}
</body>
</html>"""
