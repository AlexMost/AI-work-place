import type { CheckedTextItem } from '../../core/checkText';

interface Props {
  claim: CheckedTextItem;
  verdict: 'refuted' | 'notEnoughInfo';
}

export function ClaimDetail({ claim, verdict }: Props) {
  return (
    <div className="claim-detail">
      <div className={`verdict ${verdict === 'refuted' ? 'refuted' : 'not-enough-info'}`}>
        {verdict === 'refuted' ? 'Спростовано' : 'Недостатньо інформації'}
      </div>
      <div className="claim-text">"{claim.claim}"</div>
      <div className="explanation">{claim.explanation}</div>
    </div>
  );
}
