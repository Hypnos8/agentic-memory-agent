"use strict";
const unavailable = "Nicht verfügbar";
let runs = [];
let selected = null;
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};
const value = input => input === null || input === undefined ? unavailable :
  typeof input === "object" ? JSON.stringify(input, null, 2) : String(input);
const duration = input => typeof input === "number" ? `${input.toFixed(2)} s` : unavailable;
const key = entry => `${entry.line}:${value(entry.record.task_id)}`;
const status = record => record.success === true ? "Erfolgreich" : record.success === false ? "Nicht erfolgreich" : unavailable;
function badge(record) { return node("span", status(record), `badge ${record.success === true ? "good" : record.success === false ? "bad" : ""}`); }
function disclosure(title, content) {
  const details = node("details");
  details.append(node("summary", title), node("pre", value(content)));
  return details;
}
function render() {
  const list = document.getElementById("runs");
  list.replaceChildren();
  document.getElementById("count").textContent = runs.length;
  for (const entry of runs) {
    const record = entry.record;
    const button = node("button", undefined, "run");
    button.type = "button";
    button.setAttribute("aria-current", String(key(entry) === selected));
    button.append(badge(record), node("span", value(record.question), "run-title"),
      node("span", `${value(record.task_id).slice(0, 12)} · ${duration(record.duration_seconds)}`, "run-meta"));
    button.addEventListener("click", () => { selected = key(entry); render(); });
    list.append(button);
  }
  const detail = document.getElementById("detail");
  detail.replaceChildren();
  const entry = runs.find(item => key(item) === selected);
  if (!entry) { detail.append(node("p", "Noch keine Läufe vorhanden", "empty")); return; }
  const record = entry.record;
  detail.append(badge(record), node("h2", value(record.question), "question"), node("p", `Task-ID: ${value(record.task_id)}`, "id"));
  const metadata = node("div", undefined, "meta");
  metadata.append(node("span", `Modell: ${value(record.model)}`), node("span", `Prompt: ${value(record.prompt_version)}`),
    node("span", `Abbruchgrund: ${value(record.termination_reason)}`));
  const metrics = node("div", undefined, "metrics");
  for (const [label, content] of [["Laufzeit", duration(record.duration_seconds)], ["LLM-Aufrufe", value(record.llm_calls)],
    ["Tool-Aufrufe", value(record.tool_calls)], ["Input-Tokens", value(record.input_tokens)],
    ["Output-Tokens", value(record.output_tokens)], ["Tokens gesamt", value(record.total_tokens)]]) {
    const metric = node("div", undefined, "metric");
    metric.append(node("span", label), node("strong", content)); metrics.append(metric);
  }
  detail.append(metadata, metrics, node("h3", "Antwort"), node("div", value(record.final_answer), "answer"));
  if (record.error) detail.append(node("h3", "Fehler"), node("div", value(record.error), "error"));
  renderMemory(detail, record);
  detail.append(node("h2", "Interaktionen", "section-title"));
  const labels = {llm_call: "Modell aufgerufen", llm_response: "Modellantwort", llm_error: "Modellfehler",
    tool_call: "Tool aufgerufen", tool_result: "Tool-Ergebnis", tool_error: "Tool-Fehler",
    memory_retrieve: "Memory-Abruf", memory_retrieve_result: "Memory-Ergebnis", memory_retrieve_error: "Memory-Fehler"};
  if (Array.isArray(record.events) && record.events.length) {
    record.events.forEach((event, i) => {
      const title = event && typeof event === "object" ? (labels[event.type] || value(event.type)) +
        (event.name ? ` · ${event.name}` : event.tool_call_id ? ` · ${event.tool_call_id}` : "") : "Eintrag";
      detail.append(disclosure(`${i + 1}. ${title}`, event));
    });
  } else detail.append(node("p", "Keine Interaktionsdaten verfügbar.", "muted"));
  detail.append(disclosure("Konfiguration", record.configuration), disclosure("Gespräch", record.messages));
}
function renderMemory(detail, record) {
  detail.append(node("h2", "Memory", "section-title"));
  const events = Array.isArray(record.events) ? record.events : [];
  const request = events.find(event => event?.type === "memory_retrieve");
  const outcome = events.find(event => ["memory_retrieve_result", "memory_retrieve_error"].includes(event?.type));
  if (!request) {
    detail.append(node("p", "Memory-Daten nicht verfügbar.", "muted"));
    return;
  }
  detail.append(node("p", `Strategie: ${value(record.memory_strategy)}`),
    node("p", `Abrufdauer: ${duration(outcome?.duration_seconds)} · k: ${value(request.k)}`));
  if (outcome?.type === "memory_retrieve_error") {
    detail.append(node("div", value(outcome.error), "error"));
    return;
  }
  if (!outcome) {
    detail.append(node("p", "Kein Abrufresultat verfügbar.", "muted"));
    return;
  }
  const memories = Array.isArray(record.retrieved_memories) ? record.retrieved_memories : [];
  detail.append(node("p", record.memory_strategy === "no_memory" ? "No-Memory-Baseline: keine Erinnerungen." :
    `Gefundene Erfahrungen: ${value(outcome.count)}`));
  memories.forEach((memory, i) => detail.append(disclosure(`${i + 1}. Erfahrung · ${value(memory.id)}`, memory)));
  detail.append(node("p", "Der eingefügte Memory-Prompt ist im Gespräch einsehbar. Ein Abruf allein belegt keine Nutzung durch das Modell.", "muted"));
}
async function refresh() {
  const button = document.getElementById("refresh");
  const notice = document.getElementById("notice");
  button.disabled = true;
  try {
    const response = await fetch("/api/runs", {cache: "no-store"});
    if (!response.ok) throw new Error("Läufe konnten nicht geladen werden. Bitte erneut versuchen.");
    const data = await response.json();
    runs = data.runs;
    if (!runs.some(item => key(item) === selected)) selected = runs.length ? key(runs[0]) : null;
    notice.textContent = data.invalid_lines.length ? `Ungültige Logzeilen übersprungen: ${data.invalid_lines.join(", ")}` : "";
    render();
  } catch (error) {
    notice.textContent = error.message;
    if (!runs.length) document.getElementById("detail").replaceChildren(node("p", "Keine Daten geladen.", "empty"));
  } finally { button.disabled = false; }
}
document.getElementById("refresh").addEventListener("click", refresh);
refresh();
