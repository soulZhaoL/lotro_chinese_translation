-- LOTRO 文本汉化系统 - 时间字段统一迁移为 uptTime/crtTime

DO $$
DECLARE
  has_created_at BOOLEAN;
  has_createdAt BOOLEAN;
  has_crtTime BOOLEAN;
  has_updated_at BOOLEAN;
  has_updatedAt BOOLEAN;
  has_uptTime BOOLEAN;
BEGIN
  -- users.created
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'created_at'
  ) INTO has_created_at;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'createdAt'
  ) INTO has_createdAt;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'crtTime'
  ) INTO has_crtTime;

  IF has_created_at AND has_createdAt THEN
    RAISE EXCEPTION 'users 创建时间字段冲突: created_at 与 createdAt 同时存在';
  END IF;
  IF has_crtTime AND (has_created_at OR has_createdAt) THEN
    RAISE EXCEPTION 'users 创建时间字段冲突: crtTime 与旧字段同时存在';
  END IF;

  IF has_created_at THEN
    ALTER TABLE users RENAME COLUMN created_at TO "crtTime";
  ELSIF has_createdAt THEN
    ALTER TABLE users RENAME COLUMN "createdAt" TO "crtTime";
  END IF;

  -- users.updated
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'updated_at'
  ) INTO has_updated_at;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'updatedAt'
  ) INTO has_updatedAt;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'uptTime'
  ) INTO has_uptTime;

  IF has_updated_at AND has_updatedAt THEN
    RAISE EXCEPTION 'users 更新时间字段冲突: updated_at 与 updatedAt 同时存在';
  END IF;
  IF has_uptTime AND (has_updated_at OR has_updatedAt) THEN
    RAISE EXCEPTION 'users 更新时间字段冲突: uptTime 与旧字段同时存在';
  END IF;

  IF has_updated_at THEN
    ALTER TABLE users RENAME COLUMN updated_at TO "uptTime";
  ELSIF has_updatedAt THEN
    ALTER TABLE users RENAME COLUMN "updatedAt" TO "uptTime";
  END IF;

  -- text_main.created
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'created_at'
  ) INTO has_created_at;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'createdAt'
  ) INTO has_createdAt;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'crtTime'
  ) INTO has_crtTime;

  IF has_created_at AND has_createdAt THEN
    RAISE EXCEPTION 'text_main 创建时间字段冲突: created_at 与 createdAt 同时存在';
  END IF;
  IF has_crtTime AND (has_created_at OR has_createdAt) THEN
    RAISE EXCEPTION 'text_main 创建时间字段冲突: crtTime 与旧字段同时存在';
  END IF;

  IF has_created_at THEN
    ALTER TABLE text_main RENAME COLUMN created_at TO "crtTime";
  ELSIF has_createdAt THEN
    ALTER TABLE text_main RENAME COLUMN "createdAt" TO "crtTime";
  END IF;

  -- text_main.updated
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'updated_at'
  ) INTO has_updated_at;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'updatedAt'
  ) INTO has_updatedAt;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'text_main' AND column_name = 'uptTime'
  ) INTO has_uptTime;

  IF has_updated_at AND has_updatedAt THEN
    RAISE EXCEPTION 'text_main 更新时间字段冲突: updated_at 与 updatedAt 同时存在';
  END IF;
  IF has_uptTime AND (has_updated_at OR has_updatedAt) THEN
    RAISE EXCEPTION 'text_main 更新时间字段冲突: uptTime 与旧字段同时存在';
  END IF;

  IF has_updated_at THEN
    ALTER TABLE text_main RENAME COLUMN updated_at TO "uptTime";
  ELSIF has_updatedAt THEN
    ALTER TABLE text_main RENAME COLUMN "updatedAt" TO "uptTime";
  END IF;

  -- dictionary_entries.created
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'created_at'
  ) INTO has_created_at;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'createdAt'
  ) INTO has_createdAt;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'crtTime'
  ) INTO has_crtTime;

  IF has_created_at AND has_createdAt THEN
    RAISE EXCEPTION 'dictionary_entries 创建时间字段冲突: created_at 与 createdAt 同时存在';
  END IF;
  IF has_crtTime AND (has_created_at OR has_createdAt) THEN
    RAISE EXCEPTION 'dictionary_entries 创建时间字段冲突: crtTime 与旧字段同时存在';
  END IF;

  IF has_created_at THEN
    ALTER TABLE dictionary_entries RENAME COLUMN created_at TO "crtTime";
  ELSIF has_createdAt THEN
    ALTER TABLE dictionary_entries RENAME COLUMN "createdAt" TO "crtTime";
  END IF;

  -- dictionary_entries.updated
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'updated_at'
  ) INTO has_updated_at;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'updatedAt'
  ) INTO has_updatedAt;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dictionary_entries' AND column_name = 'uptTime'
  ) INTO has_uptTime;

  IF has_updated_at AND has_updatedAt THEN
    RAISE EXCEPTION 'dictionary_entries 更新时间字段冲突: updated_at 与 updatedAt 同时存在';
  END IF;
  IF has_uptTime AND (has_updated_at OR has_updatedAt) THEN
    RAISE EXCEPTION 'dictionary_entries 更新时间字段冲突: uptTime 与旧字段同时存在';
  END IF;

  IF has_updated_at THEN
    ALTER TABLE dictionary_entries RENAME COLUMN updated_at TO "uptTime";
  ELSIF has_updatedAt THEN
    ALTER TABLE dictionary_entries RENAME COLUMN "updatedAt" TO "uptTime";
  END IF;

  -- 索引名称同步
  IF EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'public' AND tablename = 'text_main' AND indexname = 'idx_text_main_updated_at'
  )
  AND EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'public' AND tablename = 'text_main' AND indexname = 'idx_text_main_upt_time'
  ) THEN
    RAISE EXCEPTION 'text_main 索引冲突: idx_text_main_updated_at 与 idx_text_main_upt_time 同时存在';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'public' AND tablename = 'text_main' AND indexname = 'idx_text_main_updated_at'
  )
  AND NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'public' AND tablename = 'text_main' AND indexname = 'idx_text_main_upt_time'
  ) THEN
    ALTER INDEX idx_text_main_updated_at RENAME TO idx_text_main_upt_time;
  END IF;
END
$$;
