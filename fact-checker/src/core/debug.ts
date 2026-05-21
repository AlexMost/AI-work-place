const DEBUG_ENABLED_VALUES = new Set(['1', 'true', 'yes', 'on']);
const DEBUG_DISABLED_VALUES = new Set(['0', 'false', 'no', 'off']);

function isDebugEnabled(): boolean {
  try {
    if (typeof window !== 'undefined') {
      const flag = window.localStorage?.getItem('fact-checker-debug')?.toLowerCase();
      if (flag && DEBUG_DISABLED_VALUES.has(flag)) return false;
      return true;
    }
    const value = (
      globalThis as { process?: { env?: Record<string, string | undefined> } }
    ).process?.env?.FACT_CHECKER_DEBUG?.toLowerCase();
    return value !== undefined && DEBUG_ENABLED_VALUES.has(value);
  } catch {
    return false;
  }
}

export function debugLog(stage: string, details?: unknown): void {
  if (!isDebugEnabled()) {
    return;
  }

  if (details === undefined) {
    console.debug(`[fact-checker] ${stage}`);
    return;
  }

  if (typeof details === 'string') {
    console.debug(`[fact-checker] ${stage} ${details}`);
    return;
  }

  console.debug(`[fact-checker] ${stage}`, details);
}
