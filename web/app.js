const T = {
  en: {
    demo_note: "You are exploring the demo shop: Lakshmi Medicals, Mylapore, Chennai. Everything here is live.",
    create_shop: "Create your shop, free", reset_demo: "Reset demo", login: "Log in", logout: "Log out",
    sales_import: "Import sales (CSV)", sales_template: "CSV template", f_shop: "Shop name", f_area: "Area / city", f_pw: "Password",
    a_need_sales: "Add sales data",
    hero_title: "Sell it before it expires.",
    hero_lede: "ShelfMitra reads your distributor invoices, predicts which medicines will still be on the shelf when the return window closes, and reminds you in time to send them back.",
    k_rupees: "Money at risk", k_rupees_sub: "stock likely unsold by the return cutoff",
    k_return: "Return now", k_return_sub: "batches inside their last 45 days", k_watch: "Batches watched",
    ask_title: "Ask ShelfMitra", ask_hint: "Tamil, Hindi or English", chat_empty: "Ask about expiry, returns or how much to reorder.", ask_btn: "Ask", ask_ph: "Which medicines should I return this week?",
    inv_title: "Add a distributor invoice", inv_drop: "Drop a photo of the invoice",
    inv_drop_sub: "or tap to take one. Batch, expiry and quantity are read for you, and every line is checked.",
    inv_sample: "Try a sample invoice", shelf_title: "Your shelf, by money at risk", msg_btn: "Message distributor",
    c_product: "Medicine", c_expiry: "Expiry", c_cutoff: "Return by", c_qty: "On hand", c_risk: "Risk", c_rupees: "₹ at risk", c_action: "What to do",
    wf_title: "Watching every batch", log_title: "What happened",
    foot_note: "Risk is a prediction, not a guarantee. Always check the physical stock before returning it.",
    a_return_now: "Return now", a_stop_reorder: "Stop reordering", a_watch: "Watch", a_ok: "Fine", a_window_closed: "Window closed",
    days_left: "days left", returned: "Returned", sold: "Sold", pick_first: "Tick the batches to return first.",
    examples: ["Which medicines should I return this week?", "Should I order 40 more Allegra 120?", "How much money is at risk?"],
  },
  ta: {
    demo_note: "நீங்கள் மாதிரி கடையைப் பார்க்கிறீர்கள்: லக்ஷ்மி மெடிக்கல்ஸ், மயிலாப்பூர், சென்னை. இங்குள்ள அனைத்தும் நேரலை.",
    create_shop: "உங்கள் கடையை இலவசமாக உருவாக்குங்கள்", reset_demo: "மாதிரியை மீட்டமை", login: "உள்நுழை", logout: "வெளியேறு",
    sales_import: "விற்பனை CSV சேர்க்க", sales_template: "CSV மாதிரி", f_shop: "கடையின் பெயர்", f_area: "பகுதி / நகரம்", f_pw: "கடவுச்சொல்",
    a_need_sales: "விற்பனை தரவு தேவை",
    hero_title: "காலாவதிக்கு முன் விற்றுவிடுங்கள்.",
    hero_lede: "விநியோகஸ்தர் பில்லை ShelfMitra படிக்கிறது, திருப்பி அனுப்பும் காலம் முடியும்போது எந்த மருந்துகள் விற்காமல் இருக்கும் என்று கணிக்கிறது, நேரத்தில் உங்களுக்கு நினைவூட்டுகிறது.",
    k_rupees: "ஆபத்தில் உள்ள பணம்", k_rupees_sub: "திருப்பும் கடைசி நாளுக்குள் விற்காத சரக்கு",
    k_return: "இப்போதே திருப்புங்கள்", k_return_sub: "கடைசி 45 நாட்களில் உள்ள பேட்ச்கள்", k_watch: "கண்காணிப்பில் பேட்ச்கள்",
    ask_title: "ShelfMitra-விடம் கேளுங்கள்", ask_hint: "தமிழ், இந்தி அல்லது ஆங்கிலம்", chat_empty: "காலாவதி, திருப்பி அனுப்புதல் அல்லது எவ்வளவு ஆர்டர் செய்வது என்று கேளுங்கள்.", ask_btn: "கேள்", ask_ph: "இந்த வாரம் எதை திருப்பி அனுப்பணும்?",
    inv_title: "விநியோகஸ்தர் பில் சேர்க்கவும்", inv_drop: "பில்லின் புகைப்படத்தை இங்கே விடுங்கள்",
    inv_drop_sub: "அல்லது தொட்டு புகைப்படம் எடுங்கள். பேட்ச், காலாவதி, அளவு தானாகப் படிக்கப்பட்டு ஒவ்வொரு வரியும் சரிபார்க்கப்படும்.",
    inv_sample: "மாதிரி பில்லை முயற்சிக்கவும்", shelf_title: "உங்கள் அலமாரி, ஆபத்துத் தொகைப்படி", msg_btn: "விநியோகஸ்தருக்கு செய்தி",
    c_product: "மருந்து", c_expiry: "காலாவதி", c_cutoff: "திருப்ப கடைசி நாள்", c_qty: "கையிருப்பு", c_risk: "ஆபத்து", c_rupees: "₹ ஆபத்தில்", c_action: "என்ன செய்வது",
    wf_title: "ஒவ்வொரு பேட்சும் கண்காணிப்பில்", log_title: "நடந்தவை",
    foot_note: "ஆபத்து என்பது கணிப்பு மட்டுமே. திருப்புவதற்கு முன் கையிருப்பை நேரில் சரிபாருங்கள்.",
    a_return_now: "இப்போதே திருப்புங்கள்", a_stop_reorder: "மீண்டும் ஆர்டர் வேண்டாம்", a_watch: "கவனியுங்கள்", a_ok: "சரியாக உள்ளது", a_window_closed: "காலம் முடிந்தது",
    days_left: "நாட்கள் உள்ளன", returned: "திருப்பியது", sold: "விற்றது", pick_first: "முதலில் திருப்ப வேண்டிய பேட்ச்களை தேர்வு செய்யுங்கள்.",
    examples: ["இந்த வாரம் எதை திருப்பி அனுப்பணும்?", "Allegra 120 இன்னும் 40 ஆர்டர் செய்யலாமா?", "எவ்வளவு பணம் ஆபத்தில் உள்ளது?"],
  },
  hi: {
    demo_note: "आप डेमो दुकान देख रहे हैं: लक्ष्मी मेडिकल्स, मायलापुर, चेन्नई। यहाँ सब कुछ लाइव है।",
    create_shop: "अपनी दुकान मुफ़्त बनाएँ", reset_demo: "डेमो रीसेट करें", login: "लॉग इन", logout: "लॉग आउट",
    sales_import: "बिक्री CSV जोड़ें", sales_template: "CSV नमूना", f_shop: "दुकान का नाम", f_area: "इलाका / शहर", f_pw: "पासवर्ड",
    a_need_sales: "बिक्री डेटा जोड़ें",
    hero_title: "एक्सपायरी से पहले बेच दीजिए।",
    hero_lede: "ShelfMitra आपके डिस्ट्रीब्यूटर बिल पढ़ता है, अनुमान लगाता है कि रिटर्न की समय-सीमा खत्म होने तक कौन सी दवाएँ बिना बिके रह जाएँगी, और समय पर याद दिलाता है।",
    k_rupees: "जोखिम में पैसा", k_rupees_sub: "रिटर्न की आखिरी तारीख तक न बिकने वाला स्टॉक",
    k_return: "अभी लौटाएँ", k_return_sub: "आखिरी 45 दिनों वाले बैच", k_watch: "निगरानी में बैच",
    ask_title: "ShelfMitra से पूछिए", ask_hint: "तमिल, हिंदी या अंग्रेज़ी", chat_empty: "एक्सपायरी, वापसी या कितना ऑर्डर करें, यह पूछिए।", ask_btn: "पूछें", ask_ph: "इस हफ्ते कौन सी दवाएँ लौटानी हैं?",
    inv_title: "डिस्ट्रीब्यूटर का बिल जोड़ें", inv_drop: "बिल की फ़ोटो यहाँ डालें",
    inv_drop_sub: "या टैप करके फ़ोटो लें। बैच, एक्सपायरी और मात्रा अपने आप पढ़ी जाती है, और हर लाइन जाँची जाती है।",
    inv_sample: "नमूना बिल आज़माएँ", shelf_title: "आपकी शेल्फ, जोखिम वाली रकम के क्रम में", msg_btn: "डिस्ट्रीब्यूटर को मैसेज",
    c_product: "दवा", c_expiry: "एक्सपायरी", c_cutoff: "लौटाने की आखिरी तारीख", c_qty: "स्टॉक", c_risk: "जोखिम", c_rupees: "₹ जोखिम में", c_action: "क्या करें",
    wf_title: "हर बैच पर नज़र", log_title: "क्या हुआ",
    foot_note: "जोखिम एक अनुमान है, गारंटी नहीं। लौटाने से पहले स्टॉक खुद जाँच लें।",
    a_return_now: "अभी लौटाएँ", a_stop_reorder: "दोबारा ऑर्डर न करें", a_watch: "नज़र रखें", a_ok: "ठीक है", a_window_closed: "समय खत्म",
    days_left: "दिन बाकी", returned: "लौटा दिया", sold: "बिक गया", pick_first: "पहले लौटाने वाले बैच चुनें।",
    examples: ["इस हफ्ते कौन सी दवाएँ लौटानी हैं?", "क्या Allegra 120 के 40 और ऑर्डर करूँ?", "कितना पैसा जोखिम में है?"],
  },
};

