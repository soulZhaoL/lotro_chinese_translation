-- Step5: 比对备份表与 next 表，分类并继承译文（MySQL）

DELIMITER //

DROP PROCEDURE IF EXISTS step5_compare_and_inherit //
CREATE PROCEDURE step5_compare_and_inherit(
    IN p_backup_table VARCHAR(255),
    IN p_next_table VARCHAR(255)
)
BEGIN
    DECLARE msg TEXT;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @backup_dup_key_cnt FROM (',
        'SELECT fid, `textId`, COUNT(*) c FROM ', p_backup_table, ' ',
        'GROUP BY fid, `textId` HAVING COUNT(*) > 1',
        ') t'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @backup_dup_key_cnt > 0 THEN
        SET msg = CONCAT('备份表存在重复 key(fid,textId)，数量=', @backup_dup_key_cnt);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @next_dup_key_cnt FROM (',
        'SELECT fid, `textId`, COUNT(*) c FROM ', p_next_table, ' ',
        'GROUP BY fid, `textId` HAVING COUNT(*) > 1',
        ') t'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @next_dup_key_cnt > 0 THEN
        SET msg = CONCAT('next表存在重复 key(fid,textId)，数量=', @next_dup_key_cnt);
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
        'ON nxt.fid = bak.fid AND nxt.`textId` = bak.`textId`'
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

    -- class=1（新增）和 class=2（修改）合并为一次 UPDATE，减少全表扫描次数
    SET @sql = CONCAT(
        'UPDATE ', p_next_table, ' AS nxt ',
        'JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id ',
        'SET nxt.status = CASE cls.class WHEN 1 THEN 1 WHEN 2 THEN 2 END, ',
        'nxt.`uptTime` = NOW() ',
        'WHERE cls.class IN (1, 2)'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    SET @new_changed_after = ROW_COUNT();
    DEALLOCATE PREPARE stmt;

    IF @new_changed_after <> @new_cnt + @changed_cnt THEN
        SET msg = CONCAT('新增+修改更新行数不一致: expected=', @new_cnt + @changed_cnt, ' actual=', @new_changed_after);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    -- class=3（原文不变）继承备份表译文；用 ROW_COUNT() 验证，避免对 TEXT 字段逐行比较
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
    SET @unchanged_after = ROW_COUNT();
    DEALLOCATE PREPARE stmt;

    IF @unchanged_after <> @unchanged_cnt THEN
        SET msg = CONCAT('继承更新行数不一致: expected=', @unchanged_cnt, ' actual=', @unchanged_after);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    DROP TEMPORARY TABLE IF EXISTS tmp_step5_classify;

    SELECT @new_cnt AS new_cnt, @changed_cnt AS changed_cnt, @unchanged_cnt AS unchanged_cnt;
END //

CALL step5_compare_and_inherit(:'backup_table', :'next_table') //
DROP PROCEDURE step5_compare_and_inherit //

DELIMITER ;
