const DEBUG_ENABLED_VALUES = new Set(['1', 'true', 'yes', 'on']);

function isDebugEnabled(): boolean {
  const value = process.env.FACT_CHECKER_DEBUG?.toLowerCase();
  return value !== undefined && DEBUG_ENABLED_VALUES.has(value);
}

export function debugLog(stage: string, details?: unknown): void {
  if (!isDebugEnabled()) {
    return;
  }

  if (details === undefined) {
    console.debug(`[fact-checker] ${stage}`);
    return;
  }

  console.debug(`[fact-checker] ${stage} ${String(details)}`);
}
