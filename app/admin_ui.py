"""现代化后台管理页面（纯前端单文件，调用 /admin/* 接口，无外部依赖）。"""

ADMIN_HTML = r"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>llm_api · 网关后台</title>
<style>
:root{
  --bg:#0f1117; --panel:#181b24; --panel2:#1f2330; --border:#2a2f3d;
  --text:#e6e8ee; --muted:#9aa3b2; --primary:#6366f1; --primary2:#818cf8;
  --green:#22c55e; --red:#ef4444; --amber:#f59e0b; --cyan:#22d3ee;
}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--text);font-size:14px}
a{color:var(--primary2)}
.hidden{display:none!important}

/* 顶栏 */
.topbar{display:flex;align-items:center;justify-content:space-between;
  padding:14px 24px;background:linear-gradient(90deg,#1a1d27,#181b24);
  border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10}
.brand{display:flex;align-items:center;gap:10px;font-weight:600;font-size:16px}
.logo{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--primary),var(--cyan));
  display:flex;align-items:center;justify-content:center;font-size:15px}
.top-actions{display:flex;gap:8px;align-items:center}

.wrap{max-width:1120px;margin:24px auto;padding:0 20px}

/* 按钮 */
.btn{border:1px solid var(--border);background:var(--panel2);color:var(--text);
  padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;transition:.15s}
