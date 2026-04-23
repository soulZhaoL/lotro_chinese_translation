ALTER TABLE dictionary_entries
  ADD COLUMN remark VARCHAR(255) NULL COMMENT '备注' AFTER category,
  ADD COLUMN `lastModifiedBy` BIGINT NULL COMMENT '最后修改人ID' AFTER `isActive`;

CREATE INDEX idx_dictionary_category ON dictionary_entries(category);
CREATE INDEX idx_dictionary_last_modified_by ON dictionary_entries(`lastModifiedBy`);

CREATE UNIQUE INDEX uq_dictionary_term_key ON dictionary_entries(`termKey`);
