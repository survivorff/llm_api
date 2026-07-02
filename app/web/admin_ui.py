"""后台管理页面（纯前端单文件，调用 /admin/* 接口）。v1：用户/令牌/渠道/定价/用量。"""

ADMIN_HTML = r"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>llm_api · 网关后台</title>
<style>
:root{--bg:#0f1117;--panel:#181b24;--panel2:#1f2330;--border:#2a2f3d;--text:#e6e8ee;
--muted:#9aa3b2;--primary:#6366f1;--primary2:#818cf8;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;--cyan:#22d3ee;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC",sans-serif;background:var(--bg);color:var(--text);font-size:14px}
.hidden{display:none!important}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;background:linear-gradient(90deg,#1a1d27,#181b24);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10}
.brand{display:flex;align-items:center;gap:10px;font-weight:600;font-size:16px}
.logo{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--primary),var(--cyan));display:flex;align-items:center;justify-content:center;font-size:15px}
.top-actions{display:flex;gap:8px;align-items:center}
.wrap{max-width:1180px;margin:24px auto;padding:0 20px}
.btn{border:1px solid var(--border);background:var(--panel2);color:var(--text);padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;transition:.15s}
.btn:hover{border-color:var(--primary);background:#262b3a}
.btn.primary{background:linear-gradient(135deg,var(--primary),var(--primary2));border:none;color:#fff;font-weight:600}
.btn.ghost{background:transparent}
.btn.sm{padding:5px 10px;font-size:12px}
.btn.danger{color:#fda4af;border-color:#4c2230}
.btn.danger:hover{background:#3a1620;border-color:var(--red)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
.stat{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:16px 18px}
.stat .label{color:var(--muted);font-size:12px;margin-bottom:6px}
.stat .value{font-size:24px;font-weight:700}
.stat .sub{color:var(--muted);font-size:12px;margin-top:4px}
.tabs{display:flex;gap:6px;margin-bottom:14px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.tab{padding:10px 16px;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;font-weight:500}
.tab.active{color:var(--text);border-bottom-color:var(--primary)}
.card{background:var(--panel);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:18px}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border)}
.card-head h3{margin:0;font-size:15px}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:11px 16px;border-bottom:1px solid var(--border);font-size:13px;vertical-align:middle}
th{color:var(--muted);font-weight:500;background:#15171f}
tbody tr:hover{background:#1c202b}
tbody tr:last-child td{border-bottom:none}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:500}
.badge.on{background:rgba(34,197,94,.14);color:#4ade80}
.badge.off{background:rgba(239,68,68,.14);color:#f87171}
.badge.exp{background:rgba(245,158,11,.14);color:#fbbf24}
.dot{width:6px;height:6px;border-radius:50%;background:currentColor}
.keycell{display:flex;align-items:center;gap:8px}
.keycell .k{max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.icon-btn{background:none;border:none;color:var(--muted);cursor:pointer;font-size:13px;padding:2px}
.icon-btn:hover{color:var(--primary2)}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:50}
.modal{background:var(--panel);border:1px solid var(--border);border-radius:16px;width:520px;max-width:94vw;padding:22px;max-height:90vh;overflow:auto}
.modal h3{margin:0 0 16px}
.field{margin-bottom:13px}
.field label{display:block;color:var(--muted);font-size:12px;margin-bottom:5px}
.field input,.field select,.field textarea{width:100%;padding:9px 11px;background:var(--panel2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;font-family:inherit}
.field textarea{min-height:60px;font-family:ui-monospace,monospace}
.field input:focus,.field select:focus,.field textarea:focus{outline:none;border-color:var(--primary)}
.field .hint{color:var(--muted);font-size:11px;margin-top:4px}
.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.login{min-height:100vh;display:flex;align-items:center;justify-content:center}
.login .box{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:32px;width:360px;text-align:center}
.login .logo{width:46px;height:46px;border-radius:12px;margin:0 auto 14px;font-size:22px}
.login h2{margin:0 0 4px}.login p{color:var(--muted);margin:0 0 20px;font-size:13px}
.login input{width:100%;padding:11px;background:var(--panel2);border:1px solid var(--border);border-radius:9px;color:var(--text);margin-bottom:12px}
#toasts{position:fixed;right:18px;bottom:18px;display:flex;flex-direction:column;gap:8px;z-index:100}
.toast{background:var(--panel2);border:1px solid var(--border);border-left:3px solid var(--primary);padding:11px 16px;border-radius:9px;min-width:200px;box-shadow:0 8px 24px rgba(0,0,0,.4)}
.toast.ok{border-left-color:var(--green)}.toast.err{border-left-color:var(--red)}
.empty{padding:30px;text-align:center;color:var(--muted)}
@media(max-width:720px){.stats{grid-template-columns:repeat(2,1fr)}}
</style>
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
  <div class="topbar">
    <div class="brand"><span class="logo">⚡</span> llm_api 网关后台</div>
    <div class="top-actions">
      <button class="btn ghost" onclick="loadAll()">↻ 刷新</button>
      <button class="btn ghost" onclick="logout()">退出</button>
    </div>
  </div>
  <div class="wrap">
    <div class="stats" id="stats"></div>
    <div class="tabs">
      <div class="tab active" data-tab="tokens" onclick="switchTab('tokens')">令牌</div>
      <div class="tab" data-tab="users" onclick="switchTab('users')">用户</div>
      <div class="tab" data-tab="channels" onclick="switchTab('channels')">渠道</div>
      <div class="tab" data-tab="pricing" onclick="switchTab('pricing')">定价</div>
      <div class="tab" data-tab="usage" onclick="switchTab('usage')">用量</div>
    </div>

    <div id="tab-tokens">
      <div class="card"><div class="card-head"><h3>访问令牌</h3><button class="btn primary sm" onclick="openTokenModal()">＋ 新建令牌</button></div>
        <table><thead><tr><th>ID</th><th>名称</th><th>用户</th><th>Key</th><th>状态</th><th>用量</th><th>RPM</th><th>到期</th><th style="text-align:right">操作</th></tr></thead><tbody id="tokRows"></tbody></table>
      </div>
    </div>

    <div id="tab-users" class="hidden">
      <div class="card"><div class="card-head"><h3>用户</h3><button class="btn primary sm" onclick="openUserModal()">＋ 新建用户</button></div>
        <table><thead><tr><th>ID</th><th>用户名</th><th>角色</th><th>分组</th><th>余额</th><th>冻结</th><th>状态</th><th style="text-align:right">操作</th></tr></thead><tbody id="userRows"></tbody></table>
      </div>
    </div>

    <div id="tab-channels" class="hidden">
      <div class="card"><div class="card-head"><h3>上游渠道</h3><button class="btn primary sm" onclick="openChannelModal()">＋ 新建渠道</button></div>
        <table><thead><tr><th>ID</th><th>名称</th><th>类型</th><th>分组</th><th>Keys</th><th>模型</th><th>权重</th><th>状态</th><th style="text-align:right">操作</th></tr></thead><tbody id="chanRows"></tbody></table>
      </div>
    </div>

    <div id="tab-pricing" class="hidden">
      <div class="card"><div class="card-head"><h3>模型定价 <span class="mono" style="color:var(--muted)">(credits / 1K tokens，1 USD=1,000,000)</span></h3><button class="btn primary sm" onclick="openPricingModal()">＋ 新建定价</button></div>
        <table><thead><tr><th>ID</th><th>模型</th><th>分组</th><th>输入价</th><th>输出价</th><th>缓存价</th><th>倍率</th><th style="text-align:right">操作</th></tr></thead><tbody id="priceRows"></tbody></table>
      </div>
    </div>

    <div id="tab-usage" class="hidden">
      <div class="card"><div class="card-head"><h3>按令牌用量</h3></div>
        <table><thead><tr><th>令牌</th><th>请求数</th><th>Tokens</th><th>费用(credits)</th></tr></thead><tbody id="byToken"></tbody></table></div>
      <div class="card"><div class="card-head"><h3>按渠道用量</h3></div>
        <table><thead><tr><th>渠道</th><th>请求数</th><th>Tokens</th><th>费用</th><th>平均延迟(ms)</th></tr></thead><tbody id="byChannel"></tbody></table></div>
      <div class="card"><div class="card-head"><h3>最近请求</h3></div>
        <table><thead><tr><th>时间</th><th>令牌</th><th>模型</th><th>渠道</th><th>状态</th><th>Tokens</th><th>费用</th><th>延迟</th></tr></thead><tbody id="recent"></tbody></table></div>
    </div>
  </div>
</div>

<div id="modal" class="overlay hidden"><div class="modal" id="modalBox"></div></div>
<div id="toasts"></div>
<script>
const $=s=>document.querySelector(s);
const KEY=()=>localStorage.getItem('llm_admin_key')||'';
const H=()=>({'Authorization':'Bearer '+KEY(),'Content-Type':'application/json'});
let STATE={users:[],tokens:[],channels:[],pricing:[]};

function toast(m,t){const e=document.createElement('div');e.className='toast '+(t||'');e.textContent=m;$('#toasts').appendChild(e);setTimeout(()=>{e.style.opacity='0';setTimeout(()=>e.remove(),200)},2600);}
async function api(p,o={}){const r=await fetch(p,{headers:H(),...o});if(r.status===401||r.status===403){showLogin('密钥无效或无权限');throw new Error('auth');}if(!r.ok){let d='';try{d=(await r.json()).detail||''}catch(e){}toast('请求失败 '+r.status+' '+d,'err');throw new Error(r.status);}return r.json();}

function showLogin(err){$('#app').classList.add('hidden');$('#login').classList.remove('hidden');if(err)$('#loginErr').textContent=err;}
function doLogin(){const k=$('#loginKey').value.trim();if(!k){$('#loginErr').textContent='请输入密钥';return;}localStorage.setItem('llm_admin_key',k);$('#loginErr').textContent='';enterApp();}
function logout(){localStorage.removeItem('llm_admin_key');$('#loginKey').value='';showLogin('');}
async function enterApp(){try{await api('/admin/tokens');}catch(e){return;}$('#login').classList.add('hidden');$('#app').classList.remove('hidden');loadAll();}

function switchTab(n){document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.tab===n));['tokens','users','channels','pricing','usage'].forEach(x=>$('#tab-'+x).classList.toggle('hidden',x!==n));}
function maskKey(k){return k&&k.length>14?k.slice(0,7)+'····'+k.slice(-4):k;}
function fmtDate(ts){return ts==null?'永久':new Date(ts*1000).toLocaleDateString('zh-CN');}
function isExpired(ts){return ts!=null&&ts*1000<Date.now();}
function closeModal(){$('#modal').classList.add('hidden');}
function copyKey(k){navigator.clipboard?.writeText(k).then(()=>toast('已复制','ok'),()=>toast('复制失败','err'));}

async function loadAll(){
  const [tk,us,ch,pr,ug]=await Promise.all([api('/admin/tokens'),api('/admin/users'),api('/admin/channels'),api('/admin/pricing'),api('/admin/usage')]);
  STATE.tokens=tk.tokens;STATE.users=us.users;STATE.channels=ch.channels;STATE.pricing=pr.pricing;
  renderStats(ug);renderTokens();renderUsers();renderChannels();renderPricing();renderUsage(ug);
}
function renderStats(u){
  const active=STATE.tokens.filter(t=>t.enabled&&!isExpired(t.expires_at)).length;
  const totalReq=u.by_token.reduce((s,r)=>s+(r.requests||0),0);
  const totalTok=u.by_token.reduce((s,r)=>s+(r.tokens||0),0);
  const totalCost=u.by_token.reduce((s,r)=>s+(r.cost||0),0);
  $('#stats').innerHTML=`
    <div class="stat"><div class="label">活跃令牌</div><div class="value">${active}</div><div class="sub">共 ${STATE.tokens.length} 个 · ${STATE.users.length} 用户</div></div>
    <div class="stat"><div class="label">总请求数</div><div class="value">${totalReq.toLocaleString()}</div></div>
    <div class="stat"><div class="label">总消耗 Tokens</div><div class="value">${totalTok.toLocaleString()}</div></div>
    <div class="stat"><div class="label">总费用 (USD)</div><div class="value">$${(totalCost/1e6).toFixed(4)}</div></div>`;
}
function userName(id){const u=STATE.users.find(x=>x.id===id);return u?u.username:('#'+id);}

function renderTokens(){
  const tb=$('#tokRows');tb.innerHTML='';
  if(!STATE.tokens.length){tb.innerHTML='<tr><td colspan="9"><div class="empty">还没有令牌</div></td></tr>';return;}
  for(const t of STATE.tokens){
    const expired=isExpired(t.expires_at);
    let badge=t.enabled?'<span class="badge on"><span class="dot"></span>启用</span>':'<span class="badge off"><span class="dot"></span>停用</span>';
    if(t.enabled&&expired)badge='<span class="badge exp"><span class="dot"></span>已过期</span>';
    let usage=t.quota_tokens==null?`<span class="mono">${(t.used_tokens||0).toLocaleString()} / ∞</span>`:`<span class="mono">${(t.used_tokens||0).toLocaleString()} / ${t.quota_tokens.toLocaleString()}</span>`;
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="mono">${t.id}</td><td>${t.name||'-'}</td><td>${userName(t.user_id)}</td>
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
      <td style="text-align:right;white-space:nowrap"><button class="btn sm" onclick="openTopup(${u.id})">充值</button></td>`;
    tb.appendChild(tr);
  }
}
function renderChannels(){
  const tb=$('#chanRows');tb.innerHTML='';
  if(!STATE.channels.length){tb.innerHTML='<tr><td colspan="9"><div class="empty">无渠道，点右上角新建</div></td></tr>';return;}
  for(const c of STATE.channels){
    const st=c.status===1?'<span class="badge on"><span class="dot"></span>启用</span>':(c.status===2?'<span class="badge exp"><span class="dot"></span>熔断</span>':'<span class="badge off"><span class="dot"></span>禁用</span>');
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="mono">${c.id}</td><td>${c.name}</td><td>${c.type}</td><td>${c.group}</td><td class="mono">${c.key_count}</td>
      <td class="mono" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${(c.models||[]).join(', ')}">${(c.models||[]).join(', ')}</td>
      <td class="mono">${c.weight}</td><td>${st}</td>
      <td style="text-align:right;white-space:nowrap"><button class="btn sm" onclick='openChannelModal(${JSON.stringify(c)})'>编辑</button>
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
function renderUsage(u){
  $('#byToken').innerHTML=u.by_token.length?u.by_token.map(r=>`<tr><td>${r.token_name}</td><td class="mono">${r.requests}</td><td class="mono">${(r.tokens||0).toLocaleString()}</td><td class="mono">${(r.cost||0).toLocaleString()}</td></tr>`).join(''):'<tr><td colspan="4"><div class="empty">暂无</div></td></tr>';
  $('#byChannel').innerHTML=u.by_channel.length?u.by_channel.map(r=>`<tr><td>${r.channel}</td><td class="mono">${r.requests}</td><td class="mono">${(r.tokens||0).toLocaleString()}</td><td class="mono">${(r.cost||0).toLocaleString()}</td><td class="mono">${r.avg_latency_ms||0}</td></tr>`).join(''):'<tr><td colspan="5"><div class="empty">暂无</div></td></tr>';
  $('#recent').innerHTML=u.recent.length?u.recent.slice(0,40).map(r=>{const st=r.status>=400?`<span style="color:#f87171">${r.status}</span>`:`<span style="color:#4ade80">${r.status}</span>`;return `<tr><td class="mono">${new Date(r.ts*1000).toLocaleTimeString('zh-CN')}</td><td>${r.token_name||'-'}</td><td class="mono">${r.model||'-'}</td><td>${r.channel||'-'}</td><td>${st}</td><td class="mono">${r.total_tokens||0}</td><td class="mono">${r.cost||0}</td><td class="mono">${r.latency_ms||0}ms</td></tr>`;}).join(''):'<tr><td colspan="8"><div class="empty">暂无请求</div></td></tr>';
}

/* ---- token modal ---- */
function openTokenModal(t){
  const opts=STATE.users.map(u=>`<option value="${u.id}" ${t&&t.user_id===u.id?'selected':''}>${u.username}</option>`).join('');
  $('#modalBox').innerHTML=`<h3>${t?'编辑令牌':'新建令牌'}</h3>
    <div class="field"><label>名称</label><input id="fName" value="${t?(t.name||''):''}"/></div>
    <div class="field"><label>归属用户</label><select id="fUser">${opts}</select></div>
    <div class="grid2"><div class="field"><label>配额 tokens（空=无限）</label><input id="fQuota" type="number" value="${t&&t.quota_tokens!=null?t.quota_tokens:''}"/></div>
    <div class="field"><label>有效天数（空=永久）</label><input id="fDays" type="number"/></div></div>
    <div class="grid2"><div class="field"><label>限速 RPM（空=不限）</label><input id="fRpm" type="number" value="${t&&t.rpm_limit!=null?t.rpm_limit:''}"/></div>
    <div class="field"><label>备注</label><input id="fNote" value="${t?(t.note||''):''}"/></div></div>
    <div class="field"><label>允许模型（逗号分隔，空=全部）</label><input id="fModels" value="${t&&t.allowed_models?t.allowed_models:''}"/></div>
    <div class="modal-actions"><button class="btn ghost" onclick="closeModal()">取消</button><button class="btn primary" onclick="submitToken('${t?t.id:''}')">保存</button></div>`;
  $('#modal').classList.remove('hidden');
}
async function submitToken(id){
  const b={name:$('#fName').value||'friend',user_id:parseInt($('#fUser').value)};
  const q=$('#fQuota').value,d=$('#fDays').value,r=$('#fRpm').value,m=$('#fModels').value.trim(),n=$('#fNote').value.trim();
  b.quota_tokens=q!==''?parseInt(q):null;if(d!=='')b.expires_in_days=parseInt(d);b.rpm_limit=r!==''?parseInt(r):null;b.allowed_models=m;if(n!=='')b.note=n;
  try{if(id){await api('/admin/tokens/'+id,{method:'PATCH',body:JSON.stringify(b)});toast('已更新','ok');}
    else{const t=await api('/admin/tokens',{method:'POST',body:JSON.stringify(b)});toast('已创建','ok');copyKey(t.key);toast('Key 已复制，请发给对方','ok');}
    closeModal();loadAll();}catch(e){}
}
async function toggleToken(id,en){await api('/admin/tokens/'+id,{method:'PATCH',body:JSON.stringify({enabled:en})});loadAll();}
async function delToken(id){if(confirm('确认删除此令牌？')){await api('/admin/tokens/'+id,{method:'DELETE'});toast('已删除','ok');loadAll();}}

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
    <div class="field"><label>API Keys（每行一个）</label><textarea id="cKeys" placeholder="${c?'留空则不修改现有 key':'sk-...'}"></textarea></div>
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
async function delChannel(id){if(confirm('确认删除此渠道？')){await api('/admin/channels/'+id,{method:'DELETE'});toast('已删除','ok');loadAll();}}

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
</script>
</body>
</html>
"""
