import type { ReactNode } from 'react';
import type { CheckTextResult, CheckedTextItem } from '../../core/checkText';

type Verdict = 'refuted' | 'notEnoughInfo';

interface TaggedClaim {
  claim: CheckedTextItem;
  verdict: Verdict;
  start: number;
  end: number;
}

interface Props {
  text: string;
  result: CheckTextResult;
  onClaimClick: (claim: CheckedTextItem, verdict: Verdict) => void;
}

export function AnnotatedText({ text, result, onClaimClick }: Props) {
  const tagged: TaggedClaim[] = [];

  for (const claim of result.refuted) {
    if (claim.start !== null && claim.end !== null) {
      tagged.push({ claim, verdict: 'refuted', start: claim.start, end: claim.end });
    }
  }
  for (const claim of result.notEnoughInfo) {
    if (claim.start !== null && claim.end !== null) {
      tagged.push({ claim, verdict: 'notEnoughInfo', start: claim.start, end: claim.end });
    }
  }

  tagged.sort((a, b) => a.start - b.start);

  // Remove overlapping claims (keep the first one)
  const filtered: TaggedClaim[] = [];
  let lastEnd = -1;
  for (const t of tagged) {
    if (t.start >= lastEnd) {
      filtered.push(t);
      lastEnd = t.end;
    }
  }

  const segments: ReactNode[] = [];
  let pos = 0;

  for (const t of filtered) {
    if (t.start > pos) {
      segments.push(text.slice(pos, t.start));
    }
    segments.push(
      <span
        key={t.start}
        className={t.verdict === 'refuted' ? 'claim-refuted' : 'claim-not-enough-info'}
        onClick={() => onClaimClick(t.claim, t.verdict)}
      >
        {text.slice(t.start, t.end)}
      </span>
    );
    pos = t.end;
  }

  if (pos < text.length) {
    segments.push(text.slice(pos));
  }

  return <div className="annotated-text">{segments}</div>;
}
