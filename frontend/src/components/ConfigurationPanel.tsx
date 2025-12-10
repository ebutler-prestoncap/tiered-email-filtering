import { useState, useEffect } from 'react';
import type { ProcessingSettings, SettingsPreset } from '../types';
import { getPresets } from '../services/api';
import './ConfigurationPanel.css';

interface ConfigurationPanelProps {
  settings: ProcessingSettings;
  onSettingsChange: (settings: ProcessingSettings) => void;
  onProcess: () => void;
  isProcessing: boolean;
}

export default function ConfigurationPanel({
  settings,
  onSettingsChange,
  onProcess,
  isProcessing,
}: ConfigurationPanelProps) {
  const [presets, setPresets] = useState<SettingsPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('');

  useEffect(() => {
    loadPresets();
  }, []);

  const loadPresets = async () => {
    try {
      const loadedPresets = await getPresets();
      setPresets(loadedPresets);
      const defaultPreset = loadedPresets.find(p => p.is_default);
      if (defaultPreset) {
        setSelectedPresetId(defaultPreset.id);
        // Always set default preset on load
        console.log('Loading default preset:', defaultPreset.settings);
        onSettingsChange(defaultPreset.settings);
      } else {
        // Fallback to hardcoded defaults if no preset found
        const fallbackSettings: ProcessingSettings = {
          includeAllFirms: false,
          findEmails: false,
          firmExclusion: false,
          contactInclusion: false,
          tier1Limit: 10,
          tier2Limit: 6,
          tier3Limit: 3,
          userPrefix: 'Combined-Contacts',
        };
        onSettingsChange(fallbackSettings);
      }
    } catch (error) {
      console.error('Failed to load presets:', error);
      // Fallback to hardcoded defaults on error
      const fallbackSettings: ProcessingSettings = {
        includeAllFirms: false,
        findEmails: false,
        firmExclusion: false,
        contactInclusion: false,
        tier1Limit: 10,
        tier2Limit: 6,
        tier3Limit: 3,
        userPrefix: 'Combined-Contacts',
      };
      onSettingsChange(fallbackSettings);
    }
  };

  const handlePresetChange = (presetId: string) => {
    const preset = presets.find(p => p.id === presetId);
    if (preset) {
      setSelectedPresetId(presetId);
      onSettingsChange(preset.settings);
    }
  };

  const updateSetting = <K extends keyof ProcessingSettings>(
    key: K,
    value: ProcessingSettings[K]
  ) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  return (
    <div className="config-panel">
      <h2>Configuration</h2>

      {/* Preset Selection */}
      <div className="config-group">
        <h3 className="config-group-title">Preset</h3>
        <div className="config-section">
          <label className="config-label">Select Preset</label>
          <select
            className="config-select"
            value={selectedPresetId}
            onChange={(e) => handlePresetChange(e.target.value)}
          >
            {presets.map(preset => (
              <option key={preset.id} value={preset.id}>
                {preset.name} {preset.is_default ? '(Default - Matches CLI)' : ''}
              </option>
            ))}
          </select>
          <p className="config-hint">Choose a preset or customize settings below</p>
        </div>
      </div>

      {/* Tier Configuration */}
      <div className="config-group">
        <h3 className="config-group-title">Tier Limits</h3>
        <div className="config-section">
          <label className="config-label">Tier 1 Limit (Key Contacts)</label>
          <input
            type="number"
            className="config-input"
            min="1"
            max="50"
            value={settings.tier1Limit}
            onChange={(e) => updateSetting('tier1Limit', parseInt(e.target.value) || 10)}
          />
          <p className="config-hint">Max contacts per firm in Tier 1 (default: 10)</p>
        </div>

        <div className="config-section">
          <label className="config-label">Tier 2 Limit (Junior Contacts)</label>
          <input
            type="number"
            className="config-input"
            min="1"
            max="50"
            value={settings.tier2Limit}
            onChange={(e) => updateSetting('tier2Limit', parseInt(e.target.value) || 6)}
          />
          <p className="config-hint">Max contacts per firm in Tier 2 (default: 6)</p>
        </div>

        <div className="config-section">
          <label className="config-label">Tier 3 Limit (Rescued Contacts)</label>
          <input
            type="number"
            className="config-input"
            min="1"
            max="10"
            value={settings.tier3Limit}
            onChange={(e) => updateSetting('tier3Limit', parseInt(e.target.value) || 3)}
            disabled={!settings.includeAllFirms}
          />
          <p className="config-hint">Max contacts per firm in Tier 3 (default: 3, requires "Include All Firms")</p>
        </div>
      </div>

      {/* Advanced Options */}
      <div className="config-group">
        <h3 className="config-group-title">Advanced Options</h3>
        
        <div className="config-section">
          <label className="config-toggle">
            <input
              type="checkbox"
              checked={settings.includeAllFirms}
              onChange={(e) => updateSetting('includeAllFirms', e.target.checked)}
            />
            <span>Include All Firms (Tier 3 Rescue)</span>
          </label>
          <p className="config-hint">Rescue top 1-3 contacts from firms with zero Tier 1/2 contacts</p>
        </div>

        <div className="config-section">
          <label className="config-toggle">
            <input
              type="checkbox"
              checked={settings.findEmails}
              onChange={(e) => updateSetting('findEmails', e.target.checked)}
            />
            <span>Find Emails</span>
          </label>
          <p className="config-hint">Discover firm email schemas and fill missing emails in Tier 1 & 2</p>
        </div>

        <div className="config-section">
          <label className="config-toggle">
            <input
              type="checkbox"
              checked={settings.firmExclusion}
              onChange={(e) => updateSetting('firmExclusion', e.target.checked)}
            />
            <span>Firm Exclusion</span>
          </label>
          <p className="config-hint">Exclude specific firms from processing (requires firm exclusion CSV)</p>
        </div>

        <div className="config-section">
          <label className="config-toggle">
            <input
              type="checkbox"
              checked={settings.contactInclusion}
              onChange={(e) => updateSetting('contactInclusion', e.target.checked)}
            />
            <span>Contact Inclusion</span>
          </label>
          <p className="config-hint">Force specific contacts through filters (requires contact inclusion CSV)</p>
        </div>
      </div>

      {/* Output Settings */}
      <div className="config-group">
        <h3 className="config-group-title">Output Settings</h3>
        <div className="config-section">
          <label className="config-label">Output Prefix</label>
          <input
            type="text"
            className="config-input"
            value={settings.userPrefix}
            onChange={(e) => updateSetting('userPrefix', e.target.value)}
            placeholder="Combined-Contacts"
          />
          <p className="config-hint">Prefix for output filename (default: "Combined-Contacts")</p>
        </div>
      </div>

      <button
        className="process-button"
        onClick={onProcess}
        disabled={isProcessing}
      >
        {isProcessing ? 'Processing...' : 'Process Contacts'}
      </button>
    </div>
  );
}

