-- LOTRO 文本汉化系统 - 下划线字段迁移为驼峰字段
-- 注意：时间字段从 createdAt/updatedAt 到 crtTime/uptTime 的迁移由 003 脚本负责。

DO $$
BEGIN
  -- users
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'password_hash'
  ) THEN
    ALTER TABLE users RENAME COLUMN password_hash TO "passwordHash";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'password_salt'
  ) THEN
    ALTER TABLE users RENAME COLUMN password_salt TO "passwordSalt";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'is_guest'
  ) THEN
    ALTER TABLE users RENAME COLUMN is_guest TO "isGuest";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'created_at'
  ) THEN
    ALTER TABLE users RENAME COLUMN created_at TO "createdAt";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'updated_at'
  ) THEN
    ALTER TABLE users RENAME COLUMN updated_at TO "updatedAt";
  END IF;

  -- user_roles
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'user_roles' AND column_name = 'user_id'
  ) THEN
    ALTER TABLE user_roles RENAME COLUMN user_id TO "userId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'user_roles' AND column_name = 'role_id'
  ) THEN
    ALTER TABLE user_roles RENAME COLUMN role_id TO "roleId";
  END IF;

  -- permissions
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'permissions' AND column_name = 'perm_key'
  ) THEN
    ALTER TABLE permissions RENAME COLUMN perm_key TO "permKey";
  END IF;

  -- role_permissions
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'role_permissions' AND column_name = 'role_id'
  ) THEN
    ALTER TABLE role_permissions RENAME COLUMN role_id TO "roleId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'role_permissions' AND column_name = 'perm_id'
  ) THEN
    ALTER TABLE role_permissions RENAME COLUMN perm_id TO "permId";
  END IF;

  -- text_main
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'text_id'
  ) THEN
    ALTER TABLE text_main RENAME COLUMN text_id TO "textId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'source_text'
  ) THEN
    ALTER TABLE text_main RENAME COLUMN source_text TO "sourceText";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'translated_text'
  ) THEN
    ALTER TABLE text_main RENAME COLUMN translated_text TO "translatedText";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'is_claimed'
  ) THEN
    ALTER TABLE text_main RENAME COLUMN is_claimed TO "isClaimed";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'edit_count'
  ) THEN
    ALTER TABLE text_main RENAME COLUMN edit_count TO "editCount";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'updated_at'
  ) THEN
    ALTER TABLE text_main RENAME COLUMN updated_at TO "updatedAt";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'created_at'
  ) THEN
    ALTER TABLE text_main RENAME COLUMN created_at TO "createdAt";
  END IF;

  -- text_claims
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_claims' AND column_name = 'text_id'
  ) THEN
    ALTER TABLE text_claims RENAME COLUMN text_id TO "textId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_claims' AND column_name = 'user_id'
  ) THEN
    ALTER TABLE text_claims RENAME COLUMN user_id TO "userId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_claims' AND column_name = 'claimed_at'
  ) THEN
    ALTER TABLE text_claims RENAME COLUMN claimed_at TO "claimedAt";
  END IF;

  -- text_locks
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_locks' AND column_name = 'text_id'
  ) THEN
    ALTER TABLE text_locks RENAME COLUMN text_id TO "textId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_locks' AND column_name = 'user_id'
  ) THEN
    ALTER TABLE text_locks RENAME COLUMN user_id TO "userId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_locks' AND column_name = 'locked_at'
  ) THEN
    ALTER TABLE text_locks RENAME COLUMN locked_at TO "lockedAt";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_locks' AND column_name = 'expires_at'
  ) THEN
    ALTER TABLE text_locks RENAME COLUMN expires_at TO "expiresAt";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_locks' AND column_name = 'released_at'
  ) THEN
    ALTER TABLE text_locks RENAME COLUMN released_at TO "releasedAt";
  END IF;

  -- text_changes
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_changes' AND column_name = 'text_id'
  ) THEN
    ALTER TABLE text_changes RENAME COLUMN text_id TO "textId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_changes' AND column_name = 'user_id'
  ) THEN
    ALTER TABLE text_changes RENAME COLUMN user_id TO "userId";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_changes' AND column_name = 'before_text'
  ) THEN
    ALTER TABLE text_changes RENAME COLUMN before_text TO "beforeText";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_changes' AND column_name = 'after_text'
  ) THEN
    ALTER TABLE text_changes RENAME COLUMN after_text TO "afterText";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_changes' AND column_name = 'changed_at'
  ) THEN
    ALTER TABLE text_changes RENAME COLUMN changed_at TO "changedAt";
  END IF;

  -- dictionary_entries
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'term_key'
  ) THEN
    ALTER TABLE dictionary_entries RENAME COLUMN term_key TO "termKey";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'term_value'
  ) THEN
    ALTER TABLE dictionary_entries RENAME COLUMN term_value TO "termValue";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'is_active'
  ) THEN
    ALTER TABLE dictionary_entries RENAME COLUMN is_active TO "isActive";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'created_at'
  ) THEN
    ALTER TABLE dictionary_entries RENAME COLUMN created_at TO "createdAt";
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'updated_at'
  ) THEN
    ALTER TABLE dictionary_entries RENAME COLUMN updated_at TO "updatedAt";
  END IF;
END
$$;
