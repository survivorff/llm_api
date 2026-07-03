"""用户自助控制台（登录后仪表盘）。调用 /auth/* 与 /pay/*。

功能：邮箱注册/登录、OAuth 登录、余额/用量仪表盘、令牌自助管理、
充值（兑换码 + 在线支付）、账单明细。支持中/英双语。
视觉沿用门户设计系统（shared.base_css）。
"""
from .shared import base_css


def _portal_css() -> str:
    return base_css() + r"""
/* 控制台专属 */
.topbar{display:flex;align-items:center;justify-content:space-between;height:62px;padding:0 24px;
  background:rgba(11,13,19,.9);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:50}
.top-actions{display:flex;gap:10px;align-items:center}
.wrap{max-width:1000px;margin:28px auto;padding:0 20px}
.btn.danger{color:#fda4af;border-color:#4c2230;background:transparent}
.btn.danger:hover{background:#3a1620;border-color:#4c2230}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px}
.stat{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:20px 22px}
.stat .label{color:var(--muted);font-size:12px;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em}
.stat .value{font-size:28px;font-weight:700}
.stat .value.grad{background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.tabs{display:flex;gap:4px;margin-bottom:18px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.tab{padding:11px 18px;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;font-weight:500}
.tab:hover{color:var(--text)}
.tab.active{color:var(--text);border-bottom-color:var(--primary)}
.card{overflow:hidden;margin-bottom:18px;padding:0}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border)}
.card-head h3{margin:0;font-size:15px}
.card-body{padding:18px 20px}
input,select{background:var(--panel2);border:1px solid var(--border);color:var(--text);padding:10px 13px;border-radius:9px;font-size:14px;width:100%}
input:focus,select:focus{outline:none;border-color:var(--primary)}
label{display:block;color:var(--muted);font-size:12px;margin:10px 0 5px}
.row{display:flex;gap:12px;flex-wrap:wrap}
.row>div{flex:1;min-width:170px}
.auth-box{max-width:410px;margin:56px auto}
.oauth-btns{display:flex;flex-direction:column;gap:9px;margin-top:14px}
.divider{display:flex;align-items:center;gap:12px;color:var(--dim);font-size:12px;margin:18px 0}
.divider::before,.divider::after{content:"";flex:1;height:1px;background:var(--border)}
.keycell{display:flex;align-items:center;gap:8px}
"""


PORTAL_HTML = r"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>llm_api · 控制台</title>
<style>__CSS__</style>
</head>
<body>
<div class="topbar">
  <a href="/" class="brand" style="text-decoration:none"><span class="logo">⚡</span><span data-i18n="title">控制台</span></a>
  <div class="top-actions">
    <a href="/" class="btn sm ghost" data-i18n="backHome">返回首页</a>
    <select id="lang" class="langsel" style="width:auto" onchange="setLang(this.value)">
      <option value="zh">中文</option><option value="en">EN</option>
    </select>
    <span id="whoami" class="muted"></span>
    <button class="btn sm hidden" id="logoutBtn" onclick="logout()" data-i18n="logout">退出</button>
  </div>
</div>

<div id="announceWrap" class="wrap" style="margin-bottom:0"></div>

<!-- 登录/注册 -->
<div id="authView" class="wrap">
  <div class="auth-box card">
    <div class="card-body">
      <div class="tabs" id="authTabs" style="margin-bottom:18px">
        <div class="tab active" id="tabLogin" onclick="switchAuth('login')" data-i18n="login">登录</div>
        <div class="tab" id="tabReg" onclick="switchAuth('register')" data-i18n="register">注册</div>
      </div>
      <div id="authMsg"></div>
      <div id="oauthOnlyHint" class="hidden center" style="padding:8px 0 4px">
        <div style="font-size:16px;font-weight:600;margin-bottom:6px" data-i18n="welcome">欢迎</div>
        <div class="muted" data-i18n="oauthOnly">使用第三方账号一键登录</div>
      </div>
      <div id="emailAuthBox">
        <label data-i18n="email">邮箱</label>
        <input id="email" type="email" placeholder="you@example.com"/>
        <label data-i18n="password">密码</label>
        <input id="password" type="password" placeholder="••••••"/>
        <div id="regUsername" class="hidden">
          <label data-i18n="username">用户名（可选）</label>
          <input id="username" type="text"/>
        </div>
        <div style="margin-top:18px">
          <button class="btn primary" style="width:100%;justify-content:center" id="authSubmit" onclick="submitAuth()" data-i18n="login">登录</button>
        </div>
      </div>
      <div id="oauthArea" class="oauth-btns"></div>
    </div>
  </div>
