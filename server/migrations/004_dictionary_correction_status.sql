INSERT INTO users (username, `passwordHash`, `passwordSalt`, `isGuest`, `crtTime`, `uptTime`)
SELECT 'SYSTEM', '0000000000000000000000000000000000000000000000000000000000000000', '00000000000000000000000000000000', FALSE, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'SYSTEM');

ALTER TABLE dictionary_entries
  ADD COLUMN `correctionVersion` INT NOT NULL DEFAULT 0 COMMENT '当前纠错版本' AFTER `variantValues`,
  ADD COLUMN `appliedCorrectionVersion` INT NOT NULL DEFAULT 0 COMMENT '已应用纠错版本' AFTER `correctionVersion`,
  ADD COLUMN `correctionStatus` SMALLINT NOT NULL DEFAULT 0 COMMENT '纠错状态（0=无需纠错,1=待纠错,2=纠错中,3=已完成,4=失败）' AFTER `appliedCorrectionVersion`,
  ADD COLUMN `correctionLastStartedAt` TIMESTAMP NULL COMMENT '最近纠错开始时间' AFTER `correctionStatus`,
  ADD COLUMN `correctionLastFinishedAt` TIMESTAMP NULL COMMENT '最近纠错完成时间' AFTER `correctionLastStartedAt`,
  ADD COLUMN `correctionLastError` VARCHAR(255) NULL COMMENT '最近纠错错误信息' AFTER `correctionLastFinishedAt`,
  ADD COLUMN `correctionUpdatedTextCount` INT NOT NULL DEFAULT 0 COMMENT '最近纠错更新文本数' AFTER `correctionLastError`;

CREATE INDEX idx_dictionary_correction_status ON dictionary_entries(`correctionStatus`);
CREATE INDEX idx_dictionary_correction_version ON dictionary_entries(`correctionVersion`, `appliedCorrectionVersion`);
