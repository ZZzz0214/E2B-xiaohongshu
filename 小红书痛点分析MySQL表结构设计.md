# 小红书痛点分析MySQL表结构设计

### **表关系图**
```
xiaohongshu_pain_analysis (主表)
├── xiaohongshu_pain_points (痛点详情)
├── xiaohongshu_solved_problems (解决方案)
├── xiaohongshu_user_needs (用户需求)
├── xiaohongshu_usage_scenarios (使用场景)
├── xiaohongshu_brand_mentions (品牌提及)
├── xiaohongshu_product_models (产品型号)
├── xiaohongshu_emotional_keywords (情感关键词)
├── xiaohongshu_post_tags (帖子标签)
├── xiaohongshu_post_classification (帖子分类) ← 🆕 新增
└── 通过 content_id 关联

xiaohongshu_summary_insights (汇总表)
├── xiaohongshu_high_frequency_pains (高频痛点)
├── xiaohongshu_scenario_pain_ranking (场痛点景排名)
├── xiaohongshu_brand_pain_correlation (品牌痛点关联)
├── xiaohongshu_urgent_needs (紧急需求)
├── xiaohongshu_market_opportunities (市场机会)
└── 通过 analysis_batch 关联
```

---

## 🗃️ **表结构详细设计**

### **1. 痛点分析主表 - xiaohongshu_pain_analysis**

**表功能**：存储每条内容（帖子/评论）的基本信息和核心分析结果，是整个痛点分析系统的核心表。

**设计说明**：
- 使用标准关系型设计，所有数组数据通过独立表存储
- 使用枚举类型标准化常用字段值
- 支持分析批次管理，便于对比不同时期的数据
- 通过外键关联实现数据完整性

```sql
-- 痛点分析主表 - 存储每条内容的基本信息和核心分析结果
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
```

### **2. 痛点详情表 - xiaohongshu_pain_points**

**表功能**：存储LLM识别出的具体痛点信息，支持痛点分类分析和严重程度统计。

**设计说明**：
- 每个痛点一条记录，便于按痛点维度进行统计分析
- 包含证据字段，保证分析结果的可追溯性
- 痛点分类枚举基于内衣行业特点设计

```sql
-- 痛点详情表 - 存储identified_pain_points数组数据
CREATE TABLE xiaohongshu_pain_points (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    pain_point TEXT NOT NULL COMMENT '具体痛点描述',
    category ENUM('舒适度', '支撑性', '设计', '尺寸', '功能', '服务') COMMENT '痛点分类',
    severity ENUM('严重', '中等', '轻微') COMMENT '严重程度',
    evidence TEXT COMMENT '支撑证据的原文片段',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_category (category),
    INDEX idx_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='痛点详情表';
```

### **3. 解决方案表 - xiaohongshu_solved_problems**

**表功能**：存储用户提到的已解决问题和解决方案，为产品改进和营销策略提供参考。

**设计说明**：
- 记录问题-解决方案-满意度的完整链路
- 为产品功能验证和改进方向提供数据支持

```sql
-- 解决方案表 - 存储solved_problems数组数据
CREATE TABLE xiaohongshu_solved_problems (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    problem TEXT NOT NULL COMMENT '已解决的问题描述',
    solution TEXT COMMENT '采用的解决方案',
    satisfaction ENUM('非常满意', '满意', '一般', '不满意', '非常不满意') COMMENT '解决方案满意度',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_satisfaction (satisfaction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='解决方案表';
```

### **4. 用户需求表 - xiaohongshu_user_needs**

**表功能**：存储识别出的用户需求，支持需求优先级分析和产品规划。

**设计说明**：
- 需求类型分为功能性、情感性、社交性三类
- 优先级字段便于需求管理和产品规划
- 为市场机会识别提供数据基础

```sql
-- 用户需求表 - 存储user_needs数组数据
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
    INDEX idx_need_type (need_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户需求表';
```

### **5. 使用场景表 - xiaohongshu_usage_scenarios**

**表功能**：存储产品使用场景信息，支持场景化产品设计和营销。

**设计说明**：
- 记录场景-频次-痛点强度的关联关系
- 为不同场景下的产品优化提供依据
- 支持场景化营销策略制定

```sql
-- 使用场景表 - 存储usage_scenarios数组数据
CREATE TABLE xiaohongshu_usage_scenarios (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    scenario VARCHAR(100) NOT NULL COMMENT '使用场景名称',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_scenario (scenario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='使用场景表';
```

### **6. 品牌提及表 - xiaohongshu_brand_mentions**

**表功能**：存储内容中提及的品牌信息，支持品牌分析和竞品对比。

**设计说明**：
- 每个品牌提及一条记录，便于品牌维度统计分析
- 支持品牌热度和情感关联分析

```sql
-- 品牌提及表 - 存储brand_mentions数组数据
CREATE TABLE xiaohongshu_brand_mentions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    brand_name VARCHAR(100) NOT NULL COMMENT '品牌名称',
    mention_order INT DEFAULT 1 COMMENT '提及顺序（在同一内容中的顺序）',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_brand_name (brand_name),
    INDEX idx_brand_content (brand_name, content_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='品牌提及表';
```

