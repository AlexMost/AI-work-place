import { useState } from 'react';

interface Props {
  onSave: (key: string) => void;
}

export function ApiKeyDialog({ onSave }: Props) {
  const [key, setKey] = useState('');

  return (
    <div className="api-key-dialog">
      <h2>OpenAI API Key</h2>
      <p style={{ marginBottom: 16, color: '#555', fontSize: 14 }}>
        Введіть ваш OpenAI API ключ для роботи з факт-чекером.
      </p>
      <input
        type="password"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        placeholder="sk-..."
        onKeyDown={(e) => e.key === 'Enter' && key.trim() && onSave(key.trim())}
      />
      <button onClick={() => key.trim() && onSave(key.trim())}>
        Зберегти
      </button>
    </div>
  );
}