.btn:hover{border-color:var(--primary);background:#262b3a}
.btn.primary{background:linear-gradient(135deg,var(--primary),var(--primary2));border:none;color:#fff;font-weight:600}
.btn.primary:hover{filter:brightness(1.08)}
.btn.ghost{background:transparent}
.btn.sm{padding:5px 10px;font-size:12px}
.btn.danger{color:#fda4af;border-color:#4c2230}
.btn.danger:hover{background:#3a1620;border-color:var(--red)}

/* 统计卡 */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
.stat{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:16px 18px}
.stat .label{color:var(--muted);font-size:12px;margin-bottom:6px}
.stat .value{font-size:24px;font-weight:700}
.stat .sub{color:var(--muted);font-size:12px;margin-top:4px}

/* 标签页 */
.tabs{display:flex;gap:6px;margin-bottom:14px;border-bottom:1px solid var(--border)}
.tab{padding:10px 16px;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;font-weight:500}
.tab.active{color:var(--text);border-bottom-color:var(--primary)}

/* 卡片/表格 */
.card{background:var(--panel);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:18px}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border)}
.card-head h3{margin:0;font-size:15px}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:11px 16px;border-bottom:1px solid var(--border);font-size:13px;vertical-align:middle}
th{color:var(--muted);font-weight:500;background:#15171f}
tbody tr:hover{background:#1c202b}
tbody tr:last-child td{border-bottom:none}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}

/* 徽章 */
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:500}
.badge.on{background:rgba(34,197,94,.14);color:#4ade80}
.badge.off{background:rgba(239,68,68,.14);color:#f87171}
.badge.exp{background:rgba(245,158,11,.14);color:#fbbf24}
.dot{width:6px;height:6px;border-radius:50%;background:currentColor}

/* 进度条 */
.prog{height:6px;background:#2a2f3d;border-radius:4px;overflow:hidden;margin-top:5px;width:120px}
.prog > i{display:block;height:100%;background:linear-gradient(90deg,var(--primary),var(--cyan))}
.prog.warn > i{background:linear-gradient(90deg,var(--amber),var(--red))}

/* key 单元 */
.keycell{display:flex;align-items:center;gap:8px}
.keycell .k{max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.icon-btn{background:none;border:none;color:var(--muted);cursor:pointer;font-size:13px;padding:2px}
.icon-btn:hover{color:var(--primary2)}

/* 弹窗 */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:50}
.modal{background:var(--panel);border:1px solid var(--border);border-radius:16px;width:460px;max-width:94vw;padding:22px}
.modal h3{margin:0 0 16px}
.field{margin-bottom:13px}
.field label{display:block;color:var(--muted);font-size:12px;margin-bottom:5px}
.field input{width:100%;padding:9px 11px;background:var(--panel2);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:13px}
.field input:focus{outline:none;border-color:var(--primary)}
.field .hint{color:var(--muted);font-size:11px;margin-top:4px}
.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}

/* 登录 */
.login{min-height:100vh;display:flex;align-items:center;justify-content:center}
.login .box{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:32px;width:360px;text-align:center}
.login .logo{width:46px;height:46px;border-radius:12px;margin:0 auto 14px;font-size:22px}
.login h2{margin:0 0 4px} .login p{color:var(--muted);margin:0 0 20px;font-size:13px}
.login input{width:100%;padding:11px;background:var(--panel2);border:1px solid var(--border);border-radius:9px;color:var(--text);margin-bottom:12px}

/* toast */
#toasts{position:fixed;right:18px;bottom:18px;display:flex;flex-direction:column;gap:8px;z-index:100}
.toast{background:var(--panel2);border:1px solid var(--border);border-left:3px solid var(--primary);
  padding:11px 16px;border-radius:9px;min-width:200px;animation:slide .2s ease;box-shadow:0 8px 24px rgba(0,0,0,.4)}
.toast.ok{border-left-color:var(--green)} .toast.err{border-left-color:var(--red)}
@keyframes slide{from{transform:translateX(20px);opacity:0}to{transform:none;opacity:1}}
.empty{padding:30px;text-align:center;color:var(--muted)}
@media(max-width:720px){.stats{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>

<!-- 登录页 -->
<div id="login" class="login">
  <div class="box">
    <div class="logo" style="background:linear-gradient(135deg,var(--primary),var(--cyan));display:flex;align-items:center;justify-content:center">🔑</div>
    <h2>llm_api 后台</h2>
    <p>输入管理员密钥 (ADMIN_KEY)</p>
    <input id="loginKey" type="password" placeholder="ADMIN_KEY" onkeydown="if(event.key==='Enter')doLogin()"/>
    <button class="btn primary" style="width:100%" onclick="doLogin()">进入</button>
    <div id="loginErr" style="color:#f87171;font-size:12px;margin-top:10px"></div>
  </div>
</div>

<!-- 主界面 -->
<div id="app" class="hidden">
  <div class="topbar">
    <div class="brand"><span class="logo">⚡</span> llm_api 网关后台</div>
    <div class="top-actions">
      <button class="btn primary" onclick="openModal()">＋ 新建令牌</button>
      <button class="btn ghost" onclick="loadAll()">↻ 刷新</button>
      <button class="btn ghost" onclick="logout()">退出</button>
    </div>
  </div>

  <div class="wrap">
    <div class="stats" id="stats"></div>

    <div class="tabs">
      <div class="tab active" data-tab="tokens" onclick="switchTab('tokens')">令牌管理</div>
      <div class="tab" data-tab="usage" onclick="switchTab('usage')">用量统计</div>
    </div>

    <div id="tab-tokens">
      <div class="card">
        <div class="card-head"><h3>访问令牌</h3><span class="mono" id="tokCount" style="color:var(--muted)"></span></div>
        <table><thead><tr>
          <th>ID</th><th>名称</th><th>Key</th><th>状态</th><th>用量</th><th>RPM</th><th>到期</th><th style="text-align:right">操作</th>
        </tr></thead><tbody id="tokRows"></tbody></table>
      </div>
    </div>

    <div id="tab-usage" class="hidden">
      <div class="card">
        <div class="card-head"><h3>按用户用量</h3></div>
        <table><thead><tr><th>令牌</th><th>请求数</th><th>Tokens</th></tr></thead><tbody id="byToken"></tbody></table>
      </div>
      <div class="card">
        <div class="card-head"><h3>按渠道用量</h3></div>
        <table><thead><tr><th>渠道</th><th>请求数</th><th>Tokens</th><th>平均延迟(ms)</th></tr></thead><tbody id="byChannel"></tbody></table>
      </div>
      <div class="card">
        <div class="card-head"><h3>最近请求</h3></div>
        <table><thead><tr><th>时间</th><th>令牌</th><th>模型</th><th>渠道</th><th>状态</th><th>Tokens</th><th>延迟</th></tr></thead><tbody id="recent"></tbody></table>
      </div>
    </div>
  </div>
</div>

<!-- 创建/编辑弹窗 -->
<div id="modal" class="overlay hidden">
  <div class="modal">
    <h3 id="modalTitle">新建令牌</h3>
    <input type="hidden" id="editId"/>
    <div class="field">
      <label>名称</label>
      <input id="fName" placeholder="如 张三"/>
    </div>
    <div class="grid2">
      <div class="field"><label>配额 tokens（空=无限）</label><input id="fQuota" type="number" min="0"/></div>
      <div class="field"><label>有效天数（空=永久）</label><input id="fDays" type="number" min="1"/></div>
    </div>
    <div class="grid2">
      <div class="field"><label>限速 RPM（空=不限）</label><input id="fRpm" type="number" min="1"/></div>
      <div class="field"><label>备注</label><input id="fNote" placeholder="可选"/></div>
    </div>
    <div class="field">
      <label>允许模型（逗号分隔，空=全部）</label>
      <input id="fModels" placeholder="deepseek-chat,claude"/>
      <div class="hint">留空表示该令牌可用所有已配置模型</div>
    </div>
    <div class="modal-actions">
      <button class="btn ghost" onclick="closeModal()">取消</button>
      <button class="btn primary" onclick="submitToken()">保存</button>
    </div>
  </div>
</div>

<div id="toasts"></div>

<script>
const $ = s => document.querySelector(s);
const KEY = () => localStorage.getItem('llm_admin_key') || '';
const H = () => ({'Authorization':'Bearer '+KEY(),'Content-Type':'application/json'});

function toast(msg, type){
  const t = document.createElement('div');
  t.className = 'toast ' + (type||'');
  t.textContent = msg;
  $('#toasts').appendChild(t);
  setTimeout(()=>{ t.style.opacity='0'; setTimeout(()=>t.remove(),200); }, 2600);
}

async function api(path, opts={}){
  const r = await fetch(path, {headers:H(), ...opts});
  if(r.status===401 || r.status===403){ showLogin('密钥无效或无权限'); throw new Error('auth'); }
  if(!r.ok){ let d=''; try{d=(await r.json()).detail||''}catch(e){} toast('请求失败 '+r.status+' '+d,'err'); throw new Error(r.status); }
  return r.json();
}

/* 登录 */
function showLogin(err){ $('#app').classList.add('hidden'); $('#login').classList.remove('hidden'); if(err) $('#loginErr').textContent=err; }
function doLogin(){
  const k = $('#loginKey').value.trim();
  if(!k){ $('#loginErr').textContent='请输入密钥'; return; }
  localStorage.setItem('llm_admin_key', k);
  $('#loginErr').textContent='';
  enterApp();
}
function logout(){ localStorage.removeItem('llm_admin_key'); $('#loginKey').value=''; showLogin(''); }
async function enterApp(){
  try{ await api('/admin/tokens'); }catch(e){ return; }
  $('#login').classList.add('hidden'); $('#app').classList.remove('hidden');
  loadAll();
}

/* 标签 */
function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active', t.dataset.tab===name));
  $('#tab-tokens').classList.toggle('hidden', name!=='tokens');
  $('#tab-usage').classList.toggle('hidden', name!=='usage');
}

/* 渲染 */
function maskKey(k){ return k.length>14 ? k.slice(0,7)+'····'+k.slice(-4) : k; }
function fmtDate(ts){ return ts==null ? '永久' : new Date(ts*1000).toLocaleDateString('zh-CN'); }
function isExpired(ts){ return ts!=null && ts*1000 < Date.now(); }

async function loadAll(){
  const [{tokens}, usage] = await Promise.all([api('/admin/tokens'), api('/admin/usage')]);
  renderStats(tokens, usage);
  renderTokens(tokens);
  renderUsage(usage);
}

function renderStats(tokens, usage){
  const active = tokens.filter(t=>t.enabled && !isExpired(t.expires_at)).length;
  const totalReq = usage.by_token.reduce((s,r)=>s+(r.requests||0),0);
  const totalTok = usage.by_token.reduce((s,r)=>s+(r.tokens||0),0);
  const chans = usage.by_channel.filter(c=>c.channel!=='none').length;
  $('#stats').innerHTML = `
    <div class="stat"><div class="label">活跃令牌</div><div class="value">${active}</div><div class="sub">共 ${tokens.length} 个</div></div>
    <div class="stat"><div class="label">总请求数</div><div class="value">${totalReq.toLocaleString()}</div></div>
    <div class="stat"><div class="label">总消耗 Tokens</div><div class="value">${totalTok.toLocaleString()}</div></div>
    <div class="stat"><div class="label">在用渠道</div><div class="value">${chans}</div></div>`;
}

function renderTokens(tokens){
  $('#tokCount').textContent = tokens.length + ' tokens';
  const tb = $('#tokRows'); tb.innerHTML='';
  if(!tokens.length){ tb.innerHTML='<tr><td colspan="8"><div class="empty">还没有令牌，点右上角"新建令牌"创建一个</div></td></tr>'; return; }
  for(const t of tokens){
    const expired = isExpired(t.expires_at);
    let badge = t.enabled ? '<span class="badge on"><span class="dot"></span>启用</span>' : '<span class="badge off"><span class="dot"></span>停用</span>';
    if(t.enabled && expired) badge = '<span class="badge exp"><span class="dot"></span>已过期</span>';
    let usage;
    if(t.quota_tokens==null){ usage = `<span class="mono">${(t.used_tokens||0).toLocaleString()} / ∞</span>`; }
    else{
      const pct = Math.min(100, Math.round((t.used_tokens||0)/t.quota_tokens*100));
      usage = `<span class="mono">${(t.used_tokens||0).toLocaleString()} / ${t.quota_tokens.toLocaleString()}</span>
        <div class="prog ${pct>=90?'warn':''}"><i style="width:${pct}%"></i></div>`;
    }
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="mono">${t.id}</td>
      <td>${t.name||'-'}</td>
      <td><div class="keycell"><span class="k mono" title="${t.key}">${maskKey(t.key)}</span>
          <button class="icon-btn" title="复制" onclick='copyKey(${JSON.stringify(t.key)})'>⧉</button></div></td>
      <td>${badge}</td>
      <td>${usage}</td>
      <td class="mono">${t.rpm_limit==null?'∞':t.rpm_limit}</td>
      <td>${fmtDate(t.expires_at)}</td>
      <td style="text-align:right;white-space:nowrap">
        <button class="btn sm" onclick="toggle(${t.id},${t.enabled?0:1})">${t.enabled?'停用':'启用'}</button>
        <button class="btn sm" onclick='openModal(${JSON.stringify(t)})'>编辑</button>
        <button class="btn sm danger" onclick="del(${t.id},${JSON.stringify(t.name||'')})">删除</button>
      </td>`;
    tb.appendChild(tr);
  }
}

function renderUsage(u){
  $('#byToken').innerHTML = u.by_token.length ? u.by_token.map(r=>
    `<tr><td>${r.token_name}</td><td class="mono">${r.requests}</td><td class="mono">${(r.tokens||0).toLocaleString()}</td></tr>`).join('')
    : '<tr><td colspan="3"><div class="empty">暂无数据</div></td></tr>';
  $('#byChannel').innerHTML = u.by_channel.length ? u.by_channel.map(r=>
    `<tr><td>${r.channel}</td><td class="mono">${r.requests}</td><td class="mono">${(r.tokens||0).toLocaleString()}</td><td class="mono">${r.avg_latency_ms||0}</td></tr>`).join('')
    : '<tr><td colspan="4"><div class="empty">暂无数据</div></td></tr>';
  $('#recent').innerHTML = u.recent.length ? u.recent.slice(0,40).map(r=>{
    const st = r.status>=400 ? `<span style="color:#f87171">${r.status}</span>` : `<span style="color:#4ade80">${r.status}</span>`;
    return `<tr><td class="mono">${new Date(r.ts*1000).toLocaleTimeString('zh-CN')}</td><td>${r.token_name||'-'}</td>
      <td class="mono">${r.model||'-'}</td><td>${r.channel||'-'}</td><td>${st}</td>
      <td class="mono">${r.total_tokens||0}</td><td class="mono">${r.latency_ms||0}ms</td></tr>`;
  }).join('') : '<tr><td colspan="7"><div class="empty">暂无请求</div></td></tr>';
}

/* 复制 */
function copyKey(k){
  navigator.clipboard?.writeText(k).then(()=>toast('Key 已复制','ok'), ()=>toast('复制失败','err'));
}

/* 弹窗 */
function openModal(t){
  $('#modalTitle').textContent = t ? '编辑令牌' : '新建令牌';
  $('#editId').value = t ? t.id : '';
  $('#fName').value = t ? (t.name||'') : '';
  $('#fQuota').value = t && t.quota_tokens!=null ? t.quota_tokens : '';
  $('#fDays').value = '';
  $('#fRpm').value = t && t.rpm_limit!=null ? t.rpm_limit : '';
  $('#fNote').value = t ? (t.note||'') : '';
  $('#fModels').value = t && t.allowed_models ? t.allowed_models : '';
  $('#modal').classList.remove('hidden');
}
function closeModal(){ $('#modal').classList.add('hidden'); }

async function submitToken(){
  const id = $('#editId').value;
  const body = { name: $('#fName').value || 'friend' };
  const q=$('#fQuota').value, d=$('#fDays').value, r=$('#fRpm').value, m=$('#fModels').value.trim(), n=$('#fNote').value.trim();
  body.quota_tokens = q!==''? parseInt(q): null;
  if(d!=='') body.expires_in_days = parseInt(d);
  body.rpm_limit = r!==''? parseInt(r): null;
  body.allowed_models = m;
  if(n!=='') body.note = n;
  try{
    if(id){
      await api('/admin/tokens/'+id, {method:'PATCH', body:JSON.stringify(body)});
      toast('已更新','ok');
    }else{
      const t = await api('/admin/tokens', {method:'POST', body:JSON.stringify(body)});
      toast('已创建','ok');
      copyKey(t.key);
      toast('Key 已复制，请发给对方（仅此一次完整展示）','ok');
    }
    closeModal(); loadAll();
  }catch(e){}
}

async function toggle(id, enabled){ await api('/admin/tokens/'+id,{method:'PATCH',body:JSON.stringify({enabled})}); toast(enabled?'已启用':'已停用','ok'); loadAll(); }
async function del(id, name){ if(confirm('确认删除令牌「'+name+'」？此操作不可恢复')){ await api('/admin/tokens/'+id,{method:'DELETE'}); toast('已删除','ok'); loadAll(); } }

/* 启动 */
if(KEY()) enterApp(); else showLogin('');
</script>
</body>
</html>
"""
