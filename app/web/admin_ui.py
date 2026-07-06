"""后台管理页面（纯前端单文件，调用 /admin/* 接口）。

v2.2：令牌/用户/渠道/定价/用量 + 请求日志/兑换码/订单/系统设置/审计。
"""

ADMIN_HTML = r"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>llm_api · 网关后台</title>
<style>
:root{
  --bg:#fafafb;--bg2:#f3f4f7;--panel:#ffffff;--panel2:#f6f7f9;--border:#e5e7ee;
  --text:#16181f;--muted:#5b6472;--dim:#8b94a3;
  --primary:#4f46e5;--primary2:#6366f1;--accent:#0ea5e9;--green:#16a34a;--red:#dc2626;--amber:#d97706;
  --sidebar:#ffffff;--shadow:0 1px 3px rgba(16,18,31,.06);
}
:root[data-theme="dark"]{
  --bg:#0b0d13;--bg2:#0f1219;--panel:#141824;--panel2:#1b2130;--border:#262d3d;
  --text:#e8eaf0;--muted:#98a1b3;--dim:#6b7488;
  --primary:#6366f1;--primary2:#818cf8;--accent:#22d3ee;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;
  --sidebar:#0f1219;--shadow:0 1px 3px rgba(0,0,0,.4);
}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);font-size:14px}
.hidden{display:none!important}
/* 左侧边栏布局 */
.layout{display:flex;min-height:100vh}
.sidebar{width:216px;flex-shrink:0;background:var(--sidebar);border-right:1px solid var(--border);
  display:flex;flex-direction:column;position:sticky;top:0;height:100vh;overflow-y:auto}