let lang = localStorage.getItem("sm-lang") || "en";
let data = null;
const $ = (s) => document.querySelector(s);
const rupees = (n) => "₹" + Math.round(n).toLocaleString("en-IN");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmtDate = (iso) => { const [y, m, d] = iso.split("-"); return `${d}/${m}/${y}`; };

function applyLang() {
  document.body.className = lang === "en" ? "" : lang;
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-t]").forEach((el) => { if (T[lang][el.dataset.t]) el.textContent = T[lang][el.dataset.t]; });
  document.querySelectorAll("[data-tp]").forEach((el) => { el.placeholder = T[lang][el.dataset.tp]; });
  document.querySelectorAll(".lang button").forEach((b) => b.classList.toggle("on", b.dataset.lang === lang));
  $("#msg-lang").value = lang;
  $("#examples").innerHTML = T[lang].examples.map((q) => `<button class="chip-q">${esc(q)}</button>`).join("");
  if (data) render();
}

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
}

function render() {
  const t = T[lang];
  $("#shop").textContent = data.shop;
  $("#demo-bar").hidden = !data.demo;
  $("#k-rupees").textContent = rupees(data.totals.rupees_at_risk);
  $("#k-return").textContent = data.totals.return_now;
  $("#k-batches").textContent = data.totals.batches;
  $("#k-engine").textContent = data.engine === "tabpfn" ? "TabPFN-3.5" : "straight-line rule";
  $("#badges").innerHTML =
    `<span class="badge ${data.engine === "tabpfn" ? "" : "off"}">${data.engine === "tabpfn" ? "TabPFN-3.5" : "Rule only"}</span>` +
    `<span class="badge ${data.temporal ? "" : "off"}">${data.temporal ? "Temporal on" : "Temporal off"}</span>`;
  const tb = $("#rows");
  tb.innerHTML = "";
  for (const b of data.batches) {
    const tr = document.querySelector("#tpl-row").content.firstElementChild.cloneNode(true);
    tr.dataset.id = b.id;
    tr.querySelector(".p").textContent = b.product;
    tr.querySelector(".b").textContent = `Batch ${b.batch} · ${b.distributor || ""}`;
    if (b.composition) { const c = document.createElement("small"); c.className = "comp"; c.textContent = b.composition; tr.querySelector(".b").after(c); }
    tr.querySelector(".exp").textContent = fmtDate(b.expiry);
    const cut = tr.querySelector(".cut");
    cut.innerHTML = `${fmtDate(b.return_cutoff)}<span class="days">${b.days_to_cutoff} ${t.days_left}</span>`;
    if (b.days_to_cutoff <= 45) cut.classList.add("soon");
    tr.querySelector(".qty").textContent = b.qty_on_hand;
    const bar = tr.querySelector(".bar");
    bar.querySelector("i").style.width = Math.round(b.risk * 100) + "%";
    bar.classList.add(b.risk >= 0.6 ? "hot" : b.risk >= 0.3 ? "mid" : "low");
    tr.querySelector(".rp").textContent = b.no_sales ? "–" : Math.round(b.risk * 100) + "%";
    tr.querySelector(".rs").textContent = b.rupees_at_risk ? rupees(b.rupees_at_risk) : "–";
    const act = tr.querySelector(".act");
    act.textContent = t["a_" + b.action] || b.action;
    act.classList.add(b.action);
    if (b.action === "return_now") tr.querySelector(".pick").checked = true;
    tr.querySelectorAll(".dec button").forEach((btn) => {
      btn.textContent = t[btn.dataset.d];
      btn.onclick = async () => { btn.disabled = true; await api("/api/decision", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ batch_id: b.id, decision: btn.dataset.d }) }); setTimeout(load, 600); };
    });
    tb.appendChild(tr);
  }
  if (!data.batches.length) tb.innerHTML = `<tr><td colspan="9" class="muted">No batches yet. Add an invoice above.</td></tr>`;
  $("#events").innerHTML = data.events.map((e) => {
    const d = JSON.parse(e.detail || "{}");
    const txt = { received: `Received ${d.qty} (invoice ${d.invoice})`, checkpoint: `Checked: ${d.days_left} days left, risk ${Math.round(d.risk * 100)}%`,
      reminder: `Reminder sent: ${d.days_left} days left`, decision: `Marked ${d.decision}`, window_closed: `Return window closed, ${d.still_on_hand} still on hand` }[e.kind] || e.kind;
    const name = (data.batches.find((x) => x.id === e.batch_id) || {}).product || (e.batch_id ? `Batch #${e.batch_id}` : "");
    return `<li><time>${esc(e.at.slice(5, 16))}</time><span><b>${esc(name)}</b> ${esc(txt)}</span></li>`;
  }).join("") || `<li class="muted">Nothing yet.</li>`;
}

