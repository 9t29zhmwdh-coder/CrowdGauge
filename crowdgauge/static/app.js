/* CrowdGauge frontend: fetches a report and renders the week as a heatmap,
   the selected day as bars, and the live value as a stat tile. */

const { TRANSLATIONS, detectLanguage, rememberLanguage } = window.CrowdGaugeI18n;

const SEQ_STEPS = 7;
const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

const state = {
  language: detectLanguage(),
  report: null,
  insights: null,
  selectedDay: new Date().getDay() === 0 ? 6 : new Date().getDay() - 1,
  providers: [],
};

const dom = {
  form: document.getElementById("lookup-form"),
  query: document.getElementById("query"),
  provider: document.getElementById("provider"),
  submit: document.getElementById("submit"),
  language: document.getElementById("language"),
  message: document.getElementById("message"),
  messageTitle: document.getElementById("message-title"),
  messageBody: document.getElementById("message-body"),
  result: document.getElementById("result"),
  venueName: document.getElementById("venue-name"),
  venueAddress: document.getElementById("venue-address"),
  attribution: document.getElementById("attribution"),
  tiles: document.getElementById("tiles"),
  heatmap: document.getElementById("heatmap"),
  legendScale: document.getElementById("legend-scale"),
  dayPicker: document.getElementById("day-picker"),
  dayTitle: document.getElementById("day-title"),
  dayBars: document.getElementById("daybars"),
  barAxis: document.getElementById("bar-axis"),
  table: document.getElementById("data-table"),
  notes: document.getElementById("notes"),
  tooltip: document.getElementById("tooltip"),
  footerProvider: document.getElementById("footer-provider"),
  footerVersion: document.getElementById("footer-version"),
};

function t(key) {
  return TRANSLATIONS[state.language][key];
}

/* Colour: one hue, near zero to peak. Bucket boundaries are even, so a cell's
   step is a direct read of its magnitude. */
function stepFor(score) {
  const bucket = Math.min(SEQ_STEPS, Math.max(1, Math.ceil((score / 100) * SEQ_STEPS) || 1));
  return `var(--seq-${bucket})`;
}

function inkFor(score) {
  return score >= 72 ? "var(--cell-ink-high)" : "var(--cell-ink)";
}

/* Rendering */

function applyStaticText() {
  document.documentElement.lang = state.language;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const value = t(node.dataset.i18n);
    if (value) node.textContent = value;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    const value = t(node.dataset.i18nPlaceholder);
    if (value) node.placeholder = value;
  });
  dom.submit.textContent = t("submit");
}

function showMessage(title, body, tone) {
  dom.messageTitle.textContent = title;
  dom.messageBody.textContent = body;
  dom.message.dataset.tone = tone || "info";
  dom.message.hidden = false;
}

function hideMessage() {
  dom.message.hidden = true;
}

function renderTiles() {
  const { live, typical_visit_duration: duration } = state.report;
  dom.tiles.replaceChildren(
    liveTile(live),
    slotTile(t("peakLabel"), state.insights.busiest[0]),
    slotTile(t("quietLabel"), state.insights.quietest[0]),
    plainTile(t("durationLabel"), duration || t("durationUnknown"), null, true),
  );
}

function liveTile(live) {
  if (!live || live.score === null || live.score === undefined) {
    return plainTile(t("liveLabel"), t("liveNone"), t("liveNoneNote"), true);
  }
  const measuredNote = live.measured_at
    ? `${live.label || ""} (${formatTimestamp(live.measured_at)})`.trim()
    : live.label || null;
  const tile = plainTile(t("liveLabel"), `${live.score}%`, measuredNote);
  if (typeof live.delta_to_typical === "number") {
    const delta = document.createElement("p");
    delta.className = "tile-note";
    const marker = document.createElement("span");
    marker.className = "delta";
    marker.dataset.direction = live.delta_to_typical >= 0 ? "up" : "down";
    // Arrow plus wording, so the direction never rests on colour alone.
    marker.textContent = `${live.delta_to_typical >= 0 ? "↑" : "↓"} ${Math.abs(live.delta_to_typical)}%`;
    delta.append(marker, document.createTextNode(` ${t("vsTypical")}`));
    tile.append(delta);
  }
  return tile;
}

