/* سَنَد — منطق الواجهة
   الصفحات: فحص الملفات (#/)، نتيجة الفحص (#/results)، المراقبة الدورية (#/monitor)، الخصوصية (#/privacy) */

// ============ أدوات ============
const $ = (s, root = document) => root.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => Number(n || 0).toLocaleString("en-US");
const errText = (detail, fallback) => (typeof detail === "string" && detail ? detail : fallback);
const filesAr = (n) => n === 1 ? "ملف واحد" : n === 2 ? "ملفين" : n <= 10 ? `${n} ملفات` : `${fmt(n)} ملف`;
const notesAr = (n) => n === 0 ? "لا توجد" : n === 1 ? "ملاحظة واحدة" : n === 2 ? "ملاحظتان" : n <= 10 ? `${n} ملاحظات` : `${fmt(n)} ملاحظة`;
function whereAr(withPii, total) {
  if (withPii === total) return total === 1 ? "في الملف" : total === 2 ? "في الملفين" : `في كل الملفات الـ${fmt(total)}`;
  return `في ${filesAr(withPii)} من أصل ${fmt(total)}`;
}
function sizeAr(b) {
  if (b < 1024) return `${b} بايت`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} كيلوبايت`;
  return `${(b / 1024 / 1024).toFixed(1)} ميجابايت`;
}
const pad = (n) => String(n).padStart(2, "0");
function dateAr(iso, withTime = false) {
  const d = iso instanceof Date ? iso : new Date(iso);
  if (isNaN(d)) return "";
  const day = `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
  return withTime ? `${day} · ${pad(d.getHours())}:${pad(d.getMinutes())}` : day;
}

const ICON = {
  file: '<svg viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  high: '<svg viewBox="0 0 24 24"><path d="M8.3 3h7.4L21 8.3v7.4L15.7 21H8.3L3 15.7V8.3z"/><path d="M12 8v4.5M12 16h.01"/></svg>',
  medium: '<svg viewBox="0 0 24 24"><path d="M10.3 4.2L2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/><path d="M12 9.5v4M12 17h.01"/></svg>',
  low: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>',
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>',
  warn: '<svg viewBox="0 0 24 24"><path d="M10.3 4.2L2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/><path d="M12 9.5v4M12 17h.01"/></svg>',
  error: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.5h.01"/></svg>',
};

// مستويات الخطورة: لون + أيقونة + نص (ما نعتمد على اللون وحده)
const RISK = {
  "عالية": { cls: "r-high", row: "high", icon: ICON.high },
  "متوسطة": { cls: "r-medium", row: "medium", icon: ICON.medium },
  "منخفضة": { cls: "r-low", row: "low", icon: ICON.low },
};
const RISK_ORDER = ["عالية", "متوسطة", "منخفضة"];
const CAT = { "بيانات شخصية": "c-personal", "بيانات حساسة": "c-sensitive", "بيانات ائتمانية": "c-credit" };
const badge = (cls, icon, text) => `<span class="badge ${cls}">${icon}${esc(text)}</span>`;
const riskBadge = (r) => badge(RISK[r]?.cls || "r-low", RISK[r]?.icon || "", `خطورة ${r}`);
const catBadge = (c) => badge(CAT[c] || "c-personal", "", c);
const LEVEL_TAG = { high: "عاجل", medium: "مهم", info: "تنظيمي" };

// ============ التنقل ============
const VIEWS = {
  "": { view: "scan", nav: "scan", crumbs: [["الرئيسية"], ["فحص الملفات"]] },
  results: { view: "results", nav: "scan", crumbs: [["الرئيسية", "#/"], ["فحص الملفات", "#/"], ["نتيجة الفحص"]] },
  monitor: { view: "monitor", nav: "monitor", crumbs: [["الرئيسية", "#/"], ["المراقبة الدورية"]] },
  privacy: { view: "privacy", nav: "privacy", crumbs: [["الرئيسية", "#/"], ["الخصوصية ومعالجة الملفات"]] },
};
let currentScan = null;

