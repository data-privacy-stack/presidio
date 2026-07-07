const promptInput = document.querySelector("#promptInput");
const anonymizedOutput = document.querySelector("#anonymizedOutput");
const llmResponseInput = document.querySelector("#llmResponseInput");
const personalizedOutput = document.querySelector("#personalizedOutput");
const mappingList = document.querySelector("#mappingList");
const entityList = document.querySelector("#entityList");
const mappingCount = document.querySelector("#mappingCount");
const entityCount = document.querySelector("#entityCount");
const statusEl = document.querySelector("#status");
const responseDropZone = document.querySelector("#responseDropZone");

let currentMapping = [];
let currentEntities = [];

const samplePrompt = [
  "UVZ-Nr. 14-23 / 2025-sr",
  "Am ersten August 2025 sind vor mir Dr. Maria Sommer, Notarin in Krumbach (Schwaben),",
  "in meinen Amtsraeumen in 86381 Krumbach, Nassauer Strasse 8 gleichzeitig anwesend:",
  "1. Herr Max Mustermann, geboren am 01.08.1975,",
  "wohnhaft in 86473 Ziemetshausen-Hellersberg,",
  "Kapellenstrasse 2,",
  "E-Mail: max.mustermann@example.de, Telefon: +49 30 1234567.",
].join("\n");

const TOKEN_PATTERN = /#DATONYM_([A-Z0-9_]+)_(\d{4})#/gu;
const STREET_SOURCE =
  "(?:[A-ZÄÖÜ][\\p{L}äöüßÄÖÜ.-]+(?:\\s+[A-ZÄÖÜa-zäöüß][\\p{L}äöüßÄÖÜ.-]+){0,3}\\s+(?:Straße|Strasse|Str\\.|Weg|Platz|Allee|Gasse|Ring|Damm|Ufer|Steig|Pfad|Hof|Markt)|[A-ZÄÖÜ][\\p{L}äöüßÄÖÜ.-]*(?:straße|strasse|weg|platz|allee|gasse|ring|damm|ufer|steig|pfad|hof|markt))\\s+\\d+[a-zA-Z]?(?:\\s*[-/]\\s*\\d+[a-zA-Z]?)?";
const POSTAL_CITY_SOURCE =
  "\\d{5}\\s+[A-ZÄÖÜ][\\p{L}äöüßÄÖÜ.-]+(?:\\s+(?:a\\.\\s*d\\.|a\\.|d\\.|an|der|am|im|[A-ZÄÖÜ][\\p{L}äöüßÄÖÜ.-]+))*?(?:-[A-ZÄÖÜa-zäöüß][\\p{L}äöüßÄÖÜ.-]+)*";
const STREET_PATTERN = new RegExp(STREET_SOURCE, "iu");
const POSTAL_CITY_PATTERN = new RegExp(POSTAL_CITY_SOURCE, "iu");