function slotTile(label, slot) {
  if (!slot) return plainTile(label, t("noData"), null, true);
  const weekday = TRANSLATIONS[state.language].weekdaysShort[slot.weekday];
  const measured = countFor(slot.weekday, slot.hour);
  const note =
    measured === null
      ? `${weekday} ${formatHour(slot.hour)}`
      : `${weekday} ${formatHour(slot.hour)}, ${measured} ${t("peoplePerHour")}`;
  return plainTile(label, `${slot.score}%`, note);
}

/* Head counts only exist for sources that actually measure people, so every
   place that shows one has to cope with its absence. */
function countFor(weekday, hour) {
  const slot = state.report?.days?.[weekday]?.hours?.[hour];
  return slot && typeof slot.count === "number" ? slot.count : null;
}

function plainTile(label, value, note, smallValue) {
  const tile = document.createElement("div");
  tile.className = "tile";
  const labelNode = document.createElement("p");
  labelNode.className = "tile-label";
  labelNode.textContent = label;
  const valueNode = document.createElement("p");
  valueNode.className = smallValue ? "tile-value small" : "tile-value";
  valueNode.textContent = value;
  tile.append(labelNode, valueNode);
  if (note) {
    const noteNode = document.createElement("p");
    noteNode.className = "tile-note";
    noteNode.textContent = note;
    tile.append(noteNode);
  }
  return tile;
}

function renderHeatmap() {
  const cells = [corner()];
  HOURS.forEach((hour) => cells.push(hourHeader(hour)));
  state.report.days.forEach((day, index) => {
    cells.push(dayLabel(index));
    day.hours.forEach((slot) => cells.push(heatCell(index, slot)));
  });
  dom.heatmap.replaceChildren(...cells);
  renderLegend();
}

function corner() {
  const node = document.createElement("span");
  node.className = "hm-corner";
  node.setAttribute("aria-hidden", "true");
  return node;
}

function hourHeader(hour) {
  const node = document.createElement("span");
  node.className = "hm-hour";
  // Label every third hour, a label on all 24 collides at this column width.
  node.textContent = hour % 3 === 0 ? String(hour).padStart(2, "0") : "";
  return node;
}

function dayLabel(index) {
  const node = document.createElement("span");
  node.className = "hm-day";
  node.textContent = TRANSLATIONS[state.language].weekdaysShort[index];
  return node;
}

function heatCell(dayIndex, slot) {
  const cell = document.createElement("button");
  cell.type = "button";
  cell.className = "hm-cell";
  const label = `${TRANSLATIONS[state.language].weekdays[dayIndex]} ${formatHour(slot.hour)}`;
  if (slot.score === null || slot.score === undefined) {
    cell.dataset.empty = "true";
    cell.setAttribute("aria-label", `${label}: ${t("noData")}`);
    cell.tabIndex = -1;
    return cell;
  }
  cell.style.setProperty("--cell-bg", stepFor(slot.score));
  cell.style.color = inkFor(slot.score);
  cell.setAttribute("aria-label", `${label}: ${slot.score}${t("percentOfPeak")}`);
  if (isCurrentSlot(dayIndex, slot.hour)) cell.dataset.now = "true";
  attachTooltip(
    cell,
    `${label}\n${slot.score}${t("percentOfPeak")}${countSuffix(slot)}${labelSuffix(slot)}`,
  );
  cell.addEventListener("click", () => selectDay(dayIndex));
  return cell;
}

function labelSuffix(slot) {
  return slot.label ? `\n${slot.label}` : "";
}

function countSuffix(slot) {
  return typeof slot.count === "number" ? `\n${slot.count} ${t("peoplePerHour")}` : "";
}

function isCurrentSlot(dayIndex, hour) {
  const now = new Date();
  const weekday = now.getDay() === 0 ? 6 : now.getDay() - 1;
  return dayIndex === weekday && hour === now.getHours();
}

function renderLegend() {
  const swatches = Array.from({ length: SEQ_STEPS }, (_, index) => {
    const node = document.createElement("span");
    node.className = "legend-swatch";
    node.style.background = `var(--seq-${index + 1})`;
    return node;
  });
  dom.legendScale.replaceChildren(...swatches);
}

