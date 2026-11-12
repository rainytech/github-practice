"use strict";

const state = { items: [], meta: null, dups: [], scanWasRunning: false };
const $ = (id) => document.getElementById(id);
const inr = new Intl.NumberFormat("en-IN");
const rupees = (n) => (n === null || n === undefined ? "—" : "₹" + inr.format(n));
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function niceDate(s, withTime = true) {
  if (!s) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})(?: (\d{2}):(\d{2}))?/.exec(s);
  if (!m) return s;
  let out = `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}`;
  if (withTime && m[4] !== undefined) {
    const h = +m[4], ap = h < 12 ? "AM" : "PM";
    out += `, ${h % 12 || 12}:${m[5]} ${ap}`;
  }
  return out;
}

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, "");
    else e.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    e.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return e;
}

// ------------------------------------------------------------------ server calls
async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(path, options);
  } catch (e) {
    throw new Error("The tracker is not running. Start it again with 'Start Tracker.bat', then reload this page.");
  }
  let data = {};
  try { data = await res.json(); } catch (e) { /* not JSON */ }
  if (!res.ok) throw new Error(data.error || `The tracker answered with an error (${res.status}).`);
  return data;
}
const post = (path, body) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
});

function showMessage(text, isError = false, link = null) {
  const m = $("message");
  m.hidden = false;
  m.className = "message" + (isError ? " error" : "");
  m.textContent = text;
  if (link) { m.append(" "); m.append(el("a", { href: link.href, text: link.text })); }
  if (!isError) setTimeout(() => { if (m.textContent.startsWith(text)) m.hidden = true; }, 12000);
}

// ------------------------------------------------------------------ loading
async function loadAll() {
  try {
    const [meta, items, dups] = await Promise.all([api("/api/meta"), api("/api/items"), api("/api/duplicates")]);
    state.meta = meta; state.items = items.items; state.dups = dups.duplicates;
    fillFilterOptions();
    render();
  } catch (e) { showMessage(e.message, true); }
}

function fillFilterOptions() {
  const keep = (sel, values, firstLabel) => {
    const s = $(sel), cur = s.value;
    s.replaceChildren(el("option", { value: "", text: firstLabel }), ...values.map((v) => el("option", { value: v, text: v })));
    s.value = values.includes(cur) ? cur : "";
  };
  keep("f-category", state.meta.categories, "All");
  keep("f-status", state.meta.statuses, "All shown");
  const locs = [...new Set(state.items.map((i) => i.location).filter(Boolean))].sort();
  keep("f-location", locs, "All");
  const c = state.meta.counts;
  let foot = `Screenshot folder: ${state.meta.screenshot_folder}` +
    (state.meta.folder_exists ? "" : "  (NOT FOUND — check settings.ini)") +
    ` · Data folder: ${state.meta.data_folder} · ${c.items} item(s), ${c.screenshots} screenshot(s) processed.`;
  if (c.errors.length) foot += ` · ${c.errors.length} screenshot(s) could not be read (they are retried on the next scan).`;
  $("footer").textContent = foot;
}

