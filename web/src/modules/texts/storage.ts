import { TEXT_LIST_STORAGE_KEY } from "./constants";
import type { ListStateSnapshot } from "./types";

export function parseStoredListState(): ListStateSnapshot | null {
  const raw = sessionStorage.getItem(TEXT_LIST_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as ListStateSnapshot;
  } catch {
    return null;
  }
}

export function saveListState(snapshot: ListStateSnapshot): void {
  sessionStorage.setItem(TEXT_LIST_STORAGE_KEY, JSON.stringify(snapshot));
}
