import type { ExtractedClaim, LocatedClaim } from './textSchemas';

export function locateExtractedClaims(text: string, claims: ExtractedClaim[]): LocatedClaim[] {
  const assignedStartsBySourceText = new Map<string, Set<number>>();

  return claims.map(({ claim, sourceText }) => {
    const assignedStarts = assignedStartsBySourceText.get(sourceText) ?? new Set<number>();
    const startCandidates: number[] = [];
    let searchFrom = 0;

    while (searchFrom <= text.length) {
      const matchIndex = text.indexOf(sourceText, searchFrom);
      if (matchIndex === -1) {
        break;
      }

      startCandidates.push(matchIndex);
      searchFrom = matchIndex + 1;
    }

    const start = startCandidates.find((candidate) => !assignedStarts.has(candidate)) ?? null;

    if (start !== null) {
      assignedStarts.add(start);
      assignedStartsBySourceText.set(sourceText, assignedStarts);
    }

    return {
      claim,
      sourceText,
      start,
      end: start === null ? null : start + sourceText.length,
    };
  });
}
