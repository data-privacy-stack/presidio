const promptInput = document.querySelector("#promptInput");
const anonymizedOutput = document.querySelector("#anonymizedOutput");
const llmResponseInput = document.querySelector("#llmResponseInput");
const personalizedOutput = document.querySelector("#personalizedOutput");
const mappingList = document.querySelector("#mappingList");
const entityList = document.querySelector("#entityList");
const mappingCount = document.querySelector("#mappingCount");
const entityCount = document.querySelector("#entityCount");
const statusEl = document.querySelector("#status");
const promptDragHandle = document.querySelector("#promptDragHandle");
const responseDropZone = document.querySelector("#responseDropZone");

let currentMapping = [];
let currentEntities = [];

const samplePrompt = [
  "Bitte formuliere eine freundliche Antwort an Max Mustermann von der DatOnym GmbH in Berlin.",
  "Er ist erreichbar unter max.mustermann@example.de oder +49 30 1234567.",
  "Seine IBAN lautet DE89370400440532013000, die Steuer-ID ist 12 345 678 901.",
].join("\n");

const recognizers = [
  {
    entityType: "EMAIL_ADDRESS",
    pattern: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/giu,
  },
  {
    entityType: "URL",
    pattern: /\b(?:https?:\/\/|www\.)[^\s<>"']+/giu,
  },
  {
    entityType: "IBAN_CODE",
    pattern: /\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b/giu,
    validate: (value) => /^DE|^AT|^CH|^LU/i.test(value.replaceAll(" ", "")),
  },
  {
    entityType: "PHONE_NUMBER",
    pattern:
      /(?:^|[^\w])((?:(?:\+|00)(?:49|43|41|352)[\s/-]?|0)(?:\(?\d{2,5}\)?[\s/-]?)\d(?:[\d\s/-]{4,})\d)\b/giu,
    useGroup: 1,
  },
  {
    entityType: "CREDIT_CARD",
    pattern: /\b(?:\d[ -]*?){13,19}\b/gu,
    validate: isLikelyCreditCard,
  },
  {
    entityType: "IP_ADDRESS",
    pattern:
      /\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/gu,
  },
  {
    entityType: "DE_TAX_ID",
    pattern: /\b\d{2}[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}\b/gu,
  },
  {
    entityType: "DATE_TIME",
    pattern:
      /\b(?:\d{1,2}\.\d{1,2}\.\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),?\s+\d{1,2}\.\d{1,2}\.)\b/giu,
  },
  {
    entityType: "ORGANIZATION",
    pattern:
      /\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,4}\s+(?:GmbH|AG|UG|KG|OHG|SE|GbR|e\.K\.)\b/gu,
  },
  {
    entityType: "PERSON",
    pattern:
      /\b(?:Herr|Frau|Dr\.|Prof\.|Name ist|ich bin|an)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b/gu,
    useGroup: 1,
  },
  {
    entityType: "LOCATION",
    pattern:
      /\b(?:Berlin|Hamburg|Muenchen|Koeln|Frankfurt|Stuttgart|Duesseldorf|Dortmund|Essen|Leipzig|Bremen|Dresden|Hannover|Nuernberg|Wien|Zuerich|Basel|Bern|Luxemburg)\b/gu,
  },
];

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function isLikelyCreditCard(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length < 13 || digits.length > 19) {
    return false;
  }

  let sum = 0;
  let shouldDouble = false;
  for (let index = digits.length - 1; index >= 0; index -= 1) {
    let digit = Number(digits[index]);
    if (shouldDouble) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }
    sum += digit;
    shouldDouble = !shouldDouble;
  }
  return sum % 10 === 0;
}