function route() {
  let key = location.hash.replace(/^#\/?/, "");
  if (!(key in VIEWS)) key = "";
  if (key === "results" && !currentScan) { location.replace("#/"); return; }
  const v = VIEWS[key];
  document.querySelectorAll(".view").forEach((el) => el.classList.toggle("active", el.id === `view-${v.view}`));
  document.querySelectorAll(".mainnav a").forEach((a) => {
    if (a.dataset.nav === v.nav) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  $("#crumbs").innerHTML = v.crumbs.map(([label, href], i) => i === v.crumbs.length - 1
    ? `<li><span aria-current="page">${label}</span></li>`
    : `<li><a href="${href || "#/"}">${label}</a></li>`).join("");
  document.title = `سَنَد | ${v.crumbs[v.crumbs.length - 1][0]}`;
  window.scrollTo({ top: 0 });
  if (v.view === "monitor") loadMonitor();
}
window.addEventListener("hashchange", route);

// ============ حالة النظام ============
async function loadStatus() {
  const box = $("#sys-status"), text = $(".status-text", box);
  try {
    const d = await (await fetch("/api/status")).json();
    box.className = "system-status " + (d.model ? "ok" : "partial");
    text.textContent = d.model ? "النظام يعمل" : "الفحص متاح · المساعد غير متاح";
    box.title = d.model ? "" : "النموذج المحلي (Ollama) غير شغّال: لن تُكتشف الأسماء، ولن يجيب المساعد على الأسئلة.";
  } catch {
    box.className = "system-status";
    text.textContent = "تعذّر الاتصال بالخادم";
  }
}

// ============ اختيار الملفات ============
const ALLOWED = ["csv", "xlsx", "docx", "pdf", "jsonl", "txt"];
const MAX_FILES = 10, MAX_BYTES = 50 * 1024 * 1024;
let picked = [];        // [{file, error}]
let lastSent = [];      // آخر ملفات أُرسلت (لإعادة المحاولة)

function validate() {
  const seen = new Set();
  let validCount = 0;
  picked.forEach((p) => {
    const ext = (p.file.name.split(".").pop() || "").toLowerCase();
    const key = p.file.name + "|" + p.file.size;
    p.error = !ALLOWED.includes(ext) ? "صيغة غير مدعومة"
      : p.file.size === 0 ? "الملف فارغ"
      : p.file.size > MAX_BYTES ? "أكبر من 50 ميجابايت"
      : seen.has(key) ? "مكرر"
      : validCount >= MAX_FILES ? `تجاوز الحد (${MAX_FILES} ملفات)` : "";
    seen.add(key);
    if (!p.error) validCount++;
  });
  return validCount;
}

function renderPicked() {
  const valid = validate();
  $("#file-list").innerHTML = picked.map((p, i) => `
    <li class="file-item${p.error ? " invalid" : ""}">
      <span class="file-ico">${p.error ? ICON.error : ICON.file}</span>
      <span><bdi class="file-name">${esc(p.file.name)}</bdi>
        <span class="file-meta">${sizeAr(p.file.size)}${p.error ? ` · ${p.error}` : ""}</span></span>
      <button type="button" class="icon-btn" data-remove="${i}" aria-label="إزالة ${esc(p.file.name)}">${ICON.x}</button>
    </li>`).join("");
  const invalid = picked.length - valid;
  $("#start").disabled = valid === 0;
  $("#clear").hidden = picked.length === 0;
  $("#start-hint").textContent = valid === 0
    ? (picked.length ? "لا يوجد ملف صالح للفحص. أزل الملفات غير المدعومة أو أضف ملفات أخرى." : "اختر ملفًا واحدًا على الأقل لبدء الفحص.")
    : `جاهز لفحص ${filesAr(valid)}${invalid ? `، وسيتم تجاهل ${invalid === 1 ? "ملف واحد غير صالح" : invalid === 2 ? "ملفين غير صالحين" : `${filesAr(invalid)} غير صالحة`}` : ""}.`;
}

function addFiles(list) {
  picked = picked.concat([...list].map((file) => ({ file, error: "" })));
  renderPicked();
}

const drop = $("#drop"), input = $("#file");
["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "dragend"].forEach((t) => drop.addEventListener(t, () => drop.classList.remove("over")));
drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files); });
$("#pick-btn").addEventListener("click", (e) => { e.stopPropagation(); input.click(); });
drop.addEventListener("click", () => input.click());
input.addEventListener("change", () => { if (input.files.length) addFiles(input.files); input.value = ""; });
$("#file-list").addEventListener("click", (e) => {
  const b = e.target.closest("[data-remove]");
  if (!b) return;
  picked.splice(Number(b.dataset.remove), 1);
  renderPicked();
  $("#start").disabled ? $("#pick-btn").focus() : $("#start").focus();
});
$("#clear").addEventListener("click", () => { picked = []; renderPicked(); });
$("#start").addEventListener("click", () => {
  validate();
  const files = picked.filter((p) => !p.error).map((p) => p.file);
  if (files.length) startScan(files);
});
$("#retry").addEventListener("click", () => lastSent.length && startScan(lastSent));
$("#repick").addEventListener("click", () => showUpload("pick"));

function showUpload(state) {
  ["pick", "progress", "error"].forEach((s) => ($(`#upload-${s}`).hidden = s !== state));
}

// ============ الفحص ============
function setStep(name, cls) {
  const li = $(`#steps [data-step="${name}"]`);
  if (li) li.className = cls;
}

function startScan(files) {
  lastSent = files;
  showUpload("progress");
  document.querySelectorAll("#steps li").forEach((li) => (li.className = ""));
  setStep("upload", "doing");
  const bar = $("#prog-bar"), label = $("#prog-label"), prog = $("#upload-progress .progress");
  prog.classList.remove("indeterminate");
  bar.style.width = "0%";
  label.textContent = "جاري رفع الملفات…";

  const body = new FormData();
  files.forEach((f) => body.append("files", f));
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/scan");
  xhr.responseType = "json";
  xhr.upload.onprogress = (e) => {
    if (!e.lengthComputable) return;
    const p = Math.round((e.loaded / e.total) * 100);
    bar.style.width = p + "%";
    label.textContent = `جاري رفع الملفات… ${p}%`;
  };
  xhr.upload.onload = () => {
    setStep("upload", "done");
    setStep("analyze", "doing");
    prog.classList.add("indeterminate");
    label.textContent = `جاري تحليل ${filesAr(files.length)}…`;
  };
  xhr.onload = () => {
    const d = xhr.response || {};
    if (xhr.status >= 200 && xhr.status < 300) {
      setStep("analyze", "done"); setStep("results", "done");
      currentScan = d;
      currentScan.at = new Date();
      renderResults(d);
      picked = []; renderPicked(); showUpload("pick");
      location.hash = "#/results";
    } else {
      fail(errText(d.detail, "تعذّر فحص الملفات."));
    }
  };
  xhr.onerror = () => fail("تعذّر الاتصال بالخادم. تأكد أن الخدمة تعمل ثم أعد المحاولة.");
  xhr.send(body);
}

function fail(msg) {
  $("#error-text").textContent = msg;
  showUpload("error");
  $("#retry").focus();
}

// ============ نتيجة الفحص ============
const sumRows = (list) => list.reduce((a, x) => a + x.rows, 0);

function renderResults(d) {
  const f = d.findings;
  const ok = d.files.filter((x) => !x.error), bad = d.files.filter((x) => x.error);
  const filesWith = new Set(f.map((x) => x.file)).size;
  const total = sumRows(f);
  const sensitive = sumRows(f.filter((x) => x.category === "بيانات حساسة"));

  $("#res-meta").textContent = `تاريخ الفحص: ${dateAr(d.at || new Date(), true)} · ${filesAr(d.files.length)}`;
  $("#report-btn").href = `/report?scan=${encodeURIComponent(d.scan_id)}`;

  let alerts = f.length
    ? `<div class="alert alert-warning" role="status">${ICON.warn}<div>
        <h2>تم العثور على مؤشرات بيانات شخصية</h2>
        <p>تم العثور على ${fmt(total)} معلومة شخصية ${whereAr(filesWith, ok.length)}${sensitive ? `، منها ${fmt(sensitive)} معلومة حساسة` : ""}. راجع الملاحظات قبل مشاركة ${ok.length === 1 ? "الملف" : "الملفات"}.</p></div></div>`
    : `<div class="alert alert-info" role="status">${ICON.info}<div>
        <h2>لم يتم العثور على مؤشرات مطابقة</h2>
        <p>لم يتم العثور على أي من أنواع البيانات الشخصية التي تكشفها الخدمة.</p>
        <p class="note">هذا لا يعني أن ${ok.length === 1 ? "الملف خالٍ" : "الملفات خالية"} تمامًا من البيانات الشخصية؛ يُنصح بالمراجعة قبل المشاركة.</p></div></div>`;
  if (bad.length) alerts += `<div class="alert alert-danger" role="alert">${ICON.error}<div>
      <h2>تعذّرت قراءة ${filesAr(bad.length)}</h2>
      <p>${bad.map((x) => `<bdi>${esc(x.name)}</bdi>: ${esc(x.error)}`).join("، ")}.</p></div></div>`;
  $("#res-alert").innerHTML = alerts;

  $("#stats").innerHTML = [
    [fmt(ok.length), "الملفات التي تم فحصها"],
    [fmt(d.records), "السجلات التي تم فحصها"],
    [fmt(total), "المعلومات الشخصية المكتشفة"],
    [fmt(sensitive), "المعلومات الحساسة المكتشفة"],
  ].map(([v, l]) => `<div class="stat"><div class="stat-label">${l}</div><div class="stat-value">${v}</div></div>`).join("");

  $("#res-body").hidden = !f.length;
  if (f.length) {
    renderRiskSummary("#risk-summary", f);
    renderTypes("#types", f);
    renderFindings("#findings", "#risk-filter", f);
    renderRecs("#recs", d.recommendations);
  }

  $("#files-table").innerHTML = `<thead><tr><th>الملف</th><th>المحتوى</th><th>السجلات</th><th>النتيجة</th></tr></thead><tbody>` +
    d.files.map((x) => `<tr>
      <td><bdi>${esc(x.name)}</bdi></td>
      <td>${x.error ? "—" : x.is_text ? "نص" : `${fmt(x.sheets)} ${x.sheets === 1 ? "جدول" : "جداول"} · ${fmt(x.columns)} عمود`}</td>
      <td class="num">${x.error ? "—" : fmt(x.records)}</td>
      <td>${x.error ? `<span class="status-bad">تعذّرت القراءة: ${esc(x.error)}</span>`
        : x.found ? `<span class="status-ok">${notesAr(x.found)}</span>` : "لا توجد مؤشرات مطابقة"}</td></tr>`).join("") + "</tbody>";

  $("#answers").innerHTML = "";
  $("#ask-q").value = "";
  $("#ask-card").hidden = !ok.length;
}

function renderRiskSummary(target, f) {
  $(target).innerHTML = RISK_ORDER.map((r) => {
    const items = f.filter((x) => x.risk === r);
    return `<div class="risk-row">${riskBadge(r)}
      <span class="desc">${items.length ? `${fmt(sumRows(items))} معلومة` : ""}</span>
      <span class="count">${notesAr(items.length)}</span></div>`;
  }).join("");
}

function renderTypes(target, f) {
  const by = {};
  f.forEach((x) => (by[x.label_ar] = (by[x.label_ar] || 0) + x.rows));
  const rows = Object.entries(by).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...rows.map(([, n]) => n));
  $(target).innerHTML = `<div class="bars">${rows.map(([k, n]) => `<div class="bar-row">
      <span>${esc(k)}</span>
      <div class="bar-track" role="img" aria-label="${esc(k)}: ${fmt(n)}"><div class="bar-fill" data-w="${(n / max) * 100}"></div></div>
      <span class="bar-num">${fmt(n)}</span></div>`).join("")}</div>`;
  requestAnimationFrame(() => document.querySelectorAll(`${target} .bar-fill`).forEach((b) => (b.style.width = b.dataset.w + "%")));
}

