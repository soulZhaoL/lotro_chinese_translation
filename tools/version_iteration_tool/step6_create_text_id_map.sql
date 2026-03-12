-- Step6: 生成新老 ID 映射（MySQL）

DELIMITER //

DROP PROCEDURE IF EXISTS step6_create_text_id_map //
CREATE PROCEDURE step6_create_text_id_map(
    IN p_backup_table VARCHAR(255),
    IN p_next_table VARCHAR(255),
    IN p_map_table VARCHAR(255)
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

    SET @sql = CONCAT(
        'CREATE TABLE ', p_map_table, ' (',
        '`oldId` BIGINT NOT NULL, ',
        '`newId` BIGINT NOT NULL, ',
        'fid VARCHAR(64) NOT NULL, ',
        '`textId` BIGINT NOT NULL, ',
        'part INT NOT NULL, ',
        '`sourceTextHash` VARCHAR(64) NOT NULL, ',
        '`crtTime` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, ',
        'PRIMARY KEY (`oldId`), ',
        'UNIQUE KEY uq_map_new_id (`newId`), ',
        'UNIQUE KEY uq_map_text_key (fid, `textId`)',
        ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'INSERT INTO ', p_map_table, ' (`oldId`, `newId`, fid, `textId`, part, `sourceTextHash`) ',
        'SELECT bak.id AS `oldId`, nxt.id AS `newId`, nxt.fid, nxt.`textId`, nxt.part, nxt.`sourceTextHash` ',
        'FROM ', p_next_table, ' AS nxt ',
        'JOIN ', p_backup_table, ' AS bak ',
        'ON nxt.fid = bak.fid AND nxt.`textId` = bak.`textId` ',
        'WHERE nxt.`sourceTextHash` <=> bak.`sourceTextHash`'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT('SELECT COUNT(*) INTO @mapped_rows FROM ', p_map_table);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @expected_rows ',
        'FROM ', p_next_table, ' AS nxt ',
        'JOIN ', p_backup_table, ' AS bak ',
        'ON nxt.fid = bak.fid AND nxt.`textId` = bak.`textId` ',
        'WHERE nxt.`sourceTextHash` <=> bak.`sourceTextHash`'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    IF @mapped_rows <> @expected_rows THEN
        SET msg = CONCAT('映射行数不一致: expected=', @expected_rows, ' actual=', @mapped_rows);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    SELECT @mapped_rows AS mapped_rows;
END //

CALL step6_create_text_id_map(:'backup_table', :'next_table', :'map_table') //
DROP PROCEDURE step6_create_text_id_map //

DELIMITER ;
