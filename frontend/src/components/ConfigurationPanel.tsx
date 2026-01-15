import { useState, useEffect } from 'react';
import type { ProcessingSettings, SettingsPreset } from '@/types';
import { getPresets, createPreset, updatePreset, getActiveRemovalLists, type ActiveRemovalLists } from '@/services/api';
import TierFilterConfigComponent from './TierFilterConfig';
import ListInput from './ListInput';
import FieldFilters from './FieldFilters';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Loader2 } from 'lucide-react';

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

  const ensureTierFilters = (presetSettings: ProcessingSettings): ProcessingSettings => {
    return {
      ...presetSettings,
      tier1Filters: presetSettings.tier1Filters || defaultTierFilters.tier1Filters,
      tier2Filters: presetSettings.tier2Filters || defaultTierFilters.tier2Filters,
      tier3Filters: presetSettings.tier3Filters || defaultTierFilters.tier3Filters,
    };
  };

  useEffect(() => {
    loadPresets().then((loadedSettings) => {
      loadActiveRemovalLists(loadedSettings || undefined);
    });
  }, []);

  const loadActiveRemovalLists = async (currentSettings?: ProcessingSettings) => {
    try {
      const lists = await getActiveRemovalLists();
      setActiveLists(lists);
      const settingsToUse = currentSettings || settings;
      const updates: Partial<ProcessingSettings> = {};

      if (lists.accountRemovalList && settingsToUse.applyAccountRemovalList === undefined) {
        updates.applyAccountRemovalList = true;
      }
      if (lists.contactRemovalList && settingsToUse.applyContactRemovalList === undefined) {
        updates.applyContactRemovalList = true;
      }

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
        const presetSettings = ensureTierFilters(defaultPreset.settings);
        onSettingsChange(presetSettings);
        return presetSettings;
      } else {
        const fallbackSettings: ProcessingSettings = {
          includeAllFirms: false,
          findEmails: true,
          firmExclusion: false,
          contactInclusion: false,
          tier1Limit: 10,
          tier2Limit: 6,
          tier3Limit: 3,
          userPrefix: 'Combined-Contacts',
          ...defaultTierFilters,
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
      if (import.meta.env.DEV) {
        console.error('Failed to load presets:', error);
      }
      const fallbackSettings: ProcessingSettings = {
        includeAllFirms: false,
        findEmails: true,
        firmExclusion: false,
        contactInclusion: false,
        tier1Limit: 10,
        tier2Limit: 6,
        tier3Limit: 3,
        userPrefix: 'Combined-Contacts',
        ...defaultTierFilters,
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
      onSettingsChange(ensureTierFilters(preset.settings));
    }
  };

  const updateSetting = <K extends keyof ProcessingSettings>(
    key: K,
    value: ProcessingSettings[K]
  ) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  const handleSavePreset = async () => {
    if (!savePresetName.trim()) {
      alert('Please enter a preset name');
      return;
    }

    setIsSaving(true);
    try {
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
  };

  if (isLoadingPresets) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading settings...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Configuration</h2>

      {/* Preset Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Preset</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label>Select Preset</Label>
            <Select value={selectedPresetId} onValueChange={handlePresetChange}>
              <SelectTrigger>
                <SelectValue placeholder="Select a preset" />
              </SelectTrigger>
              <SelectContent>
                {presets.map(preset => (
                  <SelectItem key={preset.id} value={preset.id}>
                    {preset.name} {preset.is_default ? '(Default)' : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">Choose a preset or customize settings below</p>
          </div>
        </CardContent>
      </Card>

      {/* Tier Limits */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tier Limits</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label>Tier 1 Limit</Label>
              <Input
                type="number"
                min={1}
                max={50}
                value={settings.tier1Limit}
                onChange={(e) => updateSetting('tier1Limit', parseInt(e.target.value) || 10)}
              />
              <p className="text-xs text-muted-foreground">Key contacts per firm</p>
            </div>
            <div className="space-y-2">
              <Label>Tier 2 Limit</Label>
              <Input
                type="number"
                min={1}
                max={50}
                value={settings.tier2Limit}
                onChange={(e) => updateSetting('tier2Limit', parseInt(e.target.value) || 6)}
              />
              <p className="text-xs text-muted-foreground">Junior contacts per firm</p>
            </div>
            <div className="space-y-2">
              <Label>Tier 3 Limit</Label>
              <Input
                type="number"
                min={1}
                max={10}
                value={settings.tier3Limit}
                onChange={(e) => updateSetting('tier3Limit', parseInt(e.target.value) || 3)}
                disabled={!settings.includeAllFirms}
              />
              <p className="text-xs text-muted-foreground">Rescued contacts per firm</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Options */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Advanced Options</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Include All Firms (Tier 3 Rescue)</Label>
              <p className="text-sm text-muted-foreground">Rescue contacts from firms with zero Tier 1/2</p>
            </div>
            <Switch
              checked={settings.includeAllFirms}
              onCheckedChange={(checked) => updateSetting('includeAllFirms', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Find Emails</Label>
              <p className="text-sm text-muted-foreground">Auto-discover firm email schemas</p>
            </div>
            <Switch
              checked={settings.findEmails}
              onCheckedChange={(checked) => updateSetting('findEmails', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Separate by Firm Type</Label>
              <p className="text-sm text-muted-foreground">Generate separate files by firm type</p>
            </div>
            <Switch
              checked={settings.separateByFirmType || false}
              onCheckedChange={(checked) => updateSetting('separateByFirmType', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Merge AUM Data</Label>
              <p className="text-sm text-muted-foreground">Merge Assets Under Management from Accounts</p>
            </div>
            <Switch
              checked={settings.enableAumMerge !== false}
              onCheckedChange={(checked) => updateSetting('enableAumMerge', checked)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Premier Contacts */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Premier Contacts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Extract Premier Contacts</Label>
              <p className="text-sm text-muted-foreground">
                {settings.separateByFirmType
                  ? `Top ${settings.premierLimit || 25} firms per type`
                  : `Top ${settings.premierLimit || 25} firms by AUM`}
              </p>
            </div>
            <Switch
              checked={settings.extractPremierContacts || false}
              onCheckedChange={(checked) => updateSetting('extractPremierContacts', checked)}
              disabled={settings.enableAumMerge === false}
            />
          </div>

          {settings.extractPremierContacts && (
            <div className="space-y-2">
              <Label>Premier Limit</Label>
              <Input
                type="number"
                min={1}
                max={100}
                value={settings.premierLimit || 25}
                onChange={(e) => updateSetting('premierLimit', parseInt(e.target.value) || 25)}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Removal Lists */}
      {(activeLists.accountRemovalList || activeLists.contactRemovalList) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Removal Lists</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {activeLists.accountRemovalList && (
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Apply Account Removal List</Label>
                  <p className="text-sm text-muted-foreground">
                    {activeLists.accountRemovalList.originalName} ({activeLists.accountRemovalList.entryCount.toLocaleString()} accounts)
                  </p>
                </div>
                <Switch
                  checked={settings.applyAccountRemovalList !== false}
                  onCheckedChange={(checked) => updateSetting('applyAccountRemovalList', checked)}
                />
              </div>
            )}

            {activeLists.contactRemovalList && (
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Apply Contact Removal List</Label>
                  <p className="text-sm text-muted-foreground">
                    {activeLists.contactRemovalList.originalName} ({activeLists.contactRemovalList.entryCount.toLocaleString()} contacts)
                  </p>
                </div>
                <Switch
                  checked={settings.applyContactRemovalList !== false}
                  onCheckedChange={(checked) => updateSetting('applyContactRemovalList', checked)}
                />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Firm & Contact Lists */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Firm & Contact Lists</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ListInput
            label="Firm Exclusion List"
            value={settings.firmExclusionList || ''}
            onChange={(value) => updateSetting('firmExclusionList', value)}
            placeholder="Enter firm names to exclude, one per line"
            hint="These firms will be excluded from all tiers."
          />
          <ListInput
            label="Firm Inclusion List"
            value={settings.firmInclusionList || ''}
            onChange={(value) => updateSetting('firmInclusionList', value)}
            placeholder="Enter firm names to include, one per line"
            hint="Only these firms will be processed (if specified)."
          />
          <ListInput
            label="Contact Exclusion List"
            value={settings.contactExclusionList || ''}
            onChange={(value) => updateSetting('contactExclusionList', value)}
            placeholder="Format: Name|Firm or Name, Firm"
            hint="These contacts will be excluded."
          />
          <ListInput
            label="Contact Inclusion List"
            value={settings.contactInclusionList || ''}
            onChange={(value) => updateSetting('contactInclusionList', value)}
            placeholder="Format: Name|Firm or Name, Firm"
            hint="These contacts will be forced through filters."
          />
        </CardContent>
      </Card>

      {/* Field Filters */}
      <Card>
        <CardContent className="pt-6">
          <FieldFilters
            filters={settings.fieldFilters || []}
            onFiltersChange={(filters) => updateSetting('fieldFilters', filters)}
          />
        </CardContent>
      </Card>

      {/* Tier Filter Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tier Filter Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">Configure which job titles are included or excluded for each tier.</p>

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
        </CardContent>
      </Card>

      {/* Output Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Output Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Label>Output Prefix</Label>
          <Input
            value={settings.userPrefix}
            onChange={(e) => updateSetting('userPrefix', e.target.value)}
            placeholder="Combined-Contacts"
          />
          <p className="text-sm text-muted-foreground">Prefix for output filename</p>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3 justify-end">
        <Button variant="outline" onClick={() => setShowSaveDialog(true)} disabled={isProcessing}>
          Save as Preset
        </Button>
        <Button onClick={onProcess} disabled={isProcessing}>
          {isProcessing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            'Process Contacts'
          )}
        </Button>
      </div>

      {/* Save Dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Configuration as Preset</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Preset Name</Label>
              <Input
                value={savePresetName}
                onChange={(e) => setSavePresetName(e.target.value)}
                placeholder="Enter preset name"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && savePresetName.trim()) {
                    handleSavePreset();
                  }
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowSaveDialog(false); setSavePresetName(''); }}>
              Cancel
            </Button>
            <Button onClick={handleSavePreset} disabled={!savePresetName.trim() || isSaving}>
              {isSaving ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
