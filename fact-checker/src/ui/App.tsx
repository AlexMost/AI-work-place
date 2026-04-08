import { useState, useCallback } from 'react';
import { checkText } from '../core/checkText';
import type { CheckTextResult, CheckedTextItem } from '../core/checkText';
import { ApiKeyDialog } from './components/ApiKeyDialog';
import { AnnotatedText } from './components/AnnotatedText';
import { ClaimDetail } from './components/ClaimDetail';
import './App.css';

type SelectedClaim = CheckedTextItem & { verdict: 'refuted' | 'notEnoughInfo' };

export function App() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('openai-api-key') ?? '');
  const [inputText, setInputText] = useState('');
  const [checkedText, setCheckedText] = useState('');
  const [result, setResult] = useState<CheckTextResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedClaim, setSelectedClaim] = useState<SelectedClaim | null>(null);
  const [showKeyDialog, setShowKeyDialog] = useState(!apiKey);

  const handleSaveKey = useCallback((key: string) => {
    localStorage.setItem('openai-api-key', key);
    setApiKey(key);
    setShowKeyDialog(false);
  }, []);

  const handleCheck = useCallback(async () => {
    if (!inputText.trim() || !apiKey) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedClaim(null);
    setCheckedText(inputText);

    try {
      const r = await checkText(inputText, apiKey);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Невідома помилка');
    } finally {
      setLoading(false);
    }
  }, [inputText, apiKey]);

  const handleClaimClick = useCallback(
    (claim: CheckedTextItem, verdict: 'refuted' | 'notEnoughInfo') => {
      setSelectedClaim({ ...claim, verdict });
    },
    []
  );

  if (showKeyDialog) {
    return <ApiKeyDialog onSave={handleSaveKey} />;
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Fact Checker</h1>
        <button className="key-btn" onClick={() => setShowKeyDialog(true)}>
          Змінити API ключ
        </button>
      </header>

      <div className="input-section">
        <textarea
          className="text-input"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Введіть текст для перевірки..."
          rows={6}
          disabled={loading}
        />
        <button
          className="check-btn"
          onClick={handleCheck}
          disabled={loading || !inputText.trim()}
        >
          {loading ? 'Перевіряємо...' : 'Перевірити'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="result-section">
          <h2>Результат</h2>
          <AnnotatedText
            text={checkedText}
            result={result}
            onClaimClick={handleClaimClick}
          />
          {selectedClaim && (
            <ClaimDetail claim={selectedClaim} verdict={selectedClaim.verdict} />
          )}
        </div>
      )}
    </div>
  );
}
