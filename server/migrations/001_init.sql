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
  password_hash VARCHAR(128) NOT NULL,
  password_salt VARCHAR(64) NOT NULL,
  is_guest BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.id IS '主键ID';
COMMENT ON COLUMN users.username IS '用户名';
COMMENT ON COLUMN users.password_hash IS '密码哈希';
COMMENT ON COLUMN users.password_salt IS '密码盐';
COMMENT ON COLUMN users.is_guest IS '是否游客';
COMMENT ON COLUMN users.created_at IS '创建时间';
COMMENT ON COLUMN users.updated_at IS '更新时间';

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
  user_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL,
  PRIMARY KEY (user_id, role_id)
);

COMMENT ON TABLE user_roles IS '用户-角色关联表';
COMMENT ON COLUMN user_roles.user_id IS '用户ID';
COMMENT ON COLUMN user_roles.role_id IS '角色ID';

-- permissions
CREATE TABLE permissions (
  id BIGSERIAL PRIMARY KEY,
  perm_key VARCHAR(64) NOT NULL UNIQUE,
  description VARCHAR(128)
);

COMMENT ON TABLE permissions IS '权限表';
COMMENT ON COLUMN permissions.id IS '主键ID';
COMMENT ON COLUMN permissions.perm_key IS '权限标识';
COMMENT ON COLUMN permissions.description IS '权限描述';

-- role_permissions
CREATE TABLE role_permissions (
  role_id BIGINT NOT NULL,
  perm_id BIGINT NOT NULL,
  PRIMARY KEY (role_id, perm_id)
);

COMMENT ON TABLE role_permissions IS '角色-权限关联表';
COMMENT ON COLUMN role_permissions.role_id IS '角色ID';
COMMENT ON COLUMN role_permissions.perm_id IS '权限ID';

-- text_main
CREATE TABLE text_main (
  id BIGSERIAL PRIMARY KEY,
  fid VARCHAR(64) NOT NULL,
  part VARCHAR(64) NOT NULL,
  source_text TEXT,
  translated_text TEXT,
  status SMALLINT NOT NULL DEFAULT 1,
  is_claimed BOOLEAN NOT NULL DEFAULT FALSE,
  edit_count INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_text_main_status CHECK (status IN (1, 2, 3))
);

COMMENT ON TABLE text_main IS '主文本与翻译表';
COMMENT ON COLUMN text_main.id IS '主键ID';
COMMENT ON COLUMN text_main.fid IS '文件标识';
COMMENT ON COLUMN text_main.part IS '分段标识';
COMMENT ON COLUMN text_main.source_text IS '原文（允许为空）';
COMMENT ON COLUMN text_main.translated_text IS '译文';
COMMENT ON COLUMN text_main.status IS '文本状态（1=新增, 2=修改, 3=已完成）';
COMMENT ON COLUMN text_main.is_claimed IS '认领状态（false=未认领, true=已认领）';
COMMENT ON COLUMN text_main.edit_count IS '变更次数';
COMMENT ON COLUMN text_main.updated_at IS '最近更新时间';
COMMENT ON COLUMN text_main.created_at IS '创建时间';
CREATE UNIQUE INDEX uq_text_main_fid_part ON text_main(fid, part);
CREATE INDEX idx_text_main_status ON text_main(status);
CREATE INDEX idx_text_main_updated_at ON text_main(updated_at DESC);
CREATE INDEX idx_text_main_source_trgm ON text_main USING GIN (source_text gin_trgm_ops);
CREATE INDEX idx_text_main_trans_trgm ON text_main USING GIN (translated_text gin_trgm_ops);

-- text_claims
CREATE TABLE text_claims (
  id BIGSERIAL PRIMARY KEY,
  text_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  claimed_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (text_id, user_id)
);

COMMENT ON TABLE text_claims IS '文本认领记录表';
COMMENT ON COLUMN text_claims.id IS '主键ID';
COMMENT ON COLUMN text_claims.text_id IS '关联文本ID';
COMMENT ON COLUMN text_claims.user_id IS '认领用户ID';
COMMENT ON COLUMN text_claims.claimed_at IS '认领时间';
CREATE INDEX idx_text_claims_text_id ON text_claims(text_id);
CREATE INDEX idx_text_claims_user_id ON text_claims(user_id);

-- text_locks
CREATE TABLE text_locks (
  id BIGSERIAL PRIMARY KEY,
  text_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  locked_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  released_at TIMESTAMP
);

COMMENT ON TABLE text_locks IS '文本锁定表';
COMMENT ON COLUMN text_locks.id IS '主键ID';
COMMENT ON COLUMN text_locks.text_id IS '关联文本ID';
COMMENT ON COLUMN text_locks.user_id IS '锁定用户ID';
COMMENT ON COLUMN text_locks.locked_at IS '锁定时间';
COMMENT ON COLUMN text_locks.expires_at IS '过期时间';
COMMENT ON COLUMN text_locks.released_at IS '释放时间';
CREATE UNIQUE INDEX uq_text_locks_active ON text_locks(text_id) WHERE released_at IS NULL;
CREATE INDEX idx_text_locks_user_id ON text_locks(user_id);

-- text_changes
CREATE TABLE text_changes (
  id BIGSERIAL PRIMARY KEY,
  text_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  before_text TEXT NOT NULL,
  after_text TEXT NOT NULL,
  reason VARCHAR(255),
  changed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE text_changes IS '文本变更记录表';
COMMENT ON COLUMN text_changes.id IS '主键ID';
COMMENT ON COLUMN text_changes.text_id IS '关联文本ID';
COMMENT ON COLUMN text_changes.user_id IS '操作用户ID';
COMMENT ON COLUMN text_changes.before_text IS '变更前文本';
COMMENT ON COLUMN text_changes.after_text IS '变更后文本';
COMMENT ON COLUMN text_changes.reason IS '变更原因';
COMMENT ON COLUMN text_changes.changed_at IS '变更时间';
CREATE INDEX idx_text_changes_text_id ON text_changes(text_id);
CREATE INDEX idx_text_changes_changed_at ON text_changes(changed_at DESC);

-- dictionary_entries
CREATE TABLE dictionary_entries (
  id BIGSERIAL PRIMARY KEY,
  term_key VARCHAR(128) NOT NULL,
  term_value VARCHAR(128) NOT NULL,
  category VARCHAR(64),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE dictionary_entries IS '词典条目表';
COMMENT ON COLUMN dictionary_entries.id IS '主键ID';
COMMENT ON COLUMN dictionary_entries.term_key IS '词条Key';
COMMENT ON COLUMN dictionary_entries.term_value IS '词条Value';
COMMENT ON COLUMN dictionary_entries.category IS '分类';
COMMENT ON COLUMN dictionary_entries.is_active IS '是否启用';
COMMENT ON COLUMN dictionary_entries.created_at IS '创建时间';
COMMENT ON COLUMN dictionary_entries.updated_at IS '更新时间';
CREATE INDEX idx_dictionary_key ON dictionary_entries(term_key);
CREATE INDEX idx_dictionary_value ON dictionary_entries(term_value);