### **7. 产品型号表 - xiaohongshu_product_models**

**表功能**：存储内容中提及的具体产品型号信息，支持产品级别的详细分析。

**设计说明**：
- 记录具体的产品型号或系列名称
- 便于产品级别的痛点和需求分析

```sql
-- 产品型号表 - 存储product_models数组数据
CREATE TABLE xiaohongshu_product_models (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    product_model VARCHAR(100) NOT NULL COMMENT '产品型号或系列名称',
    mention_order INT DEFAULT 1 COMMENT '提及顺序（在同一内容中的顺序）',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_product_model (product_model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品型号表';
```

### **8. 情感关键词表 - xiaohongshu_emotional_keywords**

**表功能**：存储情感分析中识别出的关键词，支持情感词汇的统计和趋势分析。

**设计说明**：
- 每个情感关键词一条记录，便于词频统计
- 为情感分析和用户画像提供基础数据

```sql
-- 情感关键词表 - 存储emotional_keywords数组数据
CREATE TABLE xiaohongshu_emotional_keywords (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID',
    
    keyword VARCHAR(50) NOT NULL COMMENT '情感关键词',
    keyword_order INT DEFAULT 1 COMMENT '关键词顺序（按重要性排序）',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_keyword (keyword),
    INDEX idx_keyword_freq (keyword, content_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='情感关键词表';
```

### **9. 帖子标签表 - xiaohongshu_post_tags** 

**表功能**：存储小红书帖子的标签信息，仅适用于帖子类型内容，支持标签维度的数据分析。

**设计说明**：
- 仅针对帖子类型(content_type='post')的内容存储标签
- 每个标签一条记录，便于标签热度统计和趋势分析
- 支持标签与痛点、情感的关联分析

```sql
-- 帖子标签表 - 存储tags数组数据（仅帖子类型）
CREATE TABLE xiaohongshu_post_tags (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    content_id VARCHAR(50) NOT NULL COMMENT '关联内容ID（仅帖子）',
    
    tag_name VARCHAR(100) NOT NULL COMMENT '标签名称',
    tag_order INT DEFAULT 1 COMMENT '标签顺序（在同一帖子中的顺序）',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_content_id (content_id),
    INDEX idx_tag_name (tag_name),
    INDEX idx_tag_content (tag_name, content_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='帖子标签表';
```

### **10. 帖子分类表 - xiaohongshu_post_classification** 

**表功能**：存储小红书帖子的分类标注信息，支持内容类型识别、用户画像分析和内容汇总。

**设计说明**：
- 主要用于帖子类型内容的分类标注
- **核心必要字段**：作者ID、作者昵称、帖子标题、内容分类、分类判断理由
- 通过post_id关联到主表的content_id，支持数据关联查询
- 分类标准：测评 > 推荐 > 避雷 > 踩坑 > 问询互动 > 个人笔记（按优先级排序）
- **新增分析字段**：用户画像初步分析、内容初步汇总，支持深度内容理解

```sql
-- 帖子分类表 - 存储小红书帖子分类标注信息
CREATE TABLE xiaohongshu_post_classification (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    post_id VARCHAR(50) NOT NULL UNIQUE COMMENT '帖子ID，关联主表content_id',
    
    -- ========== 核心必要字段 ==========
    author_id VARCHAR(50) NOT NULL COMMENT '作者ID（必要字段）',
    author_name VARCHAR(100) NOT NULL COMMENT '作者昵称（必要字段）',
    title TEXT NOT NULL COMMENT '帖子标题（必要字段）',
    classification ENUM('测评', '推荐', '避雷', '踩坑', '问询互动', '个人笔记', 'INVALID') NOT NULL COMMENT '内容分类（必要字段）',
    reasoning TEXT NOT NULL COMMENT '分类判断理由（必要字段）',
    
    -- ========== 分析结果字段 ==========
    user_profile TEXT COMMENT '用户画像初步分析',
    content_summary TEXT COMMENT '内容初步汇总',
    content_quality_score DECIMAL(3,2) COMMENT '内容质量评分 0.00-1.00',
    
    -- ========== 系统管理字段 ==========
    analysis_batch VARCHAR(50) COMMENT '分析批次标识',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 索引优化
    INDEX idx_post_id (post_id),
    INDEX idx_author_id (author_id),
    INDEX idx_author_name (author_name),
    INDEX idx_classification (classification),
    INDEX idx_content_quality_score (content_quality_score),
    INDEX idx_analysis_batch (analysis_batch),
    INDEX idx_created_at (created_at),
    
    -- 外键约束（可选，根据实际情况决定是否启用）
    FOREIGN KEY (post_id) REFERENCES xiaohongshu_pain_analysis(content_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='帖子分类表';
```

### **11. 汇总洞察表 - xiaohongshu_summary_insights**

**表功能**：存储每个分析批次的基本统计信息，为决策提供高层次数据支持。