</div>

<!-- 主界面 -->
<div id="appView" class="wrap hidden">
  <div class="stats">
    <div class="stat"><div class="label" data-i18n="balance">余额</div><div class="value grad" id="statBalance">-</div></div>
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
  zh:{title:"控制台",backHome:"返回首页",login:"登录",register:"注册",logout:"退出",email:"邮箱",password:"密码",
      username:"用户名（可选）",balance:"余额",frozen:"冻结中",tokens:"令牌",topup:"充值",ledger:"账单",
      create:"新建",used:"已用",redeem:"兑换",onlinePay:"在线充值",method:"支付方式",amount:"金额(元/USDT)",
      pay:"支付",type:"类型",balanceAfter:"余额",delete:"删除",copy:"复制",loginWith:"使用 %s 登录",
      copied:"已复制",created:"创建成功",redeemOk:"兑换成功，到账 %s credits",
      welcome:"欢迎",oauthOnly:"使用第三方账号一键登录"},
  en:{title:"Console",backHome:"Home",login:"Login",register:"Register",logout:"Logout",email:"Email",password:"Password",
      username:"Username (optional)",balance:"Balance",frozen:"Frozen",tokens:"Tokens",topup:"Top up",ledger:"Ledger",
      create:"Create",used:"Used",redeem:"Redeem",onlinePay:"Online Payment",method:"Method",amount:"Amount",
      pay:"Pay",type:"Type",balanceAfter:"Balance",delete:"Delete",copy:"Copy",loginWith:"Sign in with %s",
      copied:"Copied",created:"Created",redeemOk:"Redeemed %s credits",
      welcome:"Welcome",oauthOnly:"Sign in with a third-party account"}
};
let lang = localStorage.getItem("lang") || "zh";
if(!I18N[lang]) lang="zh";
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
  document.getElementById("authSubmit").textContent = t(mode);
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
  // 仅当邮箱登录也开启时，才显示 "OAuth" 分隔线
  if((providers.oauth||[]).length && providers.email){
    const div=document.createElement("div");div.className="divider";div.textContent="OAuth";area.appendChild(div);
  }
  (providers.oauth||[]).forEach(p=>{
    const b=document.createElement("button");
    b.className="btn primary"; b.style.justifyContent="center"; b.textContent=t("loginWith").replace("%s",p);
    b.onclick=async()=>{const d=await api("/auth/oauth/"+p);location.href=d.authorize_url;};
    area.appendChild(b);
  });
}

async function loadProviders(){
  try{providers=await fetch("/auth/providers").then(r=>r.json());
    if(providers.default_language && !localStorage.getItem("lang")){lang=providers.default_language;}
    applyEmailAuth();
    renderOAuth();
  }catch(e){}
}

// 根据后端开关决定是否显示邮箱注册/登录表单
function applyEmailAuth(){
  const on = providers && providers.email;
  const box = document.getElementById("emailAuthBox");
  const tabs = document.getElementById("authTabs");
  if(box) box.classList.toggle("hidden", !on);
  if(tabs) tabs.classList.toggle("hidden", !on);
  const hint=document.getElementById("oauthOnlyHint");
  if(hint) hint.classList.toggle("hidden", !!on);
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
    `<tr><td>${tk.id}</td><td>${tk.name}</td>
     <td><div class="keycell"><span class="mono">${tk.key}</span>
       <button class="btn sm" onclick="copyKey('${tk.key}')">${t("copy")}</button></div></td>
     <td>${tk.used_tokens}</td>
     <td><button class="btn sm danger" onclick="delToken(${tk.id})">${t("delete")}</button></td></tr>`).join("");
}
function copyKey(k){navigator.clipboard.writeText(k);}
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

(function(){const p=new URLSearchParams(location.search);const s=p.get("session");
  if(s){setSession(s);history.replaceState({},"",location.pathname);}})();
boot();
</script>
</body>
</html>
""".replace("__CSS__", _portal_css())


def portal_html() -> str:
    return PORTAL_HTML
