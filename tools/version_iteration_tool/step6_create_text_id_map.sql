\if :{?backup_table}
\else
\echo 'ERROR: missing required variable backup_table'
\echo 'Usage: psql "$LOTRO_DATABASE_DSN" -v backup_table=text_main_bak_u46 -v next_table=text_main_next -v map_table=textIdMap_u46_to_u46_1 -f tools/version_iteration_tool/step6_create_text_id_map.sql'
\quit 1
\endif

\if :{?next_table}
\else
\echo 'ERROR: missing required variable next_table'
\echo 'Usage: psql "$LOTRO_DATABASE_DSN" -v backup_table=text_main_bak_u46 -v next_table=text_main_next -v map_table=textIdMap_u46_to_u46_1 -f tools/version_iteration_tool/step6_create_text_id_map.sql'
\quit 1
\endif

\if :{?map_table}
\else
\echo 'ERROR: missing required variable map_table'
\echo 'Usage: psql "$LOTRO_DATABASE_DSN" -v backup_table=text_main_bak_u46 -v next_table=text_main_next -v map_table=textIdMap_u46_to_u46_1 -f tools/version_iteration_tool/step6_create_text_id_map.sql'
\quit 1
\endif

BEGIN;

DO $$
DECLARE
  backup_table_name TEXT := :'backup_table';
  next_table_name TEXT := :'next_table';
  map_table_name TEXT := :'map_table';

  backup_rel REGCLASS;
  next_rel REGCLASS;
  map_rel REGCLASS;

  map_schema TEXT;
  map_name TEXT;
  map_qualified TEXT;
  map_parts TEXT[];
  map_parts_len INT;
  schema_exists BOOLEAN;

  required_column TEXT;
  backup_dup_key_cnt BIGINT;
  next_dup_key_cnt BIGINT;
  backup_null_hash_cnt BIGINT;
  next_null_hash_cnt BIGINT;
  mapped_rows BIGINT;
  expected_rows BIGINT;
