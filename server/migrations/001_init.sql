-- LOTRO 文本汉化系统 - 初始表结构

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 确保数据库编码为 UTF8，避免特殊字符写入异常
DO $$
BEGIN
  IF (SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = current_database()) <> 'UTF8' THEN
    RAISE EXCEPTION 'Database encoding must be UTF8 for special characters.';
  END IF;
END
$$;

DROP TABLE IF EXISTS text_changes CASCADE;
DROP TABLE IF EXISTS text_locks CASCADE;
DROP TABLE IF EXISTS text_claims CASCADE;
DROP TABLE IF EXISTS text_main CASCADE;
DROP TABLE IF EXISTS role_permissions CASCADE;
DROP TABLE IF EXISTS permissions CASCADE;
DROP TABLE IF EXISTS user_roles CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS dictionary_entries CASCADE;

-- users
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  "passwordHash" VARCHAR(128) NOT NULL,
  "passwordSalt" VARCHAR(64) NOT NULL,
  "isGuest" BOOLEAN NOT NULL DEFAULT FALSE,
  "crtTime" TIMESTAMP NOT NULL DEFAULT NOW(),
  "uptTime" TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.id IS '主键ID';
COMMENT ON COLUMN users.username IS '用户名';
COMMENT ON COLUMN users."passwordHash" IS '密码哈希';
COMMENT ON COLUMN users."passwordSalt" IS '密码盐';
COMMENT ON COLUMN users."isGuest" IS '是否游客';
COMMENT ON COLUMN users."crtTime" IS '创建时间';
COMMENT ON COLUMN users."uptTime" IS '更新时间';

-- roles
CREATE TABLE roles (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(32) NOT NULL UNIQUE,
  description VARCHAR(128)
);

COMMENT ON TABLE roles IS '角色表';
COMMENT ON COLUMN roles.id IS '主键ID';
COMMENT ON COLUMN roles.name IS '角色名';
COMMENT ON COLUMN roles.description IS '角色描述';

-- user_roles
CREATE TABLE user_roles (
  "userId" BIGINT NOT NULL,
  "roleId" BIGINT NOT NULL,
  PRIMARY KEY ("userId", "roleId")
);

COMMENT ON TABLE user_roles IS '用户-角色关联表';
COMMENT ON COLUMN user_roles."userId" IS '用户ID';
COMMENT ON COLUMN user_roles."roleId" IS '角色ID';

-- permissions
CREATE TABLE permissions (
  id BIGSERIAL PRIMARY KEY,
  "permKey" VARCHAR(64) NOT NULL UNIQUE,
  description VARCHAR(128)
);

COMMENT ON TABLE permissions IS '权限表';
COMMENT ON COLUMN permissions.id IS '主键ID';
COMMENT ON COLUMN permissions."permKey" IS '权限标识';
COMMENT ON COLUMN permissions.description IS '权限描述';

-- role_permissions
CREATE TABLE role_permissions (
  "roleId" BIGINT NOT NULL,
  "permId" BIGINT NOT NULL,
  PRIMARY KEY ("roleId", "permId")
);

COMMENT ON TABLE role_permissions IS '角色-权限关联表';
COMMENT ON COLUMN role_permissions."roleId" IS '角色ID';
COMMENT ON COLUMN role_permissions."permId" IS '权限ID';

-- text_main
CREATE TABLE text_main (
  id BIGSERIAL PRIMARY KEY,
  fid VARCHAR(64) NOT NULL,
  "textId" BIGINT NOT NULL,
  part INTEGER NOT NULL,
  "sourceText" TEXT,
  "translatedText" TEXT,
  status SMALLINT NOT NULL DEFAULT 1,
  "isClaimed" BOOLEAN NOT NULL DEFAULT FALSE,
  "editCount" INT NOT NULL DEFAULT 0,
  "uptTime" TIMESTAMP NOT NULL DEFAULT NOW(),
  "crtTime" TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_text_main_status CHECK (status IN (1, 2, 3))
);

COMMENT ON TABLE text_main IS '主文本与翻译表';
COMMENT ON COLUMN text_main.id IS '主键ID';
COMMENT ON COLUMN text_main.fid IS '文件标识';
COMMENT ON COLUMN text_main."textId" IS '文本标识';
COMMENT ON COLUMN text_main.part IS '分段顺序';
COMMENT ON COLUMN text_main."sourceText" IS '原文（允许为空）';
COMMENT ON COLUMN text_main."translatedText" IS '译文';
COMMENT ON COLUMN text_main.status IS '文本状态（1=新增, 2=修改, 3=已完成）';
COMMENT ON COLUMN text_main."isClaimed" IS '认领状态（false=未认领, true=已认领）';
COMMENT ON COLUMN text_main."editCount" IS '变更次数';
COMMENT ON COLUMN text_main."uptTime" IS '最近更新时间';
COMMENT ON COLUMN text_main."crtTime" IS '创建时间';
CREATE INDEX idx_text_main_fid ON text_main(fid);
CREATE INDEX idx_text_main_fid_part ON text_main(fid, part);
CREATE INDEX idx_text_main_text_id ON text_main("textId");
CREATE INDEX idx_text_main_fid_text_id ON text_main(fid, "textId");
CREATE INDEX idx_text_main_part1 ON text_main(fid) WHERE part = 1;
CREATE INDEX idx_text_main_status ON text_main(status);
CREATE INDEX idx_text_main_upt_time ON text_main("uptTime" DESC);
CREATE INDEX idx_text_main_source_trgm ON text_main USING GIN ("sourceText" gin_trgm_ops);
CREATE INDEX idx_text_main_trans_trgm ON text_main USING GIN ("translatedText" gin_trgm_ops);