.sidebar .brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;padding:18px 20px;border-bottom:1px solid var(--border)}
.sidebar .logo{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--primary),var(--accent));display:flex;align-items:center;justify-content:center;font-size:15px;color:#fff}
.navm{padding:12px 10px;flex:1}
.navm .item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:9px;cursor:pointer;color:var(--muted);font-size:14px;font-weight:500;margin-bottom:2px}
.navm .item:hover{background:var(--panel2);color:var(--text)}
.navm .item.active{background:color-mix(in srgb,var(--primary) 12%,transparent);color:var(--primary)}
.navm .item .ic{width:18px;text-align:center}
.sidebar .foot{padding:12px 14px;border-top:1px solid var(--border);display:flex;gap:8px;align-items:center}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;border-bottom:1px solid var(--border);background:var(--panel);position:sticky;top:0;z-index:10}
.topbar h2{margin:0;font-size:17px}
.top-actions{display:flex;gap:8px;align-items:center}
.wrap{padding:24px;max-width:1280px;width:100%}
.icon-toggle{width:32px;height:32px;border-radius:8px;border:1px solid var(--border);background:var(--panel);color:var(--muted);cursor:pointer;font-size:14px}
.icon-toggle:hover{color:var(--text);border-color:var(--primary)}
.btn{border:1px solid var(--border);background:var(--panel);color:var(--text);padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;transition:.15s;box-shadow:var(--shadow)}
.btn:hover{border-color:var(--primary)}
.btn.primary{background:var(--primary);border-color:var(--primary);color:#fff;font-weight:600}
.btn.primary:hover{filter:brightness(1.06)}
.btn.ghost{background:transparent;box-shadow:none}
.btn.sm{padding:5px 10px;font-size:12px;box-shadow:none}
.btn.danger{color:var(--red);border-color:color-mix(in srgb,var(--red) 40%,var(--border))}
.btn.danger:hover{background:color-mix(in srgb,var(--red) 10%,transparent)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
.stat{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px 18px;box-shadow:var(--shadow)}
.stat .label{color:var(--muted);font-size:12px;margin-bottom:6px}
.stat .value{font-size:24px;font-weight:700}
.stat .sub{color:var(--muted);font-size:12px;margin-top:4px}
.card{background:var(--panel);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:18px;box-shadow:var(--shadow)}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);flex-wrap:wrap;gap:8px}
.card-head h3{margin:0;font-size:15px}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--border);font-size:13px;vertical-align:middle}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em;background:var(--bg2)}
tbody tr:hover{background:var(--panel2)}
tbody tr:last-child td{border-bottom:none}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:500}
.badge.on{background:color-mix(in srgb,var(--green) 14%,transparent);color:var(--green)}
.badge.off{background:color-mix(in srgb,var(--red) 14%,transparent);color:var(--red)}
.badge.exp{background:color-mix(in srgb,var(--amber) 14%,transparent);color:var(--amber)}
.dot{width:6px;height:6px;border-radius:50%;background:currentColor}
.keycell{display:flex;align-items:center;gap:8px}
.keycell .k{max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.icon-btn{background:none;border:none;color:var(--muted);cursor:pointer;font-size:13px;padding:2px}
.icon-btn:hover{color:var(--primary2)}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:50}
.modal{background:var(--panel);border:1px solid var(--border);border-radius:14px;width:520px;max-width:94vw;padding:22px;max-height:90vh;overflow:auto}
.modal h3{margin:0 0 16px}
.field{margin-bottom:13px}
.field label{display:block;color:var(--muted);font-size:12px;margin-bottom:5px}
.field input,.field select,.field textarea{width:100%;padding:9px 11px;background:var(--panel2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;font-family:inherit}
.field textarea{min-height:60px;font-family:ui-monospace,monospace}
.field input:focus,.field select:focus,.field textarea:focus{outline:none;border-color:var(--primary)}
.field .hint{color:var(--muted);font-size:11px;margin-top:4px}
.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:end}
.filters input,.filters select{padding:7px 10px;background:var(--panel2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px}
.pager{display:flex;gap:8px;align-items:center;justify-content:flex-end;padding:12px 18px}
.login{min-height:100vh;display:flex;align-items:center;justify-content:center}
.login .box{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:32px;width:360px;text-align:center;box-shadow:var(--shadow)}
.login .logo{width:46px;height:46px;border-radius:12px;margin:0 auto 14px;font-size:22px;background:linear-gradient(135deg,var(--primary),var(--accent));display:flex;align-items:center;justify-content:center;color:#fff}
.login h2{margin:0 0 4px}.login p{color:var(--muted);margin:0 0 20px;font-size:13px}
.login input{width:100%;padding:11px;background:var(--panel2);border:1px solid var(--border);border-radius:9px;color:var(--text);margin-bottom:12px}
#toasts{position:fixed;right:18px;bottom:18px;display:flex;flex-direction:column;gap:8px;z-index:100}
.toast{background:var(--panel);border:1px solid var(--border);border-left:3px solid var(--primary);padding:11px 16px;border-radius:9px;min-width:200px;box-shadow:0 8px 24px rgba(0,0,0,.2)}
.toast.ok{border-left-color:var(--green)}.toast.err{border-left-color:var(--red)}
.empty{padding:30px;text-align:center;color:var(--muted)}
@media(max-width:820px){.sidebar{position:fixed;left:-220px;z-index:60;transition:.2s}.sidebar.open{left:0}.stats{grid-template-columns:repeat(2,1fr)}}
</style>
<script>
(function(){const K='theme';function sd(){return matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches;}
function rv(){const s=localStorage.getItem(K);return s==='dark'||s==='light'?s:(sd()?'dark':'light');}
window.__toggleTheme=function(){const c=document.documentElement.getAttribute('data-theme')||rv();const n=c==='dark'?'light':'dark';localStorage.setItem(K,n);document.documentElement.setAttribute('data-theme',n);var b=document.getElementById('themeBtn');if(b)b.textContent=n==='dark'?'☀':'🌙';};
document.documentElement.setAttribute('data-theme',rv());})();
</script>
</head>
<body>
<div id="login" class="login">
  <div class="box">
    <div class="logo">🔑</div>
    <h2>llm_api 后台</h2>
    <p>输入管理员密钥 (ADMIN_KEY)</p>
    <input id="loginKey" type="password" placeholder="ADMIN_KEY" onkeydown="if(event.key==='Enter')doLogin()"/>
    <button class="btn primary" style="width:100%" onclick="doLogin()">进入</button>
    <div id="loginErr" style="color:#f87171;font-size:12px;margin-top:10px"></div>
  </div>
</div>

<div id="app" class="hidden">
 <div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="brand"><span class="logo">⚡</span> llm_api</div>
    <nav class="navm">
      <div class="item active" data-tab="tokens" onclick="switchTab('tokens')"><span class="ic">🎫</span>令牌</div>
      <div class="item" data-tab="users" onclick="switchTab('users')"><span class="ic">👤</span>用户</div>
      <div class="item" data-tab="channels" onclick="switchTab('channels')"><span class="ic">🔌</span>渠道</div>
      <div class="item" data-tab="pricing" onclick="switchTab('pricing')"><span class="ic">💲</span>定价</div>
      <div class="item" data-tab="logs" onclick="switchTab('logs')"><span class="ic">📜</span>请求日志</div>
      <div class="item" data-tab="analytics" onclick="switchTab('analytics')"><span class="ic">📊</span>数据分析</div>
      <div class="item" data-tab="redemption" onclick="switchTab('redemption')"><span class="ic">🎟️</span>兑换码</div>
      <div class="item" data-tab="orders" onclick="switchTab('orders')"><span class="ic">🧾</span>订单</div>
      <div class="item" data-tab="settings" onclick="switchTab('settings')"><span class="ic">⚙️</span>系统设置</div>
      <div class="item" data-tab="audit" onclick="switchTab('audit')"><span class="ic">🔍</span>审计</div>
    </nav>
    <div class="foot">
      <button class="icon-toggle" id="themeBtn" onclick="__toggleTheme()" title="切换主题">🌙</button>
      <button class="btn sm ghost" onclick="loadAll()">↻ 刷新</button>
      <button class="btn sm ghost" onclick="logout()">退出</button>
    </div>
  </aside>
  <div class="main">
    <div class="topbar">
      <h2 id="pageTitle">令牌</h2>
      <div class="top-actions"><a class="btn sm ghost" href="/" target="_blank">↗ 前台</a></div>
    </div>
    <div class="wrap">
    <div class="stats" id="stats"></div>
    <div id="tab-tokens">
      <div class="card"><div class="card-head"><h3>访问令牌</h3>
        <div style="display:flex;gap:8px">
          <button class="btn sm" onclick="batchTokens('enable')">批量启用</button>
          <button class="btn sm" onclick="batchTokens('disable')">批量停用</button>
          <button class="btn sm danger" onclick="batchTokens('delete')">批量删除</button>
          <button class="btn primary sm" onclick="openTokenModal()">＋ 新建令牌</button>
        </div></div>
        <table><thead><tr><th style="width:32px"><input type="checkbox" id="tokAll" onclick="toggleAllTokens(this.checked)"/></th><th>ID</th><th>名称</th><th>用户</th><th>Key</th><th>状态</th><th>用量</th><th>RPM</th><th>到期</th><th style="text-align:right">操作</th></tr></thead><tbody id="tokRows"></tbody></table>
      </div>
    </div>

    <div id="tab-users" class="hidden">
      <div class="card"><div class="card-head"><h3>用户</h3><button class="btn primary sm" onclick="openUserModal()">＋ 新建用户</button></div>
        <table><thead><tr><th>ID</th><th>用户名</th><th>角色</th><th>分组</th><th>余额</th><th>冻结</th><th>状态</th><th style="text-align:right">操作</th></tr></thead><tbody id="userRows"></tbody></table>
      </div>
    </div>

    <div id="tab-channels" class="hidden">
      <div class="card"><div class="card-head"><h3>上游渠道</h3><button class="btn primary sm" onclick="openChannelModal()">＋ 新建渠道</button></div>
        <table><thead><tr><th>ID</th><th>名称</th><th>类型</th><th>分组</th><th>Keys</th><th>模型</th><th>权重</th><th>失败</th><th>状态</th><th style="text-align:right">操作</th></tr></thead><tbody id="chanRows"></tbody></table>
      </div>
    </div>

    <div id="tab-pricing" class="hidden">
      <div class="card"><div class="card-head"><h3>模型定价 <span class="mono" style="color:var(--muted)">(credits / 1K tokens，1 USD=1,000,000)</span></h3><button class="btn primary sm" onclick="openPricingModal()">＋ 新建定价</button></div>
        <table><thead><tr><th>ID</th><th>模型</th><th>分组</th><th>输入价</th><th>输出价</th><th>缓存价</th><th>倍率</th><th style="text-align:right">操作</th></tr></thead><tbody id="priceRows"></tbody></table>
      </div>
    </div>

    <div id="tab-logs" class="hidden">
      <div class="card">
        <div class="card-head">
          <h3>请求日志</h3>
          <div class="filters">
            <input id="fUser" placeholder="令牌名" style="width:110px"/>
            <input id="fModel" placeholder="模型" style="width:120px"/>
            <input id="fChannel" placeholder="渠道" style="width:110px"/>
            <input id="fStatus" placeholder="状态码" style="width:80px"/>
            <label style="font-size:12px;color:var(--muted);display:flex;align-items:center;gap:4px"><input type="checkbox" id="fErr" style="width:auto"/>仅错误</label>
            <button class="btn sm primary" onclick="logsPage=0;loadLogs()">查询</button>
          </div>
        </div>
        <table><thead><tr><th>时间</th><th>令牌</th><th>模型</th><th>渠道</th><th>状态</th><th>Tokens</th><th>费用</th><th>延迟</th><th>错误</th></tr></thead><tbody id="logRows"></tbody></table>
        <div class="pager">
          <span id="logInfo" class="mono" style="color:var(--muted);margin-right:auto"></span>
          <button class="btn sm" onclick="logsPrev()">上一页</button>
          <button class="btn sm" onclick="logsNext()">下一页</button>
        </div>
      </div>
    </div>

    <div id="tab-analytics" class="hidden">
      <div class="card"><div class="card-head"><h3>数据分析</h3>
        <select id="anDays" onchange="loadAnalytics()" style="padding:7px 10px;background:var(--panel2);border:1px solid var(--border);border-radius:8px;color:var(--text)"><option value="7">近 7 天</option><option value="30" selected>近 30 天</option><option value="90">近 90 天</option></select>
      </div></div>
      <div class="stats" id="anRevenue"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="card"><div class="card-head"><h3>模型消耗排行</h3></div><table><thead><tr><th>模型</th><th>请求</th><th>Tokens</th><th>费用</th></tr></thead><tbody id="rankModel"></tbody></table></div>
        <div class="card"><div class="card-head"><h3>用户消耗排行</h3></div><table><thead><tr><th>令牌</th><th>请求</th><th>Tokens</th><th>费用</th></tr></thead><tbody id="rankUser"></tbody></table></div>
      </div>
      <div class="card"><div class="card-head"><h3>渠道消耗排行</h3></div><table><thead><tr><th>渠道</th><th>请求</th><th>Tokens</th><th>费用</th></tr></thead><tbody id="rankChannel"></tbody></table></div>
      <div class="card"><div class="card-head"><h3>按天趋势</h3></div><table><thead><tr><th>日期</th><th>请求</th><th>Tokens</th><th>费用(credits)</th></tr></thead><tbody id="tsRows"></tbody></table></div>
      <div class="card"><div class="card-head"><h3>告警</h3></div><div style="padding:16px 18px" id="alertsBox"></div></div>
    </div>

    <div id="tab-redemption" class="hidden">
      <div class="card"><div class="card-head"><h3>兑换码</h3>
        <div style="display:flex;gap:8px">
          <button class="btn sm" onclick="exportCodes()">导出未用(CSV)</button>
          <button class="btn primary sm" onclick="openGenCodesModal()">＋ 批量生成</button>
        </div></div>
        <table><thead><tr><th>ID</th><th>兑换码</th><th>面额</th><th>批次</th><th>状态</th><th>使用者</th><th style="text-align:right">操作</th></tr></thead><tbody id="codeRows"></tbody></table>
      </div>
    </div>

    <div id="tab-orders" class="hidden">
      <div class="card"><div class="card-head"><h3>充值订单</h3></div>
        <table><thead><tr><th>订单号</th><th>用户</th><th>方式</th><th>金额</th><th>到账credits</th><th>状态</th><th>创建</th><th style="text-align:right">操作</th></tr></thead><tbody id="orderRows"></tbody></table>
      </div>
    </div>

    <div id="tab-settings" class="hidden">
      <div class="card"><div class="card-head"><h3>系统设置（热更新，无需重启）</h3></div>
        <div style="padding:18px" id="settingsForm"></div>
      </div>
    </div>

    <div id="tab-audit" class="hidden">
      <div class="card"><div class="card-head"><h3>审计日志</h3></div>
        <table><thead><tr><th>时间</th><th>操作者</th><th>动作</th><th>对象</th><th>详情</th><th>IP</th></tr></thead><tbody id="auditRows"></tbody></table>
      </div>
    </div>
    </div><!-- /.wrap -->
  </div><!-- /.main -->
 </div><!-- /.layout -->
</div><!-- /#app -->

<div id="modal" class="overlay hidden"><div class="modal" id="modalBox"></div></div>
<div id="toasts"></div>
<script>
const $=s=>document.querySelector(s);
const KEY=()=>localStorage.getItem('llm_admin_key')||'';
const H=()=>({'Authorization':'Bearer '+KEY(),'Content-Type':'application/json'});
let STATE={users:[],tokens:[],channels:[],pricing:[]};
let logsPage=0; const LOGS_LIMIT=50; let logsTotal=0;

function toast(m,t){const e=document.createElement('div');e.className='toast '+(t||'');e.textContent=m;$('#toasts').appendChild(e);setTimeout(()=>{e.style.opacity='0';setTimeout(()=>e.remove(),200)},2600);}
async function api(p,o={}){const r=await fetch(p,{headers:H(),...o});if(r.status===401||r.status===403){showLogin('密钥无效或无权限');throw new Error('auth');}if(!r.ok){let d='';try{d=(await r.json()).detail||''}catch(e){}toast('请求失败 '+r.status+' '+d,'err');throw new Error(r.status);}return r.json();}
async function apiText(p){const r=await fetch(p,{headers:H()});if(!r.ok)throw new Error(r.status);return r.text();}

function showLogin(err){$('#app').classList.add('hidden');$('#login').classList.remove('hidden');if(err)$('#loginErr').textContent=err;}
function doLogin(){const k=$('#loginKey').value.trim();if(!k){$('#loginErr').textContent='请输入密钥';return;}localStorage.setItem('llm_admin_key',k);$('#loginErr').textContent='';enterApp();}
function logout(){localStorage.removeItem('llm_admin_key');$('#loginKey').value='';showLogin('');}
async function enterApp(){try{await api('/admin/tokens');}catch(e){return;}$('#login').classList.add('hidden');$('#app').classList.remove('hidden');loadAll();}

const TABS=['tokens','users','channels','pricing','logs','analytics','redemption','orders','settings','audit'];
const TAB_TITLES={tokens:'令牌',users:'用户',channels:'渠道',pricing:'定价',logs:'请求日志',analytics:'数据分析',redemption:'兑换码',orders:'订单',settings:'系统设置',audit:'审计'};
function switchTab(n){document.querySelectorAll('.navm .item').forEach(t=>t.classList.toggle('active',t.dataset.tab===n));TABS.forEach(x=>$('#tab-'+x).classList.toggle('hidden',x!==n));
  const pt=$('#pageTitle');if(pt)pt.textContent=TAB_TITLES[n]||n;
  if(n==='logs')loadLogs();else if(n==='analytics')loadAnalytics();else if(n==='redemption')loadCodes();else if(n==='orders')loadOrders();else if(n==='settings')loadSettings();else if(n==='audit')loadAudit();}
function maskKey(k){return k&&k.length>14?k.slice(0,7)+'····'+k.slice(-4):k;}
function fmtDate(ts){return ts==null?'永久':new Date(ts*1000).toLocaleDateString('zh-CN');}
function fmtTime(ts){return ts==null?'-':new Date(ts*1000).toLocaleString('zh-CN');}
function isExpired(ts){return ts!=null&&ts*1000<Date.now();}
function closeModal(){$('#modal').classList.add('hidden');}
function copyKey(k){navigator.clipboard?.writeText(k).then(()=>toast('已复制','ok'),()=>toast('复制失败','err'));}

async function loadAll(){
  const [tk,us,ch,pr,ug,stx]=await Promise.all([api('/admin/tokens'),api('/admin/users'),api('/admin/channels'),api('/admin/pricing'),api('/admin/usage'),api('/admin/logs/stats?days=7').catch(()=>null)]);
  STATE.tokens=tk.tokens;STATE.users=us.users;STATE.channels=ch.channels;STATE.pricing=pr.pricing;
  renderStats(ug,stx);renderTokens();renderUsers();renderChannels();renderPricing();
}
function renderStats(u,stx){
  const active=STATE.tokens.filter(t=>t.enabled&&!isExpired(t.expires_at)).length;
  const today=stx?stx.today:null;
  const total=stx?stx.total:null;
  $('#stats').innerHTML=`
    <div class="stat"><div class="label">活跃令牌</div><div class="value">${active}</div><div class="sub">共 ${STATE.tokens.length} 令牌 · ${STATE.users.length} 用户</div></div>
    <div class="stat"><div class="label">今日请求</div><div class="value">${today?today.requests.toLocaleString():'-'}</div><div class="sub">成功率 ${today?today.success_rate:'-'}%</div></div>
    <div class="stat"><div class="label">今日消费</div><div class="value">$${today?(today.cost/1e6).toFixed(4):'-'}</div><div class="sub">${today?today.tokens.toLocaleString():'-'} tokens</div></div>
    <div class="stat"><div class="label">累计消费</div><div class="value">$${total?(total.cost/1e6).toFixed(2):'-'}</div><div class="sub">${total?total.requests.toLocaleString():'-'} 次请求</div></div>`;
}
function userName(id){const u=STATE.users.find(x=>x.id===id);return u?u.username:('#'+id);}

function renderTokens(){
  const tb=$('#tokRows');tb.innerHTML='';
  if(!STATE.tokens.length){tb.innerHTML='<tr><td colspan="10"><div class="empty">还没有令牌</div></td></tr>';return;}
  for(const t of STATE.tokens){
    const expired=isExpired(t.expires_at);
    let badge=t.enabled?'<span class="badge on"><span class="dot"></span>启用</span>':'<span class="badge off"><span class="dot"></span>停用</span>';
    if(t.enabled&&expired)badge='<span class="badge exp"><span class="dot"></span>已过期</span>';
    let usage=t.quota_tokens==null?`<span class="mono">${(t.used_tokens||0).toLocaleString()} / ∞</span>`:`<span class="mono">${(t.used_tokens||0).toLocaleString()} / ${t.quota_tokens.toLocaleString()}</span>`;
    const tr=document.createElement('tr');
    tr.innerHTML=`<td><input type="checkbox" class="tokChk" value="${t.id}"/></td><td class="mono">${t.id}</td><td>${t.name||'-'}</td><td>${userName(t.user_id)}</td>
      <td><div class="keycell"><span class="k mono" title="${t.key}">${maskKey(t.key)}</span><button class="icon-btn" onclick='copyKey(${JSON.stringify(t.key)})'>⧉</button></div></td>
      <td>${badge}</td><td>${usage}</td><td class="mono">${t.rpm_limit==null?'∞':t.rpm_limit}</td><td>${fmtDate(t.expires_at)}</td>
      <td style="text-align:right;white-space:nowrap">
        <button class="btn sm" onclick="toggleToken(${t.id},${t.enabled?0:1})">${t.enabled?'停用':'启用'}</button>
        <button class="btn sm" onclick='openTokenModal(${JSON.stringify(t)})'>编辑</button>
        <button class="btn sm danger" onclick="delToken(${t.id})">删除</button></td>`;
    tb.appendChild(tr);
  }
}
function renderUsers(){
  const tb=$('#userRows');tb.innerHTML='';
  if(!STATE.users.length){tb.innerHTML='<tr><td colspan="8"><div class="empty">无用户</div></td></tr>';return;}
  for(const u of STATE.users){
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="mono">${u.id}</td><td>${u.username}</td><td>${u.role}</td><td>${u.group}</td>
      <td class="mono">${(u.balance||0).toLocaleString()} <span style="color:var(--muted)">($${(u.balance/1e6).toFixed(4)})</span></td>
      <td class="mono">${(u.frozen||0).toLocaleString()}</td>
      <td>${u.status?'<span class="badge on"><span class="dot"></span>启用</span>':'<span class="badge off"><span class="dot"></span>禁用</span>'}</td>
      <td style="text-align:right;white-space:nowrap">
        <button class="btn sm" onclick="openTopup(${u.id})">充值</button>
        <button class="btn sm" onclick="toggleUser(${u.id},${u.status?0:1})">${u.status?'禁用':'启用'}</button></td>`;
    tb.appendChild(tr);
  }
}
function renderChannels(){
  const tb=$('#chanRows');tb.innerHTML='';
  if(!STATE.channels.length){tb.innerHTML='<tr><td colspan="10"><div class="empty">无渠道，点右上角新建</div></td></tr>';return;}
  for(const c of STATE.channels){
    const st=c.status===1?'<span class="badge on"><span class="dot"></span>启用</span>':(c.status===2?'<span class="badge exp"><span class="dot"></span>熔断</span>':'<span class="badge off"><span class="dot"></span>禁用</span>');
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="mono">${c.id}</td><td>${c.name}</td><td>${c.type}</td><td>${c.group}</td><td class="mono">${c.key_count}</td>
      <td class="mono" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${(c.models||[]).join(', ')}">${(c.models||[]).join(', ')}</td>
      <td class="mono">${c.weight}</td><td class="mono">${c.fail_count||0}</td><td>${st}</td>
      <td style="text-align:right;white-space:nowrap">
        <button class="btn sm" onclick="openChannelDetail(${c.id})">账号池</button>
        <button class="btn sm" onclick="toggleChannel(${c.id},${c.status===1?0:1})">${c.status===1?'停用':'启用'}</button>
        <button class="btn sm" onclick='openChannelModal(${JSON.stringify(c)})'>编辑</button>
        <button class="btn sm danger" onclick="delChannel(${c.id})">删除</button></td>`;
    tb.appendChild(tr);
  }
}
function renderPricing(){
  const tb=$('#priceRows');tb.innerHTML='';
  if(!STATE.pricing.length){tb.innerHTML='<tr><td colspan="8"><div class="empty">无定价，未配价的模型不扣费</div></td></tr>';return;}
  for(const p of STATE.pricing){
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="mono">${p.id}</td><td>${p.model}</td><td>${p.group}</td><td class="mono">${p.input_price}</td><td class="mono">${p.output_price}</td>
      <td class="mono">${p.cache_price==null?'-':p.cache_price}</td><td class="mono">${p.multiplier}</td>
      <td style="text-align:right;white-space:nowrap"><button class="btn sm" onclick='openPricingModal(${JSON.stringify(p)})'>编辑</button>
        <button class="btn sm danger" onclick="delPricing(${p.id})">删除</button></td>`;
    tb.appendChild(tr);
  }
}

/* ---- 请求日志 ---- */
function logsPrev(){if(logsPage>0){logsPage--;loadLogs();}}
function logsNext(){if((logsPage+1)*LOGS_LIMIT<logsTotal){logsPage++;loadLogs();}}
async function loadLogs(){
  const qs=new URLSearchParams({limit:LOGS_LIMIT,offset:logsPage*LOGS_LIMIT});
  const u=$('#fUser').value.trim(),m=$('#fModel').value.trim(),c=$('#fChannel').value.trim(),s=$('#fStatus').value.trim();
  if(u)qs.set('token_name',u);if(m)qs.set('model',m);if(c)qs.set('channel',c);if(s)qs.set('status',s);
  if($('#fErr').checked)qs.set('only_errors','1');
  const d=await api('/admin/logs?'+qs.toString());logsTotal=d.total;
  const tb=$('#logRows');
  tb.innerHTML=d.items.length?d.items.map(r=>{
    const st=r.status>=400?`<span style="color:#f87171">${r.status}</span>`:`<span style="color:#4ade80">${r.status}</span>`;
    return `<tr><td class="mono">${fmtTime(r.ts)}</td><td>${r.token_name||'-'}</td><td class="mono">${r.model||'-'}</td>
      <td>${r.channel||'-'}</td><td>${st}</td><td class="mono">${r.total_tokens||0}</td><td class="mono">${r.cost||0}</td>
      <td class="mono">${r.latency_ms||0}ms</td><td class="mono" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${(r.error||'').replace(/"/g,'&quot;')}">${r.error?r.error.slice(0,40):''}</td></tr>`;
  }).join(''):'<tr><td colspan="9"><div class="empty">无记录</div></td></tr>';
  const from=logsTotal?logsPage*LOGS_LIMIT+1:0, to=Math.min((logsPage+1)*LOGS_LIMIT,logsTotal);
  $('#logInfo').textContent=`${from}-${to} / 共 ${logsTotal} 条`;
}

/* ---- 兑换码 ---- */
async function loadCodes(){
  const d=await api('/admin/redemption');
  const tb=$('#codeRows');
  tb.innerHTML=d.codes.length?d.codes.map(c=>{
    const st=c.status===1?'<span class="badge on">可用</span>':(c.status===0?'<span class="badge exp">已用</span>':'<span class="badge off">作废</span>');
    return `<tr><td class="mono">${c.id}</td><td class="mono">${c.code}</td><td class="mono">${c.amount_credits.toLocaleString()}</td>
      <td>${c.batch||'-'}</td><td>${st}</td><td>${c.used_by?('#'+c.used_by):'-'}</td>
      <td style="text-align:right"><button class="icon-btn" onclick='copyKey(${JSON.stringify(c.code)})'>⧉</button>
      ${c.status===1?`<button class="btn sm danger" onclick="voidCode(${c.id})">作废</button>`:''}</td></tr>`;
  }).join(''):'<tr><td colspan="7"><div class="empty">还没有兑换码</div></td></tr>';
}
function openGenCodesModal(){
  $('#modalBox').innerHTML=`<h3>批量生成兑换码</h3>
    <div class="grid2"><div class="field"><label>单张面额 credits</label><input id="gAmount" type="number" value="500000"/><div class="hint">1 USD = 1,000,000 credits</div></div>
    <div class="field"><label>数量（1-1000）</label><input id="gCount" type="number" value="10"/></div></div>
    <div class="field"><label>批次标记（可选）</label><input id="gBatch" placeholder="如 2026-promo"/></div>
    <div class="modal-actions"><button class="btn ghost" onclick="closeModal()">取消</button><button class="btn primary" onclick="genCodes()">生成</button></div>`;
  $('#modal').classList.remove('hidden');
}
async function genCodes(){
  const b={amount_credits:parseInt($('#gAmount').value||'0'),count:parseInt($('#gCount').value||'0'),batch:$('#gBatch').value.trim()||null};
  try{const d=await api('/admin/redemption/generate',{method:'POST',body:JSON.stringify(b)});
    toast(`已生成 ${d.count} 张`,'ok');copyKey(d.codes.join('\n'));toast('兑换码已复制到剪贴板','ok');closeModal();loadCodes();}catch(e){}
}
async function voidCode(id){if(confirm('确认作废此兑换码？')){await api('/admin/redemption/void',{method:'POST',body:JSON.stringify({id})});toast('已作废','ok');loadCodes();}}
async function exportCodes(){try{const txt=await apiText('/admin/redemption/export?only_unused=1');
  const blob=new Blob([txt],{type:'text/csv'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='redemption_codes.csv';a.click();toast('已导出','ok');}catch(e){toast('导出失败','err');}}

/* ---- 订单 ---- */
async function loadOrders(){
  const d=await api('/admin/orders');
  const tb=$('#orderRows');
  tb.innerHTML=d.orders.length?d.orders.map(o=>{
    const stmap={paid:'<span class="badge on">已付</span>',pending:'<span class="badge exp">待付</span>',expired:'<span class="badge off">过期</span>',failed:'<span class="badge off">失败</span>'};
    const money=o.currency==='USDT'?(o.amount_money/1e6).toFixed(2)+' USDT':'¥'+(o.amount_money/100).toFixed(2);
    return `<tr><td class="mono">${o.order_no}</td><td>${userName(o.user_id)}</td><td>${o.method}</td><td class="mono">${money}</td>
      <td class="mono">${o.amount_credits.toLocaleString()}</td><td>${stmap[o.status]||o.status}</td><td class="mono">${fmtTime(o.created_at)}</td>
      <td style="text-align:right">${o.status==='pending'?`<button class="btn sm primary" onclick="markPaid('${o.order_no}')">补单</button>`:''}</td></tr>`;
  }).join(''):'<tr><td colspan="8"><div class="empty">还没有订单</div></td></tr>';
}
async function markPaid(no){if(confirm('确认手动标记该订单为已支付并入账？')){await api('/admin/orders/'+no+'/mark-paid',{method:'POST'});toast('已补单入账','ok');loadOrders();}}

/* ---- 系统设置 ---- */
async function loadSettings(){
  const d=await api('/admin/settings');const s=d.settings||{};
  $('#settingsForm').innerHTML=`
    <div class="grid2">
      <div class="field"><label>站点名称</label><input id="sSiteName" value="${s.site_name||''}"/></div>
      <div class="field"><label>最小充值额（展示用）</label><input id="sTopupMin" type="number" value="${s.topup_min||1}"/></div>
    </div>
    <div class="field"><label>首页公告（留空则不显示）</label><textarea id="sAnnounce">${s.announcement||''}</textarea></div>
    <div class="grid2">
      <div class="field"><label>开放注册</label><select id="sReg"><option value="true" ${s.allow_registration?'selected':''}>是</option><option value="false" ${!s.allow_registration?'selected':''}>否</option></select></div>
      <div class="field"><label></label><button class="btn primary" onclick="saveSettings()">保存设置</button></div>
    </div>
    <div class="hint" style="color:var(--muted);font-size:12px">注：邮箱登录开关、汇率等属于部署级配置，在服务器 .env 中修改。此处为运营级热更新项。</div>`;
}
async function saveSettings(){
  const b={site_name:$('#sSiteName').value.trim(),topup_min:parseInt($('#sTopupMin').value||'1'),
    announcement:$('#sAnnounce').value,allow_registration:$('#sReg').value==='true'};
  try{await api('/admin/settings',{method:'PUT',body:JSON.stringify(b)});toast('已保存','ok');}catch(e){}
}

/* ---- 审计 ---- */
async function loadAudit(){
  const d=await api('/admin/audit?limit=200');
  const tb=$('#auditRows');
  tb.innerHTML=d.logs.length?d.logs.map(l=>`<tr><td class="mono">${fmtTime(l.ts)}</td><td>${l.actor}</td><td class="mono">${l.action}</td>
    <td>${l.target||'-'}</td><td class="mono" style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title='${(l.detail||"").replace(/'/g,"")}'>${l.detail||''}</td><td class="mono">${l.ip||'-'}</td></tr>`).join(''):'<tr><td colspan="6"><div class="empty">暂无</div></td></tr>';
}

/* ---- 数据分析（v2.4）---- */
function usd(c){return '$'+((c||0)/1e6).toFixed(2);}
async function loadAnalytics(){
  const days=parseInt($('#anDays').value);
  const [ov,rm,ru,rc,ts,al]=await Promise.all([
    api('/admin/analytics/overview?days='+days),
    api('/admin/analytics/ranking?by=model&days='+days),
    api('/admin/analytics/ranking?by=user&days='+days),
    api('/admin/analytics/ranking?by=channel&days='+days),
    api('/admin/analytics/timeseries?days='+Math.min(days,30)+'&metric=cost'),
    api('/admin/alerts?min_balance=1'),
  ]);
  const rev=ov.revenue;
  $('#anRevenue').innerHTML=`
    <div class="stat"><div class="label">充值收入</div><div class="value">${usd(rev.topup)}</div></div>
    <div class="stat"><div class="label">消费</div><div class="value">${usd(rev.consume)}</div></div>
    <div class="stat"><div class="label">退款</div><div class="value">${usd(rev.refund)}</div></div>
    <div class="stat"><div class="label">净收入</div><div class="value">${usd(rev.net_income)}</div></div>`;
  const rrow=r=>`<tr><td>${r.key||'-'}</td><td class="mono">${r.requests}</td><td class="mono">${(r.tokens||0).toLocaleString()}</td><td class="mono">${usd(r.cost)}</td></tr>`;
  $('#rankModel').innerHTML=rm.ranking.length?rm.ranking.map(rrow).join(''):'<tr><td colspan="4"><div class="empty">暂无</div></td></tr>';
  $('#rankUser').innerHTML=ru.ranking.length?ru.ranking.map(rrow).join(''):'<tr><td colspan="4"><div class="empty">暂无</div></td></tr>';
  $('#rankChannel').innerHTML=rc.ranking.length?rc.ranking.map(rrow).join(''):'<tr><td colspan="4"><div class="empty">暂无</div></td></tr>';
  $('#tsRows').innerHTML=ts.series.map(s=>`<tr><td class="mono">${s.date}</td><td class="mono">${s.requests}</td><td class="mono">${(s.tokens||0).toLocaleString()}</td><td class="mono">${s.cost}</td></tr>`).join('');
  let alerts='';
  if(al.circuit_open.length)alerts+='<div class="msg err">⚠️ 熔断渠道：'+al.circuit_open.map(c=>c.name+'(失败'+c.fail_count+')').join('、')+'</div>';
  if(al.low_balance.length)alerts+='<div class="msg err">💰 低余额用户：'+al.low_balance.map(u=>u.username).join('、')+'</div>';
  $('#alertsBox').innerHTML=alerts||'<div class="empty">一切正常</div>';
}

/* ---- token modal ---- */
function openTokenModal(t){
  const opts=STATE.users.map(u=>`<option value="${u.id}" ${t&&t.user_id===u.id?'selected':''}>${u.username}</option>`).join('');
  $('#modalBox').innerHTML=`<h3>${t?'编辑令牌':'新建令牌'}</h3>
    <div class="field"><label>名称</label><input id="fName" value="${t?(t.name||''):''}"/></div>
    <div class="field"><label>归属用户</label><select id="fUserSel">${opts}</select></div>
    <div class="grid2"><div class="field"><label>配额 tokens（空=无限）</label><input id="fQuota" type="number" value="${t&&t.quota_tokens!=null?t.quota_tokens:''}"/></div>
    <div class="field"><label>有效天数（空=永久）</label><input id="fDays" type="number"/></div></div>
    <div class="grid2"><div class="field"><label>限速 RPM（空=不限）</label><input id="fRpm" type="number" value="${t&&t.rpm_limit!=null?t.rpm_limit:''}"/></div>
    <div class="field"><label>备注</label><input id="fNote" value="${t?(t.note||''):''}"/></div></div>
    <div class="field"><label>允许模型（逗号分隔，空=全部）</label><input id="fModels" value="${t&&t.allowed_models?t.allowed_models:''}"/></div>
    <div class="modal-actions"><button class="btn ghost" onclick="closeModal()">取消</button><button class="btn primary" onclick="submitToken('${t?t.id:''}')">保存</button></div>`;
  $('#modal').classList.remove('hidden');
}
async function submitToken(id){
  const b={name:$('#fName').value||'friend',user_id:parseInt($('#fUserSel').value)};
  const q=$('#fQuota').value,d=$('#fDays').value,r=$('#fRpm').value,m=$('#fModels').value.trim(),n=$('#fNote').value.trim();
  b.quota_tokens=q!==''?parseInt(q):null;if(d!=='')b.expires_in_days=parseInt(d);b.rpm_limit=r!==''?parseInt(r):null;b.allowed_models=m;if(n!=='')b.note=n;
  try{if(id){await api('/admin/tokens/'+id,{method:'PATCH',body:JSON.stringify(b)});toast('已更新','ok');}
    else{const t=await api('/admin/tokens',{method:'POST',body:JSON.stringify(b)});toast('已创建','ok');copyKey(t.key);toast('Key 已复制，请发给对方','ok');}
    closeModal();loadAll();}catch(e){}
}
async function toggleToken(id,en){await api('/admin/tokens/'+id,{method:'PATCH',body:JSON.stringify({enabled:en})});loadAll();}
async function delToken(id){if(confirm('确认删除此令牌？')){await api('/admin/tokens/'+id,{method:'DELETE'});toast('已删除','ok');loadAll();}}
function toggleAllTokens(ck){document.querySelectorAll('.tokChk').forEach(c=>c.checked=ck);}
async function batchTokens(action){
  const ids=[...document.querySelectorAll('.tokChk:checked')].map(c=>parseInt(c.value));
  if(!ids.length){toast('请先勾选令牌','err');return;}
  const label={enable:'启用',disable:'停用',delete:'删除'}[action];
  if(!confirm(`确认批量${label} ${ids.length} 个令牌？`))return;
  try{const d=await api('/admin/tokens/batch',{method:'POST',body:JSON.stringify({ids,action})});
    toast(`已${label} ${d.affected} 个`,'ok');const a=$('#tokAll');if(a)a.checked=false;loadAll();}catch(e){}
}

/* ---- user modal ---- */
function openUserModal(){
  $('#modalBox').innerHTML=`<h3>新建用户</h3>
    <div class="field"><label>用户名</label><input id="uName"/></div>
    <div class="grid2"><div class="field"><label>角色</label><select id="uRole"><option value="user">user</option><option value="admin">admin</option></select></div>
    <div class="field"><label>分组</label><input id="uGroup" value="default"/></div></div>
    <div class="field"><label>初始余额 credits</label><input id="uBalance" type="number" value="0"/><div class="hint">1 USD = 1,000,000 credits</div></div>
    <div class="modal-actions"><button class="btn ghost" onclick="closeModal()">取消</button><button class="btn primary" onclick="submitUser()">保存</button></div>`;
  $('#modal').classList.remove('hidden');
}
async function submitUser(){
  const b={username:$('#uName').value.trim(),role:$('#uRole').value,group:$('#uGroup').value.trim()||'default',balance:parseInt($('#uBalance').value||'0')};
  if(!b.username){toast('用户名必填','err');return;}
  try{await api('/admin/users',{method:'POST',body:JSON.stringify(b)});toast('已创建','ok');closeModal();loadAll();}catch(e){}
}
async function toggleUser(id,st){await api('/admin/users/'+id,{method:'PATCH',body:JSON.stringify({status:st})});toast(st?'已启用':'已禁用','ok');loadAll();}
function openTopup(uid){
  $('#modalBox').innerHTML=`<h3>充值 / 调整余额</h3>
    <div class="field"><label>金额 credits（可负）</label><input id="tpAmount" type="number"/><div class="hint">1 USD = 1,000,000 credits</div></div>
    <div class="modal-actions"><button class="btn ghost" onclick="closeModal()">取消</button><button class="btn primary" onclick="submitTopup(${uid})">确认</button></div>`;
  $('#modal').classList.remove('hidden');
}
async function submitTopup(uid){
  const a=parseInt($('#tpAmount').value||'0');if(!a){toast('金额必填','err');return;}
  try{await api('/admin/users/'+uid+'/topup',{method:'POST',body:JSON.stringify({amount:a})});toast('已调整','ok');closeModal();loadAll();}catch(e){}
}

/* ---- channel modal ---- */
function openChannelModal(c){
  $('#modalBox').innerHTML=`<h3>${c?'编辑渠道':'新建渠道'}</h3>
    <div class="grid2"><div class="field"><label>名称</label><input id="cName" value="${c?c.name:''}"/></div>
    <div class="field"><label>类型</label><select id="cType">${['openai','deepseek','openrouter','claude','gemini','qwen'].map(x=>`<option ${c&&c.type===x?'selected':''}>${x}</option>`).join('')}</select></div></div>
    <div class="field"><label>Base URL</label><input id="cUrl" value="${c?c.base_url:''}" placeholder="https://api.deepseek.com/v1"/></div>
    <div class="field"><label>API Keys（每行一个，多个即轮询池）</label><textarea id="cKeys" placeholder="${c?'留空则不修改现有 key':'sk-...'}"></textarea></div>
    <div class="field"><label>模型（每行一个，支持 * 和 前缀*）</label><textarea id="cModels">${c?(c.models||[]).join('\n'):''}</textarea></div>
    <div class="field"><label>model_map 别名（JSON）</label><textarea id="cMap">${c?JSON.stringify(c.model_map||{}):'{}'}</textarea></div>
    <div class="grid2"><div class="field"><label>分组</label><input id="cGroup" value="${c?c.group:'default'}"/></div>
    <div class="field"><label>权重</label><input id="cWeight" type="number" value="${c?c.weight:1}"/></div></div>
    <div class="modal-actions"><button class="btn ghost" onclick="closeModal()">取消</button><button class="btn primary" onclick="submitChannel('${c?c.id:''}')">保存</button></div>`;
  $('#modal').classList.remove('hidden');
}
async function submitChannel(id){
  const b={name:$('#cName').value.trim(),type:$('#cType').value,base_url:$('#cUrl').value.trim(),
    group:$('#cGroup').value.trim()||'default',weight:parseInt($('#cWeight').value||'1')};
  const keys=$('#cKeys').value.split('\n').map(x=>x.trim()).filter(Boolean);
  b.models=$('#cModels').value.split('\n').map(x=>x.trim()).filter(Boolean);
  try{b.model_map=JSON.parse($('#cMap').value||'{}');}catch(e){toast('model_map 不是合法 JSON','err');return;}
  if(keys.length||!id)b.api_keys=keys;
  try{if(id)await api('/admin/channels/'+id,{method:'PATCH',body:JSON.stringify(b)});
    else await api('/admin/channels',{method:'POST',body:JSON.stringify(b)});
    toast('已保存','ok');closeModal();loadAll();}catch(e){}
}
async function toggleChannel(id,st){await api('/admin/channels/'+id,{method:'PATCH',body:JSON.stringify({status:st})});toast('已更新','ok');loadAll();}
async function delChannel(id){if(confirm('确认删除此渠道？')){await api('/admin/channels/'+id,{method:'DELETE'});toast('已删除','ok');loadAll();}}

/* ---- 渠道账号池详情（v2.3）---- */
let CUR_CHANNEL=null;
async function openChannelDetail(cid){
  CUR_CHANNEL=cid;
  $('#modalBox').innerHTML=`<h3>渠道账号池 #${cid}</h3>
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <button class="btn sm primary" onclick="testChannel(false)">测试首个 key</button>
      <button class="btn sm" onclick="testChannel(true)">测试全部 key</button>
      <button class="btn sm" onclick="discoverModels()">发现模型</button>
    </div>
    <div id="chTestMsg"></div>
    <div id="chKeys"><div class="empty">加载中…</div></div>
    <div class="modal-actions"><button class="btn ghost" onclick="closeModal()">关闭</button></div>`;
  $('#modal').classList.remove('hidden');
  loadChannelKeys();
}
async function loadChannelKeys(){
  try{const d=await api('/admin/channels/'+CUR_CHANNEL+'/keys');
    const box=$('#chKeys');
    if(!d.keys.length){box.innerHTML='<div class="empty">该渠道无 key</div>';return;}
    box.innerHTML='<table><thead><tr><th>Key</th><th>成功</th><th>失败</th><th>最近状态</th><th>状态</th><th></th></tr></thead><tbody>'+
      d.keys.map(k=>`<tr><td class="mono">${k.masked}</td><td class="mono">${k.ok}</td><td class="mono">${k.fail}</td>
        <td class="mono">${k.last_status==null?'-':k.last_status}</td>
        <td>${k.disabled?'<span class="badge off">停用</span>':'<span class="badge on">启用</span>'}</td>
        <td><button class="btn sm" onclick="toggleKey('${k.fp}',${k.disabled?0:1})">${k.disabled?'启用':'停用'}</button></td></tr>`).join('')+
      '</tbody></table>';
  }catch(e){}
}
async function toggleKey(fp,dis){await api('/admin/channels/'+CUR_CHANNEL+'/keys/'+fp+'/toggle',{method:'POST',body:JSON.stringify({disabled:!!dis})});toast('已更新','ok');loadChannelKeys();loadAll();}
async function testChannel(all){
  $('#chTestMsg').innerHTML='<div class="msg">测试中…</div>';
  try{const d=await api('/admin/channels/'+CUR_CHANNEL+'/test',{method:'POST',body:JSON.stringify({all_keys:all})});
    const rows=d.results.map(r=>`<div class="msg ${r.ok?'ok':'err'}">${r.masked} · ${r.ok?'OK':'FAIL'} · ${r.status} · ${r.latency_ms}ms ${r.error?('· '+r.error.slice(0,60)):''}</div>`).join('');
    $('#chTestMsg').innerHTML=`<div style="margin-bottom:8px;color:var(--muted);font-size:12px">模型 ${d.model}</div>${rows}`;
    loadChannelKeys();
  }catch(e){$('#chTestMsg').innerHTML=`<div class="msg err">测试失败：${e.message||e}</div>`;}
}
async function discoverModels(){
  $('#chTestMsg').innerHTML='<div class="msg">拉取中…</div>';
  try{const d=await api('/admin/channels/'+CUR_CHANNEL+'/discover-models');
    $('#chTestMsg').innerHTML=`<div class="msg ok">上游 ${d.models.length} 个模型（可复制到渠道编辑的模型框）：</div>
      <textarea class="mono" style="width:100%;min-height:90px;background:var(--panel2);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:8px">${d.models.join('\n')}</textarea>`;
  }catch(e){$('#chTestMsg').innerHTML=`<div class="msg err">${e.message||e}</div>`;}
}

/* ---- pricing modal ---- */
function openPricingModal(p){
  $('#modalBox').innerHTML=`<h3>${p?'编辑定价':'新建定价'}</h3>
    <div class="grid2"><div class="field"><label>模型</label><input id="pModel" value="${p?p.model:''}"/></div>
    <div class="field"><label>分组</label><input id="pGroup" value="${p?p.group:'default'}"/></div></div>
    <div class="grid2"><div class="field"><label>输入价 (credits/1K)</label><input id="pIn" type="number" value="${p?p.input_price:0}"/></div>
    <div class="field"><label>输出价 (credits/1K)</label><input id="pOut" type="number" value="${p?p.output_price:0}"/></div></div>
    <div class="grid2"><div class="field"><label>缓存价（空=无）</label><input id="pCache" type="number" value="${p&&p.cache_price!=null?p.cache_price:''}"/></div>
    <div class="field"><label>倍率</label><input id="pMul" type="number" step="0.01" value="${p?p.multiplier:1.0}"/></div></div>
    <div class="modal-actions"><button class="btn ghost" onclick="closeModal()">取消</button><button class="btn primary" onclick="submitPricing('${p?p.id:''}')">保存</button></div>`;
  $('#modal').classList.remove('hidden');
}
async function submitPricing(id){
  const c=$('#pCache').value;
  const b={model:$('#pModel').value.trim(),group:$('#pGroup').value.trim()||'default',
    input_price:parseInt($('#pIn').value||'0'),output_price:parseInt($('#pOut').value||'0'),
    cache_price:c!==''?parseInt(c):null,multiplier:parseFloat($('#pMul').value||'1')};
  if(!b.model){toast('模型必填','err');return;}
  try{if(id)await api('/admin/pricing/'+id,{method:'PATCH',body:JSON.stringify(b)});
    else await api('/admin/pricing',{method:'POST',body:JSON.stringify(b)});
    toast('已保存','ok');closeModal();loadAll();}catch(e){}
}
async function delPricing(id){if(confirm('确认删除此定价？')){await api('/admin/pricing/'+id,{method:'DELETE'});toast('已删除','ok');loadAll();}}

if(KEY())enterApp();else showLogin('');
(function(){var t=document.documentElement.getAttribute('data-theme');var b=document.getElementById('themeBtn');if(b)b.textContent=t==='dark'?'☀':'🌙';})();
</script>
</body>
</html>
"""
