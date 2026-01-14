import { useState, useEffect } from 'react';
import type { ProcessingSettings, SettingsPreset } from '../types';
import { getPresets, createPreset, updatePreset, getActiveRemovalLists, type ActiveRemovalLists } from '../services/api';
import TierFilterConfigComponent from './TierFilterConfig';
import ListInput from './ListInput';
import FieldFilters from './FieldFilters';
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
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [savePresetName, setSavePresetName] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingPresets, setIsLoadingPresets] = useState(true);
  const [activeLists, setActiveLists] = useState<ActiveRemovalLists>({ accountRemovalList: null, contactRemovalList: null });

  // Default tier filter configurations - used when loading presets that don't have them
  const defaultTierFilters = {
    tier1Filters: {
      includeKeywords: ['cio', 'chief investment officer', 'portfolio manager', 'director'],
      excludeKeywords: ['operations', 'hr', 'marketing'],
      requireInvestmentTeam: false,
    },
    tier2Filters: {
      includeKeywords: ['analyst', 'associate', 'director'],
      excludeKeywords: ['operations', 'hr', 'marketing'],
      requireInvestmentTeam: true,
    },
    tier3Filters: {
      includeKeywords: ['ceo', 'cfo', 'director'],
      excludeKeywords: [],
      requireInvestmentTeam: false,
    },
  };

  // Ensure settings have tier filters with defaults if missing
  const ensureTierFilters = (presetSettings: ProcessingSettings): ProcessingSettings => {
    return {
      ...presetSettings,
      tier1Filters: presetSettings.tier1Filters || defaultTierFilters.tier1Filters,
      tier2Filters: presetSettings.tier2Filters || defaultTierFilters.tier2Filters,
      tier3Filters: presetSettings.tier3Filters || defaultTierFilters.tier3Filters,
    };
  };

  useEffect(() => {
    // Load presets first, then removal lists
    // This ensures preset settings are applied before removal list toggles
    loadPresets().then((loadedSettings) => {
      loadActiveRemovalLists(loadedSettings || undefined);
    });
  }, []);

  const loadActiveRemovalLists = async (currentSettings?: ProcessingSettings) => {
    try {
      const lists = await getActiveRemovalLists();
      setActiveLists(lists);
      // Set default toggle values based on whether lists exist
      // Use currentSettings if provided (from loadPresets chain), otherwise fall back to props
      const settingsToUse = currentSettings || settings;
      const updates: Partial<ProcessingSettings> = {};

      if (lists.accountRemovalList && settingsToUse.applyAccountRemovalList === undefined) {
        updates.applyAccountRemovalList = true;
      }
      if (lists.contactRemovalList && settingsToUse.applyContactRemovalList === undefined) {
        updates.applyContactRemovalList = true;
      }

      // Only call onSettingsChange if there are updates to make
      if (Object.keys(updates).length > 0) {
        onSettingsChange({ ...settingsToUse, ...updates });
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to load active removal lists:', error);
      }
    }
  };

  const loadPresets = async (): Promise<ProcessingSettings | null> => {
    setIsLoadingPresets(true);
    try {
      const loadedPresets = await getPresets();
      setPresets(loadedPresets);
      const defaultPreset = loadedPresets.find(p => p.is_default);
      if (defaultPreset) {
        setSelectedPresetId(defaultPreset.id);
        // Always set default preset on load, ensuring tier filters exist
        const presetSettings = ensureTierFilters(defaultPreset.settings);
        onSettingsChange(presetSettings);
        return presetSettings;
      } else {
        // Fallback to hardcoded defaults if no preset found
        const fallbackSettings: ProcessingSettings = {
          includeAllFirms: false,
          findEmails: true,
          firmExclusion: false,
          contactInclusion: false,
          tier1Limit: 10,
          tier2Limit: 6,
          tier3Limit: 3,
          userPrefix: 'Combined-Contacts',
          tier1Filters: {
            includeKeywords: ['cio', 'chief investment officer', 'portfolio manager', 'director'],
            excludeKeywords: ['operations', 'hr', 'marketing'],
            requireInvestmentTeam: false,
          },
          tier2Filters: {
            includeKeywords: ['analyst', 'associate', 'director'],
            excludeKeywords: ['operations', 'hr', 'marketing'],
            requireInvestmentTeam: true,
          },
          tier3Filters: {
            includeKeywords: ['ceo', 'cfo', 'director'],
            excludeKeywords: [],
            requireInvestmentTeam: false,
          },
          firmExclusionList: '',
          firmInclusionList: '',
          contactExclusionList: '',
          contactInclusionList: '',
          fieldFilters: [],
          separateByFirmType: false,
        };
        onSettingsChange(fallbackSettings);
        return fallbackSettings;
      }
    } catch (error) {
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Failed to load presets:', error);
      }
      // Fallback to hardcoded defaults on error
      const fallbackSettings: ProcessingSettings = {
        includeAllFirms: false,
        findEmails: true,
        firmExclusion: false,
        contactInclusion: false,
        tier1Limit: 10,
        tier2Limit: 6,
        tier3Limit: 3,
        userPrefix: 'Combined-Contacts',
        tier1Filters: {
          includeKeywords: ['cio', 'chief investment officer', 'portfolio manager', 'director'],
          excludeKeywords: ['operations', 'hr', 'marketing'],
          requireInvestmentTeam: false,
        },
        tier2Filters: {
          includeKeywords: ['analyst', 'associate', 'director'],
          excludeKeywords: ['operations', 'hr', 'marketing'],
          requireInvestmentTeam: true,
        },
        tier3Filters: {
          includeKeywords: ['ceo', 'cfo', 'director'],
          excludeKeywords: [],
          requireInvestmentTeam: false,
        },
        firmExclusionList: '',
        firmInclusionList: '',
        contactExclusionList: '',
        contactInclusionList: '',
        fieldFilters: [],
        separateByFirmType: false,
      };
      onSettingsChange(fallbackSettings);
      return fallbackSettings;
    } finally {
      setIsLoadingPresets(false);
    }
  };

  const handlePresetChange = (presetId: string) => {
    const preset = presets.find(p => p.id === presetId);
    if (preset) {
      setSelectedPresetId(presetId);
      // Ensure tier filters exist when loading preset
      onSettingsChange(ensureTierFilters(preset.settings));
    }
  };

  const updateSetting = <K extends keyof ProcessingSettings>(
    key: K,
    value: ProcessingSettings[K]
  ) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  if (isLoadingPresets) {
    return (
      <div className="config-panel">
        <h2>Configuration</h2>
        <div className="config-loading">
          <p>Loading settings...</p>
        </div>
      </div>
    );
  }

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
          <p className="config-hint">Force specific contacts through filters</p>
        </div>

        <div className="config-section">
          <label className="config-toggle">
            <input
              type="checkbox"
              checked={settings.separateByFirmType || false}
              onChange={(e) => updateSetting('separateByFirmType', e.target.checked)}
            />
            <span>Separate by Firm Type</span>
          </label>
          <p className="config-hint">Generate 6 separate output files by firm type: Insurance, Wealth/Family Office, Endowments/Foundations, Pension Funds, Funds of Funds, Other</p>
        </div>

        <div className="config-section">
          <label className="config-toggle">
            <input
              type="checkbox"
              checked={settings.enableAumMerge !== false}
              onChange={(e) => updateSetting('enableAumMerge', e.target.checked)}
            />
            <span>Merge AUM Data</span>
          </label>
          <p className="config-hint">Merge Assets Under Management data from Accounts sheets into contacts</p>
        </div>
      </div>

      {/* Premier Contacts Extraction */}
      <div className="config-group">
        <h3 className="config-group-title">Premier Contacts</h3>
        <p className="config-hint" style={{ marginBottom: 'var(--spacing-md)' }}>
          Extract top firms by AUM into a separate Premier Contacts list. Requires AUM data.
        </p>

        <div className="config-section">
          <label className="config-toggle">
            <input
              type="checkbox"
              checked={settings.extractPremierContacts || false}
              onChange={(e) => updateSetting('extractPremierContacts', e.target.checked)}
              disabled={settings.enableAumMerge === false}
            />
            <span>Extract Premier Contacts</span>
          </label>
          <p className="config-hint">
            {settings.separateByFirmType
              ? `Top ${settings.premierLimit || 25} firms per firm type bucket (up to ${(settings.premierLimit || 25) * 6} firms total)`
              : `Top ${settings.premierLimit || 25} firms overall by AUM`
            }. Premier firms are removed from tiered output.
          </p>
        </div>

        {settings.extractPremierContacts && (
          <div className="config-section">
            <label className="config-label">Premier Limit (firms per bucket)</label>
            <input
              type="number"
              className="config-input"
              min="1"
              max="100"
              value={settings.premierLimit || 25}
              onChange={(e) => updateSetting('premierLimit', parseInt(e.target.value) || 25)}
            />
            <p className="config-hint">Number of top firms by AUM to extract (default: 25)</p>
          </div>
        )}
      </div>

      {/* Removal Lists */}
      {(activeLists.accountRemovalList || activeLists.contactRemovalList) && (
        <div className="config-group">
          <h3 className="config-group-title">Removal Lists</h3>
          <p className="config-hint" style={{ marginBottom: 'var(--spacing-md)' }}>
            Apply uploaded removal lists to exclude accounts or contacts from processing.
          </p>

          {activeLists.accountRemovalList && (
            <div className="config-section">
              <label className="config-toggle">
                <input
                  type="checkbox"
                  checked={settings.applyAccountRemovalList !== false}
                  onChange={(e) => updateSetting('applyAccountRemovalList', e.target.checked)}
                />
                <span>Apply Account Removal List</span>
              </label>
              <p className="config-hint">
                <strong>{activeLists.accountRemovalList.originalName}</strong> ({activeLists.accountRemovalList.entryCount.toLocaleString()} accounts)
              </p>
            </div>
          )}

          {activeLists.contactRemovalList && (
            <div className="config-section">
              <label className="config-toggle">
                <input
                  type="checkbox"
                  checked={settings.applyContactRemovalList !== false}
                  onChange={(e) => updateSetting('applyContactRemovalList', e.target.checked)}
                />
                <span>Apply Contact Removal List</span>
              </label>
              <p className="config-hint">
                <strong>{activeLists.contactRemovalList.originalName}</strong> ({activeLists.contactRemovalList.entryCount.toLocaleString()} contacts)
              </p>
            </div>
          )}
        </div>
      )}

      {/* Firm and Contact Lists */}
      <div className="config-group">
        <h3 className="config-group-title">Firm & Contact Lists</h3>
        
        <div className="config-section">
          <ListInput
            label="Firm Exclusion List"
            value={settings.firmExclusionList || ''}
            onChange={(value) => updateSetting('firmExclusionList', value)}
            placeholder="Enter firm names to exclude, one per line&#10;Example:&#10;Blackstone&#10;Goldman Sachs"
            hint="One firm name per line. These firms will be excluded from all tiers."
          />
        </div>

        <div className="config-section">
          <ListInput
            label="Firm Inclusion List"
            value={settings.firmInclusionList || ''}
            onChange={(value) => updateSetting('firmInclusionList', value)}
            placeholder="Enter firm names to include, one per line&#10;Example:&#10;Blackstone&#10;Goldman Sachs"
            hint="One firm name per line. Only these firms will be processed (if specified)."
          />
        </div>

        <div className="config-section">
          <ListInput
            label="Contact Exclusion List"
            value={settings.contactExclusionList || ''}
            onChange={(value) => updateSetting('contactExclusionList', value)}
            placeholder="Enter contacts to exclude, one per line&#10;Format: Name|Firm or Name, Firm&#10;Example:&#10;John Doe|Blackstone&#10;Jane Smith, Goldman Sachs"
            hint="Format: Name|Firm or Name, Firm (one per line). These contacts will be excluded."
          />
        </div>

        <div className="config-section">
          <ListInput
            label="Contact Inclusion List"
            value={settings.contactInclusionList || ''}
            onChange={(value) => updateSetting('contactInclusionList', value)}
            placeholder="Enter contacts to include, one per line&#10;Format: Name|Firm or Name, Firm&#10;Example:&#10;John Doe|Blackstone&#10;Jane Smith, Goldman Sachs"
            hint="Format: Name|Firm or Name, Firm (one per line). These contacts will be forced through filters."
          />
        </div>
      </div>

      {/* Field Filters */}
      <div className="config-group">
        <FieldFilters
          filters={settings.fieldFilters || []}
          onFiltersChange={(filters) => updateSetting('fieldFilters', filters)}
        />
      </div>

      {/* Tier Filter Configuration */}
      <div className="config-group">
        <h3 className="config-group-title">Tier Filter Configuration</h3>
        <p className="config-hint" style={{ marginBottom: 'var(--spacing-md)' }}>
          Configure which job titles are included or excluded for each tier. Keywords are case-insensitive.
        </p>
        
        {settings.tier1Filters && (
          <TierFilterConfigComponent
            tierNumber={1}
            config={settings.tier1Filters}
            onChange={(config) => updateSetting('tier1Filters', config)}
          />
        )}
        
        {settings.tier2Filters && (
          <TierFilterConfigComponent
            tierNumber={2}
            config={settings.tier2Filters}
            onChange={(config) => updateSetting('tier2Filters', config)}
          />
        )}
        
        {settings.tier3Filters && settings.includeAllFirms && (
          <TierFilterConfigComponent
            tierNumber={3}
            config={settings.tier3Filters}
            onChange={(config) => updateSetting('tier3Filters', config)}
          />
        )}
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

      <div className="config-actions">
        <button
          className="save-preset-button"
          onClick={() => setShowSaveDialog(true)}
          disabled={isProcessing}
        >
          Save as Preset
        </button>
        <button
          className="process-button"
          onClick={onProcess}
          disabled={isProcessing}
        >
          {isProcessing ? 'Processing...' : 'Process Contacts'}
        </button>
      </div>

      {showSaveDialog && (
        <div className="save-dialog-overlay" onClick={() => setShowSaveDialog(false)}>
          <div className="save-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Save Configuration as Preset</h3>
            <div className="save-dialog-content">
              <label>
                Preset Name:
                <input
                  type="text"
                  className="preset-name-input"
                  value={savePresetName}
                  onChange={(e) => setSavePresetName(e.target.value)}
                  placeholder="Enter preset name"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && savePresetName.trim()) {
                      handleSavePreset();
                    } else if (e.key === 'Escape') {
                      setShowSaveDialog(false);
                    }
                  }}
                />
              </label>
              <div className="save-dialog-actions">
                <button
                  className="cancel-button"
                  onClick={() => {
                    setShowSaveDialog(false);
                    setSavePresetName('');
                  }}
                >
                  Cancel
                </button>
                <button
                  className="save-button"
                  onClick={handleSavePreset}
                  disabled={!savePresetName.trim() || isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  async function handleSavePreset() {
    if (!savePresetName.trim()) {
      alert('Please enter a preset name');
      return;
    }

    setIsSaving(true);
    try {
      // Check if we're updating an existing preset
      if (selectedPresetId && !presets.find(p => p.id === selectedPresetId)?.is_default) {
        await updatePreset(selectedPresetId, savePresetName, settings);
        alert('Preset updated successfully!');
      } else {
        await createPreset(savePresetName, settings);
        alert('Preset saved successfully!');
      }
      setShowSaveDialog(false);
      setSavePresetName('');
      await loadPresets();
      // Select the newly created/updated preset
      const updatedPresets = await getPresets();
      const newPreset = updatedPresets.find(p => p.name === savePresetName);
      if (newPreset) {
        setSelectedPresetId(newPreset.id);
      }
    } catch (error) {
      console.error('Failed to save preset:', error);
      alert('Failed to save preset. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }
}

