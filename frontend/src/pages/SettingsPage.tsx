import { useEffect, useState } from 'react';
import { getPresets, createPreset, updatePreset, deletePreset, setDefaultPreset } from '@/services/api';
import type { SettingsPreset, ProcessingSettings, TierFilterConfig } from '@/types';
import FieldFilters from '@/components/FieldFilters';
import ListInput from '@/components/ListInput';
import TierFilterConfigComponent from '@/components/TierFilterConfig';
import RemovalListManager from '@/components/RemovalListManager';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus, X, Pencil, Star } from 'lucide-react';

const DEFAULT_TIER1_FILTERS: TierFilterConfig = {
  includeKeywords: ['cio', 'chief investment officer', 'portfolio manager', 'director'],
  excludeKeywords: ['operations', 'hr', 'marketing'],
  requireInvestmentTeam: false,
};

const DEFAULT_TIER2_FILTERS: TierFilterConfig = {
  includeKeywords: ['analyst', 'associate', 'director'],
  excludeKeywords: ['operations', 'hr', 'marketing'],
  requireInvestmentTeam: true,
};

const DEFAULT_TIER3_FILTERS: TierFilterConfig = {
  includeKeywords: ['ceo', 'cfo', 'director'],
  excludeKeywords: [],
  requireInvestmentTeam: false,
};

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
      if (import.meta.env.DEV) {
        console.error('Create preset error:', error);
      }
    }
  };

  const handleEditPreset = (preset: SettingsPreset) => {
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
      if (import.meta.env.DEV) {
        console.error('Delete preset error:', error);
      }
    }
  };

  const handleSetDefault = async (presetId: string, presetName: string) => {
    if (!confirm(`Set "${presetName}" as the default preset? This will be applied to all new processing jobs.`)) {
      return;
    }

    try {
      await setDefaultPreset(presetId);
      loadPresets();
    } catch (error) {
      alert('Failed to set default preset');
      if (import.meta.env.DEV) {
        console.error('Set default preset error:', error);
      }
    }
  };

  const renderEditForm = (preset: SettingsPreset) => (
    <div className="space-y-6">
      <h4 className="font-semibold">Edit {preset.is_default ? 'Default Preset' : `Preset: ${preset.name}`}</h4>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="includeAllFirms"
            checked={editSettings?.includeAllFirms || false}
            onCheckedChange={(checked) => setEditSettings(prev => prev ? { ...prev, includeAllFirms: !!checked } : null)}
          />
          <Label htmlFor="includeAllFirms">Include All Firms</Label>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="findEmails"
            checked={editSettings?.findEmails || false}
            onCheckedChange={(checked) => setEditSettings(prev => prev ? { ...prev, findEmails: !!checked } : null)}
          />
          <Label htmlFor="findEmails">Find Emails</Label>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="firmExclusion"
            checked={editSettings?.firmExclusion || false}
            onCheckedChange={(checked) => setEditSettings(prev => prev ? { ...prev, firmExclusion: !!checked } : null)}
          />
          <Label htmlFor="firmExclusion">Firm Exclusion</Label>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="contactInclusion"
            checked={editSettings?.contactInclusion || false}
            onCheckedChange={(checked) => setEditSettings(prev => prev ? { ...prev, contactInclusion: !!checked } : null)}
          />
          <Label htmlFor="contactInclusion">Contact Inclusion</Label>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="separateByFirmType"
            checked={editSettings?.separateByFirmType || false}
            onCheckedChange={(checked) => setEditSettings(prev => prev ? { ...prev, separateByFirmType: !!checked } : null)}
          />
          <Label htmlFor="separateByFirmType">Separate by Firm Type</Label>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-2">
          <Label htmlFor="tier1Limit">Tier 1 Limit</Label>
          <Input
            id="tier1Limit"
            type="number"
            min={1}
            max={50}
            value={editSettings?.tier1Limit || 10}
            onChange={(e) => setEditSettings(prev => prev ? { ...prev, tier1Limit: parseInt(e.target.value) || 10 } : null)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="tier2Limit">Tier 2 Limit</Label>
          <Input
            id="tier2Limit"
            type="number"
            min={1}
            max={50}
            value={editSettings?.tier2Limit || 6}
            onChange={(e) => setEditSettings(prev => prev ? { ...prev, tier2Limit: parseInt(e.target.value) || 6 } : null)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="tier3Limit">Tier 3 Limit</Label>
          <Input
            id="tier3Limit"
            type="number"
            min={1}
            max={10}
            value={editSettings?.tier3Limit || 3}
            onChange={(e) => setEditSettings(prev => prev ? { ...prev, tier3Limit: parseInt(e.target.value) || 3 } : null)}
            disabled={!editSettings?.includeAllFirms}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="userPrefix">Output Prefix</Label>
          <Input
            id="userPrefix"
            type="text"
            value={editSettings?.userPrefix || 'Combined-Contacts'}
            onChange={(e) => setEditSettings(prev => prev ? { ...prev, userPrefix: e.target.value } : null)}
          />
        </div>
      </div>

      <div className="space-y-4">
        <h5 className="font-medium">Firm & Contact Lists</h5>
        <div className="grid gap-4 lg:grid-cols-2">
          <ListInput
            label="Firm Exclusion List"
            value={editSettings?.firmExclusionList || ''}
            onChange={(value) => setEditSettings(prev => prev ? { ...prev, firmExclusionList: value } : null)}
            placeholder="Enter firm names to exclude, one per line"
            hint="One firm name per line. These firms will be excluded."
          />
          <ListInput
            label="Firm Inclusion List"
            value={editSettings?.firmInclusionList || ''}
            onChange={(value) => setEditSettings(prev => prev ? { ...prev, firmInclusionList: value } : null)}
            placeholder="Enter firm names to include, one per line"
            hint="One firm name per line. Only these firms will be processed."
          />
          <ListInput
            label="Contact Exclusion List"
            value={editSettings?.contactExclusionList || ''}
            onChange={(value) => setEditSettings(prev => prev ? { ...prev, contactExclusionList: value } : null)}
            placeholder="Enter contacts to exclude (Name|Firm), one per line"
            hint="Format: Name|Firm per line. These contacts will be excluded."
          />
          <ListInput
            label="Contact Inclusion List"
            value={editSettings?.contactInclusionList || ''}
            onChange={(value) => setEditSettings(prev => prev ? { ...prev, contactInclusionList: value } : null)}
            placeholder="Enter contacts to include (Name|Firm), one per line"
            hint="Format: Name|Firm per line. These contacts will bypass filters."
          />
        </div>
      </div>

      <div className="space-y-4">
        <h5 className="font-medium">Tier Filter Configurations</h5>
        <div className="space-y-4">
          <TierFilterConfigComponent
            tierNumber={1}
            config={editSettings?.tier1Filters || DEFAULT_TIER1_FILTERS}
            onChange={(config) => setEditSettings(prev => prev ? { ...prev, tier1Filters: config } : null)}
          />
          <TierFilterConfigComponent
            tierNumber={2}
            config={editSettings?.tier2Filters || DEFAULT_TIER2_FILTERS}
            onChange={(config) => setEditSettings(prev => prev ? { ...prev, tier2Filters: config } : null)}
          />
          <TierFilterConfigComponent
            tierNumber={3}
            config={editSettings?.tier3Filters || DEFAULT_TIER3_FILTERS}
            onChange={(config) => setEditSettings(prev => prev ? { ...prev, tier3Filters: config } : null)}
          />
        </div>
      </div>

      <div className="space-y-4">
        <FieldFilters
          filters={editSettings?.fieldFilters || []}
          onFiltersChange={(filters) => setEditSettings(prev => prev ? { ...prev, fieldFilters: filters } : null)}
        />
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={handleCancelEdit}>Cancel</Button>
        <Button onClick={handleSaveEdit}>Save Changes</Button>
      </div>
    </div>
  );

  const renderPresetCard = (preset: SettingsPreset) => (
    <Card key={preset.id} className={preset.is_default ? 'border-primary' : ''}>
      <div className="p-4">
        {editingPreset?.id === preset.id ? (
          renderEditForm(preset)
        ) : (
          <>
            <div className="flex items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-2">
                <span className="font-semibold">{preset.name}</span>
                {preset.is_default && (
                  <Badge className="bg-primary">Default</Badge>
                )}
              </div>
              <div className="flex items-center gap-2">
                {!preset.is_default && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSetDefault(preset.id, preset.name)}
                  >
                    <Star className="h-4 w-4 mr-1" />
                    Set Default
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleEditPreset(preset)}
                >
                  <Pencil className="h-4 w-4 mr-1" />
                  Edit
                </Button>
                {!preset.is_default && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => handleDeletePreset(preset.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>

            <div className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <span className="text-muted-foreground">Include All Firms:</span>{' '}
                <span className="font-medium">{preset.settings.includeAllFirms ? 'Yes' : 'No'}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Find Emails:</span>{' '}
                <span className="font-medium">{preset.settings.findEmails ? 'Yes' : 'No'}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Firm Exclusion:</span>{' '}
                <span className="font-medium">{preset.settings.firmExclusion ? 'Yes' : 'No'}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Contact Inclusion:</span>{' '}
                <span className="font-medium">{preset.settings.contactInclusion ? 'Yes' : 'No'}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Tier 1 Limit:</span>{' '}
                <span className="font-medium">{preset.settings.tier1Limit}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Tier 2 Limit:</span>{' '}
                <span className="font-medium">{preset.settings.tier2Limit}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Tier 3 Limit:</span>{' '}
                <span className="font-medium">{preset.settings.tier3Limit}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Output Prefix:</span>{' '}
                <span className="font-medium">{preset.settings.userPrefix}</span>
              </div>
            </div>
          </>
        )}
      </div>
    </Card>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const defaultPreset = presets.find(p => p.is_default);
  const customPresets = presets.filter(p => !p.is_default);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-muted-foreground">
          Manage removal lists and configuration presets for processing contacts.
        </p>
      </div>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Removal Lists</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Upload CSV files containing accounts or contacts to remove from processing.
            The most recent active list of each type will be applied by default to all jobs.
          </p>
        </div>
        <Card className="p-6">
          <RemovalListManager />
        </Card>
      </section>

      {defaultPreset && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Default Preset</h2>
          {renderPresetCard(defaultPreset)}
        </section>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Custom Presets</h2>
          <Button
            variant={showCreateForm ? 'outline' : 'default'}
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? 'Cancel' : (
              <>
                <Plus className="h-4 w-4 mr-2" />
                Create Preset
              </>
            )}
          </Button>
        </div>

        {showCreateForm && (
          <Card className="p-4">
            <div className="flex gap-2">
              <Input
                placeholder="Preset name"
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                className="max-w-xs"
              />
              <Button onClick={handleCreatePreset}>Create</Button>
            </div>
          </Card>
        )}

        {customPresets.length === 0 ? (
          <p className="text-muted-foreground">No custom presets yet.</p>
        ) : (
          <div className="space-y-4">
            {customPresets.map(preset => renderPresetCard(preset))}
          </div>
        )}
      </section>
    </div>
  );
}
