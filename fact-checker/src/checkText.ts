import { extractClaimsFromText } from './claimExtraction';
import { locateExtractedClaims } from './claimLocation';
import { checkFact } from './factCheck';
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

export async function checkText(text: string): Promise<CheckTextResult> {
  const extractedClaims = await extractClaimsFromText(text);
  const locatedClaims = locateExtractedClaims(text, extractedClaims);

  const supported: CheckedTextItem[] = [];
  const refuted: CheckedTextItem[] = [];
  const notEnoughInfo: CheckedTextItem[] = [];

  for (const item of locatedClaims) {
    if (item.start === null || item.end === null) {
      notEnoughInfo.push({
        ...item,
        explanation: 'Could not match extracted source text back to the input text.',
      });
      continue;
    }

    try {
      const result = await checkFact(item.claim);
      const checkedItem = buildCheckedTextItem(item, result);

      if (result.verdict === 'NOT_ENOUGH_INFO') {
        notEnoughInfo.push(checkedItem);
      } else if (result.verdict === 'SUPPORTED') {
        supported.push(checkedItem);
      } else {
        refuted.push(checkedItem);
      }
    } catch (error) {
      notEnoughInfo.push({
        ...item,
        explanation: error instanceof Error ? error.message : 'Verification failed',
      });
    }
  }

  return { supported, refuted, notEnoughInfo };
}