-- text_claims
CREATE TABLE text_claims (
  id BIGSERIAL PRIMARY KEY,
  "textId" BIGINT NOT NULL,
  "userId" BIGINT NOT NULL,
  "claimedAt" TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE ("textId", "userId")
);

COMMENT ON TABLE text_claims IS '文本认领记录表';
COMMENT ON COLUMN text_claims.id IS '主键ID';
COMMENT ON COLUMN text_claims."textId" IS '关联文本ID';
COMMENT ON COLUMN text_claims."userId" IS '认领用户ID';
COMMENT ON COLUMN text_claims."claimedAt" IS '认领时间';
CREATE INDEX idx_text_claims_text_id ON text_claims("textId");
CREATE INDEX idx_text_claims_user_id ON text_claims("userId");

-- text_locks
CREATE TABLE text_locks (
  id BIGSERIAL PRIMARY KEY,
  "textId" BIGINT NOT NULL,
  "userId" BIGINT NOT NULL,
  "lockedAt" TIMESTAMP NOT NULL DEFAULT NOW(),
  "expiresAt" TIMESTAMP NOT NULL,
  "releasedAt" TIMESTAMP
);

COMMENT ON TABLE text_locks IS '文本锁定表';
COMMENT ON COLUMN text_locks.id IS '主键ID';
COMMENT ON COLUMN text_locks."textId" IS '关联文本ID';
COMMENT ON COLUMN text_locks."userId" IS '锁定用户ID';
COMMENT ON COLUMN text_locks."lockedAt" IS '锁定时间';
COMMENT ON COLUMN text_locks."expiresAt" IS '过期时间';
COMMENT ON COLUMN text_locks."releasedAt" IS '释放时间';
CREATE UNIQUE INDEX uq_text_locks_active ON text_locks("textId") WHERE "releasedAt" IS NULL;
CREATE INDEX idx_text_locks_user_id ON text_locks("userId");

-- text_changes
CREATE TABLE text_changes (
  id BIGSERIAL PRIMARY KEY,
  "textId" BIGINT NOT NULL,
  "userId" BIGINT NOT NULL,
  "beforeText" TEXT NOT NULL,
  "afterText" TEXT NOT NULL,
  reason VARCHAR(255),
  "changedAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE text_changes IS '文本变更记录表';
COMMENT ON COLUMN text_changes.id IS '主键ID';
COMMENT ON COLUMN text_changes."textId" IS '关联文本ID';
COMMENT ON COLUMN text_changes."userId" IS '操作用户ID';
COMMENT ON COLUMN text_changes."beforeText" IS '变更前文本';
COMMENT ON COLUMN text_changes."afterText" IS '变更后文本';
COMMENT ON COLUMN text_changes.reason IS '变更原因';
COMMENT ON COLUMN text_changes."changedAt" IS '变更时间';
CREATE INDEX idx_text_changes_text_id ON text_changes("textId");
CREATE INDEX idx_text_changes_changed_at ON text_changes("changedAt" DESC);

-- dictionary_entries
CREATE TABLE dictionary_entries (
  id BIGSERIAL PRIMARY KEY,
  "termKey" VARCHAR(128) NOT NULL,
  "termValue" VARCHAR(128) NOT NULL,
  category VARCHAR(64),
  "isActive" BOOLEAN NOT NULL DEFAULT TRUE,
  "crtTime" TIMESTAMP NOT NULL DEFAULT NOW(),
  "uptTime" TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE dictionary_entries IS '词典条目表';
COMMENT ON COLUMN dictionary_entries.id IS '主键ID';
COMMENT ON COLUMN dictionary_entries."termKey" IS '词条Key';
COMMENT ON COLUMN dictionary_entries."termValue" IS '词条Value';
COMMENT ON COLUMN dictionary_entries.category IS '分类';
COMMENT ON COLUMN dictionary_entries."isActive" IS '是否启用';
COMMENT ON COLUMN dictionary_entries."crtTime" IS '创建时间';
COMMENT ON COLUMN dictionary_entries."uptTime" IS '更新时间';
CREATE INDEX idx_dictionary_key ON dictionary_entries("termKey");
CREATE INDEX idx_dictionary_value ON dictionary_entries("termValue");
