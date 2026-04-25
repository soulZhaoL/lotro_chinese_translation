CREATE TABLE dictionary_correction_logs (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `dictionaryEntryId` BIGINT NOT NULL COMMENT '词典条目ID',
  `correctionVersion` INT NOT NULL COMMENT '纠错版本',
  `textMainId` BIGINT NOT NULL COMMENT '文本主表ID',
  fid VARCHAR(64) NOT NULL COMMENT '文件标识',
  `textId` VARCHAR(255) NOT NULL COMMENT '文本标识',
  action VARCHAR(16) NOT NULL COMMENT '处理结果（updated/skipped）',
  reason VARCHAR(255) NOT NULL COMMENT '原因说明',
  `sourceMatchCount` INT NOT NULL COMMENT '原文命中次数',
  `translatedMatchCount` INT NOT NULL COMMENT '译文命中次数',
  `crtTime` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_dictionary_correction_logs_entry_version (`dictionaryEntryId`, `correctionVersion`),
  KEY idx_dictionary_correction_logs_entry_action (`dictionaryEntryId`, `correctionVersion`, action),
  KEY idx_dictionary_correction_logs_text (`textMainId`),
  KEY idx_dictionary_correction_logs_fid_text_id (fid, `textId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='词典纠错明细日志表';