function normalizeEntityType(entityType) {
  return entityType.toUpperCase().replace(/[^A-Z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function collectMatches(text) {
  const matches = [];
  recognizers.forEach((recognizer, priority) => {
    recognizer.pattern.lastIndex = 0;
    for (const match of text.matchAll(recognizer.pattern)) {
      const value = recognizer.useGroup ? match[recognizer.useGroup] : match[0];
      if (!value) {
        continue;
      }

      const groupOffset = recognizer.useGroup ? match[0].indexOf(value) : 0;
      const start = match.index + groupOffset;
      const end = start + value.length;
      if (recognizer.validate && !recognizer.validate(value)) {
        continue;
      }

      matches.push({
        entityType: recognizer.entityType,
        original: value,
        start,
        end,
        priority,
      });
    }
  });

  return removeOverlaps(matches);
}

function removeOverlaps(matches) {
  const accepted = [];
  const ordered = matches.sort((left, right) => {
    const lengthDiff = right.end - right.start - (left.end - left.start);
    return lengthDiff || left.priority - right.priority || left.start - right.start;
  });

  ordered.forEach((candidate) => {
    const overlaps = accepted.some(
      (item) => candidate.start < item.end && candidate.end > item.start,
    );
    if (!overlaps) {
      accepted.push(candidate);
    }
  });

  return accepted.sort((left, right) => left.start - right.start);
}

function createTokenFactory() {
  const byValue = new Map();
  const counters = new Map();

  return (entityType, original) => {
    const normalized = normalizeEntityType(entityType);
    const key = `${normalized}\u0000${original}`;
    if (byValue.has(key)) {
      return byValue.get(key);
    }

    const next = (counters.get(normalized) || 0) + 1;
    counters.set(normalized, next);
    const token = `#DATONYM_${normalized}_${String(next).padStart(4, "0")}#`;
    byValue.set(key, token);
    return token;
  };
}

function anonymizeText(text) {
  if (/#DATONYM_[A-Z0-9_]+_\d{4}#/u.test(text)) {
    throw new Error("Der Prompt enthaelt bereits DatOnym-Tokens.");
  }

  const matches = collectMatches(text);
  const tokenFor = createTokenFactory();
  const mappingByToken = new Map();
  const entities = matches.map((match) => {
    const token = tokenFor(match.entityType, match.original);
    mappingByToken.set(token, {
      entityType: normalizeEntityType(match.entityType),
      token,
      original: match.original,
    });
    return { ...match, token };
  });

  let anonymized = text;
  entities
    .slice()
    .reverse()
    .forEach((entity) => {
      anonymized =
        anonymized.slice(0, entity.start) + entity.token + anonymized.slice(entity.end);
    });

  return {
    text: anonymized,
    entities,
    mapping: Array.from(mappingByToken.values()),
  };
}

function personalizeText(text) {
  return currentMapping.reduce(
    (result, entry) => result.replaceAll(entry.token, entry.original),
    text,
  );
}

function renderMapping(entries) {
  mappingCount.textContent = `${entries.length} Tokens`;
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
            <div class="meta">${escapeHtml(entry.entityType)}</div>
          </div>
          <div class="value">${escapeHtml(entry.original)}</div>
        </div>
      `,
    )
    .join("");
}

function renderEntities(entities) {
  entityCount.textContent = `${entities.length} Treffer`;
  if (!entities.length) {
    entityList.className = "entity-list empty";
    entityList.textContent = "Keine Treffer";
    return;
  }

  entityList.className = "entity-list";
  entityList.innerHTML = entities
    .map(
      (entity) => `
        <div class="entity-row">
          <div>
            <div class="token">${escapeHtml(entity.token)}</div>
            <div class="meta">${escapeHtml(entity.entityType)}</div>
          </div>
          <div>
            <div class="snippet">${escapeHtml(entity.original)}</div>
            <div class="meta">${entity.start}-${entity.end}</div>
          </div>
        </div>
      `,
    )
    .join("");
}

function runAnonymize() {
  try {
    const result = anonymizeText(promptInput.value);
    currentMapping = result.mapping;
    currentEntities = result.entities;
    anonymizedOutput.value = result.text;
    llmResponseInput.value = result.text;
    personalizedOutput.value = personalizeText(result.text);
    renderMapping(currentMapping);
    renderEntities(currentEntities);
    setStatus(`${currentMapping.length} Tokens`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

function clearAll() {
  promptInput.value = "";
  anonymizedOutput.value = "";
  llmResponseInput.value = "";
  personalizedOutput.value = "";
  currentMapping = [];
  currentEntities = [];
  renderMapping([]);
  renderEntities([]);
  setStatus("Bereit");
}

async function copyText(value, label) {
  await navigator.clipboard.writeText(value);
  setStatus(label);
}

document.querySelector("#anonymizeButton").addEventListener("click", runAnonymize);
document.querySelector("#clearButton").addEventListener("click", clearAll);
document.querySelector("#sampleButton").addEventListener("click", () => {
  promptInput.value = samplePrompt;
});
document.querySelector("#personalizeButton").addEventListener("click", () => {
  personalizedOutput.value = personalizeText(llmResponseInput.value);
  setStatus("Personalisiert");
});
document.querySelector("#copyPromptButton").addEventListener("click", () => {
  copyText(anonymizedOutput.value, "Prompt kopiert");
});
document.querySelector("#copyResponseButton").addEventListener("click", () => {
  copyText(personalizedOutput.value, "Antwort kopiert");
});
document.querySelector("#pasteDemoButton").addEventListener("click", () => {
  llmResponseInput.value =
    "Gerne. Ich formuliere eine Antwort an #DATONYM_PERSON_0001# von #DATONYM_ORGANIZATION_0001#.";
});

promptDragHandle.addEventListener("dragstart", (event) => {
  event.dataTransfer.effectAllowed = "copy";
  event.dataTransfer.setData("text/plain", anonymizedOutput.value);
});

responseDropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  responseDropZone.classList.add("active");
});

responseDropZone.addEventListener("dragleave", () => {
  responseDropZone.classList.remove("active");
});

responseDropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  responseDropZone.classList.remove("active");
  const droppedText = event.dataTransfer.getData("text/plain");
  if (droppedText) {
    llmResponseInput.value = droppedText;
  }
});

promptInput.value = samplePrompt;
renderMapping([]);
renderEntities([]);
