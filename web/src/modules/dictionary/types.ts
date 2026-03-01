export interface DictionaryItem {
  id: number;
  termKey: string;
  termValue: string;
  category: string | null;
  isActive: boolean;
  uptTime: string;
}

export interface DictionaryResponse {
  items: DictionaryItem[];
  total: number;
  page: number;
  pageSize: number;
}

export type DictionaryFilters = {
  termKey?: string;
  termValue?: string;
  category?: string;
};
