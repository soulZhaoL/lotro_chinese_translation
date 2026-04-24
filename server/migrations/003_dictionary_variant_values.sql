ALTER TABLE dictionary_entries
  ADD COLUMN `variantValues` JSON NULL COMMENT '非标准/历史译文变体列表' AFTER `termValue`;
