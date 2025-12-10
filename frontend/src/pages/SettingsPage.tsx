import { useEffect, useState } from 'react';
import { getPresets, createPreset, deletePreset } from '../services/api';
import type { SettingsPreset, ProcessingSettings } from '../types';
import './SettingsPage.css';

export default function SettingsPage() {
  const [presets, setPresets] = useState<SettingsPreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [newPresetName, setNewPresetName] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);

  useEffect(() => {
    loadPresets();
  }, []);

  const loadPresets = async () => {
    try {
      setLoading(true);
      const loadedPresets = await getPresets();
      setPresets(loadedPresets);
    } catch (error) {
      console.error('Failed to load presets:', error);
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
      findEmails: false,
      firmExclusion: false,
      contactInclusion: false,
      tier1Limit: 10,
      tier2Limit: 6,
      tier3Limit: 3,
      userPrefix: 'Combined-Contacts',
    };

    try {
      await createPreset(newPresetName, defaultSettings);
      setNewPresetName('');
      setShowCreateForm(false);
      loadPresets();
    } catch (error) {
      alert('Failed to create preset');
      console.error(error);
    }
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
      console.error(error);
    }
  };

  if (loading) {
    return <div className="settings-page">Loading...</div>;
  }

  const defaultPreset = presets.find(p => p.is_default);
  const customPresets = presets.filter(p => !p.is_default);

  return (
    <div className="settings-page">
      <h1>Settings Presets</h1>
      <p className="page-description">
        Manage configuration presets for processing contacts.
      </p>

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
                <div className="preset-header">
                  <div className="preset-name">{preset.name}</div>
                  <button
                    className="preset-delete"
                    onClick={() => handleDeletePreset(preset.id)}
                    aria-label="Delete preset"
                  >
                    ×
                  </button>
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
                    <span className="setting-label">Tier 1 Limit:</span>
                    <span className="setting-value">{preset.settings.tier1Limit}</span>
                  </div>
                  <div className="setting-item">
                    <span className="setting-label">Tier 2 Limit:</span>
                    <span className="setting-value">{preset.settings.tier2Limit}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

