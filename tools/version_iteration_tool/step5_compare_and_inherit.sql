\if :{?backup_table}
\else
\echo 'ERROR: missing required variable backup_table'
\echo 'Usage: psql "$LOTRO_DATABASE_DSN" -v backup_table=text_main_bak_u46 -v next_table=text_main_next -f tools/version_iteration_tool/step5_compare_and_inherit.sql'
\quit 1
\endif

\if :{?next_table}
\else
\echo 'ERROR: missing required variable next_table'
\echo 'Usage: psql "$LOTRO_DATABASE_DSN" -v backup_table=text_main_bak_u46 -v next_table=text_main_next -f tools/version_iteration_tool/step5_compare_and_inherit.sql'
\quit 1
\endif

BEGIN;

DO $$
DECLARE
  backup_table_name TEXT := :'backup_table';
  next_table_name TEXT := :'next_table';
  backup_rel REGCLASS;
  next_rel REGCLASS;
  required_column TEXT;

  backup_dup_key_cnt BIGINT;
  next_dup_key_cnt BIGINT;
  backup_null_hash_cnt BIGINT;
  next_null_hash_cnt BIGINT;

  new_cnt BIGINT;
  changed_cnt BIGINT;
  unchanged_cnt BIGINT;

  reset_new_rows BIGINT;
  updated_changed_rows BIGINT;
  inherited_rows BIGINT;
BEGIN
  backup_rel := to_regclass(backup_table_name);
  next_rel := to_regclass(next_table_name);

  IF backup_rel IS NULL THEN
    RAISE EXCEPTION '备份表不存在: %', backup_table_name;
  END IF;
  IF next_rel IS NULL THEN
    RAISE EXCEPTION 'next表不存在: %', next_table_name;
  END IF;

  FOREACH required_column IN ARRAY ARRAY['id', 'fid', 'textId', 'part', 'sourceTextHash', 'translatedText', 'status', 'editCount']
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

  PERFORM 1
  FROM pg_attribute
  WHERE attrelid = next_rel
    AND attname = 'uptTime'
    AND NOT attisdropped;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'next表缺少字段: %.uptTime', next_table_name;
  END IF;

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

  EXECUTE format(
    $q$
    SELECT
      COUNT(*) FILTER (WHERE bak.id IS NULL) AS new_cnt,
      COUNT(*) FILTER (
        WHERE bak.id IS NOT NULL
          AND nxt."sourceTextHash" IS DISTINCT FROM bak."sourceTextHash"
      ) AS changed_cnt,
      COUNT(*) FILTER (
        WHERE bak.id IS NOT NULL
          AND nxt."sourceTextHash" IS NOT DISTINCT FROM bak."sourceTextHash"
      ) AS unchanged_cnt
    FROM %1$s AS nxt
    LEFT JOIN %2$s AS bak
      ON nxt.fid = bak.fid
     AND nxt."textId" = bak."textId"
     AND nxt.part = bak.part
    $q$,
    next_rel,
    backup_rel
  ) INTO new_cnt, changed_cnt, unchanged_cnt;

  RAISE NOTICE '分类统计: new=% changed=% unchanged=%', new_cnt, changed_cnt, unchanged_cnt;

  -- 1) 新增: 保留 next 表现有译文，仅标记为新增。
  EXECUTE format(
    $q$
    UPDATE %1$s AS nxt
    SET
      status = 1,
      "uptTime" = NOW()
    WHERE NOT EXISTS (
      SELECT 1
      FROM %2$s AS bak
      WHERE bak.fid = nxt.fid
        AND bak."textId" = nxt."textId"
        AND bak.part = nxt.part
    )
    $q$,
    next_rel,
    backup_rel
  );
  GET DIAGNOSTICS reset_new_rows = ROW_COUNT;

  -- 2) 修改: 命中 key 但哈希不同，保留 next 表现有译文并标记为修改。
  EXECUTE format(
    $q$
    UPDATE %1$s AS nxt
    SET
      status = 2,
      "uptTime" = NOW()
    FROM %2$s AS bak
    WHERE nxt.fid = bak.fid
      AND nxt."textId" = bak."textId"
      AND nxt.part = bak.part
      AND nxt."sourceTextHash" IS DISTINCT FROM bak."sourceTextHash"
    $q$,
    next_rel,
    backup_rel
  );
  GET DIAGNOSTICS updated_changed_rows = ROW_COUNT;

  -- 3) 未变化: 命中 key 且哈希相同，继承译文/状态/编辑次数。
  EXECUTE format(
    $q$
    UPDATE %1$s AS nxt
    SET
      "translatedText" = bak."translatedText",
      status = bak.status,
      "editCount" = bak."editCount",
      "uptTime" = NOW()
    FROM %2$s AS bak
    WHERE nxt.fid = bak.fid
      AND nxt."textId" = bak."textId"
      AND nxt.part = bak.part
      AND nxt."sourceTextHash" IS NOT DISTINCT FROM bak."sourceTextHash"
    $q$,
    next_rel,
    backup_rel
  );
  GET DIAGNOSTICS inherited_rows = ROW_COUNT;

  IF reset_new_rows <> new_cnt THEN
    RAISE EXCEPTION '新增分类数量不一致: expected=% actual=%', new_cnt, reset_new_rows;
  END IF;
  IF updated_changed_rows <> changed_cnt THEN
    RAISE EXCEPTION '修改分类数量不一致: expected=% actual=%', changed_cnt, updated_changed_rows;
  END IF;
  IF inherited_rows <> unchanged_cnt THEN
    RAISE EXCEPTION '继承分类数量不一致: expected=% actual=%', unchanged_cnt, inherited_rows;
  END IF;

  RAISE NOTICE 'Step5 完成: reset_new=% changed=% inherited=%', reset_new_rows, updated_changed_rows, inherited_rows;
END
$$;

COMMIT;
