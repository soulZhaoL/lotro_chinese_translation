export interface DictionaryItem {
  id: number;
  termKey: string;
  termValue: string;
  category: string | null;
  remark: string | null;
  isActive: boolean;
  lastModifiedBy: number | null;
  lastModifiedByName: string | null;
  crtTime: string;
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

export type DictionaryListState = {
  search: DictionaryFilters;
  page: number;
  pageSize: number;
};

export interface DictionaryMutationPayload {
  termKey: string;
  termValue: string;
  category?: string;
  remark?: string;
}
