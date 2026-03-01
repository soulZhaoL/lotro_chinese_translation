export type MaintenanceProps = {
  message?: string;
};

export interface TranslateTextDetail {
  text: {
    id: number;
    fid: string;
    part: string;
    sourceText: string | null;
    translatedText: string | null;
    status: number;
  };
  claims: Array<{ id: number; userId: number; claimedAt: string }>;
  locks: Array<{ id: number; userId: number; lockedAt: string; expiresAt: string; releasedAt: string | null }>;
}
