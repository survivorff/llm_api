"""门户网站共享基座：设计系统 CSS、顶部导航、页脚、i18n 运行时。

各页面（首页/文档/价格/控制台）复用这份基座，保证视觉与交互一致。
零构建：纯内联 HTML/CSS/JS，随后端一起部署。
"""


def base_css() -> str:
    return r"""
:root{
  --bg:#0b0d13; --bg2:#0f1219; --panel:#151925; --panel2:#1b2130; --border:#262d3d;
  --text:#e8eaf0; --muted:#98a1b3; --dim:#6b7488;
  --primary:#6366f1; --primary2:#818cf8; --cyan:#22d3ee; --green:#22c55e; --red:#ef4444; --amber:#f59e0b;
  --radius:14px; --maxw:1160px;
  --grad:linear-gradient(135deg,#6366f1,#22d3ee);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC",sans-serif;
  background:var(--bg);color:var(--text);font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--primary2);text-decoration:none}
a:hover{color:var(--cyan)}
.hidden{display:none!important}
.container{max-width:var(--maxw);margin:0 auto;padding:0 24px}
h1,h2,h3{line-height:1.25;margin:0 0 .5em}
.muted{color:var(--muted)}
.dim{color:var(--dim)}

/* nav */
.nav{position:sticky;top:0;z-index:50;background:rgba(11,13,19,.82);backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border)}
.nav-in{display:flex;align-items:center;justify-content:space-between;height:62px;max-width:var(--maxw);margin:0 auto;padding:0 24px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:17px;color:var(--text)}
.brand .logo{width:30px;height:30px;border-radius:9px;background:var(--grad);display:flex;align-items:center;justify-content:center;font-size:16px}
.nav-links{display:flex;align-items:center;gap:6px}
.nav-links a{color:var(--muted);padding:8px 14px;border-radius:9px;font-weight:500;font-size:14px}
.nav-links a:hover,.nav-links a.active{color:var(--text);background:var(--panel2)}
.nav-right{display:flex;align-items:center;gap:10px}
.langsel{background:var(--panel2);border:1px solid var(--border);color:var(--text);padding:7px 10px;border-radius:9px;font-size:13px;cursor:pointer}
.menu-btn{display:none;background:var(--panel2);border:1px solid var(--border);color:var(--text);border-radius:9px;padding:8px 12px;cursor:pointer}

/* buttons */
.btn{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--border);background:var(--panel2);
  color:var(--text);padding:10px 18px;border-radius:10px;cursor:pointer;font-size:14px;font-weight:500;transition:.15s;white-space:nowrap}
.btn:hover{border-color:var(--primary);background:#232a3b;color:var(--text)}
.btn.primary{background:var(--grad);border:none;color:#fff;font-weight:600}
.btn.primary:hover{filter:brightness(1.08);color:#fff}
.btn.lg{padding:13px 26px;font-size:15px}
.btn.sm{padding:6px 12px;font-size:13px}
.btn.ghost{background:transparent}

/* cards */
.card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:24px}
.grid{display:grid;gap:20px}
.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
.g2{grid-template-columns:repeat(2,1fr)}

/* sections */
.section{padding:72px 0}
.section h2{font-size:30px;text-align:center;margin-bottom:10px}
.section .sub{text-align:center;color:var(--muted);max-width:640px;margin:0 auto 44px;font-size:16px}
.eyebrow{color:var(--primary2);font-weight:600;font-size:13px;letter-spacing:.08em;text-transform:uppercase;text-align:center;margin-bottom:12px}

/* hero */
.hero{position:relative;padding:110px 0 80px;text-align:center;overflow:hidden}
.hero::before{content:"";position:absolute;top:-30%;left:50%;transform:translateX(-50%);
  width:900px;height:600px;background:radial-gradient(ellipse,rgba(99,102,241,.22),transparent 62%);pointer-events:none}
.hero h1{font-size:52px;font-weight:800;letter-spacing:-.02em;margin-bottom:20px;position:relative}
.hero h1 .grad{background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero p{font-size:19px;color:var(--muted);max-width:660px;margin:0 auto 34px;position:relative}
.hero-cta{display:flex;gap:14px;justify-content:center;position:relative;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;gap:8px;background:var(--panel2);border:1px solid var(--border);
  color:var(--muted);padding:7px 15px;border-radius:999px;font-size:13px;margin-bottom:26px;position:relative}
.badge .dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}

/* feature card */
.feat{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:26px;transition:.18s}
.feat:hover{border-color:var(--primary);transform:translateY(-3px)}
.feat .ic{width:44px;height:44px;border-radius:11px;background:var(--panel2);display:flex;align-items:center;justify-content:center;font-size:22px;margin-bottom:16px}
.feat h3{font-size:17px;margin-bottom:8px}
.feat p{color:var(--muted);font-size:14px;margin:0}

/* code */
.code{background:#0a0c11;border:1px solid var(--border);border-radius:12px;padding:18px 20px;overflow-x:auto;
  font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;line-height:1.7;color:#c8d0e0}
.code .k{color:#c792ea}.code .s{color:#89dceb}.code .c{color:#6b7488}.code .f{color:#82aaff}

/* table */
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:14px 16px;border-bottom:1px solid var(--border);font-size:14px}
th{color:var(--muted);font-weight:600;font-size:13px;background:var(--bg2)}
tbody tr:hover{background:var(--panel2)}

/* footer */
.footer{border-top:1px solid var(--border);padding:44px 0 30px;margin-top:40px;color:var(--muted)}
.footer-in{display:flex;justify-content:space-between;gap:30px;flex-wrap:wrap}
.footer h4{color:var(--text);font-size:14px;margin-bottom:12px}
.footer a{display:block;color:var(--muted);font-size:14px;margin-bottom:8px}
.footer a:hover{color:var(--text)}
.footer .cols{display:flex;gap:60px;flex-wrap:wrap}
.footer .copy{margin-top:26px;padding-top:20px;border-top:1px solid var(--border);font-size:13px;color:var(--dim)}

/* misc */
.pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;background:var(--panel2);border:1px solid var(--border);color:var(--muted)}
.mono{font-family:ui-monospace,Menlo,monospace}
.msg{padding:11px 15px;border-radius:10px;margin:10px 0;font-size:14px}
.msg.err{background:#3a1620;color:#fda4af;border:1px solid #4c2230}
.msg.ok{background:#12301e;color:#86efac;border:1px solid #1d4a30}

@media(max-width:820px){
  .nav-links{display:none;position:absolute;top:62px;left:0;right:0;flex-direction:column;background:var(--bg2);
    border-bottom:1px solid var(--border);padding:10px;gap:4px}
  .nav-links.open{display:flex}
  .nav-links a{padding:11px 14px}
  .menu-btn{display:block}
  .g3,.g4,.g2{grid-template-columns:1fr}
  .hero h1{font-size:36px}.hero p{font-size:17px}
  .section{padding:52px 0}.section h2{font-size:25px}
}
"""


