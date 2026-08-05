const ANALYTICS_SCHEMA_VERSION = 1;
const ALLOWED_EVENT_TYPES = new Set(["answer_generated", "feedback_submitted"]);
const RAW_SHEET_NAME = "RawEvents";
const ANSWER_FEEDBACK_SHEET_NAME = "AnswerFeedbackView";
const SUMMARY_SHEET_NAME = "Summary";
const OPT_IN_SHEET_NAME = "OptInTextReview";

const RAW_HEADERS = [
  "received_at_utc",
  "schema_version",
  "event_id",
  "event_type",
  "answer_event_id",
  "timestamp_utc",
  "app_variant",
  "app_version",
  "ui_language",
  "question_kind",
  "suggested_question",
  "full_text_consent",
  "question_text",
  "answer_text",
  "question_character_count",
  "answer_character_count",
  "intent",
  "status",
  "guidance_code",
  "error_code",
  "period",
  "routing_source",
  "match_status",
  "routing_confidence",
  "ai_attempted",
  "ai_succeeded",
  "ai_diagnostic_code",
  "mentioned_alliance_count",
  "selected_alliance_count",
  "selected_net_status_count",
  "selected_player_count",
  "total_player_count",
  "helpful",
  "reason",
  "comment",
  "raw_event_json",
];

const ANSWER_FEEDBACK_HEADERS = [
  "answer_event_id",
  "answer_timestamp_utc",
  "app_version",
  "ui_language",
  "question_kind",
  "suggested_question",
  "full_text_consent",
  "question_text",
  "answer_text",
  "intent",
  "status",
  "guidance_code",
  "routing_source",
  "match_status",
  "ai_attempted",
  "ai_succeeded",
  "feedback_timestamp_utc",
  "helpful",
  "feedback_reason",
  "feedback_comment",
];

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return jsonResponse_({ ok: false, error: "missing_body" });
    }

    const envelope = JSON.parse(e.postData.contents);
    const properties = PropertiesService.getScriptProperties();
    const expectedSecret = properties.getProperty("ANALYTICS_SHARED_SECRET");
    const spreadsheetId = properties.getProperty("SPREADSHEET_ID");

    if (!expectedSecret || !spreadsheetId) {
      return jsonResponse_({ ok: false, error: "receiver_not_configured" });
    }
    if (!constantTimeEquals_(String(envelope.secret || ""), expectedSecret)) {
      return jsonResponse_({ ok: false, error: "forbidden" });
    }

    const event = validateEvent_(envelope.event);
    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
      appendRawEvent_(spreadsheet, event);
      rebuildDerivedSheets_(spreadsheet);
    } finally {
      lock.releaseLock();
    }

    return jsonResponse_({ ok: true, event_id: event.event_id });
  } catch (error) {
    console.error(error);
    return jsonResponse_({ ok: false, error: "receiver_error" });
  }
}

function setupSheets() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    throw new Error("Open this script from the target Google Spreadsheet before running setupSheets().");
  }

  PropertiesService.getScriptProperties().setProperty(
    "SPREADSHEET_ID",
    spreadsheet.getId()
  );

  const rawSheet = getOrCreateSheet_(spreadsheet, RAW_SHEET_NAME);
  ensureHeaders_(rawSheet, RAW_HEADERS);
  getOrCreateSheet_(spreadsheet, ANSWER_FEEDBACK_SHEET_NAME);
  getOrCreateSheet_(spreadsheet, SUMMARY_SHEET_NAME);
  getOrCreateSheet_(spreadsheet, OPT_IN_SHEET_NAME);
  rebuildDerivedSheets_(spreadsheet);
}

function rebuildAnalyticsViews() {
  const spreadsheetId = PropertiesService.getScriptProperties().getProperty("SPREADSHEET_ID");
  if (!spreadsheetId) {
    throw new Error("Run setupSheets() first.");
  }
  rebuildDerivedSheets_(SpreadsheetApp.openById(spreadsheetId));
}

function validateEvent_(event) {
  if (!event || typeof event !== "object" || Array.isArray(event)) {
    throw new Error("invalid_event");
  }
  if (event.schema_version !== ANALYTICS_SCHEMA_VERSION) {
    throw new Error("unsupported_schema_version");
  }
  if (!ALLOWED_EVENT_TYPES.has(event.event_type)) {
    throw new Error("unsupported_event_type");
  }
  if (typeof event.event_id !== "string" || !event.event_id.trim()) {
    throw new Error("missing_event_id");
  }
  if (
    event.event_type === "feedback_submitted" &&
    (typeof event.answer_event_id !== "string" || !event.answer_event_id.trim())
  ) {
    throw new Error("missing_answer_event_id");
  }

  const serialized = JSON.stringify(event);
  if (serialized.length > 64000) {
    throw new Error("event_too_large");
  }
  return event;
}

function appendRawEvent_(spreadsheet, event) {
  const sheet = getOrCreateSheet_(spreadsheet, RAW_SHEET_NAME);
  ensureHeaders_(sheet, RAW_HEADERS);

  const rowObject = Object.assign(
    { received_at_utc: new Date().toISOString() },
    event,
    { raw_event_json: JSON.stringify(event) }
  );
  const row = RAW_HEADERS.map((header) => safeCellValue_(rowObject[header]));
  sheet.appendRow(row);
}

