-- LOTRO 文本汉化系统 - MySQL 初始表结构

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS text_changes;
DROP TABLE IF EXISTS text_locks;
DROP TABLE IF EXISTS text_claims;
DROP TABLE IF EXISTS text_main;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS dictionary_entries;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  username VARCHAR(64) NOT NULL COMMENT '用户名',
  `passwordHash` VARCHAR(128) NOT NULL COMMENT '密码哈希',
  `passwordSalt` VARCHAR(64) NOT NULL COMMENT '密码盐值',
  `isGuest` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否游客',
  `crtTime` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `uptTime` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户表';

CREATE TABLE roles (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  name VARCHAR(32) NOT NULL COMMENT '角色名',
  description VARCHAR(128) COMMENT '角色描述',
  PRIMARY KEY (id),
  UNIQUE KEY uq_roles_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色表';

CREATE TABLE user_roles (
  `userId` BIGINT NOT NULL COMMENT '用户ID',
  `roleId` BIGINT NOT NULL COMMENT '角色ID',
  PRIMARY KEY (`userId`, `roleId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户-角色关联表';

CREATE TABLE permissions (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `permKey` VARCHAR(64) NOT NULL COMMENT '权限标识',
  description VARCHAR(128) COMMENT '权限描述',
  PRIMARY KEY (id),
  UNIQUE KEY uq_permissions_perm_key (`permKey`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='权限表';

CREATE TABLE role_permissions (
  `roleId` BIGINT NOT NULL COMMENT '角色ID',
  `permId` BIGINT NOT NULL COMMENT '权限ID',
  PRIMARY KEY (`roleId`, `permId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色-权限关联表';

CREATE TABLE text_main (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  fid VARCHAR(64) NOT NULL COMMENT '文件标识',
  `textId` BIGINT NOT NULL COMMENT '文本标识',
  part INT NOT NULL COMMENT '分段顺序',
  `sourceText` TEXT COMMENT '原文',
  `sourceTextHash` VARCHAR(64) COMMENT '原文哈希（SHA256）',
  `translatedText` TEXT COMMENT '译文',
  status SMALLINT NOT NULL DEFAULT 1 COMMENT '状态（1=新增,2=修改,3=已完成）',
  `isClaimed` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已认领',
  `editCount` INT NOT NULL DEFAULT 0 COMMENT '编辑次数',
  `uptTime` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最近更新时间',
  `crtTime` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  CONSTRAINT chk_text_main_status CHECK (status IN (1, 2, 3))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='主文本与翻译表';

CREATE UNIQUE INDEX uq_text_main_fid_text_id_part ON text_main(fid, `textId`, part);
CREATE INDEX idx_text_main_fid ON text_main(fid);
CREATE INDEX idx_text_main_fid_part ON text_main(fid, part);
CREATE INDEX idx_text_main_text_id ON text_main(`textId`);
CREATE INDEX idx_text_main_fid_text_id ON text_main(fid, `textId`);
CREATE INDEX idx_text_main_status ON text_main(status);
CREATE INDEX idx_text_main_upt_time ON text_main(`uptTime`);

CREATE TABLE text_claims (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `textId` BIGINT NOT NULL COMMENT '文本ID',
  `userId` BIGINT NOT NULL COMMENT '用户ID',
  `claimedAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '认领时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_text_claims_text_user (`textId`, `userId`),
  KEY idx_text_claims_text_id (`textId`),
  KEY idx_text_claims_user_id (`userId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='文本认领记录表';

CREATE TABLE text_locks (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `textId` BIGINT NOT NULL COMMENT '文本ID',
  `userId` BIGINT NOT NULL COMMENT '用户ID',
  `lockedAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '锁定时间',
  `expiresAt` TIMESTAMP NOT NULL COMMENT '过期时间',
  `releasedAt` TIMESTAMP NULL COMMENT '释放时间',
  `activeLockTextId` BIGINT GENERATED ALWAYS AS (
    CASE
      WHEN `releasedAt` IS NULL THEN `textId`
      ELSE NULL
    END
  ) STORED COMMENT '活跃锁文本ID（用于唯一约束）',
  PRIMARY KEY (id),
  UNIQUE KEY uq_text_locks_active (`activeLockTextId`),
  KEY idx_text_locks_user_id (`userId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='文本锁定表';

CREATE TABLE text_changes (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `textId` BIGINT NOT NULL COMMENT '文本ID',
  `userId` BIGINT NOT NULL COMMENT '用户ID',
  `beforeText` TEXT NOT NULL COMMENT '变更前文本',
  `afterText` TEXT NOT NULL COMMENT '变更后文本',
  reason VARCHAR(255) COMMENT '变更原因',
  `changedAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
  PRIMARY KEY (id),
  KEY idx_text_changes_text_id (`textId`),
  KEY idx_text_changes_changed_at (`changedAt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='文本变更记录表';

CREATE TABLE dictionary_entries (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `termKey` VARCHAR(128) NOT NULL COMMENT '词条Key',
  `termValue` VARCHAR(128) NOT NULL COMMENT '词条Value',
  category VARCHAR(64) COMMENT '分类',
  `isActive` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
  `crtTime` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `uptTime` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_dictionary_key (`termKey`),
  KEY idx_dictionary_value (`termValue`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='词典条目表';
