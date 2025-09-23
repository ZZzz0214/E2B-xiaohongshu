-- 小红书痛点分析数据库表结构
-- 根据例子.md的JSON输出结构设计，完全适配

-- 1. 痛点分析主表
CREATE TABLE xiaohongshu_pain_analysis (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL UNIQUE COMMENT '内容唯一标识（帖子ID或评论ID）',
    content_type ENUM('post', 'comment') NOT NULL COMMENT '内容类型：post=帖子, comment=评论',
    user_name VARCHAR(100) COMMENT '发布用户昵称',
    content_snippet TEXT COMMENT '内容（帖子正文/评论内容）',
    
    -- 情感分析结果
    overall_sentiment ENUM('正面', '负面', '中性') COMMENT '整体情感倾向',
    intensity_score DECIMAL(3,2) COMMENT '情感强度分数 0.00-1.00',
    user_satisfaction ENUM('非常满意', '满意', '一般', '不满意', '非常不满意') COMMENT '用户满意度',
    
    -- 商业洞察
    purchase_intent ENUM('高', '中', '低', '无') COMMENT '购买意向',
    recommendation_likelihood ENUM('会推荐', '可能推荐', '不会推荐') COMMENT '推荐可能性',
    competitor_comparison VARCHAR(100) COMMENT '是否涉及竞品对比',
    price_sensitivity VARCHAR(50) COMMENT '价格敏感度评估',
    
    -- 系统字段
    analysis_batch VARCHAR(50) COMMENT '分析批次标识',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 索引优化
    INDEX idx_content_type (content_type),
    INDEX idx_user_name (user_name),
    INDEX idx_overall_sentiment (overall_sentiment),
    INDEX idx_purchase_intent (purchase_intent),
    INDEX idx_analysis_batch (analysis_batch),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='痛点分析主表';

-- 2. 痛点详情表
CREATE TABLE xiaohongshu_pain_points (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    pain_point TEXT NOT NULL COMMENT '具体痛点描述',
    category ENUM('舒适度', '支撑性', '设计', '尺寸', '功能', '服务', '其他') COMMENT '痛点分类',
    severity ENUM('严重', '中等', '轻微') COMMENT '严重程度',
    evidence TEXT COMMENT '支撑证据的原文片段',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_category (category),
    INDEX idx_severity (severity),
    
    -- 外键约束
    FOREIGN KEY (content_id) REFERENCES xiaohongshu_pain_analysis(content_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='痛点详情表';

-- 3. 解决方案表
CREATE TABLE xiaohongshu_solved_problems (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    problem TEXT NOT NULL COMMENT '已解决的问题描述',
    solution TEXT COMMENT '采用的解决方案',
    satisfaction ENUM('非常满意', '满意', '一般', '不满意', '非常不满意') COMMENT '解决方案满意度',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_satisfaction (satisfaction),
    
    -- 外键约束
    FOREIGN KEY (content_id) REFERENCES xiaohongshu_pain_analysis(content_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='解决方案表';

-- 4. 用户需求表
CREATE TABLE xiaohongshu_user_needs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    need TEXT NOT NULL COMMENT '用户需求描述',
    priority ENUM('高', '中', '低') COMMENT '需求优先级',
    need_type ENUM('功能性', '情感性', '社交性') COMMENT '需求类型',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_priority (priority),
    INDEX idx_need_type (need_type),
    
    -- 外键约束
    FOREIGN KEY (content_id) REFERENCES xiaohongshu_pain_analysis(content_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户需求表';

-- 5. 使用场景表 - 严格按照设计文档
CREATE TABLE xiaohongshu_usage_scenarios (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    scenario VARCHAR(100) NOT NULL COMMENT '使用场景名称',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_scenario (scenario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='使用场景表';

-- 6. 品牌提及表
CREATE TABLE xiaohongshu_brand_mentions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    brand_name VARCHAR(100) NOT NULL COMMENT '品牌名称',
    mention_order INT DEFAULT 1 COMMENT '提及顺序（在同一内容中的顺序）',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_brand_name (brand_name),
    INDEX idx_brand_content (brand_name, content_id),
    
    -- 外键约束
    FOREIGN KEY (content_id) REFERENCES xiaohongshu_pain_analysis(content_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='品牌提及表';

-- 7. 产品型号表
CREATE TABLE xiaohongshu_product_models (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    product_model VARCHAR(100) NOT NULL COMMENT '产品型号或系列名称',
    mention_order INT DEFAULT 1 COMMENT '提及顺序（在同一内容中的顺序）',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_product_model (product_model),
    
    -- 外键约束
    FOREIGN KEY (content_id) REFERENCES xiaohongshu_pain_analysis(content_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品型号表';

-- 8. 情感关键词表
CREATE TABLE xiaohongshu_emotional_keywords (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    keyword VARCHAR(50) NOT NULL COMMENT '情感关键词',
    keyword_order INT DEFAULT 1 COMMENT '关键词顺序（按重要性排序）',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_keyword (keyword),
    INDEX idx_keyword_freq (keyword, content_id),
    
    -- 外键约束
    FOREIGN KEY (content_id) REFERENCES xiaohongshu_pain_analysis(content_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='情感关键词表';

-- 9. 帖子标签表
CREATE TABLE xiaohongshu_post_tags (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID（仅帖子）',
    
    tag_name VARCHAR(100) NOT NULL COMMENT '标签名称',
    tag_order INT DEFAULT 1 COMMENT '标签顺序（在同一帖子中的顺序）',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_tag_name (tag_name),
    INDEX idx_tag_content (tag_name, content_id),
    
    -- 外键约束
    FOREIGN KEY (content_id) REFERENCES xiaohongshu_pain_analysis(content_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='帖子标签表';

-- 如果表已经存在，可以使用以下ALTER语句添加字段
-- ALTER TABLE xiaohongshu_usage_scenarios 
-- ADD COLUMN frequency VARCHAR(50) COMMENT '使用频次' AFTER scenario,
-- ADD COLUMN pain_intensity VARCHAR(50) COMMENT '痛点强度' AFTER frequency,
-- ADD INDEX idx_frequency (frequency),
-- ADD INDEX idx_pain_intensity (pain_intensity);

-- 验证表结构的查询语句
-- SELECT table_name, column_name, data_type, is_nullable, column_default, column_comment 
-- FROM information_schema.columns 
-- WHERE table_schema = 'e2b_server_data' 
-- AND table_name LIKE 'xiaohongshu_%'
-- ORDER BY table_name, ordinal_position;
