import { useState } from 'react';
import type { FieldFilter } from '@/types';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ChevronDown, ChevronRight, X, Plus } from 'lucide-react';

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
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Field Filters</h3>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
        >
          {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </Button>
      </div>

      {isOpen && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Filter contacts by specific field values. Only contacts matching the selected values will be included.
          </p>

          {filters.length === 0 ? (
            <div className="p-4 text-center bg-muted/50 rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">No field filters added</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filters.map((filter, filterIndex) => (
                <div key={filterIndex} className="p-3 border rounded-lg space-y-3">
                  <div className="flex items-center gap-2">
                    <Select value={filter.field} onValueChange={(value) => updateFilterField(filterIndex, value)}>
                      <SelectTrigger className="flex-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {availableFieldsForSelect(filter.field).map(field => (
                          <SelectItem key={field.value} value={field.value}>
                            {field.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => removeFilter(filterIndex)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs">Values to include (leave empty for all):</Label>
                    <Input
                      placeholder="Enter value and press Enter"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addFilterValue(filterIndex, e.currentTarget.value);
                          e.currentTarget.value = '';
                        }
                      }}
                    />
                    {filter.values.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {filter.values.map((value, valueIndex) => (
                          <Badge key={valueIndex} variant="secondary" className="gap-1">
                            {value}
                            <button
                              onClick={() => removeFilterValue(filterIndex, valueIndex)}
                              className="ml-1 hover:text-destructive"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">All contacts will be included for this field</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {filters.length < AVAILABLE_FIELDS.length && (
            <Button variant="outline" size="sm" onClick={addFilter} type="button">
              <Plus className="h-4 w-4 mr-1" />
              Add Filter
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