async function load() {
  data = await api("/api/dashboard");
  render();
  loadWorkflows();
}

async function loadWorkflows() {
  const w = await api("/api/workflows").catch(() => ({ temporal: false, workflows: [] }));
  const box = $("#workflows");
  if (!w.temporal) { box.innerHTML = `<div class="muted">Temporal is off in this deployment, so reminders run from the dashboard only.</div>`; return; }
  box.innerHTML = w.workflows.map((x) => {
    const name = (data.batches.find((b) => b.id === x.batch_id) || {}).product || `Batch #${x.batch_id}`;
    return `<div class="wf-row"><span><b>${esc(name)}</b></span><span>${esc(x.stage || x.status)}${x.last_risk != null ? ` · risk ${Math.round(x.last_risk * 100)}%` : ""}</span></div>`;
  }).join("") || `<div class="muted">No workflows yet.</div>`;
}

// Ask ShelfMitra
function bubble(cls, html) {
  const chat = $("#chat");
  chat.querySelector(".empty-chat")?.remove();
  const d = document.createElement("div");
  d.className = "msg " + cls;
  d.innerHTML = html;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}
async function ask(q) {
  if (!q.trim()) return;
  bubble("me", esc(q));
  const wait = bubble("bot", `<span class="spin"></span>`);
  try {
    const r = await api("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) });
    const tools = r.trace.map((x) => `<span class="tool">${esc(x.tool)}</span>`).join("");
    wait.innerHTML = esc(r.answer).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/^\s*\|?[-| :]+\|\s*$/gm, "") + (tools ? `<div class="tools">${tools}</div>` : "");
  } catch (e) { wait.textContent = "Sorry, that did not work: " + e.message.slice(0, 160); }
}
$("#ask-form").onsubmit = (e) => { e.preventDefault(); const q = $("#ask-input").value; $("#ask-input").value = ""; ask(q); };
$("#examples").onclick = (e) => { if (e.target.classList.contains("chip-q")) ask(e.target.textContent); };