function rebuildDerivedSheets_(spreadsheet) {
  const events = readRawEvents_(spreadsheet);
  const answers = events.filter((event) => event.event_type === "answer_generated");
  const feedback = events.filter((event) => event.event_type === "feedback_submitted");

  const feedbackByAnswer = {};
  feedback.forEach((event) => {
    const previous = feedbackByAnswer[event.answer_event_id];
    if (!previous || String(previous.timestamp_utc || "") <= String(event.timestamp_utc || "")) {
      feedbackByAnswer[event.answer_event_id] = event;
    }
  });

  const joinedRows = answers.map((answer) => {
    const feedbackEvent = feedbackByAnswer[answer.event_id] || {};
    return [
      answer.event_id,
      answer.timestamp_utc,
      answer.app_version,
      answer.ui_language,
      answer.question_kind,
      answer.suggested_question,
      answer.full_text_consent,
      answer.question_text,
      answer.answer_text,
      answer.intent,
      answer.status,
      answer.guidance_code,
      answer.routing_source,
      answer.match_status,
      answer.ai_attempted,
      answer.ai_succeeded,
      feedbackEvent.timestamp_utc,
      feedbackEvent.helpful,
      feedbackEvent.reason,
      feedbackEvent.comment,
    ].map(safeCellValue_);
  });

  writeTable_(
    getOrCreateSheet_(spreadsheet, ANSWER_FEEDBACK_SHEET_NAME),
    ANSWER_FEEDBACK_HEADERS,
    joinedRows
  );

  const optInRows = joinedRows.filter((row) => row[6] === true);
  writeTable_(
    getOrCreateSheet_(spreadsheet, OPT_IN_SHEET_NAME),
    ANSWER_FEEDBACK_HEADERS,
    optInRows
  );

  writeSummary_(spreadsheet, answers, feedback, feedbackByAnswer);
}

function readRawEvents_(spreadsheet) {
  const sheet = getOrCreateSheet_(spreadsheet, RAW_SHEET_NAME);
  ensureHeaders_(sheet, RAW_HEADERS);
  if (sheet.getLastRow() < 2) {
    return [];
  }

  const values = sheet
    .getRange(2, 1, sheet.getLastRow() - 1, RAW_HEADERS.length)
    .getValues();
  const rawIndex = RAW_HEADERS.indexOf("raw_event_json");
  const events = [];
  values.forEach((row) => {
    try {
      const event = JSON.parse(String(row[rawIndex] || ""));
      events.push(validateEvent_(event));
    } catch (error) {
      console.warn("Skipping malformed RawEvents row", error);
    }
  });
  return events;
}

function writeSummary_(spreadsheet, answers, feedback, feedbackByAnswer) {
  const helpfulCount = feedback.filter((event) => event.helpful === true).length;
  const unsupportedCount = answers.filter(
    (event) =>
      event.intent === "unsupported_question" || event.match_status === "unsupported"
  ).length;
  const aiAttemptCount = answers.filter((event) => event.ai_attempted === true).length;
  const aiSuccessCount = answers.filter((event) => event.ai_succeeded === true).length;
  const orphanFeedbackCount = feedback.filter(
    (event) => !answers.some((answer) => answer.event_id === event.answer_event_id)
  ).length;

  const rows = [
    ["Metric", "Value"],
    ["Answers", answers.length],
    ["Feedback", feedback.length],
    ["Feedback coverage", percent_(Object.keys(feedbackByAnswer).length, answers.length)],
    ["Helpful rate", percent_(helpfulCount, feedback.length)],
    ["Unsupported rate", percent_(unsupportedCount, answers.length)],
    ["AI attempt count", aiAttemptCount],
    ["AI success rate", percent_(aiSuccessCount, aiAttemptCount)],
    ["Full-text opt-in count", answers.filter((event) => event.full_text_consent === true).length],
    ["Orphan feedback count", orphanFeedbackCount],
    [],
    ["Intent", "Count"],
    ...counterRows_(answers, "intent"),
    [],
    ["UI language", "Count"],
    ...counterRows_(answers, "ui_language"),
    [],
    ["App version", "Count"],
    ...counterRows_(answers, "app_version"),
    [],
    ["Feedback reason", "Count"],
    ...counterRows_(feedback, "reason"),
  ];

  const sheet = getOrCreateSheet_(spreadsheet, SUMMARY_SHEET_NAME);
  sheet.clearContents();
  if (rows.length) {
    const width = Math.max.apply(
      null,
      rows.map((row) => row.length)
    );
    const padded = rows.map((row) => row.concat(Array(width - row.length).fill("")));
    sheet.getRange(1, 1, padded.length, width).setValues(padded);
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, width);
  }
}

function counterRows_(events, field) {
  const counts = {};
  events.forEach((event) => {
    const key = String(event[field] || "(blank)");
    counts[key] = (counts[key] || 0) + 1;
  });
  return Object.keys(counts)
    .sort()
    .map((key) => [safeCellValue_(key), counts[key]]);
}

function percent_(numerator, denominator) {
  return denominator ? numerator / denominator : "";
}

function writeTable_(sheet, headers, rows) {
  sheet.clearContents();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (rows.length) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, headers.length);
}

function ensureHeaders_(sheet, headers) {
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
    return;
  }
  const existing = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  if (JSON.stringify(existing) !== JSON.stringify(headers)) {
    throw new Error("RawEvents headers do not match the expected schema.");
  }
}

function getOrCreateSheet_(spreadsheet, name) {
  return spreadsheet.getSheetByName(name) || spreadsheet.insertSheet(name);
}

function safeCellValue_(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    value = JSON.stringify(value);
  }
  if (typeof value !== "string") {
    return value;
  }

  // Prevent spreadsheet formula injection for user-controlled text.
  if (/^[=+\-@\t\r]/.test(value)) {
    return "'" + value;
  }
  return value;
}

function constantTimeEquals_(left, right) {
  if (left.length !== right.length) {
    return false;
  }
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function jsonResponse_(payload) {
  return ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(
    ContentService.MimeType.JSON
  );
}