BEGIN
  backup_rel := to_regclass(backup_table_name);
  next_rel := to_regclass(next_table_name);

  IF backup_rel IS NULL THEN
    RAISE EXCEPTION '备份表不存在: %', backup_table_name;
  END IF;
  IF next_rel IS NULL THEN
    RAISE EXCEPTION 'next表不存在: %', next_table_name;
  END IF;

  FOREACH required_column IN ARRAY ARRAY['id', 'fid', 'textId', 'part', 'sourceTextHash']
  LOOP
    PERFORM 1
    FROM pg_attribute
    WHERE attrelid = backup_rel
      AND attname = required_column
      AND NOT attisdropped;
    IF NOT FOUND THEN
      RAISE EXCEPTION '备份表缺少字段: %.%', backup_table_name, required_column;
    END IF;

    PERFORM 1
    FROM pg_attribute
    WHERE attrelid = next_rel
      AND attname = required_column
      AND NOT attisdropped;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'next表缺少字段: %.%', next_table_name, required_column;
    END IF;
  END LOOP;

  EXECUTE format(
    'SELECT COUNT(*) FROM (SELECT fid, "textId", part, COUNT(*) c FROM %s GROUP BY fid, "textId", part HAVING COUNT(*) > 1) t',
    backup_rel
  ) INTO backup_dup_key_cnt;
  IF backup_dup_key_cnt > 0 THEN
    RAISE EXCEPTION '备份表存在重复 key(fid,textId,part)，数量=%', backup_dup_key_cnt;
  END IF;

  EXECUTE format(
    'SELECT COUNT(*) FROM (SELECT fid, "textId", part, COUNT(*) c FROM %s GROUP BY fid, "textId", part HAVING COUNT(*) > 1) t',
    next_rel
  ) INTO next_dup_key_cnt;
  IF next_dup_key_cnt > 0 THEN
    RAISE EXCEPTION 'next表存在重复 key(fid,textId,part)，数量=%', next_dup_key_cnt;
  END IF;

  EXECUTE format('SELECT COUNT(*) FROM %s WHERE "sourceTextHash" IS NULL', backup_rel)
    INTO backup_null_hash_cnt;
  EXECUTE format('SELECT COUNT(*) FROM %s WHERE "sourceTextHash" IS NULL', next_rel)
    INTO next_null_hash_cnt;

  IF backup_null_hash_cnt > 0 THEN
    RAISE EXCEPTION '备份表存在空哈希记录，数量=%', backup_null_hash_cnt;
  END IF;
  IF next_null_hash_cnt > 0 THEN
    RAISE EXCEPTION 'next表存在空哈希记录，数量=%', next_null_hash_cnt;
  END IF;

  map_parts := string_to_array(map_table_name, '.');
  map_parts_len := COALESCE(array_length(map_parts, 1), 0);

  IF map_parts_len = 1 THEN
    map_schema := 'public';
    map_name := map_parts[1];
  ELSIF map_parts_len = 2 THEN
    map_schema := map_parts[1];
    map_name := map_parts[2];
  ELSE
    RAISE EXCEPTION 'map_table 格式不合法，必须为 table 或 schema.table: %', map_table_name;
  END IF;

  IF map_schema IS NULL OR map_schema = '' OR map_name IS NULL OR map_name = '' THEN
    RAISE EXCEPTION 'map_table 解析失败: %', map_table_name;
  END IF;

  SELECT EXISTS (
    SELECT 1
    FROM pg_namespace
    WHERE nspname = map_schema
  ) INTO schema_exists;

  IF NOT schema_exists THEN
    RAISE EXCEPTION '映射表 schema 不存在: %', map_schema;
  END IF;

  SELECT c.oid::regclass
  INTO map_rel
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = map_schema
    AND c.relname = map_name
    AND c.relkind IN ('r', 'p')
  LIMIT 1;

  IF map_rel IS NOT NULL THEN
    RAISE EXCEPTION '映射表已存在，请先确认并手动处理: %', map_table_name;
  END IF;

  map_qualified := quote_ident(map_schema) || '.' || quote_ident(map_name);

  EXECUTE format(
    $q$
    CREATE TABLE %s (
      "oldId" BIGINT PRIMARY KEY,
      "newId" BIGINT NOT NULL UNIQUE,
      fid VARCHAR(64) NOT NULL,
      "textId" BIGINT NOT NULL,
      part INTEGER NOT NULL,
      "sourceTextHash" VARCHAR(64) NOT NULL,
      "crtTime" TIMESTAMP NOT NULL DEFAULT NOW(),
      UNIQUE (fid, "textId", part)
    )
    $q$,
    map_qualified
  );

  EXECUTE format(
    $q$
    INSERT INTO %1$s ("oldId", "newId", fid, "textId", part, "sourceTextHash")
    SELECT
      bak.id AS "oldId",
      nxt.id AS "newId",
      nxt.fid,
      nxt."textId",
      nxt.part,
      nxt."sourceTextHash"
    FROM %2$s AS nxt
    JOIN %3$s AS bak
      ON nxt.fid = bak.fid
     AND nxt."textId" = bak."textId"
     AND nxt.part = bak.part
    WHERE nxt."sourceTextHash" IS NOT DISTINCT FROM bak."sourceTextHash"
    $q$,
    map_qualified,
    next_rel,
    backup_rel
  );
  GET DIAGNOSTICS mapped_rows = ROW_COUNT;

  EXECUTE format(
    $q$
    SELECT COUNT(*)
    FROM %1$s AS nxt
    JOIN %2$s AS bak
      ON nxt.fid = bak.fid
     AND nxt."textId" = bak."textId"
     AND nxt.part = bak.part
    WHERE nxt."sourceTextHash" IS NOT DISTINCT FROM bak."sourceTextHash"
    $q$,
    next_rel,
    backup_rel
  ) INTO expected_rows;

  IF mapped_rows <> expected_rows THEN
    RAISE EXCEPTION '映射行数不一致: expected=% actual=%', expected_rows, mapped_rows;
  END IF;

  RAISE NOTICE 'Step6 完成: map_table=%, mapped_rows=%', map_table_name, mapped_rows;
END
$$;

COMMIT;
