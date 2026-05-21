import type { CheckedTextItem } from '../../core/checkText';

interface Props {
  claim: CheckedTextItem;
  verdict: 'refuted' | 'notEnoughInfo';
}

export function ClaimDetail({ claim, verdict }: Props) {
  const isRefuted = verdict === 'refuted';
  return (
    <div className={`claim-detail ${isRefuted ? '--refuted' : '--nei'}`}>
      <div className={`verdict ${isRefuted ? 'refuted' : 'not-enough-info'}`}>
        {isRefuted ? 'Спростовано' : 'Недостатньо доказів'}
      </div>
      <div className="claim-text">«{claim.claim}»</div>
      <div className="explanation">{claim.explanation}</div>
    </div>
  );
}