const recognizers = [
  {
    entityType: "ADDRESS",
    find: findGermanAddresses,
  },
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
      /\b(?:\d{1,2}\.\d{1,2}\.\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\.\s*(?:Januar|Februar|Maerz|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}|(?:ersten|zweiten|dritten|vierten|fuenften|fünften|sechsten|siebten|achten|neunten|zehnten|elften|zwoelften|zwölften|dreizehnten|vierzehnten|fuenfzehnten|fünfzehnten|sechzehnten|siebzehnten|achtzehnten|neunzehnten|zwanzigsten|einundzwanzigsten|zweiundzwanzigsten|dreiundzwanzigsten|vierundzwanzigsten|fuenfundzwanzigsten|fünfundzwanzigsten|sechsundzwanzigsten|siebenundzwanzigsten|achtundzwanzigsten|neunundzwanzigsten|dreissigsten|dreißigsten|einunddreissigsten|einunddreißigsten)\s+(?:Januar|Februar|Maerz|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}|(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),?\s+\d{1,2}\.\d{1,2}\.)\b/giu,
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
    find: findContextLocations,
  },
  {
    entityType: "LOCATION",
    pattern:
      /\b(?:Berlin|Hamburg|Muenchen|München|Koeln|Köln|Frankfurt|Stuttgart|Duesseldorf|Düsseldorf|Dortmund|Essen|Leipzig|Bremen|Dresden|Hannover|Nuernberg|Nürnberg|Wien|Zuerich|Zürich|Basel|Bern|Luxemburg|Krumbach|Ziemetshausen-Hellersberg|Pfaffenhofen a\. d\. Roth-Roth)\b/gu,
  },
  {
    entityType: "DE_PLZ_LOCATION",
    pattern: new RegExp(`\\b${POSTAL_CITY_SOURCE}\\b`, "gu"),
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

function existingTokenRanges(text) {
  TOKEN_PATTERN.lastIndex = 0;
  return Array.from(text.matchAll(TOKEN_PATTERN), (match) => ({
    start: match.index,
    end: match.index + match[0].length,
    entityType: match[1],
    index: Number(match[2]),
  }));
}

function overlapsToken(start, end, tokenRanges) {
  return tokenRanges.some((range) => start < range.end && end > range.start);
}

function collectMatches(text) {
  const matches = [];
  const tokenRanges = existingTokenRanges(text);
  recognizers.forEach((recognizer, priority) => {
    if (recognizer.find) {
      recognizer.find(text).forEach((item) => {
        if (!overlapsToken(item.start, item.end, tokenRanges)) {
          matches.push({ ...item, entityType: recognizer.entityType, priority });
        }
      });
      return;
    }

    recognizer.pattern.lastIndex = 0;
    for (const match of text.matchAll(recognizer.pattern)) {
      const value = recognizer.useGroup ? match[recognizer.useGroup] : match[0];
      if (!value) {
        continue;
      }

      const groupOffset = recognizer.useGroup ? match[0].indexOf(value) : 0;
      const start = match.index + groupOffset;
      const end = start + value.length;
      if (overlapsToken(start, end, tokenRanges)) {
        continue;
      }
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

function getLineRanges(text) {
  const lines = [];
  const pattern = /.*(?:\r?\n|$)/gu;
  for (const match of text.matchAll(pattern)) {
    if (!match[0]) {
      continue;
    }
    const raw = match[0];
    const content = raw.replace(/\r?\n$/u, "");
    lines.push({
      text: content,
      start: match.index,
      end: match.index + content.length,
      rawEnd: match.index + raw.length,
    });
  }
  return lines;
}

function trimMatch(text, start, end) {
  while (start < end && /[\s,]/u.test(text[start])) {
    start += 1;
  }
  while (end > start && /[\s,]/u.test(text[end - 1])) {
    end -= 1;
  }
  return { start, end, original: text.slice(start, end) };
}

function findGermanAddresses(text) {
  const matches = [];
  const lines = getLineRanges(text);
  const sameLinePattern = new RegExp(`${POSTAL_CITY_SOURCE}\\s*,\\s*${STREET_SOURCE}`, "giu");

  for (const match of text.matchAll(sameLinePattern)) {
    matches.push(trimMatch(text, match.index, match.index + match[0].length));
  }

  lines.forEach((line, index) => {
    const postalMatch = line.text.match(POSTAL_CITY_PATTERN);
    if (!postalMatch || postalMatch.index === undefined) {
      return;
    }

    const nextLine = lines[index + 1];
    if (!nextLine) {
      return;
    }

    const streetMatch = nextLine.text.match(STREET_PATTERN);
    if (!streetMatch || streetMatch.index === undefined) {
      return;
    }

    const start = line.start + postalMatch.index;
    const end = nextLine.start + streetMatch.index + streetMatch[0].length;
    matches.push(trimMatch(text, start, end));
  });

  return matches;
}

function findContextLocations(text) {
  const matches = [];
  const pattern =
    /\b(?:in|aus|bei|nach)\s+([A-ZÄÖÜ][\p{L}äöüßÄÖÜ.-]+(?:\s+(?:a\.\s*d\.|a\.|d\.|[A-ZÄÖÜ][\p{L}äöüßÄÖÜ.-]+|\([^)]+\))){0,4}(?:-[A-ZÄÖÜa-zäöüß][\p{L}äöüßÄÖÜ.-]+)*)/gu;

  for (const match of text.matchAll(pattern)) {
    const original = match[1];
    const start = match.index + match[0].indexOf(original);
    matches.push({
      start,
      end: start + original.length,
      original,
    });
  }

  return matches;
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

function createTokenFactory(text) {
  const byValue = new Map();
  const counters = new Map();

  existingTokenRanges(text).forEach((token) => {
    counters.set(token.entityType, Math.max(counters.get(token.entityType) || 0, token.index));
  });

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
  const matches = collectMatches(text);
  const tokenFor = createTokenFactory(text);
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
    llmResponseInput.value = "";
    personalizedOutput.value = "";
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
