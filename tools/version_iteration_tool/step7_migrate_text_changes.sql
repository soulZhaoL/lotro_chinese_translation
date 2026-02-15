\if :{?map_table}
\else
\echo 'ERROR: missing required variable map_table'
\echo 'Usage: psql "$LOTRO_DATABASE_DSN" -v map_table=textIdMap_u46_to_u46_1 -v changes_table=text_changes -f tools/version_iteration_tool/step7_migrate_text_changes.sql'
\quit 1
\endif

\if :{?changes_table}
\else
\echo 'ERROR: missing required variable changes_table'
\echo 'Usage: psql "$LOTRO_DATABASE_DSN" -v map_table=textIdMap_u46_to_u46_1 -v changes_table=text_changes -f tools/version_iteration_tool/step7_migrate_text_changes.sql'
\quit 1
\endif

BEGIN;

DO $$
DECLARE
  map_table_name TEXT := :'map_table';
  changes_table_name TEXT := :'changes_table';

  map_rel REGCLASS;
  changes_rel REGCLASS;
  map_schema TEXT;
  map_name TEXT;
  map_parts TEXT[];
  map_parts_len INT;
  changes_schema TEXT;
  changes_name TEXT;
  changes_parts TEXT[];
  changes_parts_len INT;
  schema_exists BOOLEAN;
  required_column TEXT;

  map_dup_old_id_cnt BIGINT;
  map_dup_new_id_cnt BIGINT;
  map_row_cnt BIGINT;

  total_before BIGINT;
  matched_old_before BIGINT;
  matched_new_before BIGINT;
  expected_remaining BIGINT;

  updated_rows BIGINT;
  deleted_rows BIGINT;
  remaining_rows BIGINT;
