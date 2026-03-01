export const CATEGORY_LABELS: Record<string, string> = {
  skill: "技能",
  race: "种族",
  place: "地点",
  item: "物品",
  quest: "任务",
};

export const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
  value,
  label,
}));
