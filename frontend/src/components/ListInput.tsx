import { useState } from 'react';
import './ListInput.css';

interface ListInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  hint?: string;
  rows?: number;
}

export default function ListInput({
  label,
  value,
  onChange,
  placeholder,
  hint,
  rows = 5,
}: ListInputProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="list-input-section">
      <div className="list-input-header">
        <label className="list-input-label">{label}</label>
        <button
          type="button"
          className="expand-button"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>
      {isExpanded && (
        <>
          <textarea
            className="list-input-textarea"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            rows={rows}
          />
          {hint && <p className="list-input-hint">{hint}</p>}
        </>
      )}
    </div>
  );
}