def nav_html(active: str = "") -> str:
    """顶部导航。active 取值：home/docs/pricing。"""
    def cls(name):
        return ' class="active"' if active == name else ""
    return f"""
<nav class="nav">
  <div class="nav-in">
    <a href="/" class="brand"><span class="logo">⚡</span><span data-i18n="brand">llm_api</span></a>
    <div class="nav-links" id="navLinks">
      <a href="/"{cls('home')} data-i18n="nav_home">首页</a>
      <a href="/docs"{cls('docs')} data-i18n="nav_docs">文档</a>
      <a href="/pricing"{cls('pricing')} data-i18n="nav_pricing">价格</a>
    </div>
    <div class="nav-right">
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
    """i18n 运行时 + 语言切换 + 动态站点域名注入。dict_json 为各页面合并后的词典 JSON。"""
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


# 跨页面共用词典（导航、页脚、品牌）。各页面再 merge 自己的键。
SHARED_I18N = {
    "zh": {
        "brand": "llm_api", "nav_home": "首页", "nav_docs": "文档", "nav_pricing": "价格",
        "nav_console": "控制台",
        "footer_tag": "OpenAI 兼容的多模型 API 网关，一个 key 调用主流大模型。",
        "footer_product": "产品", "footer_dev": "开发者", "footer_api": "API 参考",
        "footer_status": "服务状态", "footer_copy": "© 2026 llm_api · 基于 MIT 许可开源",
    },
    "en": {
        "brand": "llm_api", "nav_home": "Home", "nav_docs": "Docs", "nav_pricing": "Pricing",
        "nav_console": "Console",
        "footer_tag": "An OpenAI-compatible multi-model API gateway. One key for all major LLMs.",
        "footer_product": "Product", "footer_dev": "Developers", "footer_api": "API Reference",
        "footer_status": "Status", "footer_copy": "© 2026 llm_api · Open source under MIT",
    },
}


def merge_i18n(*dicts) -> str:
    """合并多个 {lang:{k:v}} 词典为 JSON 字符串。"""
    import json
    out: dict = {}
    for d in (SHARED_I18N, *dicts):
        for lang, kv in d.items():
            out.setdefault(lang, {}).update(kv)
    return json.dumps(out, ensure_ascii=False)


def page(title: str, active: str, body: str, i18n_json: str, extra_head: str = "",
         extra_js: str = "") -> str:
    """组装完整 HTML 页面。"""
    return f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<style>{base_css()}</style>
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
