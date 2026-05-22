import { useState, useCallback, useMemo } from 'react';
import { checkText } from '../core/checkText';
import type {
  CheckTextResult,
  CheckedTextItem,
  CheckProgressEvent,
  LocatedMatchedClaim,
} from '../core/checkText';
import { ApiKeyDialog } from './components/ApiKeyDialog';
import { AnnotatedText } from './components/AnnotatedText';
import { ClaimDetail } from './components/ClaimDetail';
import { LiveAnnotatedText } from './components/LiveAnnotatedText';
import type { ClaimStatus } from './components/LiveAnnotatedText';
import './App.css';

type SelectedClaim = CheckedTextItem & { verdict: 'refuted' | 'notEnoughInfo' };

function formatDate(d: Date) {
  return d
    .toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', year: 'numeric' })
    .replace(/\./g, '·');
}

export function App() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('openai-api-key') ?? '');
  const [inputText, setInputText] = useState('');
  const [checkedText, setCheckedText] = useState('');
  const [result, setResult] = useState<CheckTextResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedClaim, setSelectedClaim] = useState<SelectedClaim | null>(null);
  const [showKeyDialog, setShowKeyDialog] = useState(false);
  const [pendingCheck, setPendingCheck] = useState(false);
  const [dossierNo, setDossierNo] = useState<string | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [liveClaims, setLiveClaims] = useState<LocatedMatchedClaim[]>([]);
  const [liveStatuses, setLiveStatuses] = useState<ClaimStatus[]>([]);
  const [inputCollapsed, setInputCollapsed] = useState(false);

  const today = useMemo(() => formatDate(new Date()), []);

  const runCheck = useCallback(
    async (key: string) => {
      setLoading(true);
      setError(null);
      setResult(null);
      setSelectedClaim(null);
      setCheckedText(inputText);
      setLiveClaims([]);
      setLiveStatuses([]);
      setInputCollapsed(true);
      const started = performance.now();

      const handleProgress = (event: CheckProgressEvent) => {
        if (event.type === 'claims_located') {
          setLiveClaims(event.claims);
          setLiveStatuses(event.claims.map(() => 'pending'));
          return;
        }
        if (event.type === 'claim_check_start') {
          setLiveStatuses((prev) => {
            const next = [...prev];
            next[event.index] = 'checking';
            return next;
          });
          return;
        }
        if (event.type === 'claim_check_done') {
          setLiveStatuses((prev) => {
            const next = [...prev];
            next[event.index] =
              event.verdict === 'SUPPORTED'
                ? 'supported'
                : event.verdict === 'REFUTED'
                  ? 'refuted'
                  : event.verdict === 'NOT_ENOUGH_INFO'
                    ? 'nei'
                    : 'error';
            return next;
          });
        }
      };

      try {
        const r = await checkText(inputText, key, handleProgress);
        setResult(r);
        setDossierNo(
          String(Math.floor(Math.random() * 900) + 100).padStart(3, '0') +
            '·' +
            String(Date.now()).slice(-4)
        );
        setDuration((performance.now() - started) / 1000);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Невідома помилка');
      } finally {
        setLoading(false);
      }
    },
    [inputText]
  );

  const handleCheck = useCallback(() => {
    if (!inputText.trim()) return;
    if (!apiKey) {
      setPendingCheck(true);
      setShowKeyDialog(true);
      return;
    }
    void runCheck(apiKey);
  }, [inputText, apiKey, runCheck]);

  const handleSaveKey = useCallback(
    (key: string) => {
      localStorage.setItem('openai-api-key', key);
      setApiKey(key);
      setShowKeyDialog(false);
      if (pendingCheck) {
        setPendingCheck(false);
        void runCheck(key);
      }
    },
    [pendingCheck, runCheck]
  );

  const handleCloseKeyDialog = useCallback(() => {
    setShowKeyDialog(false);
    setPendingCheck(false);
  }, []);

  const handleClaimClick = useCallback(
    (claim: CheckedTextItem, verdict: 'refuted' | 'notEnoughInfo') => {
      setSelectedClaim({ ...claim, verdict });
    },
    []
  );

  const totals = result
    ? {
        s: result.supported.length,
        r: result.refuted.length,
        n: result.notEnoughInfo.length,
        all: result.supported.length + result.refuted.length + result.notEnoughInfo.length,
      }
    : null;

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-meta">
          Випуск <strong>I · {today}</strong>
          <br />
          Кириличний фактчекер
        </div>
        <div className="wordmark">
          <span>
            <em>В</em>ердикт
          </span>
          <span className="wordmark-ornament">Wikipedia · LangGraph · OpenAI</span>
        </div>
        <div className="masthead-meta masthead-meta--right">
          <button className="key-btn" onClick={() => setShowKeyDialog(true)}>
            Змінити ключ ⌁
          </button>
        </div>
      </header>

      <section className="hero">
        <h2 className="hero-title">
          Перевірка
          <br />
          <em>фактологічної</em>
          <br />
          істинності&nbsp;<span className="underline">тексту.</span>
        </h2>
        <aside className="hero-side">
          <span className="kicker">Як це працює</span>
          <p>
            Алгоритм витягує атомарні твердження, прив'язує їх до фрагментів вашого тексту й
            перевіряє кожне через відкриту Wikipedia. У відповідь — позначений рукопис із трьома
            кольорами вердиктів.
          </p>
          <div className="legend">
            <div className="legend-item">
              <span className="legend-swatch legend-swatch--supported" />
              Підтверджено
            </div>
            <div className="legend-item">
              <span className="legend-swatch legend-swatch--refuted" />
              Спростовано
            </div>
            <div className="legend-item">
              <span className="legend-swatch legend-swatch--nei" />
              Недостатньо доказів
            </div>
          </div>
        </aside>
      </section>

      <div className="section-rule">
        <span className="section-rule-tag">§ 01 — Подання тексту</span>
        <span className="section-rule-line" />
        <span>{today}</span>
      </div>

      <div className="input-section">
        <div className="paper-card" data-collapsed={inputCollapsed || undefined}>
          <div className="input-pane">
            <div className="input-head">
              <span className="filenum">
                ЧЕРНЕТКА · {String(inputText.length).padStart(4, '0')} ЗН.
              </span>
              <span className="input-head-right">
                <span className="input-head-hint">Українською або англійською</span>
                <button
                  type="button"
                  className="collapse-btn"
                  onClick={() => setInputCollapsed((v) => !v)}
                  aria-expanded={!inputCollapsed}
                  aria-label={inputCollapsed ? 'Розгорнути ввід' : 'Згорнути ввід'}
                >
                  {inputCollapsed ? 'Розгорнути ▾' : 'Згорнути ▴'}
                </button>
              </span>
            </div>
            <div className="input-body">
              <textarea
                className="text-input"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Вставте абзац, цитату чи новину — алгоритм розкладе її на твердження…"
                rows={6}
                disabled={loading}
              />
              <div className="input-actions">
                <span className="input-hint">⌘/Ctrl + Enter — швидке подання</span>
                <button
                  className="check-btn"
                  onClick={handleCheck}
                  disabled={loading || !inputText.trim()}
                  data-loading={loading || undefined}
                >
                  {loading ? 'Досліджуємо' : 'Передати на перевірку'}
                </button>
              </div>
            </div>
          </div>
        </div>
        {loading && (
          <div className="loading-trace">
            <span>extract · витягуємо атомарні твердження</span>
            <span>locate · прив'язуємо до фрагментів</span>
            <span>verify · звіряємо з Wikipedia</span>
          </div>
        )}
        {loading && liveClaims.length > 0 && (
          <LiveAnnotatedText text={checkedText} claims={liveClaims} statuses={liveStatuses} />
        )}
      </div>

      {error && <div className="error">{error}</div>}

      {result && totals && (
        <section className="result-section">
          <div className="section-rule">
            <span className="section-rule-tag">§ 02 — Дос'є №&nbsp;{dossierNo ?? '—'}</span>
            <span className="section-rule-line" />
            <span>
              {duration ? `${duration.toFixed(1)}с` : '—'} · {totals.all} твердж.
            </span>
          </div>

          <div className="result-meta">
            <div className="result-meta-cell">
              <span className="result-meta-label">Підтверджено</span>
              <span className="result-meta-value --green">
                {String(totals.s).padStart(2, '0')}
                <small>од.</small>
              </span>
            </div>
            <div className="result-meta-cell">
              <span className="result-meta-label">Спростовано</span>
              <span className="result-meta-value --red">
                {String(totals.r).padStart(2, '0')}
                <small>од.</small>
              </span>
            </div>
            <div className="result-meta-cell">
              <span className="result-meta-label">Недостатньо</span>
              <span className="result-meta-value --ochre">
                {String(totals.n).padStart(2, '0')}
                <small>од.</small>
              </span>
            </div>
            <div className="result-meta-cell">
              <span className="result-meta-label">Усього</span>
              <span className="result-meta-value">
                {String(totals.all).padStart(2, '0')}
                <small>од.</small>
              </span>
            </div>
          </div>

          <AnnotatedText text={checkedText} result={result} onClaimClick={handleClaimClick} />
          {selectedClaim && <ClaimDetail claim={selectedClaim} verdict={selectedClaim.verdict} />}
        </section>
      )}

      <footer className="colophon">
        <span>Версія I · 2026</span>
        <span>Опус роботи редактора з фактами</span>
      </footer>

      {showKeyDialog && <ApiKeyDialog onSave={handleSaveKey} onClose={handleCloseKeyDialog} />}
    </div>
  );
}
