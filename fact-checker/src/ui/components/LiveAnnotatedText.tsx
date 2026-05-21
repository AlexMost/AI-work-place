import type { ReactNode } from 'react';
import type { LocatedMatchedClaim } from '../../core/checkText';

export type ClaimStatus = 'pending' | 'checking' | 'supported' | 'refuted' | 'nei' | 'error';

interface Props {
  text: string;
  claims: LocatedMatchedClaim[];
  statuses: ClaimStatus[];
}

const STATUS_CLASS: Record<ClaimStatus, string> = {
  pending: 'claim-live claim-live--pending',
  checking: 'claim-live claim-live--checking',
  supported: 'claim-live claim-live--supported',
  refuted: 'claim-live claim-live--refuted',
  nei: 'claim-live claim-live--nei',
  error: 'claim-live claim-live--nei',
};

const STATUS_LABEL: Record<ClaimStatus, string> = {
  pending: 'очікує',
  checking: 'перевіряємо',
  supported: 'підтверджено',
  refuted: 'спростовано',
  nei: 'недостатньо',
  error: 'недостатньо',
};

export function LiveAnnotatedText({ text, claims, statuses }: Props) {
  const indexed = claims
    .map((claim, i) => ({ claim, status: statuses[i] ?? 'pending', index: i }))
    .sort((a, b) => a.claim.start - b.claim.start);

  const filtered: typeof indexed = [];
  let lastEnd = -1;
  for (const t of indexed) {
    if (t.claim.start >= lastEnd) {
      filtered.push(t);
      lastEnd = t.claim.end;
    }
  }

  const segments: ReactNode[] = [];
  let pos = 0;

  for (const t of filtered) {
    if (t.claim.start > pos) {
      segments.push(text.slice(pos, t.claim.start));
    }
    segments.push(
      <span
        key={`${t.claim.start}-${t.index}`}
        className={STATUS_CLASS[t.status]}
        data-status-label={STATUS_LABEL[t.status]}
      >
        {text.slice(t.claim.start, t.claim.end)}
      </span>
    );
    pos = t.claim.end;
  }

  if (pos < text.length) {
    segments.push(text.slice(pos));
  }

  return <div className="annotated-text annotated-text--live">{segments}</div>;
}
