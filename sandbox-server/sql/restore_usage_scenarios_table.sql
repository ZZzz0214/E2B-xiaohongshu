-- 恢复 xiaohongshu_usage_scenarios 表到原始设计
-- 移除之前添加的 frequency 和 pain_intensity 字段
-- 说明：保持表结构简洁，只存储核心的 scenario 字段

-- 检查表是否存在
SELECT 'Checking if table exists...' as status;
SELECT COUNT(*) as table_exists 
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
AND table_name = 'xiaohongshu_usage_scenarios';

-- 检查当前表结构
SELECT 'Current table structure:' as status;
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM information_schema.columns 
WHERE table_schema = DATABASE() 
AND table_name = 'xiaohongshu_usage_scenarios'
ORDER BY ORDINAL_POSITION;

-- 开始恢复表结构
SELECT 'Starting table restoration...' as status;

-- 如果存在额外字段，先删除索引
DROP INDEX IF EXISTS idx_frequency ON xiaohongshu_usage_scenarios;
DROP INDEX IF EXISTS idx_pain_intensity ON xiaohongshu_usage_scenarios;

-- 删除额外字段（如果存在）
ALTER TABLE xiaohongshu_usage_scenarios 
DROP COLUMN IF EXISTS frequency;

ALTER TABLE xiaohongshu_usage_scenarios 
DROP COLUMN IF EXISTS pain_intensity;

-- 验证恢复结果
SELECT 'Restoration completed. Verifying results...' as status;
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM information_schema.columns 
WHERE table_schema = DATABASE() 
AND table_name = 'xiaohongshu_usage_scenarios'
ORDER BY ORDINAL_POSITION;

-- 显示当前索引
SELECT 'Current indexes:' as status;
SHOW INDEX FROM xiaohongshu_usage_scenarios;

SELECT '✅ Table restoration completed successfully!' as final_status;
SELECT '📝 Note: API will still accept full JSON but only store scenario field' as note;
