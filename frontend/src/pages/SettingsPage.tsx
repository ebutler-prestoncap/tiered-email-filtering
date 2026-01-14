import { useEffect, useState } from 'react';
import { getPresets, createPreset, updatePreset, deletePreset } from '../services/api';
import type { SettingsPreset, ProcessingSettings } from '../types';
import FieldFilters from '../components/FieldFilters';
import RemovalListManager from '../components/RemovalListManager';
import './SettingsPage.css';

export default function SettingsPage() {
  const [presets, setPresets] = useState<SettingsPreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [newPresetName, setNewPresetName] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingPreset, setEditingPreset] = useState<SettingsPreset | null>(null);
  const [editSettings, setEditSettings] = useState<ProcessingSettings | null>(null);

  useEffect(() => {
    loadPresets();
  }, []);

  const loadPresets = async () => {
    try {
      setLoading(true);
      const loadedPresets = await getPresets();
      setPresets(loadedPresets);
    } catch (error) {
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Failed to load presets:', error);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePreset = async () => {
    if (!newPresetName.trim()) {
      alert('Please enter a preset name');
      return;
    }

    // Use default settings as base
    const defaultSettings: ProcessingSettings = {
      includeAllFirms: false,
      findEmails: true,
      firmExclusion: false,
      contactInclusion: false,
      tier1Limit: 10,
      tier2Limit: 6,
      tier3Limit: 3,
      userPrefix: 'Combined-Contacts',
      fieldFilters: [],
    };

    try {
      await createPreset(newPresetName, defaultSettings);
      setNewPresetName('');
      setShowCreateForm(false);
      loadPresets();
    } catch (error) {
      alert('Failed to create preset');
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Create preset error:', error);
      }
    }
  };

  const handleEditPreset = (preset: SettingsPreset) => {
    if (preset.is_default) {
      alert('Cannot edit the default preset');
      return;
    }
    setEditingPreset(preset);
    setEditSettings({ ...preset.settings });
  };

  const handleSaveEdit = async () => {
    if (!editingPreset || !editSettings) return;

    try {
      await updatePreset(editingPreset.id, editingPreset.name, editSettings);
      setEditingPreset(null);
      setEditSettings(null);
      loadPresets();
      alert('Preset updated successfully!');
    } catch (error) {
      alert('Failed to update preset');
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Update preset error:', error);
      }
    }
  };

  const handleCancelEdit = () => {
    setEditingPreset(null);
    setEditSettings(null);
  };

  const handleDeletePreset = async (presetId: string) => {
    if (!confirm('Are you sure you want to delete this preset?')) {
      return;
    }

    try {
      await deletePreset(presetId);
      loadPresets();
    } catch (error) {
      alert('Failed to delete preset (may be default preset)');
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Delete preset error:', error);
      }
    }
  };

  if (loading) {
    return <div className="settings-page">Loading...</div>;
  }

  const defaultPreset = presets.find(p => p.is_default);
  const customPresets = presets.filter(p => !p.is_default);

  return (
    <div className="settings-page">
      <h1>Settings</h1>
      <p className="page-description">
        Manage removal lists and configuration presets for processing contacts.
      </p>

      <section className="preset-section">
        <h2>Removal Lists</h2>
        <p className="section-description">
          Upload CSV files containing accounts or contacts to remove from processing.
          The most recent active list of each type will be applied by default to all jobs.
        </p>
        <RemovalListManager />
      </section>

      {defaultPreset && (
        <section className="preset-section">
          <h2>Default Preset</h2>
          <div className="preset-card readonly">
            <div className="preset-header">
              <div className="preset-name">{defaultPreset.name}</div>
              <div className="preset-badge">Default</div>
            </div>
            <div className="preset-settings">
              <div className="setting-item">
                <span className="setting-label">Include All Firms:</span>
                <span className="setting-value">{defaultPreset.settings.includeAllFirms ? 'Yes' : 'No'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-label">Find Emails:</span>
                <span className="setting-value">{defaultPreset.settings.findEmails ? 'Yes' : 'No'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-label">Tier 1 Limit:</span>
                <span className="setting-value">{defaultPreset.settings.tier1Limit}</span>
              </div>
              <div className="setting-item">
                <span className="setting-label">Tier 2 Limit:</span>
                <span className="setting-value">{defaultPreset.settings.tier2Limit}</span>
              </div>
              <div className="setting-item">
                <span className="setting-label">Output Prefix:</span>
                <span className="setting-value">{defaultPreset.settings.userPrefix}</span>
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="preset-section">
        <div className="section-header">
          <h2>Custom Presets</h2>
          <button
            className="create-button"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? 'Cancel' : '+ Create Preset'}
          </button>
        </div>

        {showCreateForm && (
          <div className="create-form">
            <input
              type="text"
              className="preset-name-input"
              placeholder="Preset name"
              value={newPresetName}
              onChange={(e) => setNewPresetName(e.target.value)}
            />
            <button className="save-button" onClick={handleCreatePreset}>
              Create
            </button>
          </div>
        )}

        {customPresets.length === 0 ? (
          <p className="empty-message">No custom presets yet.</p>
        ) : (
          <div className="presets-list">
            {customPresets.map(preset => (
              <div key={preset.id} className="preset-card">
                {editingPreset?.id === preset.id ? (
                  <div className="preset-edit-form">
                    <h4>Edit Preset: {preset.name}</h4>
                    <div className="edit-settings-grid">
                      <div className="edit-setting">
                        <label>
                          <input
                            type="checkbox"
                            checked={editSettings?.includeAllFirms || false}
                            onChange={(e) => setEditSettings(prev => prev ? { ...prev, includeAllFirms: e.target.checked } : null)}
                          />
                          Include All Firms
                        </label>
                      </div>
                      <div className="edit-setting">
                        <label>
                          <input
                            type="checkbox"
                            checked={editSettings?.findEmails || false}
                            onChange={(e) => setEditSettings(prev => prev ? { ...prev, findEmails: e.target.checked } : null)}
                          />
                          Find Emails
                        </label>
                      </div>
                      <div className="edit-setting">
                        <label>
                          <input
                            type="checkbox"
                            checked={editSettings?.firmExclusion || false}
                            onChange={(e) => setEditSettings(prev => prev ? { ...prev, firmExclusion: e.target.checked } : null)}
                          />
                          Firm Exclusion
                        </label>
                      </div>
                      <div className="edit-setting">
                        <label>
                          <input
                            type="checkbox"
                            checked={editSettings?.contactInclusion || false}
                            onChange={(e) => setEditSettings(prev => prev ? { ...prev, contactInclusion: e.target.checked } : null)}
                          />
                          Contact Inclusion
                        </label>
                      </div>
                      <div className="edit-setting">
                        <label>
                          Tier 1 Limit:
                          <input
                            type="number"
                            min="1"
                            max="50"
                            value={editSettings?.tier1Limit || 10}
                            onChange={(e) => setEditSettings(prev => prev ? { ...prev, tier1Limit: parseInt(e.target.value) || 10 } : null)}
                          />
                        </label>
                      </div>
                      <div className="edit-setting">
                        <label>
                          Tier 2 Limit:
                          <input
                            type="number"
                            min="1"
                            max="50"
                            value={editSettings?.tier2Limit || 6}
                            onChange={(e) => setEditSettings(prev => prev ? { ...prev, tier2Limit: parseInt(e.target.value) || 6 } : null)}
                          />
                        </label>
                      </div>
                      <div className="edit-setting">
                        <label>
                          Tier 3 Limit:
                          <input
                            type="number"
                            min="1"
                            max="10"
                            value={editSettings?.tier3Limit || 3}
                            onChange={(e) => setEditSettings(prev => prev ? { ...prev, tier3Limit: parseInt(e.target.value) || 3 } : null)}
                            disabled={!editSettings?.includeAllFirms}
                          />
                        </label>
                      </div>
                      <div className="edit-setting">
                        <label>
                          Output Prefix:
                          <input
                            type="text"
                            value={editSettings?.userPrefix || 'Combined-Contacts'}
                            onChange={(e) => setEditSettings(prev => prev ? { ...prev, userPrefix: e.target.value } : null)}
                          />
                        </label>
                      </div>
                    </div>
                    <div className="edit-field-filters">
                      <FieldFilters
                        filters={editSettings?.fieldFilters || []}
                        onFiltersChange={(filters) => setEditSettings(prev => prev ? { ...prev, fieldFilters: filters } : null)}
                      />
                    </div>
                    <div className="edit-actions">
                      <button className="cancel-button" onClick={handleCancelEdit}>
                        Cancel
                      </button>
                      <button className="save-button" onClick={handleSaveEdit}>
                        Save Changes
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="preset-header">
                      <div className="preset-name">{preset.name}</div>
                      <div className="preset-actions">
                        <button
                          className="preset-edit"
                          onClick={() => handleEditPreset(preset)}
                          aria-label="Edit preset"
                        >
                          Edit
                        </button>
                        <button
                          className="preset-delete"
                          onClick={() => handleDeletePreset(preset.id)}
                          aria-label="Delete preset"
                        >
                          ×
                        </button>
                      </div>
                    </div>
                    <div className="preset-settings">
                      <div className="setting-item">
                        <span className="setting-label">Include All Firms:</span>
                        <span className="setting-value">{preset.settings.includeAllFirms ? 'Yes' : 'No'}</span>
                      </div>
                      <div className="setting-item">
                        <span className="setting-label">Find Emails:</span>
                        <span className="setting-value">{preset.settings.findEmails ? 'Yes' : 'No'}</span>
                      </div>
                      <div className="setting-item">
                        <span className="setting-label">Firm Exclusion:</span>
                        <span className="setting-value">{preset.settings.firmExclusion ? 'Yes' : 'No'}</span>
                      </div>
                      <div className="setting-item">
                        <span className="setting-label">Contact Inclusion:</span>
                        <span className="setting-value">{preset.settings.contactInclusion ? 'Yes' : 'No'}</span>
                      </div>
                      <div className="setting-item">
                        <span className="setting-label">Tier 1 Limit:</span>
                        <span className="setting-value">{preset.settings.tier1Limit}</span>
                      </div>
                      <div className="setting-item">
                        <span className="setting-label">Tier 2 Limit:</span>
                        <span className="setting-value">{preset.settings.tier2Limit}</span>
                      </div>
                      <div className="setting-item">
                        <span className="setting-label">Tier 3 Limit:</span>
                        <span className="setting-value">{preset.settings.tier3Limit}</span>
                      </div>
                      <div className="setting-item">
                        <span className="setting-label">Output Prefix:</span>
                        <span className="setting-value">{preset.settings.userPrefix}</span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

