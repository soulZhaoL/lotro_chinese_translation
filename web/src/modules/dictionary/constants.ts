export type DictionaryCategoryMeta = {
  label: string;
  color: string;
};

export const CATEGORY_META: Record<string, DictionaryCategoryMeta> = {
  skill: { label: "技能", color: "blue" },
  race: { label: "种族", color: "gold" },
  place: { label: "地点", color: "cyan" },
  item: { label: "物品", color: "green" },
  quest: { label: "任务", color: "purple" },
};

export const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(CATEGORY_META).map(([value, meta]) => [value, meta.label])
);

export const CATEGORY_OPTIONS = Object.entries(CATEGORY_META).map(([value, meta]) => ({
  value,
  label: meta.label,
}));

export type DictionaryCorrectionStatusMeta = {
  label: string;
  color: string;
};

export const DICTIONARY_CORRECTION_STATUS_META: Record<number, DictionaryCorrectionStatusMeta> = {
  0: { label: "无需纠错", color: "default" },
  1: { label: "待纠错", color: "orange" },
  2: { label: "纠错中", color: "processing" },
  3: { label: "已完成", color: "success" },
  4: { label: "失败", color: "error" },
};