function renderDayPicker() {
  const buttons = state.report.days.map((_, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = TRANSLATIONS[state.language].weekdaysShort[index];
    button.setAttribute("aria-pressed", String(index === state.selectedDay));
    button.addEventListener("click", () => selectDay(index));
    return button;
  });
  dom.dayPicker.replaceChildren(...buttons);
}

function renderDayBars() {
  const day = state.report.days[state.selectedDay];
  const peak = Math.max(...day.hours.map((slot) => slot.score || 0), 1);
  dom.dayTitle.textContent = TRANSLATIONS[state.language].weekdays[state.selectedDay];
  dom.dayBars.replaceChildren(...day.hours.map((slot) => barColumn(slot, peak)));
  dom.barAxis.replaceChildren(
    ...HOURS.map((hour) => {
      const node = document.createElement("span");
      node.textContent = hour % 3 === 0 ? String(hour).padStart(2, "0") : "";
      return node;
    }),
  );
}

function barColumn(slot, peak) {
  const column = document.createElement("div");
  column.className = "bar-col";
  const bar = document.createElement("div");
  bar.className = "bar";
  if (slot.score === null || slot.score === undefined) {
    bar.dataset.empty = "true";
  } else {
    bar.style.height = `${Math.max(2, (slot.score / peak) * 100)}%`;
    // Only the peak carries a printed number, the rest is on hover.
    if (slot.score === peak) {
      const label = document.createElement("span");
      label.className = "bar-label";
      label.textContent = `${slot.score}%`;
      column.append(label);
    }
    attachTooltip(column, `${formatHour(slot.hour)}\n${slot.score}${t("percentOfPeak")}`);
  }
  column.append(bar);
  return column;
}

function renderTable() {
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  headRow.append(cell("th", t("day")));
  HOURS.forEach((hour) => headRow.append(cell("th", String(hour).padStart(2, "0"))));
  head.append(headRow);
  const body = document.createElement("tbody");
  state.report.days.forEach((day, index) => {
    const row = document.createElement("tr");
    row.append(cell("td", TRANSLATIONS[state.language].weekdays[index]));
    day.hours.forEach((slot) =>
      row.append(cell("td", slot.score === null || slot.score === undefined ? "" : String(slot.score))),
    );
    body.append(row);
  });
  const caption = dom.table.querySelector("caption");
  dom.table.replaceChildren(caption, head, body);
}

function cell(tag, text) {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}

function renderNotes() {
  dom.notes.replaceChildren(
    ...state.report.notes.map((note) => {
      const item = document.createElement("li");
      item.textContent = note;
      return item;
    }),
  );
  dom.footerProvider.textContent = `${t("footerSource")}: ${state.report.provider_label}`;
}

/* The default subtitle insists the figure is not a head count, which is true
   for Google and BestTime but wrong for a counting station that measures
   exactly that. */
function updateWeekSubtitle() {
  const node = document.querySelector('[data-i18n="weekSubtitle"]');
  if (!node) return;
  const hasCounts = state.report.days.some((day) =>
    day.hours.some((slot) => typeof slot.count === "number"),
  );
  node.textContent = hasCounts ? t("weekSubtitleCounts") : t("weekSubtitle");
}

function renderReport() {
  const venue = state.report.venue;
  dom.venueName.textContent = venue.name;
  dom.venueAddress.textContent = venue.address || "";
  dom.attribution.textContent = state.report.attribution;
  renderTiles();
  renderHeatmap();
  renderDayPicker();
  renderDayBars();
  renderTable();
  renderNotes();
  dom.result.hidden = false;
}

function selectDay(index) {
  state.selectedDay = index;
  renderDayPicker();
  renderDayBars();
}

/* Tooltip layer */

function attachTooltip(node, text) {
  node.addEventListener("pointerenter", (event) => {
    dom.tooltip.textContent = text;
    dom.tooltip.hidden = false;
    positionTooltip(event);
  });
  node.addEventListener("pointermove", positionTooltip);
  node.addEventListener("pointerleave", () => {
    dom.tooltip.hidden = true;
  });
}