// Invoice
async function sendInvoice(blob, name) {
  const out = $("#inv-result");
  out.innerHTML = `<div class="inv-box"><span class="spin"></span> Reading ${esc(name)}…</div>`;
  const fd = new FormData();
  fd.append("file", blob, name);
  try {
    const r = await api("/api/invoice", { method: "POST", body: fd });
    const rows = r.lines.map((l) => `<tr><td>${esc(l.product)}</td><td>${esc(l.batch)}</td><td>${l.expiry ? fmtDate(l.expiry) : "?"}</td><td>${l.qty ?? "?"}</td><td>${l.needs_review ? `<span class="flag">${esc(l.issues.join("; "))}</span>` : `<span class="okk">✓</span>`}</td></tr>`).join("");
    out.innerHTML = `<div class="inv-box"><b>${esc(r.distributor || "")}</b> · ${esc(r.invoice_no || "")}<br><small class="muted">${esc(r.return_policy || "")}</small>
      <table><tr><th>Medicine</th><th>Batch</th><th>Expiry</th><th>Qty</th><th></th></tr>${rows}</table>
      <span class="muted">${r.ok} lines checked, ${r.review} need a look.</span> <button class="btn primary small" id="inv-ok">Add ${r.ok} to shelf</button></div>`;
    $("#inv-ok").onclick = async () => {
      const lines = r.lines.filter((l) => !l.needs_review).map((l) => ({ product: l.product, pack: l.pack, batch: l.batch, expiry: l.expiry, qty: l.qty, rate: l.rate, mrp: l.mrp }));
      const res = await api("/api/invoice/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ distributor: r.distributor, invoice_no: r.invoice_no, return_policy: r.return_policy, lines }) });
      out.innerHTML = `<div class="inv-box okk">Added ${res.saved} batches. Return window: ${res.return_window_days} days before expiry.</div>`;
      load();
    };
  } catch (e) { out.innerHTML = `<div class="inv-box flag">Could not read the invoice: ${esc(e.message.slice(0, 200))}</div>`; }
}
$("#file").onchange = (e) => e.target.files[0] && sendInvoice(e.target.files[0], e.target.files[0].name);
const drop = $("#drop");
["dragover", "dragenter"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => e.dataTransfer.files[0] && sendInvoice(e.dataTransfer.files[0], e.dataTransfer.files[0].name));
$("#sample").onclick = async () => sendInvoice(await (await fetch("/static/invoice_sample.jpg")).blob(), "sample invoice");

// Distributor message
$("#msg-btn").onclick = async () => {
  const ids = [...document.querySelectorAll("#rows tr")].filter((tr) => tr.querySelector(".pick")?.checked).map((tr) => +tr.dataset.id);
  if (!ids.length) { $("#msg-out").innerHTML = `<div class="out muted">${T[lang].pick_first}</div>`; return; }
  $("#msg-out").innerHTML = `<div class="out"><span class="spin"></span></div>`;
  const r = await api("/api/message", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ batch_ids: ids, lang: $("#msg-lang").value }) });
  $("#msg-out").innerHTML = `<div class="out"><pre>${esc(r.text)}</pre><a class="btn primary" href="${r.whatsapp}" target="_blank" rel="noopener">Open in WhatsApp</a></div>`;
};

