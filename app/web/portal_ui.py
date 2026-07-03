"""用户自助门户（单文件前端，调用 /auth/* 与 /pay/*）。

功能：邮箱注册/登录、OAuth 登录、用量与余额仪表盘、令牌自助管理、
充值（兑换码 + 在线支付）、账单明细。支持中/英双语。
"""

PORTAL_HTML = r"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>llm_api · 用户中心</title>
<style>
:root{--bg:#0f1117;--panel:#181b24;--panel2:#1f2330;--border:#2a2f3d;--text:#e6e8ee;
--muted:#9aa3b2;--primary:#6366f1;--primary2:#818cf8;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;--cyan:#22d3ee;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC",sans-serif;background:var(--bg);color:var(--text);font-size:14px}
.hidden{display:none!important}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;background:linear-gradient(90deg,#1a1d27,#181b24);border-bottom:1px solid var(--border)}
.brand{display:flex;align-items:center;gap:10px;font-weight:600;font-size:16px}
.logo{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--primary),var(--cyan));display:flex;align-items:center;justify-content:center}
.top-actions{display:flex;gap:8px;align-items:center}
.wrap{max-width:960px;margin:24px auto;padding:0 20px}
.btn{border:1px solid var(--border);background:var(--panel2);color:var(--text);padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;transition:.15s}
.btn:hover{border-color:var(--primary);background:#262b3a}
.btn.primary{background:linear-gradient(135deg,var(--primary),var(--primary2));border:none;color:#fff;font-weight:600}
.btn.sm{padding:5px 10px;font-size:12px}
.btn.danger{color:#fda4af;border-color:#4c2230}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:22px}
.stat{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:16px 18px}
.stat .label{color:var(--muted);font-size:12px;margin-bottom:6px}
.stat .value{font-size:24px;font-weight:700}
.tabs{display:flex;gap:6px;margin-bottom:14px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.tab{padding:10px 16px;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;font-weight:500}
.tab.active{color:var(--text);border-bottom-color:var(--primary)}
.card{background:var(--panel);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:18px}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border)}
.card-head h3{margin:0;font-size:15px}
.card-body{padding:16px 18px}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:11px 16px;border-bottom:1px solid var(--border);font-size:13px}
th{color:var(--muted);font-weight:500;background:#15171f}
input,select{background:var(--panel2);border:1px solid var(--border);color:var(--text);padding:9px 12px;border-radius:8px;font-size:13px;width:100%}
label{display:block;color:var(--muted);font-size:12px;margin:10px 0 5px}
.row{display:flex;gap:12px;flex-wrap:wrap}
.row>div{flex:1;min-width:180px}
.auth-box{max-width:400px;margin:60px auto}
.center{text-align:center}
.msg{padding:10px 14px;border-radius:8px;margin:10px 0;font-size:13px}
.msg.err{background:#3a1620;color:#fda4af;border:1px solid #4c2230}
.msg.ok{background:#12301e;color:#86efac;border:1px solid #1d4a30}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px}
.oauth-btns{display:flex;flex-direction:column;gap:8px;margin-top:14px}
.muted{color:var(--muted)}
a{color:var(--primary2)}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand"><div class="logo">⚡</div><span data-i18n="title">用户中心</span></div>
  <div class="top-actions">
    <select id="lang" style="width:auto" onchange="setLang(this.value)">
      <option value="zh">中文</option><option value="en">English</option>
    </select>
    <span id="whoami" class="muted"></span>
    <button class="btn sm hidden" id="logoutBtn" onclick="logout()" data-i18n="logout">退出</button>
  </div>
</div>

<!-- 登录/注册 -->
<div id="authView" class="wrap">
  <div class="auth-box card">
    <div class="card-body">
      <div class="tabs">
        <div class="tab active" id="tabLogin" onclick="switchAuth('login')" data-i18n="login">登录</div>
        <div class="tab" id="tabReg" onclick="switchAuth('register')" data-i18n="register">注册</div>
      </div>
      <div id="authMsg"></div>
      <label data-i18n="email">邮箱</label>
      <input id="email" type="email" placeholder="you@example.com"/>
      <label data-i18n="password">密码</label>
      <input id="password" type="password" placeholder="••••••"/>
      <div id="regUsername" class="hidden">
        <label data-i18n="username">用户名（可选）</label>
        <input id="username" type="text"/>
      </div>
      <div style="margin-top:16px">
        <button class="btn primary" style="width:100%" id="authSubmit" onclick="submitAuth()" data-i18n="login">登录</button>
      </div>
      <div id="oauthArea" class="oauth-btns"></div>
    </div>
  </div>
</div>

<!-- 公告 -->
<div class="wrap" id="announceWrap" style="margin-bottom:0"></div>

<!-- 主界面 -->
<div id="appView" class="wrap hidden">
  <div class="stats">
    <div class="stat"><div class="label" data-i18n="balance">余额</div><div class="value" id="statBalance">-</div></div>
    <div class="stat"><div class="label" data-i18n="frozen">冻结中</div><div class="value" id="statFrozen">-</div></div>
    <div class="stat"><div class="label" data-i18n="tokens">令牌数</div><div class="value" id="statTokens">-</div></div>
  </div>
  <div class="tabs">
    <div class="tab active" data-tab="tokens" onclick="switchTab('tokens')" data-i18n="tokens">令牌</div>
    <div class="tab" data-tab="topup" onclick="switchTab('topup')" data-i18n="topup">充值</div>
    <div class="tab" data-tab="ledger" onclick="switchTab('ledger')" data-i18n="ledger">账单</div>
  </div>

  <div id="tab-tokens">
    <div class="card">
      <div class="card-head"><h3 data-i18n="tokens">令牌</h3>
        <div class="row" style="margin:0">
          <input id="newTokenName" placeholder="name" style="width:160px"/>
          <button class="btn primary sm" onclick="createToken()" data-i18n="create">新建</button>
        </div>
      </div>
      <table><thead><tr><th>ID</th><th>Name</th><th>Key</th><th data-i18n="used">已用</th><th></th></tr></thead>
      <tbody id="tokenRows"></tbody></table>
    </div>
  </div>

  <div id="tab-topup" class="hidden">
    <div class="card"><div class="card-head"><h3 data-i18n="redeem">兑换码充值</h3></div>
      <div class="card-body">
        <div class="row">
          <div><input id="redeemCode" placeholder="code"/></div>
          <div style="flex:0"><button class="btn primary" onclick="redeem()" data-i18n="redeem">兑换</button></div>
        </div>
        <div id="redeemMsg"></div>
      </div>
    </div>
    <div class="card"><div class="card-head"><h3 data-i18n="onlinePay">在线充值</h3></div>
      <div class="card-body">
        <div class="row">
          <div><label data-i18n="method">支付方式</label><select id="payMethod"></select></div>
          <div><label data-i18n="amount">金额</label><input id="payAmount" type="number" value="10" min="1"/></div>
          <div style="flex:0;display:flex;align-items:flex-end"><button class="btn primary" onclick="createOrder()" data-i18n="pay">支付</button></div>
        </div>
        <div id="payMsg"></div>
      </div>
    </div>
  </div>

  <div id="tab-ledger" class="hidden">
    <div class="card">
      <div class="card-head"><h3 data-i18n="ledger">账单</h3></div>
      <table><thead><tr><th data-i18n="type">类型</th><th data-i18n="amount">金额</th><th data-i18n="balanceAfter">余额</th><th>Ref</th></tr></thead>
      <tbody id="ledgerRows"></tbody></table>
    </div>
  </div>
</div>

<script>
const I18N = {
  zh:{title:"用户中心",login:"登录",register:"注册",logout:"退出",email:"邮箱",password:"密码",
      username:"用户名（可选）",balance:"余额",frozen:"冻结中",tokens:"令牌",topup:"充值",ledger:"账单",
      create:"新建",used:"已用",redeem:"兑换",onlinePay:"在线充值",method:"支付方式",amount:"金额(元/USDT)",
      pay:"支付",type:"类型",balanceAfter:"余额",delete:"删除",loginWith:"使用 %s 登录",
      copied:"已复制",created:"创建成功",redeemOk:"兑换成功，到账 %s credits"},
  en:{title:"User Center",login:"Login",register:"Register",logout:"Logout",email:"Email",password:"Password",
      username:"Username (optional)",balance:"Balance",frozen:"Frozen",tokens:"Tokens",topup:"Top up",ledger:"Ledger",
      create:"Create",used:"Used",redeem:"Redeem",onlinePay:"Online Payment",method:"Method",amount:"Amount",
      pay:"Pay",type:"Type",balanceAfter:"Balance",delete:"Delete",loginWith:"Sign in with %s",
      copied:"Copied",created:"Created",redeemOk:"Redeemed %s credits"}
};
let lang = localStorage.getItem("lang") || "zh";
let authMode = "login";
function t(k){return (I18N[lang]&&I18N[lang][k])||k;}
function session(){return localStorage.getItem("session")||"";}
function setSession(s){localStorage.setItem("session",s);}
function clearSession(){localStorage.removeItem("session");}
function H(){return {"Authorization":"Bearer "+session(),"Content-Type":"application/json"};}

function applyI18n(){
  document.documentElement.lang = lang;
  document.getElementById("lang").value = lang;
  document.querySelectorAll("[data-i18n]").forEach(el=>{el.textContent=t(el.getAttribute("data-i18n"));});
}
function setLang(l){lang=l;localStorage.setItem("lang",l);applyI18n();renderOAuth();}

async function api(path,opts={}){
  opts.headers = Object.assign(H(), opts.headers||{});
  const r = await fetch(path, opts);
  const txt = await r.text();
  let data; try{data=JSON.parse(txt);}catch(e){data=txt;}
  if(!r.ok) throw (data && data.detail ? data.detail : ("HTTP "+r.status));
  return data;
}

function switchAuth(mode){
  authMode=mode;
  document.getElementById("tabLogin").classList.toggle("active",mode==="login");
  document.getElementById("tabReg").classList.toggle("active",mode==="register");
  document.getElementById("regUsername").classList.toggle("hidden",mode!=="register");
  const btn=document.getElementById("authSubmit");
  btn.textContent = t(mode);
}
function showMsg(id,text,ok){document.getElementById(id).innerHTML=`<div class="msg ${ok?'ok':'err'}">${text}</div>`;}

async function submitAuth(){
  const email=document.getElementById("email").value.trim();
  const password=document.getElementById("password").value;
  const body={email,password};
  if(authMode==="register") body.username=document.getElementById("username").value.trim()||null;
  try{
    const data=await fetch("/auth/"+authMode,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}).then(async r=>{
      const d=await r.json(); if(!r.ok) throw d.detail||"error"; return d;});
    setSession(data.session);
    boot();
  }catch(e){showMsg("authMsg",e,false);}
}
function logout(){clearSession();location.reload();}

let providers=null;
async function renderOAuth(){
  if(!providers) return;
  const area=document.getElementById("oauthArea");
  area.innerHTML="";
  (providers.oauth||[]).forEach(p=>{
    const b=document.createElement("button");
    b.className="btn"; b.textContent=t("loginWith").replace("%s",p);
    b.onclick=async()=>{const d=await api("/auth/oauth/"+p);location.href=d.authorize_url;};
    area.appendChild(b);
  });
}

async function loadProviders(){
  try{providers=await fetch("/auth/providers").then(r=>r.json());
    if(providers.default_language && !localStorage.getItem("lang")){lang=providers.default_language;}
    renderOAuth();
  }catch(e){}
}

async function loadAnnouncement(){
  try{const s=await fetch("/public/settings").then(r=>r.json());
    const el=document.getElementById("announceWrap");
    if(s && s.announcement){el.innerHTML=`<div class="msg ok">📢 ${s.announcement}</div>`;}
    else{el.innerHTML="";}
  }catch(e){}
}

function switchTab(name){
  document.querySelectorAll("#appView .tab").forEach(el=>el.classList.toggle("active",el.dataset.tab===name));
  ["tokens","topup","ledger"].forEach(n=>document.getElementById("tab-"+n).classList.toggle("hidden",n!==name));
  if(name==="ledger") loadLedger();
}

async function loadMe(){
  const d=await api("/auth/me");
  document.getElementById("whoami").textContent=d.user.email||d.user.username;
  document.getElementById("statBalance").textContent=d.user.balance;
  document.getElementById("statFrozen").textContent=d.user.frozen;
}
async function loadTokens(){
  const d=await api("/auth/tokens");
  document.getElementById("statTokens").textContent=d.tokens.length;
  document.getElementById("tokenRows").innerHTML=d.tokens.map(tk=>
    `<tr><td>${tk.id}</td><td>${tk.name}</td><td class="mono">${tk.key}</td>
     <td>${tk.used_tokens}</td>
     <td><button class="btn sm danger" onclick="delToken(${tk.id})">${t("delete")}</button></td></tr>`).join("");
}
async function createToken(){
  const name=document.getElementById("newTokenName").value.trim()||"token";
  await api("/auth/tokens",{method:"POST",body:JSON.stringify({name})});
  document.getElementById("newTokenName").value="";
  loadTokens();
}
async function delToken(id){await api("/auth/tokens/"+id,{method:"DELETE"});loadTokens();}

async function loadPayMethods(){
  try{const d=await fetch("/pay/methods",{headers:H()}).then(r=>r.json());
    document.getElementById("payMethod").innerHTML=(d.methods||[]).map(m=>`<option>${m}</option>`).join("")||`<option value="">-</option>`;
  }catch(e){}
}
async function redeem(){
  const code=document.getElementById("redeemCode").value.trim();
  try{const d=await api("/pay/redeem",{method:"POST",body:JSON.stringify({code})});
    showMsg("redeemMsg",t("redeemOk").replace("%s",d.credited),true);
    document.getElementById("redeemCode").value="";loadMe();
  }catch(e){showMsg("redeemMsg",e,false);}
}
async function createOrder(){
  const method=document.getElementById("payMethod").value;
  const amt=parseFloat(document.getElementById("payAmount").value||"0");
  // 法币按分，crypto 按微 USDT
  const amount_money = method==="crypto" ? Math.round(amt*1e6) : Math.round(amt*100);
  try{const d=await api("/pay/orders",{method:"POST",body:JSON.stringify({method,amount_money})});
    let html=`Order ${d.order_no} · ${d.status}`;
    if(d.pay_url) html+=`<br/><a href="${d.pay_url}" target="_blank">${d.pay_url}</a>`;
    if(d.pay_address) html+=`<br/>Address: <span class="mono">${d.pay_address}</span>`;
    showMsg("payMsg",html,true);
  }catch(e){showMsg("payMsg",e,false);}
}
async function loadLedger(){
  const d=await api("/auth/ledger");
  document.getElementById("ledgerRows").innerHTML=d.ledger.map(e=>
    `<tr><td>${e.type}</td><td>${e.amount}</td><td>${e.balance_after}</td><td class="mono">${e.ref||""}</td></tr>`).join("");
}

async function boot(){
  applyI18n();
  loadAnnouncement();
  if(!session()){
    document.getElementById("authView").classList.remove("hidden");
    document.getElementById("appView").classList.add("hidden");
    document.getElementById("logoutBtn").classList.add("hidden");
    await loadProviders(); applyI18n();
    return;
  }
  try{
    await loadMe();
    document.getElementById("authView").classList.add("hidden");
    document.getElementById("appView").classList.remove("hidden");
    document.getElementById("logoutBtn").classList.remove("hidden");
    await Promise.all([loadTokens(),loadPayMethods()]);
  }catch(e){clearSession();boot();}
}

// OAuth 回调把 session 放在 query
(function(){const p=new URLSearchParams(location.search);const s=p.get("session");
  if(s){setSession(s);history.replaceState({},"",location.pathname);}})();
boot();
</script>
</body>
</html>
"""
