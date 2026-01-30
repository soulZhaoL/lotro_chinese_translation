-- LOTRO 文本汉化系统 - 初始表结构

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(128) NOT NULL,
  password_salt VARCHAR(64) NOT NULL,
  is_guest BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE roles (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(32) NOT NULL UNIQUE,
  description VARCHAR(128)
);

CREATE TABLE user_roles (
  user_id BIGINT NOT NULL REFERENCES users(id),
  role_id BIGINT NOT NULL REFERENCES roles(id),
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE permissions (
  id BIGSERIAL PRIMARY KEY,
  perm_key VARCHAR(64) NOT NULL UNIQUE,
  description VARCHAR(128)
);

CREATE TABLE role_permissions (
  role_id BIGINT NOT NULL REFERENCES roles(id),
  perm_id BIGINT NOT NULL REFERENCES permissions(id),
  PRIMARY KEY (role_id, perm_id)
);

CREATE TABLE text_main (
  id BIGSERIAL PRIMARY KEY,
  fid VARCHAR(64) NOT NULL,
  part VARCHAR(64) NOT NULL,
  source_text TEXT NOT NULL,
  translated_text TEXT,
  status VARCHAR(16) NOT NULL DEFAULT '待认领',
  edit_count INT NOT NULL DEFAULT 1,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_text_main_fid_part ON text_main(fid, part);
CREATE INDEX idx_text_main_status ON text_main(status);
CREATE INDEX idx_text_main_updated_at ON text_main(updated_at DESC);
CREATE INDEX idx_text_main_source_trgm ON text_main USING GIN (source_text gin_trgm_ops);
CREATE INDEX idx_text_main_trans_trgm ON text_main USING GIN (translated_text gin_trgm_ops);

CREATE TABLE text_claims (
  id BIGSERIAL PRIMARY KEY,
  text_id BIGINT NOT NULL REFERENCES text_main(id),
  user_id BIGINT NOT NULL REFERENCES users(id),
  claimed_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (text_id, user_id)
);
CREATE INDEX idx_text_claims_text_id ON text_claims(text_id);
CREATE INDEX idx_text_claims_user_id ON text_claims(user_id);

CREATE TABLE text_locks (
  id BIGSERIAL PRIMARY KEY,
  text_id BIGINT NOT NULL REFERENCES text_main(id),
  user_id BIGINT NOT NULL REFERENCES users(id),
  locked_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  released_at TIMESTAMP
);
CREATE UNIQUE INDEX uq_text_locks_active ON text_locks(text_id) WHERE released_at IS NULL;
CREATE INDEX idx_text_locks_user_id ON text_locks(user_id);

CREATE TABLE text_changes (
  id BIGSERIAL PRIMARY KEY,
  text_id BIGINT NOT NULL REFERENCES text_main(id),
  user_id BIGINT NOT NULL REFERENCES users(id),
  before_text TEXT NOT NULL,
  after_text TEXT NOT NULL,
  reason VARCHAR(255),
  changed_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_text_changes_text_id ON text_changes(text_id);
CREATE INDEX idx_text_changes_changed_at ON text_changes(changed_at DESC);

CREATE TABLE dictionary_entries (
  id BIGSERIAL PRIMARY KEY,
  term_key VARCHAR(128) NOT NULL,
  term_value VARCHAR(128) NOT NULL,
  category VARCHAR(64),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_dictionary_key ON dictionary_entries(term_key);
CREATE INDEX idx_dictionary_value ON dictionary_entries(term_value);