// ------------------------------------------------------------------ filtering & sorting
function visibleItems() {
  const q = $("f-search").value.trim().toLowerCase();
  const cat = $("f-category").value, st = $("f-status").value, loc = $("f-location").value;
  const min = $("f-min").value === "" ? null : +$("f-min").value;
  const max = $("f-max").value === "" ? null : +$("f-max").value;
  const showHidden = $("f-hidden").checked, needsOnly = $("f-needs").checked;
  const hidden = state.meta.hidden_statuses;
  let list = state.items.filter((i) => {
    if (!showHidden && hidden.includes(i.status) && st !== i.status) return false;
    if (cat && i.category !== cat) return false;
    if (st && i.status !== st) return false;
    if (loc && i.location !== loc) return false;
    if (needsOnly && !i.needs_checking) return false;
    if (min !== null && (i.current_price === null || i.current_price < min)) return false;
    if (max !== null && (i.current_price === null || i.current_price > max)) return false;
    if (q) {
      const hay = [i.title, i.brand_model, i.seller, i.location, i.description, i.notes, i.condition_notes, i.category]
        .join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  const sort = $("f-sort").value;
  const nul = (v, big) => (v === null || v === undefined ? big : v);
  const cmp = {
    checked: (a, b) => a.last_checked.localeCompare(b.last_checked),
    drop: (a, b) => nul(b.drop_amount, -Infinity) - nul(a.drop_amount, -Infinity),
    added: (a, b) => b.date_added.localeCompare(a.date_added) || b.id - a.id,
    price: (a, b) => nul(a.current_price, Infinity) - nul(b.current_price, Infinity),
    deal: (a, b) => nul(b.deal_score, -1) - nul(a.deal_score, -1),
  }[sort];
  return list.sort(cmp);
}

// ------------------------------------------------------------------ rendering
function render() {
  const focus = document.activeElement;
  const focusKey = focus && focus.dataset && focus.dataset.field
    ? { id: focus.closest(".card")?.dataset.id, field: focus.dataset.field } : null;

  renderDuplicates();
  const list = visibleItems();
  $("cards").replaceChildren(...list.map(card));
  const total = state.items.length;
  $("count").textContent = `Showing ${list.length} of ${total} item(s)`;
  const empty = $("empty");
  empty.hidden = list.length > 0;
  empty.textContent = total === 0
    ? "No items yet. Put Marketplace screenshots in your screenshot folder and press \"Scan for new screenshots\"."
    : "No items match these filters.";

  if (focusKey) {
    const again = document.querySelector(`.card[data-id="${focusKey.id}"] [data-field="${focusKey.field}"]`);
    if (again) again.focus();
  }
}

function dealBadge(item) {
  if (item.deal_score === null) return el("span", { class: "badge none", title: item.deal_reasons.join("\n"), text: "Deal score —" });
  const s = item.deal_score;
  const cls = s >= 8 ? "deal-hi" : s >= 5 ? "deal-mid" : "deal-lo";
  return el("span", { class: "badge " + cls, title: "Offline rule, not AI:\n" + item.deal_reasons.join("\n"), text: `Deal ${s}/10` });
}

function field(item, name, value, attrs = {}) {
  const tag = attrs.textarea ? "textarea" : "input";
  const input = el(tag, { "data-field": name, value: tag === "input" ? (value ?? "") : null, ...attrs.extra });
  if (tag === "textarea") input.value = value ?? "";
  input.addEventListener("change", () => save(item.id, name, input.value, input));
  return input;
}

function selectField(item, name, options, value, blankLabel) {
  const s = el("select", { "data-field": name });
  if (blankLabel !== undefined) s.append(el("option", { value: "", text: blankLabel }));
  for (const o of options) s.append(el("option", { value: o, text: o }));
  s.value = value || "";
  s.addEventListener("change", () => save(item.id, name, s.value, s));
  return s;
}

function openImage(src) {
  $("lightbox-img").src = src;
  $("lightbox").hidden = false;
}

function card(item) {
  const hiddenStatus = state.meta.hidden_statuses.includes(item.status);
  const thumb = item.thumb
    ? el("img", { class: "thumb", src: `/thumbs/${item.thumb}`, alt: "Screenshot", title: "Click to enlarge",
                  onclick: () => openImage(item.latest_screenshot_id ? `/shot/${item.latest_screenshot_id}` : `/thumbs/${item.thumb}`) })
    : el("div", { class: "thumb-missing", text: "No screenshot" });

  const badges = el("div", { class: "badges" },
    item.price_dropped && el("span", { class: "badge dropped", text: `Price dropped ${rupees(item.previous_price)} → ${rupees(item.current_price)}` }),
    item.target_reached && el("span", { class: "badge target", text: "At or below target" }),
    item.needs_checking ? el("span", { class: "badge check", title: item.check_reasons, text: "Needs checking" }) : null,
    dealBadge(item),
  );

  let dropText = null;
  if (item.drop_amount !== null && item.drop_amount !== 0 && item.history.length > 1) {
    dropText = item.drop_amount > 0
      ? el("span", { class: "drop-down", text: `Drop ${rupees(item.drop_amount)} (${item.drop_pct}%)` })
      : el("span", { class: "drop-up", text: `Up ${rupees(-item.drop_amount)} (${-item.drop_pct}%)` });
  }
  const prices = el("div", { class: "prices" },
    el("span", { class: "now" }, "Current ₹ ", field(item, "price", item.current_price ?? "", { extra: { inputmode: "numeric", title: "Changing this adds a price-history line" } })),
    el("span", {}, `First ${rupees(item.first_price)}`),
    dropText,
  );

  const grid = el("div", { class: "grid2" },
    el("label", { text: "Target ₹" }), field(item, "target_price", item.target_price ?? "", { extra: { inputmode: "numeric" } }),
    el("label", { text: "New price ₹" }), field(item, "new_price", item.new_price ?? "", { extra: { inputmode: "numeric" } }),
    el("label", { text: "Category" }), el("div", { class: "span3" }, selectField(item, "category", state.meta.categories, item.category, "— choose —")),
    el("label", { text: "Status" }), selectField(item, "status", state.meta.statuses, item.status),
    el("label", { text: "Location" }), field(item, "location", item.location),
    el("label", { text: "Seller" }), el("div", { class: "span3" }, field(item, "seller", item.seller)),
  );

  const dates = el("div", { class: "dates" },
    `Last checked ${niceDate(item.last_checked)} · Added ${niceDate(item.date_added, false)}`,
    item.listed_ago ? ` · ${item.listed_ago}` : "",
    el("span", { class: "card-status" }));

  const needs = el("input", { type: "checkbox", "data-field": "needs_checking", checked: !!item.needs_checking });
  needs.addEventListener("change", () => save(item.id, "needs_checking", needs.checked, needs));

  const more = el("details", {},
    el("summary", { text: "More details, notes, price history" }),
    el("div", { class: "grid2" },
      el("label", { text: "Brand / model" }), field(item, "brand_model", item.brand_model),
      el("label", { text: "Seller profile" }), field(item, "seller_profile", item.seller_profile, { extra: { placeholder: "optional" } }),
      el("label", { text: "Condition / faults" }), field(item, "condition_notes", item.condition_notes),
      el("label", { text: "Listed" }), field(item, "listed_ago", item.listed_ago),
      el("label", { text: "My notes" }), field(item, "notes", item.notes, { textarea: true }),
      el("label", { text: "Description" }), field(item, "description", item.description, { textarea: true }),
      el("label", { text: "Needs checking" }), el("span", {}, needs, item.check_reasons ? ` ${item.check_reasons}` : ""),
    ),
    el("p", { text: "Price history:" }),
    el("ul", { class: "history" }, item.history.length
      ? item.history.map((h) => el("li", {}, `${niceDate(h.observed_at)} — ${rupees(h.price)} `,
          el("i", { text: h.source === "screenshot" ? `(screenshot ${h.screenshot_path ? h.screenshot_path.split(/[\\/]/).pop() : ""})` : "(typed by you)" })))
      : el("li", { text: "No price yet." })),
    el("p", { text: "Deal score (offline rule):" }),
    el("ul", { class: "reasons" }, item.deal_reasons.map((r) => el("li", { text: r }))),
    item.screenshots.map((s) => el("details", {},
      el("summary", { text: `Raw OCR text — ${s.path.split(/[\\/]/).pop()} (${niceDate(s.observed_at)})` }),
      el("div", { class: "raw", text: s.raw_text || "(no text)" }))),
  );

  return el("article", {
      class: "card" + (item.target_reached ? " target" : "") + (hiddenStatus ? " hidden-status" : ""),
      "data-id": item.id },
    el("div", {}, thumb),
    el("div", {},
      field(item, "title", item.title, { extra: { class: "title", placeholder: "Title (not read — please type it)" } }),
      badges, prices, grid, dates, more),
  );
}

function renderDuplicates() {
  const box = $("dups");
  box.hidden = state.dups.length === 0;
  $("dup-list").replaceChildren(...state.dups.map((d) => {
    const c = d.candidate;
    const p = d.parsed || {};
    return el("div", { class: "dup" },
      el("img", { src: `/thumbs/${d.thumb}`, alt: "New screenshot", title: "New screenshot — click to enlarge", onclick: () => openImage(`/shot/${d.screenshot_id}`) }),
      el("div", {},
        el("div", {}, el("b", { text: "New screenshot: " }), `${p.title || "(no title read)"} — ${rupees(p.price)} — ${p.seller || "seller not visible"} — ${niceDate(d.observed_at)}`),
        el("div", {}, el("b", { text: "Existing item: " }), c ? `${c.title} — ${rupees(c.current_price)} — ${c.seller || "seller unknown"}` : "(missing)"),
        el("div", { class: "hint", text: `Why it might be the same: ${d.reasons}` }),
        el("div", { class: "choices" },
          el("button", { type: "button", text: "Same item — add to its price history", onclick: (e) => resolveDup(d.id, "same", e.target) }),
          el("button", { type: "button", text: "Different item — add as new", onclick: (e) => resolveDup(d.id, "different", e.target) }),
        ),
      ),
      c && c.thumb ? el("img", { src: `/thumbs/${c.thumb}`, alt: "Existing item", title: "Existing item — click to enlarge",
                                 onclick: () => openImage(c.latest_screenshot_id ? `/shot/${c.latest_screenshot_id}` : `/thumbs/${c.thumb}`) }) : el("div"),
    );
  }));
}

// ------------------------------------------------------------------ actions
function cardStatus(id, text, cls) {
  const s = document.querySelector(`.card[data-id="${id}"] .card-status`);
  if (!s) return;
  s.className = "card-status " + cls;
  s.textContent = text;
  if (cls === "saved") setTimeout(() => { if (s.textContent === text) s.textContent = ""; }, 2500);
}

async function save(id, name, value, input) {
  try {
    const data = await post(`/api/items/${id}`, { [name]: value });
    const idx = state.items.findIndex((i) => i.id === id);
    if (idx >= 0) state.items[idx] = data.item;
    if (["location", "status"].includes(name)) fillFilterOptions();
    if ($("message").classList.contains("error")) $("message").hidden = true;
    render();
    cardStatus(id, " Saved ✓", "saved");
  } catch (e) {
    input.classList.add("bad");
    cardStatus(id, " Not saved: " + e.message, "err");
    showMessage(e.message, true);
  }
}

async function resolveDup(id, decision, btn) {
  btn.disabled = true;
  try {
    await post(`/api/duplicates/${id}/${decision}`);
    showMessage(decision === "same" ? "Added to the existing item's price history." : "Added as a new item.");
    await loadAll();
  } catch (e) { showMessage(e.message, true); btn.disabled = false; }
}

async function startScan() {
  try {
    await post("/api/scan");
    pollScan();
  } catch (e) { showMessage(e.message, true); }
}

async function pollScan() {
  let st;
  try { st = await api("/api/scan"); } catch (e) { showMessage(e.message, true); return; }
  const box = $("scan-status");
  $("btn-scan").disabled = st.running;
  if (st.running) {
    state.scanWasRunning = true;
    box.hidden = false;
    box.textContent = st.total
      ? `Reading screenshots… ${st.done} of ${st.total}${st.current ? " — " + st.current : ""}`
      : "Looking for new screenshots…";
    setTimeout(pollScan, 1200);
    return;
  }
  if (state.scanWasRunning && st.summary) {
    state.scanWasRunning = false;
    box.hidden = false;
    box.replaceChildren(el("b", { text: st.summary.message }));
    if (st.summary.errors.length) box.append(el("ul", {}, st.summary.errors.map((e) => el("li", { text: e }))));
    await loadAll();
  }
}

async function doBackup(btn) {
  btn.disabled = true;
  try {
    const r = await post("/api/backup");
    showMessage(`Backup saved: ${r.path}`);
  } catch (e) { showMessage("Backup failed: " + e.message, true); }
  btn.disabled = false;
}

async function doExport(btn) {
  btn.disabled = true;
  try {
    const r = await post("/api/export");
    showMessage(`Export saved: ${r.path}`, false, { href: r.download, text: "Download a copy" });
  } catch (e) { showMessage("Export failed: " + e.message, true); }
  btn.disabled = false;
}

// ------------------------------------------------------------------ wiring
$("btn-scan").addEventListener("click", startScan);
$("btn-backup").addEventListener("click", (e) => doBackup(e.target));
$("btn-export").addEventListener("click", (e) => doExport(e.target));
$("lightbox").addEventListener("click", () => { $("lightbox").hidden = true; $("lightbox-img").src = ""; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("lightbox").hidden = true; });
for (const id of ["f-search", "f-min", "f-max"]) $(id).addEventListener("input", render);
for (const id of ["f-category", "f-status", "f-location", "f-sort", "f-hidden", "f-needs"]) $(id).addEventListener("change", render);

state.scanWasRunning = true;      // the tracker starts a scan when it opens
loadAll().then(pollScan);
