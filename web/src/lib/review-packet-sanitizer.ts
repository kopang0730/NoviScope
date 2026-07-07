const HIDDEN_REVIEW_PAYLOAD_KEYS = new Set([
  "api_key",
  "encrypted_api_key",
  "raw_response",
  "secret",
  "token",
]);

type SanitizedPayloadValue = {
  readonly hiddenFields: readonly string[];
  readonly value: unknown;
};

export type SanitizedPayloadRecord = {
  readonly hiddenFields: readonly string[];
  readonly payload: Record<string, unknown>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function sanitizePayloadValue(value: unknown, parentPath: string): SanitizedPayloadValue {
  if (Array.isArray(value)) {
    const hiddenFields: string[] = [];
    const sanitizedItems = value.map((item, index) => {
      const child = sanitizePayloadValue(item, `${parentPath}[${index}]`);
      hiddenFields.push(...child.hiddenFields);
      return child.value;
    });
    return { hiddenFields, value: sanitizedItems };
  }

  if (isRecord(value)) {
    const hiddenFields: string[] = [];
    const sanitized: Record<string, unknown> = {};
    for (const [fieldName, item] of Object.entries(value)) {
      const childPath = `${parentPath}.${fieldName}`;
      if (HIDDEN_REVIEW_PAYLOAD_KEYS.has(fieldName)) {
        hiddenFields.push(childPath);
        continue;
      }
      const child = sanitizePayloadValue(item, childPath);
      sanitized[fieldName] = child.value;
      hiddenFields.push(...child.hiddenFields);
    }
    return { hiddenFields, value: sanitized };
  }

  return { hiddenFields: [], value };
}

export function sanitizeReviewPayload(
  payload: Record<string, unknown>,
  rootPath: string,
): SanitizedPayloadRecord {
  const sanitized = sanitizePayloadValue(payload, rootPath);
  if (isRecord(sanitized.value)) {
    return { hiddenFields: sanitized.hiddenFields, payload: sanitized.value };
  }
  return { hiddenFields: sanitized.hiddenFields, payload: {} };
}
