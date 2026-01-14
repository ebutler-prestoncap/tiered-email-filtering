import { useState } from 'react';
import type { FieldFilter } from '../types';
import './FieldFilters.css';

interface FieldFiltersProps {
  filters: FieldFilter[];
  onFiltersChange: (filters: FieldFilter[]) => void;
}

const AVAILABLE_FIELDS = [
  { value: 'COUNTRY', label: 'Country' },
  { value: 'CITY', label: 'City' },
  { value: 'ASSET_CLASS', label: 'Asset Class' },
  { value: 'FIRM_TYPE', label: 'Firm Type' },
];

export default function FieldFilters({ filters, onFiltersChange }: FieldFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);

  const addFilter = () => {
    // Find an unused field
    const usedFields = new Set(filters.map(f => f.field));
    const availableField = AVAILABLE_FIELDS.find(f => !usedFields.has(f.value));
    
    if (availableField) {
      onFiltersChange([
        ...filters,
        { field: availableField.value, values: [] }
      ]);
    }
  };

  const removeFilter = (index: number) => {
    onFiltersChange(filters.filter((_, i) => i !== index));
  };

  const updateFilterField = (index: number, field: string) => {
    const updated = [...filters];
    updated[index] = { ...updated[index], field };
    onFiltersChange(updated);
  };

  const addFilterValue = (filterIndex: number, value: string) => {
    if (!value.trim()) return;
    
    const updated = [...filters];
    const filter = updated[filterIndex];
    if (!filter.values.includes(value.trim())) {
      filter.values = [...filter.values, value.trim()];
      onFiltersChange(updated);
    }
  };

  const removeFilterValue = (filterIndex: number, valueIndex: number) => {
    const updated = [...filters];
    updated[filterIndex].values = updated[filterIndex].values.filter((_, i) => i !== valueIndex);
    onFiltersChange(updated);
  };

  const availableFieldsForSelect = (currentField: string) => {
    const usedFields = new Set(filters.map(f => f.field));
    return AVAILABLE_FIELDS.filter(f => f.value === currentField || !usedFields.has(f.value));
  };

  return (
    <div className="field-filters">
      <div className="field-filters-header">
        <h3 className="field-filters-title">Field Filters</h3>
        <button
          className="field-filters-toggle"
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
        >
          {isOpen ? '▼' : '▶'}
        </button>
      </div>

      {isOpen && (
        <div className="field-filters-content">
          <p className="field-filters-description">
            Filter contacts by specific field values. Only contacts matching the selected values will be included.
          </p>

          {filters.length === 0 ? (
            <div className="field-filters-empty">
              <p>No field filters added. Click "Add Filter" to start filtering by field values.</p>
            </div>
          ) : (
            <div className="field-filters-list">
              {filters.map((filter, filterIndex) => (
                <div key={filterIndex} className="field-filter-item">
                  <div className="field-filter-header">
                    <select
                      className="field-filter-select"
                      value={filter.field}
                      onChange={(e) => updateFilterField(filterIndex, e.target.value)}
                    >
                      {availableFieldsForSelect(filter.field).map(field => (
                        <option key={field.value} value={field.value}>
                          {field.label}
                        </option>
                      ))}
                    </select>
                    <button
                      className="field-filter-remove"
                      onClick={() => removeFilter(filterIndex)}
                      aria-label="Remove filter"
                    >
                      ×
                    </button>
                  </div>

                  <div className="field-filter-values">
                    <label className="field-filter-values-label">
                      Values to include (leave empty to include all):
                    </label>
                    <div className="field-filter-values-input-group">
                      <input
                        type="text"
                        className="field-filter-value-input"
                        placeholder="Enter value and press Enter"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            addFilterValue(filterIndex, e.currentTarget.value);
                            e.currentTarget.value = '';
                          }
                        }}
                      />
                    </div>
                    {filter.values.length > 0 && (
                      <div className="field-filter-values-list">
                        {filter.values.map((value, valueIndex) => (
                          <span key={valueIndex} className="field-filter-value-tag">
                            {value}
                            <button
                              className="field-filter-value-remove"
                              onClick={() => removeFilterValue(filterIndex, valueIndex)}
                              aria-label={`Remove ${value}`}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                    {filter.values.length === 0 && (
                      <p className="field-filter-hint">
                        No values specified - all contacts will be included for this field
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {filters.length < AVAILABLE_FIELDS.length && (
            <button
              className="field-filters-add"
              onClick={addFilter}
              type="button"
            >
              + Add Filter
            </button>
          )}
        </div>
      )}
    </div>
  );
}

