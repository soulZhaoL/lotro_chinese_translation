export type TextStatus = 1 | 2 | 3;
export type TextMatchMode = "fuzzy" | "exact";

export interface TextClaim {
  id: number;
  userId: number;
  claimedAt: string;
}

export interface TextLock {
  id: number;
  userId: number;
  lockedAt: string;
  expiresAt: string;
  releasedAt: string | null;
}

export interface TextItem {
  id: number;
  fid: string;
  textId: string;
  part: number;
  sourceText: string | null;
  translatedText: string | null;
  status: TextStatus;
  editCount: number;
  uptTime: string;
  crtTime: string;
  claimId: number | null;
  claimedBy: string | null;
  claimedAt: string | null;
  isClaimed: boolean;
}

export interface TextListResponse {
  items: TextItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface QueryParams {
  fid?: string;
  textId?: string;
  status?: number | string;
  sourceKeyword?: string;
  sourceMatchMode?: TextMatchMode;
  translatedKeyword?: string;
  translatedMatchMode?: TextMatchMode;
  updatedFrom?: string;
  updatedTo?: string;
  claimer?: string;
  claimed?: string | boolean;
}

export type ListStateSnapshot = {
  search: QueryParams;
  page: number;
  pageSize: number;
};

export type ActiveConfirmState = { type: "claim" | "release"; id: number } | null;

export interface TextDetailByTextIdResponse {
  text: {
    id: number;
    fid: string;
    textId: string;
    part: number;
    sourceText: string | null;
    translatedText: string | null;
    status: TextStatus;
    editCount: number;
    uptTime: string;
    crtTime: string;
  };
  claims: TextClaim[];
  locks: TextLock[];
}

export interface ChangeItem {
  id: number;
  textId: number;
  userId: number;
  beforeText: string;
  afterText: string;
  reason: string | null;
  changedAt: string;
}

export interface ChangesResponse {
  items: ChangeItem[];
}

export interface TextIdOnlyResponse {
  text: {
    id: number;
  };
}
