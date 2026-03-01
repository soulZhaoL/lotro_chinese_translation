import type { TextStatus } from "./types";

export const TEXT_LIST_STORAGE_KEY = "texts_list_state";

export const TEXT_STATUS_META: Record<TextStatus, { label: string; color: string }> = {
  1: { label: "新增", color: "default" },
  2: { label: "修改", color: "processing" },
  3: { label: "已完成", color: "success" },
};

export const TEXT_STATUS_VALUE_ENUM = {
  1: { text: "新增" },
  2: { text: "修改" },
  3: { text: "已完成" },
} as const;
