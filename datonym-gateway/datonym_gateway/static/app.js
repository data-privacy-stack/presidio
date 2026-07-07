const sourceText = document.querySelector("#sourceText");
const anonymizedText = document.querySelector("#anonymizedText");
const responseText = document.querySelector("#responseText");
const restoredText = document.querySelector("#restoredText");
const mappingList = document.querySelector("#mappingList");
const entityList = document.querySelector("#entityList");
const statusEl = document.querySelector("#status");
const anonymizeButton = document.querySelector("#anonymizeButton");
const restoreButton = document.querySelector("#restoreButton");
const clearButton = document.querySelector("#clearButton");
const sampleButton = document.querySelector("#sampleButton");
const copyButton = document.querySelector("#copyButton");

let currentMapping = [];

const sample = [
  "Hallo, ich bin Max Mustermann von der DatOnym GmbH in Berlin.",
  "Bitte schreibe an max.mustermann@example.de oder rufe +49 30 1234567 an.",
  "Meine IBAN ist DE89370400440532013000 und meine Steuer-ID ist 12 345 678 901.",
].join("\n");

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMapping(entries) {
  currentMapping = entries;
  if (!entries.length) {
    mappingList.className = "mapping-list empty";
    mappingList.textContent = "Keine Tokens";
    return;
  }

  mappingList.className = "mapping-list";
  mappingList.innerHTML = entries
    .map(
      (entry) => `
        <div class="mapping-row">
          <div>
            <div class="token">${escapeHtml(entry.token)}</div>
            <div class="meta">${escapeHtml(entry.entity_type)}</div>
          </div>
          <div class="value">${escapeHtml(entry.original)}</div>
        </div>
      `,
    )
    .join("");
}

function renderEntities(entities) {
  if (!entities.length) {
    entityList.className = "entity-list empty";
    entityList.textContent = "Keine Treffer";
    return;
  }

  entityList.className = "entity-list";
  entityList.innerHTML = entities
    .map((entity) => {
      const score =
        typeof entity.score === "number" ? `Score ${entity.score.toFixed(2)}` : "";
      return `
        <div class="entity-row">
          <div>
            <div class="token">${escapeHtml(entity.token)}</div>
            <div class="meta">${escapeHtml(entity.entity_type)}</div>
          </div>
          <div class="meta">${entity.start}-${entity.end} ${escapeHtml(score)}</div>
        </div>
      `;
    })
    .join("");
}

function restoreWithCurrentMapping(value) {
  return currentMapping.reduce(
    (text, entry) => text.replaceAll(entry.token, entry.original),
    value,
  );
}

async function anonymize() {
  anonymizeButton.disabled = true;
  setStatus("Laeuft");

  try {
    const response = await fetch("/demo/anonymize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: sourceText.value, language: "de" }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Anonymisierung fehlgeschlagen.");
    }

    anonymizedText.value = payload.text;
    responseText.value = payload.text;
    restoredText.value = payload.restored_text;
    renderMapping(payload.mapping);
    renderEntities(payload.entities);
    setStatus(`${payload.mapping.length} Tokens`);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    anonymizeButton.disabled = false;
  }
}

function clearAll() {
  sourceText.value = "";
  anonymizedText.value = "";
  responseText.value = "";
  restoredText.value = "";
  renderMapping([]);
  renderEntities([]);
  setStatus("Bereit");
}

anonymizeButton.addEventListener("click", anonymize);

restoreButton.addEventListener("click", () => {
  restoredText.value = restoreWithCurrentMapping(responseText.value);
});

clearButton.addEventListener("click", clearAll);

sampleButton.addEventListener("click", () => {
  sourceText.value = sample;
});

copyButton.addEventListener("click", async () => {
  await navigator.clipboard.writeText(anonymizedText.value);
  setStatus("Kopiert");
});

sourceText.value = sample;
