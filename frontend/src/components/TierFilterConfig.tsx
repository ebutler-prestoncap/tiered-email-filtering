import { useState } from 'react';
import type { TierFilterConfig } from '@/types';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { X } from 'lucide-react';

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
    <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
      <h4 className="font-medium">Tier {tierNumber} Filter Configuration</h4>

      {/* Include Keywords */}
      <div className="space-y-2">
        <Label>Include Keywords</Label>
        <p className="text-xs text-muted-foreground">Job titles matching these will be included</p>
        <div className="flex gap-2">
          <Input
            value={includeKeyword}
            onChange={(e) => setIncludeKeyword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addIncludeKeyword();
              }
            }}
            placeholder="e.g., cio, chief investment officer"
            className="flex-1"
          />
          <Button type="button" onClick={addIncludeKeyword} disabled={!includeKeyword.trim()} size="sm">
            Add
          </Button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {config.includeKeywords.length === 0 ? (
            <p className="text-xs text-muted-foreground">No include keywords added</p>
          ) : (
            config.includeKeywords.map((keyword, idx) => (
              <Badge key={idx} variant="secondary" className="bg-green-500/15 text-green-600 gap-1">
                {keyword}
                <button
                  type="button"
                  onClick={() => removeIncludeKeyword(keyword)}
                  className="ml-1 hover:text-green-800"
                  aria-label={`Remove ${keyword}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))
          )}
        </div>
      </div>

      {/* Exclude Keywords */}
      <div className="space-y-2">
        <Label>Exclude Keywords</Label>
        <p className="text-xs text-muted-foreground">Job titles containing these will be excluded</p>
        <div className="flex gap-2">
          <Input
            value={excludeKeyword}
            onChange={(e) => setExcludeKeyword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addExcludeKeyword();
              }
            }}
            placeholder="e.g., operations, hr, marketing"
            className="flex-1"
          />
          <Button type="button" onClick={addExcludeKeyword} disabled={!excludeKeyword.trim()} size="sm">
            Add
          </Button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {config.excludeKeywords.length === 0 ? (
            <p className="text-xs text-muted-foreground">No exclude keywords added</p>
          ) : (
            config.excludeKeywords.map((keyword, idx) => (
              <Badge key={idx} variant="secondary" className="bg-red-500/15 text-red-600 gap-1">
                {keyword}
                <button
                  type="button"
                  onClick={() => removeExcludeKeyword(keyword)}
                  className="ml-1 hover:text-red-800"
                  aria-label={`Remove ${keyword}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))
          )}
        </div>
      </div>

      {/* Require Investment Team */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label>Require Investment Team</Label>
          <p className="text-xs text-muted-foreground">
            Must have "investment team" or "portfolio management" in ROLE field
          </p>
        </div>
        <Switch
          checked={config.requireInvestmentTeam}
          onCheckedChange={(checked) => onChange({ ...config, requireInvestmentTeam: checked })}
        />
      </div>
    </div>
  );
}