function renderFindings(listSel, filterSel, findings, opts = {}) {
  const sorted = [...findings].sort((a, b) => RISK_ORDER.indexOf(a.risk) - RISK_ORDER.indexOf(b.risk) || b.rows - a.rows);
  const counts = Object.fromEntries(RISK_ORDER.map((r) => [r, findings.filter((x) => x.risk === r).length]));
  const options = [["الكل", findings.length], ...RISK_ORDER.filter((r) => counts[r]).map((r) => [r, counts[r]])];
  const box = $(filterSel);
  box.innerHTML = options.map(([o, n], i) => `<button type="button" aria-pressed="${i === 0}" data-f="${esc(o)}">${o === "الكل" ? "الكل" : `خطورة ${o}`} (${fmt(n)})</button>`).join("");
  const PAGE = 8;
  const draw = (filter, limit = PAGE) => {
    const all = sorted.filter((x) => filter === "الكل" || x.risk === filter);
    const rows = all.slice(0, limit);
    const list = $(listSel);
    list.nextElementSibling?.classList.contains("findings-more") && list.nextElementSibling.remove();
    if (all.length > limit) {
      list.insertAdjacentHTML("afterend", `<div class="findings-more"><button type="button" class="btn btn-secondary btn-sm">عرض المزيد (${fmt(all.length - limit)})</button></div>`);
      list.nextElementSibling.querySelector("button").addEventListener("click", () => draw(filter, limit + PAGE * 2));
    }
    list.innerHTML = rows.length ? rows.map((x) => `
      <li class="finding ${RISK[x.risk]?.row || "low"}">
        <div class="finding-top">
          <div class="finding-title">${riskBadge(x.risk)}<span>${esc(x.label_ar)}</span></div>
          <span class="finding-count">${fmt(x.rows)} ${x.column === "(نص حر)" ? "مرة" : "قيمة"}</span>
        </div>
        <div class="loc"><span>الموقع:</span><bdi>${esc(x.file)}</bdi>${x.sheet ? `<span class="sep">‹</span><span>${esc(x.sheet)}</span>` : ""}
          <span class="sep">‹</span>${x.column === "(نص حر)" ? "<span>النص</span>" : `<span>عمود <bdi>${esc(x.column)}</bdi></span>`}</div>
        <div class="meta-line">${catBadge(x.category)}<span>الثقة: ${esc(x.confidence)}</span>
          <span>مثال مُخفى: <span class="sample">${esc(x.sample)}</span></span>
          ${opts.modified && x.modified_at ? `<span>آخر تعديل: ${esc(dateAr(x.modified_at))}</span>` : ""}</div>
        ${x.action ? `<div class="action"><b>الإجراء المقترح:</b><span>${esc(x.action)}</span></div>` : ""}
      </li>`).join("") : `<li class="findings-empty">لا توجد ملاحظات بهذا المستوى.</li>`;
  };
  box.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    box.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    draw(b.dataset.f);
  }));
  draw("الكل");
}