BEGIN
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

  IF map_rel IS NULL THEN
    RAISE EXCEPTION '映射表不存在: %', map_table_name;
  END IF;

  changes_parts := string_to_array(changes_table_name, '.');
  changes_parts_len := COALESCE(array_length(changes_parts, 1), 0);
  IF changes_parts_len = 1 THEN
    changes_schema := 'public';
    changes_name := changes_parts[1];
  ELSIF changes_parts_len = 2 THEN
    changes_schema := changes_parts[1];
    changes_name := changes_parts[2];
  ELSE
    RAISE EXCEPTION 'changes_table 格式不合法，必须为 table 或 schema.table: %', changes_table_name;
  END IF;

  IF changes_schema IS NULL OR changes_schema = '' OR changes_name IS NULL OR changes_name = '' THEN
    RAISE EXCEPTION 'changes_table 解析失败: %', changes_table_name;
  END IF;

  SELECT EXISTS (
    SELECT 1
    FROM pg_namespace
    WHERE nspname = changes_schema
  ) INTO schema_exists;
  IF NOT schema_exists THEN
    RAISE EXCEPTION '变更表 schema 不存在: %', changes_schema;
  END IF;

  SELECT c.oid::regclass
  INTO changes_rel
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = changes_schema
    AND c.relname = changes_name
    AND c.relkind IN ('r', 'p')
  LIMIT 1;

  IF changes_rel IS NULL THEN
    RAISE EXCEPTION '变更表不存在: %', changes_table_name;
  END IF;

  FOREACH required_column IN ARRAY ARRAY['oldId', 'newId']
  LOOP
    PERFORM 1
    FROM pg_attribute
    WHERE attrelid = map_rel
      AND attname = required_column
      AND NOT attisdropped;
    IF NOT FOUND THEN
      RAISE EXCEPTION '映射表缺少字段: %.%', map_table_name, required_column;
    END IF;
  END LOOP;

  FOREACH required_column IN ARRAY ARRAY['id', 'textId']
  LOOP
    PERFORM 1
    FROM pg_attribute
    WHERE attrelid = changes_rel
      AND attname = required_column
      AND NOT attisdropped;
    IF NOT FOUND THEN
      RAISE EXCEPTION '变更表缺少字段: %.%', changes_table_name, required_column;
    END IF;
  END LOOP;

  EXECUTE format(
    'SELECT COUNT(*) FROM (SELECT "oldId", COUNT(*) c FROM %s GROUP BY "oldId" HAVING COUNT(*) > 1) t',
    map_rel
  ) INTO map_dup_old_id_cnt;

  IF map_dup_old_id_cnt > 0 THEN
    RAISE EXCEPTION '映射表存在重复 oldId，数量=%', map_dup_old_id_cnt;
  END IF;

  EXECUTE format(
    'SELECT COUNT(*) FROM (SELECT "newId", COUNT(*) c FROM %s GROUP BY "newId" HAVING COUNT(*) > 1) t',
    map_rel
  ) INTO map_dup_new_id_cnt;

  IF map_dup_new_id_cnt > 0 THEN
    RAISE EXCEPTION '映射表存在重复 newId，数量=%', map_dup_new_id_cnt;
  END IF;

  EXECUTE format('SELECT COUNT(*) FROM %s', map_rel) INTO map_row_cnt;
  IF map_row_cnt = 0 THEN
    RAISE EXCEPTION '映射表为空，停止迁移以避免误删: %', map_table_name;
  END IF;

  EXECUTE format('SELECT COUNT(*) FROM %s', changes_rel) INTO total_before;

  EXECUTE format(
    $q$
    SELECT COUNT(*)
    FROM %1$s AS c
    JOIN %2$s AS m
      ON c."textId" = m."oldId"
    $q$,
    changes_rel,
    map_rel
  ) INTO matched_old_before;

  EXECUTE format(
    $q$
    SELECT COUNT(*)
    FROM %1$s AS c
    JOIN %2$s AS m
      ON c."textId" = m."newId"
    $q$,
    changes_rel,
    map_rel
  ) INTO matched_new_before;

  EXECUTE format(
    $q$
    SELECT COUNT(*)
    FROM %1$s AS c
    WHERE EXISTS (
      SELECT 1
      FROM %2$s AS m
      WHERE c."textId" = m."oldId"
    )
       OR EXISTS (
      SELECT 1
      FROM %2$s AS m
      WHERE c."textId" = m."newId"
    )
    $q$,
    changes_rel,
    map_rel
  ) INTO expected_remaining;

  RAISE NOTICE 'Step7 precheck: total_before=% matched_old=% matched_new=% keep_after_migrate=%',
    total_before,
    matched_old_before,
    matched_new_before,
    expected_remaining;

  -- 1) 按 oldId -> newId 做迁移。
  EXECUTE format(
    $q$
    UPDATE %1$s AS c
    SET "textId" = m."newId"
    FROM %2$s AS m
    WHERE c."textId" = m."oldId"
    $q$,
    changes_rel,
    map_rel
  );
  GET DIAGNOSTICS updated_rows = ROW_COUNT;

  -- 2) 清理未命中（只保留最终可落在 newId 集合中的记录）。
  EXECUTE format(
    $q$
    DELETE FROM %1$s AS c
    WHERE NOT EXISTS (
      SELECT 1
      FROM %2$s AS m
      WHERE c."textId" = m."newId"
    )
    $q$,
    changes_rel,
    map_rel
  );
  GET DIAGNOSTICS deleted_rows = ROW_COUNT;

  EXECUTE format('SELECT COUNT(*) FROM %s', changes_rel) INTO remaining_rows;

  IF updated_rows <> matched_old_before THEN
    RAISE EXCEPTION '迁移更新行数不一致: expected=% actual=%', matched_old_before, updated_rows;
  END IF;

  IF remaining_rows <> expected_remaining THEN
    RAISE EXCEPTION '迁移后保留行数不一致: expected=% actual=%', expected_remaining, remaining_rows;
  END IF;

  IF deleted_rows <> (total_before - expected_remaining) THEN
    RAISE EXCEPTION '清理删除行数不一致: expected=% actual=%', (total_before - expected_remaining), deleted_rows;
  END IF;

  RAISE NOTICE 'Step7 完成: updated=% deleted=% remaining=%', updated_rows, deleted_rows, remaining_rows;
END
$$;

COMMIT;
