-- Step5: 比对备份表与 next 表，分类并继承译文（MySQL）

DELIMITER //

DROP PROCEDURE IF EXISTS step5_compare_and_inherit //
CREATE PROCEDURE step5_compare_and_inherit(
    IN p_backup_table VARCHAR(255),
    IN p_next_table VARCHAR(255)
)
BEGIN
    DECLARE msg TEXT;
    DECLARE backup_schema VARCHAR(128);
    DECLARE backup_name VARCHAR(128);

    SET backup_schema = SUBSTRING_INDEX(p_backup_table, '.', 1);
    SET backup_name = SUBSTRING_INDEX(p_backup_table, '.', -1);

    SELECT COUNT(*) INTO @backup_has_join_idx
    FROM (
        SELECT index_name
        FROM information_schema.statistics
        WHERE table_schema = backup_schema
          AND table_name = backup_name
        GROUP BY index_name
        HAVING
            SUM(CASE WHEN seq_in_index = 1 AND column_name = 'fid' THEN 1 ELSE 0 END) = 1
            AND SUM(CASE WHEN seq_in_index = 2 AND column_name = 'textId' THEN 1 ELSE 0 END) = 1
            AND SUM(CASE WHEN seq_in_index = 3 AND column_name = 'part' THEN 1 ELSE 0 END) = 1
    ) AS idx_candidates;

    IF @backup_has_join_idx = 0 THEN
        SET @sql = CONCAT(
            'CREATE INDEX idx_step5_join_key ON ',
            p_backup_table,
            ' (fid, `textId`, part)'
        );
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;

    SET @sql = CONCAT('ANALYZE TABLE ', p_backup_table, ', ', p_next_table);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @backup_dup_key_cnt FROM (',
        'SELECT fid, `textId`, part, COUNT(*) c FROM ', p_backup_table, ' ',
        'GROUP BY fid, `textId`, part HAVING COUNT(*) > 1',
        ') t'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @backup_dup_key_cnt > 0 THEN
        SET msg = CONCAT('备份表存在重复 key(fid,textId,part)，数量=', @backup_dup_key_cnt);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @next_dup_key_cnt FROM (',
        'SELECT fid, `textId`, part, COUNT(*) c FROM ', p_next_table, ' ',
        'GROUP BY fid, `textId`, part HAVING COUNT(*) > 1',
        ') t'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @next_dup_key_cnt > 0 THEN
        SET msg = CONCAT('next表存在重复 key(fid,textId,part)，数量=', @next_dup_key_cnt);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    SET @sql = CONCAT('SELECT COUNT(*) INTO @backup_null_hash_cnt FROM ', p_backup_table, ' WHERE `sourceTextHash` IS NULL');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @backup_null_hash_cnt > 0 THEN
        SET msg = CONCAT('备份表存在空哈希记录，数量=', @backup_null_hash_cnt);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    SET @sql = CONCAT('SELECT COUNT(*) INTO @next_null_hash_cnt FROM ', p_next_table, ' WHERE `sourceTextHash` IS NULL');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @next_null_hash_cnt > 0 THEN
        SET msg = CONCAT('next表存在空哈希记录，数量=', @next_null_hash_cnt);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    DROP TEMPORARY TABLE IF EXISTS tmp_step5_classify;
    CREATE TEMPORARY TABLE tmp_step5_classify (
        next_id BIGINT NOT NULL,
        bak_id BIGINT NULL,
        class TINYINT NOT NULL,
        PRIMARY KEY (next_id),
        KEY idx_tmp_step5_class (class),
        KEY idx_tmp_step5_bak_id (bak_id)
    ) ENGINE=InnoDB;

    SET @sql = CONCAT(
        'INSERT INTO tmp_step5_classify (next_id, bak_id, class) ',
        'SELECT nxt.id, bak.id, ',
        'CASE ',
        'WHEN bak.id IS NULL THEN 1 ',
        'WHEN nxt.`sourceTextHash` <=> bak.`sourceTextHash` THEN 3 ',
        'ELSE 2 ',
        'END AS class ',
        'FROM ', p_next_table, ' AS nxt ',
        'LEFT JOIN ', p_backup_table, ' AS bak ',
        'ON nxt.fid = bak.fid AND nxt.`textId` = bak.`textId` AND nxt.part = bak.part'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SELECT
        COALESCE(SUM(class = 1), 0),
        COALESCE(SUM(class = 2), 0),
        COALESCE(SUM(class = 3), 0)
    INTO @new_cnt, @changed_cnt, @unchanged_cnt
    FROM tmp_step5_classify;

    SET @sql = CONCAT(
        'UPDATE ', p_next_table, ' AS nxt ',
        'JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id ',
        'SET nxt.status = 1, nxt.`uptTime` = NOW() ',
        'WHERE cls.class = 1'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'UPDATE ', p_next_table, ' AS nxt ',
        'JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id ',
        'SET nxt.status = 2, nxt.`uptTime` = NOW() ',
        'WHERE cls.class = 2'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'UPDATE ', p_next_table, ' AS nxt ',
        'JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id ',
        'JOIN ', p_backup_table, ' AS bak ON bak.id = cls.bak_id ',
        'SET nxt.`translatedText` = bak.`translatedText`, ',
        'nxt.status = bak.status, ',
        'nxt.`editCount` = bak.`editCount`, ',
        'nxt.`uptTime` = NOW() ',
        'WHERE cls.class = 3'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @new_after ',
        'FROM ', p_next_table, ' AS nxt ',
        'JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id ',
        'WHERE cls.class = 1 AND nxt.status = 1'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @changed_after ',
        'FROM ', p_next_table, ' AS nxt ',
        'JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id ',
        'WHERE cls.class = 2 AND nxt.status = 2'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @unchanged_after ',
        'FROM ', p_next_table, ' AS nxt ',
        'JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id ',
        'JOIN ', p_backup_table, ' AS bak ON bak.id = cls.bak_id ',
        'WHERE cls.class = 3 ',
        'AND (nxt.`translatedText` <=> bak.`translatedText`) ',
        'AND nxt.status = bak.status ',
        'AND nxt.`editCount` = bak.`editCount`'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    IF @new_after <> @new_cnt THEN
        SET msg = CONCAT('新增分类数量不一致: expected=', @new_cnt, ' actual=', @new_after);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    IF @changed_after <> @changed_cnt THEN
        SET msg = CONCAT('修改分类数量不一致: expected=', @changed_cnt, ' actual=', @changed_after);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    IF @unchanged_after <> @unchanged_cnt THEN
        SET msg = CONCAT('继承分类数量不一致: expected=', @unchanged_cnt, ' actual=', @unchanged_after);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    DROP TEMPORARY TABLE IF EXISTS tmp_step5_classify;

    SELECT @new_cnt AS new_cnt, @changed_cnt AS changed_cnt, @unchanged_cnt AS unchanged_cnt;
END //

CALL step5_compare_and_inherit(:'backup_table', :'next_table') //
DROP PROCEDURE step5_compare_and_inherit //

DELIMITER ;