**设计说明**：
- 存储分析批次的基础统计指标
- 详细洞察数据通过独立的明细表存储
- 便于批次间对比分析

```sql
-- 汇总洞察表 - 存储summary_insights基础统计数据
CREATE TABLE xiaohongshu_summary_insights (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    analysis_batch VARCHAR(50) NOT NULL UNIQUE COMMENT '分析批次标识',
    
    -- 统计指标
    total_contents_analyzed INT COMMENT '分析内容总数',
    posts_count INT COMMENT '帖子数量',
    comments_count INT COMMENT '评论数量',
    positive_sentiment_count INT COMMENT '正面情感数量',
    negative_sentiment_count INT COMMENT '负面情感数量',
    neutral_sentiment_count INT COMMENT '中性情感数量',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 索引优化
    INDEX idx_analysis_batch (analysis_batch),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='汇总洞察表';
```

### **12. 高频痛点表 - xiaohongshu_high_frequency_pains**

**表功能**：存储分析批次中的高频痛点列表，支持痛点热度排名。

```sql
-- 高频痛点表 - 存储high_frequency_pain_points数组数据
CREATE TABLE xiaohongshu_high_frequency_pains (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    analysis_batch VARCHAR(50) NOT NULL COMMENT '分析批次标识',
    
    pain_point VARCHAR(200) NOT NULL COMMENT '痛点描述',
    frequency_rank INT COMMENT '频次排名',
    occurrence_count INT COMMENT '出现次数',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_analysis_batch (analysis_batch),
    INDEX idx_frequency_rank (frequency_rank),
    INDEX idx_occurrence_count (occurrence_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='高频痛点表';
```

### **13. 场景痛点排名表 - xiaohongshu_scenario_pain_ranking**

**表功能**：存储不同场景下的痛点排名，支持场景化分析。

```sql
-- 场景痛点排名表 - 存储scenario_pain_ranking数据
CREATE TABLE xiaohongshu_scenario_pain_ranking (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    analysis_batch VARCHAR(50) NOT NULL COMMENT '分析批次标识',
    
    scenario_name VARCHAR(100) NOT NULL COMMENT '场景名称',
    pain_point VARCHAR(200) NOT NULL COMMENT '痛点描述',
    ranking INT COMMENT '在该场景下的排名',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_analysis_batch (analysis_batch),
    INDEX idx_scenario_name (scenario_name),
    INDEX idx_ranking (ranking)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='场景痛点排名表';
```

### **14. 品牌痛点关联表 - xiaohongshu_brand_pain_correlation**

**表功能**：存储品牌与痛点的关联关系，支持品牌维度的痛点分析。

```sql
-- 品牌痛点关联表 - 存储brand_pain_correlation数据
CREATE TABLE xiaohongshu_brand_pain_correlation (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    analysis_batch VARCHAR(50) NOT NULL COMMENT '分析批次标识',
    
    brand_name VARCHAR(100) NOT NULL COMMENT '品牌名称',
    pain_point VARCHAR(200) NOT NULL COMMENT '关联的痛点',
    correlation_strength DECIMAL(3,2) COMMENT '关联强度 0.00-1.00',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_analysis_batch (analysis_batch),
    INDEX idx_brand_name (brand_name),
    INDEX idx_correlation_strength (correlation_strength)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='品牌痛点关联表';
```

### **15. 紧急需求表 - xiaohongshu_urgent_needs**

**表功能**：存储分析识别出的紧急用户需求，为产品规划提供依据。

```sql
-- 紧急需求表 - 存储urgent_needs数组数据
CREATE TABLE xiaohongshu_urgent_needs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    analysis_batch VARCHAR(50) NOT NULL COMMENT '分析批次标识',
    
    need_description VARCHAR(200) NOT NULL COMMENT '需求描述',
    urgency_level ENUM('极高', '高', '中', '低') COMMENT '紧急程度',
    priority_rank INT COMMENT '优先级排名',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_analysis_batch (analysis_batch),
    INDEX idx_urgency_level (urgency_level),
    INDEX idx_priority_rank (priority_rank)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='紧急需求表';
```

### **16. 市场机会表 - xiaohongshu_market_opportunities**

**表功能**：存储识别出的市场机会，为业务战略制定提供参考。

```sql
-- 市场机会表 - 存储market_opportunities数组数据
CREATE TABLE xiaohongshu_market_opportunities (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    analysis_batch VARCHAR(50) NOT NULL COMMENT '分析批次标识',
    
    opportunity_description VARCHAR(300) NOT NULL COMMENT '机会描述',
    opportunity_type ENUM('产品创新', '营销策略', '服务优化', '渠道拓展', '其他') COMMENT '机会类型',
    potential_impact ENUM('高', '中', '低') COMMENT '潜在影响力',
    priority_rank INT COMMENT '优先级排名',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    -- 索引优化
    INDEX idx_analysis_batch (analysis_batch),
    INDEX idx_opportunity_type (opportunity_type),
    INDEX idx_potential_impact (potential_impact),
    INDEX idx_priority_rank (priority_rank)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场机会表';
```

---