function renderRecs(target, recs) {
  const html = (r) => `<div class="rec"><h3><span class="tag ${r.level}">${LEVEL_TAG[r.level]}</span>${esc(r.title)}</h3>
      <p>${esc(r.body)}</p><div class="refs">${r.refs.map((x) => `<span class="ref">${esc(x)}</span>`).join("")}</div></div>`;
  const TOP = 4;
  $(target).innerHTML = recs.length
    ? recs.slice(0, TOP).map(html).join("") +
      (recs.length > TOP ? `<div class="recs-more" hidden>${recs.slice(TOP).map(html).join("")}</div>
        <button type="button" class="btn btn-secondary btn-sm more-btn" aria-expanded="false">عرض بقية الإجراءات (${recs.length - TOP})</button>` : "")
    : '<p class="muted">لا توجد إجراءات مطلوبة.</p>';
  const more = $(`${target} .more-btn`);
  if (more) more.addEventListener("click", () => {
    const box = $(`${target} .recs-more`);
    box.hidden = !box.hidden;
    more.setAttribute("aria-expanded", String(!box.hidden));
    more.textContent = box.hidden ? `عرض بقية الإجراءات (${recs.length - TOP})` : "إخفاء";
  });
}

// ============ الأسئلة ============
function md(raw) {
  const inline = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/__(.+?)__/g, "<b>$1</b>")
    .replace(/`([^`]+)`/g, "$1").replace(/\*\*/g, "");
  let html = "", list = null;
  const close = () => { if (list) { html += `</${list}>`; list = null; } };
  for (const line of String(raw).split("\n")) {
    const t = line.trim();
    let m;
    if (!t) { close(); continue; }
    if ((m = t.match(/^#{1,6}\s+(.*)$/))) { close(); html += `<p class="md-h">${inline(m[1])}</p>`; }
    else if ((m = t.match(/^[-*•]\s+(.*)$/))) { if (list !== "ul") { close(); html += "<ul>"; list = "ul"; } html += `<li>${inline(m[1])}</li>`; }
    else if ((m = t.match(/^[0-9٠-٩]+[.)-]\s*(.*)$/))) { if (list !== "ol") { close(); html += "<ol>"; list = "ol"; } html += `<li>${inline(m[1])}</li>`; }
    else { close(); html += `<p>${inline(t)}</p>`; }
  }
  close();
  return html;
}

const sourcesHtml = (sources) => sources.length
  ? `<div class="refs">${sources.map((s) => `<span class="ref">${esc(s.doc)} · المادة ${esc(s.article)}${s.amended ? " (معدّلة)" : ""}</span>`).join("")}</div>` : "";

async function ask(question) {
  const box = $("#answers");
  const q = document.createElement("div");
  q.className = "qa-q"; q.textContent = question;
  const a = document.createElement("div");
  a.className = "qa-a loading"; a.innerHTML = 'جاري إعداد الإجابة<span class="dots"><i>.</i><i>.</i><i>.</i></span>';
  box.prepend(a); box.prepend(q);
  try {
    const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, scan_id: currentScan.scan_id }) });
    if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(errText(d.detail, "تعذّرت الإجابة.")); }
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "", text = "", sources = [], error = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
        if (!line) continue;
        const msg = JSON.parse(line);
        if (msg.sources) sources = msg.sources;
        if (msg.error) error = msg.error;
        if (msg.t) { a.className = "qa-a typing"; text += msg.t; a.innerHTML = md(text); }
      }
    }
    a.className = "qa-a";
    a.innerHTML = md(text || error || "تعذّرت الإجابة.") + (text ? sourcesHtml(sources) : "");
  } catch (err) {
    a.className = "qa-a"; a.textContent = err.message === "Failed to fetch" ? "تعذّر الاتصال بالخادم." : err.message;
  }
}

$("#ask-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("#ask-q").value.trim();
  if (!q) { $("#ask-q").focus(); return; }
  const btn = $("#ask-form button");
  btn.disabled = true; $("#ask-q").value = "";
  await ask(q);
  btn.disabled = false; $("#ask-q").focus();
});

// ============ المراقبة الدورية ============
const TRIGGER = { nightly: "مجدول", manual: "يدوي" };
let monitorTimer = null, lastRuns = null;

async function loadMonitor() {
  clearTimeout(monitorTimer);
  let d;
  try {
    const res = await fetch("/api/monitor");
    d = await res.json();
    if (!res.ok) throw new Error(errText(d.detail, "تعذّر تحميل السجل."));
  } catch (err) {
    $("#folder-msg").textContent = err.message === "Failed to fetch" ? "تعذّر الاتصال بالخادم." : err.message;
    return;
  }
  renderMonitor(d);
  if (d.status.running && location.hash === "#/monitor") monitorTimer = setTimeout(loadMonitor, 1500);
}

function renderMonitor(d) {
  const st = d.status, running = st.running;
  if (document.activeElement !== $("#folder-in")) $("#folder-in").value = d.folder || "";
  const msg = $("#folder-msg");
  msg.className = "hint";
  msg.textContent = !d.folder ? "انسخ مسار المجلد من مستكشف الملفات والصقه هنا."
    : d.exists ? "تتم مراقبة هذا المجلد." : "المجلد المحفوظ غير موجود. تأكد من المسار.";
  if (d.folder && !d.exists) msg.className = "hint status-bad";
  if (st.error && !running) { msg.textContent = st.error; msg.className = "hint status-bad"; }

  $("#mon-actions").hidden = !d.exists;
  $("#mon-run").disabled = running;
  $("#mon-run").textContent = running ? "جاري الفحص…" : "فحص الآن";
  $("#mon-report").hidden = !d.latest;
  $("#mon-progress").hidden = !running;
  if (running) {
    const p = st.total ? Math.round((st.done / st.total) * 100) : 0;
    $("#mon-fill").style.width = p + "%";
    $("#mon-progress-text").textContent = st.total
      ? `${fmt(st.done)} من ${fmt(st.total)} — ${st.current || ""}` : "تجهيز قائمة الملفات…";
  }

  const L = d.latest;
  $("#mon-empty").hidden = !d.exists || !!L;
  $("#mon-body").hidden = !L;
  if (!L) return;
  const r = L.run;
  $("#mon-last").innerHTML = `آخر فحص: <b>${esc(dateAr(r.finished_at, true))}</b> (${TRIGGER[r.trigger] || ""}) —
    ${r.files_scanned ? `فُحص ${filesAr(r.files_scanned)}` : "لا توجد ملفات جديدة أو متغيّرة"}${r.files_skipped ? `، وتُخطّي ${filesAr(r.files_skipped)} لم تتغيّر` : ""}${r.files_failed ? `، وتعذّرت قراءة ${filesAr(r.files_failed)}` : ""}.`;

  $("#mon-stats").innerHTML = [
    [fmt(r.files_total), "الملفات في المجلد"],
    [fmt(r.files_with_pii), "ملفات تحتوي بيانات شخصية"],
    [fmt(r.files_high_risk), "ملفات عالية الخطورة"],
    [fmt(r.values_sensitive), "المعلومات الحساسة المكتشفة"],
  ].map(([v, l]) => `<div class="stat"><div class="stat-label">${l}</div><div class="stat-value">${v}</div></div>`).join("");

  const ch = L.changes, blocks = [];
  const list = (xs) => `<ul>${xs.map((x) => `<li><bdi>${esc(x)}</bdi></li>`).join("")}</ul>`;
  if (ch.new.length) blocks.push(`<div class="change"><h3>${badge("r-high", ICON.high, "جديد")}ملفات جديدة تحتوي بيانات شخصية (${fmt(ch.new.length)})</h3>${list(ch.new)}</div>`);
  if (ch.resolved.length) blocks.push(`<div class="change"><h3>${badge("c-personal", "", "تمت المعالجة")}ملفات لم تعد تحتوي بيانات شخصية (${fmt(ch.resolved.length)})</h3>${list(ch.resolved)}</div>`);
  if (L.stale.length) blocks.push(`<div class="change"><h3>${badge("r-medium", ICON.medium, "قديم")}ملفات لم تُعدّل منذ أكثر من سنة (${fmt(L.stale.length)})</h3>${list(L.stale)}</div>`);
  $("#mon-changes").innerHTML = blocks.length ? `<div class="changes">${blocks.join("")}</div>`
    : `<p class="muted">${d.runs.length > 1 ? "لا توجد تغييرات منذ الفحص السابق." : "هذا أول فحص، وتبدأ المقارنة من الفحص التالي."}</p>`;

  lastRuns = d.runs;
  lineChart("#mon-trend", d.runs);
  renderRecs("#mon-recs", L.recommendations);
  renderFindings("#mon-findings", "#mon-filter", L.findings, { modified: true });

  $("#mon-runs").innerHTML = `<thead><tr><th>التاريخ</th><th>نوع التشغيل</th><th>الملفات</th><th>فُحص</th><th>تُخطّي</th><th>تعذّر</th><th>تحتوي بيانات شخصية</th></tr></thead><tbody>` +
    [...d.runs].reverse().map((x) => `<tr><td>${esc(dateAr(x.started_at, true))}</td><td>${TRIGGER[x.trigger] || ""}</td>
      <td class="num">${fmt(x.files_total)}</td><td class="num">${fmt(x.files_scanned)}</td><td class="num">${fmt(x.files_skipped)}</td>
      <td class="num">${fmt(x.files_failed)}</td><td class="num">${fmt(x.files_with_pii)}</td></tr>`).join("") + "</tbody>";
}

// خط زمني: الملفات التي تحتوي بيانات شخصية، والملفات عالية الخطورة، في كل فحص
function lineChart(target, runs) {
  const series = [["ملفات تحتوي بيانات شخصية", "files_with_pii", "#2764A5"], ["ملفات عالية الخطورة", "files_high_risk", "#B42318"]];
  const el = $(target);
  const W = Math.max(280, el.clientWidth || 520), H = 220, P = { t: 16, r: 32, b: 32, l: 44 };
  const max = Math.max(1, ...runs.flatMap((r) => series.map(([, k]) => r[k])));
  const n = runs.length;
  const x = (i) => n === 1 ? (W + P.l - P.r) / 2 : W - P.r - 8 - (i * (W - P.l - P.r - 24)) / (n - 1);  // الأقدم يمينًا
  const y = (v) => P.t + (1 - v / max) * (H - P.t - P.b);
  const ticks = [...new Set([0, Math.round(max / 2), max])];
  const sameDay = n > 1 && dateAr(runs[0].started_at) === dateAr(runs[n - 1].started_at);
  const xlabel = (iso) => sameDay ? dateAr(iso, true).split(" · ")[1] : dateAr(iso);
  const step = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(W / 110))));
  el.innerHTML = `<svg class="line-chart" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" direction="ltr" role="img" aria-label="الخط الزمني لعدد الملفات التي تحتوي بيانات شخصية">
    ${ticks.map((v) => `<line class="grid" x1="${P.l}" x2="${W - P.r}" y1="${y(v)}" y2="${y(v)}"/><text class="axis" x="${P.l - 8}" y="${y(v) + 4}" text-anchor="end">${fmt(v)}</text>`).join("")}
    ${runs.map((r, i) => (i % step === 0 || i === n - 1) ? `<text class="axis" x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(xlabel(r.started_at))}</text>` : "").join("")}
    ${series.map(([name, k, c]) => (n > 1 ? `<polyline fill="none" stroke="${c}" stroke-width="2" points="${runs.map((r, i) => `${x(i)},${y(r[k])}`).join(" ")}"/>` : "") +
      runs.map((r, i) => `<circle cx="${x(i)}" cy="${y(r[k])}" r="4.5" fill="${c}" stroke="#fff" stroke-width="2" data-tip="${esc(dateAr(r.started_at, true))} — ${esc(name)}: ${fmt(r[k])}"/>`).join("")).join("")}
  </svg><div class="legend">${series.map(([name, , c]) => `<span><span class="sw" style="background:${c}"></span>${name}</span>`).join("")}</div>`;
}
let resizeT;
window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(() => { if (lastRuns && !$("#mon-body").hidden) lineChart("#mon-trend", lastRuns); }, 150); });

$("#folder-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const folder = $("#folder-in").value.trim();
  if (!folder) { $("#folder-in").focus(); return; }
  const res = await fetch("/api/monitor/folder", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ folder }) });
  const d = await res.json().catch(() => ({}));
  if (!res.ok) { $("#folder-msg").textContent = errText(d.detail, "تعذّر حفظ المجلد."); $("#folder-msg").className = "hint status-bad"; return; }
  $("#folder-in").blur();
  loadMonitor();
});

$("#mon-run").addEventListener("click", async () => {
  $("#mon-run").disabled = true;
  const res = await fetch("/api/monitor/run", { method: "POST" });
  const d = await res.json().catch(() => ({}));
  if (!res.ok) { $("#folder-msg").textContent = errText(d.detail, "تعذّر بدء الفحص."); $("#folder-msg").className = "hint status-bad"; }
  setTimeout(loadMonitor, 400);
});

// تلميح عند المرور على نقاط الخط الزمني
const tip = $("#tip");
document.addEventListener("mousemove", (e) => {
  const t = e.target.closest("[data-tip]");
  if (!t) { tip.hidden = true; return; }
  tip.textContent = t.dataset.tip; tip.hidden = false;
  tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px";
  tip.style.top = e.clientY + 14 + "px";
});

// ============ البداية ============
renderPicked();
route();
loadStatus();
setInterval(loadStatus, 30000);