// Accounts
let me = null, authMode = "signup";
async function loadMe() {
  me = await api("/api/me");
  const t = T[lang];
  $("#acct").innerHTML = me.demo
    ? `<button class="btn small ghost" data-open="login">${t.login}</button>`
    : `<span class="who">${esc(me.name)}</span><button class="btn small ghost" id="logout">${t.logout}</button>`;
  $("#logout")?.addEventListener("click", async () => { await api("/api/auth/logout", { method: "POST" }); location.reload(); });
}
function openAuth(mode) {
  authMode = mode;
  const signup = mode === "signup";
  $("#auth-title").textContent = signup ? "Create your shop" : "Log in to your shop";
  $("#auth-sub").textContent = signup ? "Free while in beta. Your stock data stays in its own private database." : "Welcome back.";
  $("#f-shop").hidden = $("#f-area").hidden = !signup;
  $("#auth-go").textContent = signup ? "Create shop" : "Log in";
  $("#auth-switch").textContent = signup ? "Already have an account? Log in" : "New here? Create your shop";
  $("#auth-err").textContent = "";
  $("#auth-dlg").showModal();
}
document.addEventListener("click", (e) => { const m = e.target.closest("[data-open]"); if (m) { e.preventDefault(); openAuth(m.dataset.open); } });
$("#auth-switch").onclick = (e) => { e.preventDefault(); openAuth(authMode === "signup" ? "login" : "signup"); };
$("#auth-form").addEventListener("submit", async (e) => {
  if (e.submitter && e.submitter.value === "cancel") return;
  e.preventDefault();
  const f = Object.fromEntries(new FormData(e.target));
  const body = authMode === "signup" ? { email: f.email, password: f.password, shop_name: f.shop_name || "", area: f.area || "" } : { email: f.email, password: f.password };
  try {
    await api(`/api/auth/${authMode}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    location.reload();
  } catch (err) {
    let msg = err.message; try { msg = JSON.parse(msg).detail || msg; } catch (_) {}
    $("#auth-err").textContent = typeof msg === "string" ? msg : "Please check the form.";
  }
});
$("#reset-demo").onclick = async () => { await api("/api/demo/reset", { method: "POST" }).catch(() => {}); load(); };
$("#sales-file").onchange = async (e) => {
  const fd = new FormData(); fd.append("file", e.target.files[0]);
  const out = $("#inv-result");
  try { const r = await api("/api/sales", { method: "POST", body: fd }); out.innerHTML = `<div class="inv-box okk">Imported ${r.rows} sales rows.</div>`; load(); }
  catch (err) { out.innerHTML = `<div class="inv-box flag">${esc(err.message.slice(0, 200))}</div>`; }
};

document.querySelectorAll(".lang button").forEach((b) => (b.onclick = () => { lang = b.dataset.lang; localStorage.setItem("sm-lang", lang); applyLang(); loadMe(); }));
$("#chat").innerHTML = `<div class="empty-chat" data-t="chat_empty">Ask about expiry, returns or how much to reorder.</div>`;
applyLang();
loadMe();
load();
setInterval(load, 15000);
