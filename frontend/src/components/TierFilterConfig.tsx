import { useState } from 'react';
import type { TierFilterConfig } from '../types';
import './TierFilterConfig.css';

interface TierFilterConfigProps {
  tierNumber: 1 | 2 | 3;
  config: TierFilterConfig;
  onChange: (config: TierFilterConfig) => void;
}

export default function TierFilterConfigComponent({
  tierNumber,
  config,
  onChange,
}: TierFilterConfigProps) {
  const [includeKeyword, setIncludeKeyword] = useState('');
  const [excludeKeyword, setExcludeKeyword] = useState('');

  const addIncludeKeyword = () => {
    if (includeKeyword.trim() && !config.includeKeywords.includes(includeKeyword.trim())) {
      onChange({
        ...config,
        includeKeywords: [...config.includeKeywords, includeKeyword.trim()],
      });
      setIncludeKeyword('');
    }
  };

  const removeIncludeKeyword = (keyword: string) => {
    onChange({
      ...config,
      includeKeywords: config.includeKeywords.filter(k => k !== keyword),
    });
  };

  const addExcludeKeyword = () => {
    if (excludeKeyword.trim() && !config.excludeKeywords.includes(excludeKeyword.trim())) {
      onChange({
        ...config,
        excludeKeywords: [...config.excludeKeywords, excludeKeyword.trim()],
      });
      setExcludeKeyword('');
    }
  };

  const removeExcludeKeyword = (keyword: string) => {
    onChange({
      ...config,
      excludeKeywords: config.excludeKeywords.filter(k => k !== keyword),
    });
  };

  return (
    <div className="tier-filter-config">
      <h4 className="tier-filter-title">Tier {tierNumber} Filter Configuration</h4>
      
      <div className="filter-section">
        <label className="filter-label">
          Include Keywords (Job titles that match these will be included)
        </label>
        <div className="keyword-input-group">
          <input
            type="text"
            className="keyword-input"
            value={includeKeyword}
            onChange={(e) => setIncludeKeyword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addIncludeKeyword();
              }
            }}
            placeholder="e.g., cio, chief investment officer"
          />
          <button
            type="button"
            className="add-keyword-button"
            onClick={addIncludeKeyword}
            disabled={!includeKeyword.trim()}
          >
            Add
          </button>
        </div>
        <div className="keywords-list">
          {config.includeKeywords.length === 0 ? (
            <p className="empty-hint">No include keywords. Add keywords to filter job titles.</p>
          ) : (
            config.includeKeywords.map((keyword, idx) => (
              <span key={idx} className="keyword-tag">
                {keyword}
                <button
                  type="button"
                  className="remove-keyword"
                  onClick={() => removeIncludeKeyword(keyword)}
                  aria-label={`Remove ${keyword}`}
                >
                  ×
                </button>
              </span>
            ))
          )}
        </div>
      </div>

      <div className="filter-section">
        <label className="filter-label">
          Exclude Keywords (Job titles containing these will be excluded)
        </label>
        <div className="keyword-input-group">
          <input
            type="text"
            className="keyword-input"
            value={excludeKeyword}
            onChange={(e) => setExcludeKeyword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addExcludeKeyword();
              }
            }}
            placeholder="e.g., operations, hr, marketing"
          />
          <button
            type="button"
            className="add-keyword-button"
            onClick={addExcludeKeyword}
            disabled={!excludeKeyword.trim()}
          >
            Add
          </button>
        </div>
        <div className="keywords-list">
          {config.excludeKeywords.length === 0 ? (
            <p className="empty-hint">No exclude keywords. Add keywords to exclude job titles.</p>
          ) : (
            config.excludeKeywords.map((keyword, idx) => (
              <span key={idx} className="keyword-tag exclude">
                {keyword}
                <button
                  type="button"
                  className="remove-keyword"
                  onClick={() => removeExcludeKeyword(keyword)}
                  aria-label={`Remove ${keyword}`}
                >
                  ×
                </button>
              </span>
            ))
          )}
        </div>
      </div>

      <div className="filter-section">
        <label className="filter-toggle">
          <input
            type="checkbox"
            checked={config.requireInvestmentTeam}
            onChange={(e) => onChange({ ...config, requireInvestmentTeam: e.target.checked })}
          />
          <span>Require Investment Team Role</span>
        </label>
        <p className="filter-hint">
          If checked, contacts must have "investment team" or "investment" in their ROLE field
        </p>
      </div>
    </div>
  );
}

