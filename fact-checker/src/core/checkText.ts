import { extractClaimsFromText } from './claimExtraction';
import { locateExtractedClaims } from './claimLocation';
import { checkFact } from './factCheck';
import { debugLog } from './debug';
import type { FactCheckResult } from './factCheck';
import type { LocatedClaim } from './textSchemas';

export type CheckedTextItem = LocatedClaim & {
  explanation: string;
};

export type CheckTextResult = {
  supported: CheckedTextItem[];
  refuted: CheckedTextItem[];
  notEnoughInfo: CheckedTextItem[];
};

function buildCheckedTextItem(item: LocatedClaim, result: FactCheckResult): CheckedTextItem {
  return {
    ...item,
    explanation: result.explanation,
  };
}

export async function checkText(text: string, apiKey: string): Promise<CheckTextResult> {
  debugLog('extract:start', `textLength=${text.length}`);
  const extractedClaims = await extractClaimsFromText(text, apiKey);
  debugLog('extract:done', `claimsCount=${extractedClaims.length}`);
  const locatedClaims = locateExtractedClaims(text, extractedClaims);
  debugLog('locate:done', `claimsCount=${locatedClaims.length}`);

  const supported: CheckedTextItem[] = [];
  const refuted: CheckedTextItem[] = [];
  const notEnoughInfo: CheckedTextItem[] = [];
  const matchedClaims = locatedClaims.filter(
    (item): item is LocatedClaim & { start: number; end: number } =>
      item.start !== null && item.end !== null
  );

  for (const item of locatedClaims) {
    if (item.start === null || item.end === null) {
      debugLog('claim:skip_unmatched', `claim="${item.claim}" sourceText="${item.sourceText}"`);
      notEnoughInfo.push({
        ...item,
        explanation: 'Could not match extracted source text back to the input text.',
      });
      continue;
    }

  }

  const checkedMatchedClaims = await Promise.all(
    matchedClaims.map(async (item) => {
      try {
        debugLog(
          'claim:check:start',
          `claim="${item.claim}" sourceText="${item.sourceText}" span=${item.start}-${item.end}`
        );
        const result = await checkFact(item.claim, apiKey);
        debugLog('claim:check:done', `claim="${item.claim}" verdict=${result.verdict}`);

        return {
          kind: 'success' as const,
          item,
          result,
        };
      } catch (error) {
        const explanation = error instanceof Error ? error.message : 'Verification failed';
        debugLog('claim:check:error', `claim="${item.claim}" error="${explanation}"`);

        return {
          kind: 'error' as const,
          item,
          explanation,
        };
      }
    })
  );

  for (const checkedClaim of checkedMatchedClaims) {
    if (checkedClaim.kind === 'error') {
      notEnoughInfo.push({
        ...checkedClaim.item,
        explanation: checkedClaim.explanation,
      });
      continue;
    }

    const checkedItem = buildCheckedTextItem(checkedClaim.item, checkedClaim.result);

    if (checkedClaim.result.verdict === 'NOT_ENOUGH_INFO') {
      notEnoughInfo.push(checkedItem);
    } else if (checkedClaim.result.verdict === 'SUPPORTED') {
      supported.push(checkedItem);
    } else {
      refuted.push(checkedItem);
    }
  }

  debugLog(
    'result:summary',
    `supported=${supported.length} refuted=${refuted.length} notEnoughInfo=${notEnoughInfo.length}`
  );

  return { supported, refuted, notEnoughInfo };
}
