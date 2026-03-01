-- Step7: 迁移 text_changes.textId（MySQL）

DELIMITER //

DROP PROCEDURE IF EXISTS step7_migrate_text_changes //
CREATE PROCEDURE step7_migrate_text_changes(
    IN p_map_table VARCHAR(255),
    IN p_changes_table VARCHAR(255)
)
BEGIN
    DECLARE msg TEXT;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @map_dup_old_id_cnt FROM (',
        'SELECT `oldId`, COUNT(*) c FROM ', p_map_table, ' GROUP BY `oldId` HAVING COUNT(*) > 1',
        ') t'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @map_dup_old_id_cnt > 0 THEN
        SET msg = CONCAT('映射表存在重复 oldId，数量=', @map_dup_old_id_cnt);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @map_dup_new_id_cnt FROM (',
        'SELECT `newId`, COUNT(*) c FROM ', p_map_table, ' GROUP BY `newId` HAVING COUNT(*) > 1',
        ') t'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @map_dup_new_id_cnt > 0 THEN
        SET msg = CONCAT('映射表存在重复 newId，数量=', @map_dup_new_id_cnt);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    SET @sql = CONCAT('SELECT COUNT(*) INTO @map_row_cnt FROM ', p_map_table);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    IF @map_row_cnt = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '映射表为空，停止迁移以避免误删';
    END IF;

    SET @sql = CONCAT('SELECT COUNT(*) INTO @total_before FROM ', p_changes_table);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @matched_old_before ',
        'FROM ', p_changes_table, ' AS c ',
        'JOIN ', p_map_table, ' AS m ON c.`textId` = m.`oldId`'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'SELECT COUNT(*) INTO @expected_remaining ',
        'FROM ', p_changes_table, ' AS c ',
        'WHERE EXISTS (SELECT 1 FROM ', p_map_table, ' AS m WHERE c.`textId` = m.`oldId`) ',
        'OR EXISTS (SELECT 1 FROM ', p_map_table, ' AS m WHERE c.`textId` = m.`newId`)'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT(
        'UPDATE ', p_changes_table, ' AS c ',
        'JOIN ', p_map_table, ' AS m ON c.`textId` = m.`oldId` ',
        'SET c.`textId` = m.`newId`'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    SET @updated_rows = ROW_COUNT();

    SET @sql = CONCAT(
        'DELETE c FROM ', p_changes_table, ' AS c ',
        'LEFT JOIN ', p_map_table, ' AS m ON c.`textId` = m.`newId` ',
        'WHERE m.`newId` IS NULL'
    );
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    SET @deleted_rows = ROW_COUNT();

    SET @sql = CONCAT('SELECT COUNT(*) INTO @remaining_rows FROM ', p_changes_table);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    IF @updated_rows <> @matched_old_before THEN
        SET msg = CONCAT('迁移更新行数不一致: expected=', @matched_old_before, ' actual=', @updated_rows);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    IF @remaining_rows <> @expected_remaining THEN
        SET msg = CONCAT('迁移后保留行数不一致: expected=', @expected_remaining, ' actual=', @remaining_rows);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    IF @deleted_rows <> (@total_before - @expected_remaining) THEN
        SET msg = CONCAT('清理删除行数不一致: expected=', (@total_before - @expected_remaining), ' actual=', @deleted_rows);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;

    SELECT @updated_rows AS updated_rows, @deleted_rows AS deleted_rows, @remaining_rows AS remaining_rows;
END //

CALL step7_migrate_text_changes(:'map_table', :'changes_table') //
DROP PROCEDURE step7_migrate_text_changes //

DELIMITER ;