function positionTooltip(event) {
  const offset = 14;
  const width = dom.tooltip.offsetWidth;
  const left = Math.min(event.clientX + offset, window.innerWidth - width - 8);
  dom.tooltip.style.left = `${Math.max(8, left)}px`;
  dom.tooltip.style.top = `${event.clientY + offset}px`;
}

/* Data access */

async function loadProviders() {
  const response = await fetch(`/api/providers?lang=${state.language}`);
  if (!response.ok) return;
  const payload = await response.json();
  state.providers = payload.providers;
  dom.provider.replaceChildren(
    ...payload.providers.map((entry) => {
      const option = document.createElement("option");
      option.value = entry.name;
      const status = entry.configured ? t("providerConfigured") : t("providerMissing");
      option.textContent = `${entry.label} (${status})`;
      option.disabled = !entry.configured;
      return option;
    }),
  );
  const usable = payload.providers.find((entry) => entry.configured);
  if (usable) dom.provider.value = usable.name;
  announceSource(usable);
}

/* Which source answers without a key changes what the tool can find, so say so
   before the first lookup rather than letting a "not found" explain it. */
function announceSource(provider) {
  if (!provider) return;
  if (provider.name === "demo") {
    showMessage(t("setupTitle"), t("setupBody"), "info");
  } else if (provider.name === "opendata") {
    showMessage(t("openDataTitle"), t("openDataBody"), "info");
  }
}

async function loadVersion() {
  const response = await fetch("/api/health");
  if (!response.ok) return;
  const payload = await response.json();
  dom.footerVersion.textContent = `v${payload.version}`;
}

async function runLookup(event) {
  event.preventDefault();
  const query = dom.query.value.trim();
  if (query.length < 2) return;
  setBusy(true);
  try {
    const url =
      `/api/busyness?q=${encodeURIComponent(query)}` +
      `&provider=${encodeURIComponent(dom.provider.value)}` +
      `&lang=${encodeURIComponent(state.language)}`;
    const response = await fetch(url);
    const payload = await response.json();
    if (!response.ok) {
      dom.result.hidden = true;
      showMessage(t("errorTitle"), payload.detail || `HTTP ${response.status}`, "error");
      return;
    }
    state.report = payload.report;
    state.insights = payload.insights;
    if (!payload.insights.has_forecast) {
      showMessage(t("noForecastTitle"), t("noForecast"), "error");
    } else if (state.report.provider === "demo") {
      showMessage(t("setupTitle"), t("setupBody"), "info");
    } else {
      hideMessage();
    }
    updateWeekSubtitle();
    renderReport();
  } catch (error) {
    dom.result.hidden = true;
    showMessage(t("errorTitle"), String(error), "error");
  } finally {
    setBusy(false);
  }
}

function setBusy(busy) {
  dom.submit.disabled = busy;
  dom.submit.textContent = busy ? t("submitBusy") : t("submit");
}

function formatHour(hour) {
  return `${String(hour).padStart(2, "0")}:00`;
}

function formatTimestamp(iso) {
  const moment = new Date(iso);
  return Number.isNaN(moment.valueOf())
    ? iso
    : moment.toLocaleString(state.language, { dateStyle: "short", timeStyle: "short" });
}

async function switchLanguage(code) {
  state.language = code;
  rememberLanguage(code);
  applyStaticText();
  await loadProviders();
  // Notes and attribution come from the backend in the requested language, so a
  // language switch needs a fresh lookup rather than a re-render. That costs one
  // provider request, which is the honest price for not mixing two languages.
  if (state.report) await runLookup(new Event("submit"));
}

/* Deep links: /?q=Venue,City&provider=serpapi runs the lookup on load, so a
   place can be bookmarked. */
async function applyDeepLink() {
  const params = new URLSearchParams(window.location.search);
  const query = (params.get("q") || "").trim();
  if (query.length < 2) return;
  dom.query.value = query;
  const provider = params.get("provider");
  if (provider && [...dom.provider.options].some((option) => option.value === provider)) {
    dom.provider.value = provider;
  }
  await runLookup(new Event("submit"));
}

async function init() {
  dom.language.value = state.language;
  applyStaticText();
  dom.form.addEventListener("submit", runLookup);
  dom.language.addEventListener("change", (event) => switchLanguage(event.target.value));
  await loadProviders();
  loadVersion();
  applyDeepLink();
}

init();
