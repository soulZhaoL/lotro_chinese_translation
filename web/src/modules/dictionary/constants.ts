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
