import { useState } from 'react';

interface Props {
  onSave: (key: string) => void;
  onClose?: () => void;
}

export function ApiKeyDialog({ onSave, onClose }: Props) {
  const [key, setKey] = useState('');

  return (
    <div className="api-key-overlay" onClick={onClose}>
      <div className="api-key-dialog" onClick={(e) => e.stopPropagation()}>
        {onClose && (
          <button type="button" className="api-key-close" onClick={onClose} aria-label="Закрити">
            ✕
          </button>
        )}
        <div className="kicker">Прохід до редакції</div>
        <h2>
          OpenAI <em>ключ.</em>
        </h2>
        <p>
          Для перевірки тверджень необхідний персональний ключ OpenAI. Він зберігається лише
          локально у вашому браузері й нікуди не передається.
        </p>
        <label className="key-label" htmlFor="api-key-input">
          Секретний токен
        </label>
        <input
          id="api-key-input"
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="sk-•••••••••••••••••••••••••••••••"
          onKeyDown={(e) => e.key === 'Enter' && key.trim() && onSave(key.trim())}
          autoFocus
        />
        <button onClick={() => key.trim() && onSave(key.trim())}>Увійти</button>
        <div className="footnote">localStorage · openai-api-key · без передачі на сервер</div>
      </div>
    </div>
  );
}
