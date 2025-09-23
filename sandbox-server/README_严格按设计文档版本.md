# 小红书痛点分析系统 - 严格按设计文档版本

## 📋 重要说明

本系统**严格按照**《小红书痛点分析MySQL表结构设计.md》中定义的表结构实现，确保与设计文档完全一致。

## ⚠️ 数据兼容性说明

### 已知兼容性问题

1. **使用场景表字段不匹配**：
   - **设计文档**：`xiaohongshu_usage_scenarios` 表只有 `scenario` 字段
   - **例子.md**：包含 `frequency` 和 `pain_intensity` 字段
   - **处理方式**：系统将忽略额外字段，只存储 `scenario`

2. **价格敏感度字段类型**：
   - **设计文档**：`price_sensitivity VARCHAR(50)`
   - **实现**：支持任意字符串值，不限制枚举

## 🗃️ 严格实现的9个表结构

### 1. `xiaohongshu_pain_analysis` (主表)
```sql
CREATE TABLE xiaohongshu_pain_analysis (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL UNIQUE,
    content_type ENUM('post', 'comment') NOT NULL,
    user_name VARCHAR(100),
    content_snippet TEXT,
    overall_sentiment ENUM('正面', '负面', '中性'),
    intensity_score DECIMAL(3,2),
    user_satisfaction ENUM('非常满意', '满意', '一般', '不满意', '非常不满意'),
    purchase_intent ENUM('高', '中', '低', '无'),
    recommendation_likelihood ENUM('会推荐', '可能推荐', '不会推荐'),
    competitor_comparison ENUM('有', '无'),
    price_sensitivity VARCHAR(50),  -- 按设计文档，非枚举类型
    analysis_batch VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 2. `xiaohongshu_pain_points`
```sql
CREATE TABLE xiaohongshu_pain_points (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL,
    pain_point TEXT NOT NULL,
    category ENUM('舒适度', '支撑性', '设计', '尺寸', '功能', '服务'),
    severity ENUM('严重', '中等', '轻微'),
    evidence TEXT
);
```

### 3. `xiaohongshu_solved_problems`
```sql
CREATE TABLE xiaohongshu_solved_problems (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL,
    problem TEXT NOT NULL,
    solution TEXT,
    satisfaction ENUM('非常满意', '满意', '一般', '不满意', '非常不满意')
);
```

### 4. `xiaohongshu_user_needs`
```sql
CREATE TABLE xiaohongshu_user_needs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL,
    need TEXT NOT NULL,
    priority ENUM('高', '中', '低'),
    need_type ENUM('功能性', '情感性', '社交性')
);
```

### 5. `xiaohongshu_usage_scenarios` ⚠️
```sql
CREATE TABLE xiaohongshu_usage_scenarios (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL,
    scenario VARCHAR(100) NOT NULL  -- 注意：只有scenario字段
);
```

### 6. `xiaohongshu_brand_mentions`
```sql
CREATE TABLE xiaohongshu_brand_mentions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL,
    brand_name VARCHAR(100) NOT NULL,
    mention_order INT DEFAULT 1
);
```

### 7. `xiaohongshu_product_models`
```sql
CREATE TABLE xiaohongshu_product_models (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL,
    product_model VARCHAR(100) NOT NULL,
    mention_order INT DEFAULT 1
);
```

### 8. `xiaohongshu_emotional_keywords`
```sql
CREATE TABLE xiaohongshu_emotional_keywords (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL,
    keyword VARCHAR(50) NOT NULL,
    keyword_order INT DEFAULT 1
);
```

### 9. `xiaohongshu_post_tags`
```sql
CREATE TABLE xiaohongshu_post_tags (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content_id VARCHAR(50) NOT NULL,
    tag_name VARCHAR(100) NOT NULL,
    tag_order INT DEFAULT 1
);
```

## 🚀 API端点

### 存储数据
```http
POST /api/pain-analysis/store
```

**请求示例**：
```json
{
  "pain_point_analysis": [
    {
      "content_id": "67d668d7000000001d01a077",
      "content_type": "post",
      "user_name": "可爱小鱼鱼.",
      "usage_scenarios": [
        {
          "scenario": "日常穿着"
          // 注意：frequency 和 pain_intensity 字段会被忽略
        }
      ],
      // ... 其他字段
    }
  ]
}
```

### 其他端点
- `GET /api/pain-analysis/stats` - 获取统计信息
- `GET /api/pain-analysis/query` - 查询数据
- `GET /api/pain-analysis/batches` - 获取批次列表
- `GET /api/pain-analysis/content/{content_id}` - 获取内容详情
- `GET /api/pain-analysis/health` - 健康检查

## 📁 文件结构

```
sandbox-server/
├── src/
│   ├── models/pain_analysis_models.py          # 严格按设计文档的数据模型
│   ├── xiaohongshuDataStorage/pain_analysis_repository.py  # 数据库操作
│   ├── api/pain_analysis_routes.py             # API路由
│   └── app.py                                  # 主应用
├── sql/pain_analysis_tables.sql                # 严格按设计文档的建表语句
├── examples/pain_analysis_api_example.py       # 修正后的API示例
└── docs/pain_analysis_usage.md                 # 使用说明
```

## 🔧 使用步骤

### 1. 创建数据库表
```bash
# 执行建表SQL
mysql -u root -p e2b_server_data < sandbox-server/sql/pain_analysis_tables.sql
```

### 2. 启动服务
```bash
cd sandbox-server/src
python app.py
```

### 3. 验证服务
```bash
curl http://localhost:8000/api/pain-analysis/health
```

### 4. 测试存储数据
```bash
python sandbox-server/examples/pain_analysis_api_example.py
```

## ✅ 设计文档一致性检查

- [x] **表名称**：严格按照设计文档的9个表
- [x] **字段定义**：所有字段类型、长度、约束完全一致
- [x] **枚举值**：严格按照设计文档定义
- [x] **索引**：包含设计文档中的所有索引
- [x] **注释**：保持与设计文档一致

## ⚠️ 注意事项

1. **数据清洗**：使用此系统前，需要确保输入的JSON数据格式与表结构兼容
2. **字段忽略**：不存在的字段将被自动忽略，不会报错
3. **枚举验证**：严格验证枚举字段的值，不匹配会报错
4. **外键关系**：暂未实现外键约束，但代码中保证数据一致性

## 🔍 与例子.md的差异处理

| 字段路径 | 例子.md | 设计文档 | 处理方式 |
|---------|---------|----------|----------|
| `usage_scenarios.frequency` | 存在 | 不存在 | 忽略 |
| `usage_scenarios.pain_intensity` | 存在 | 不存在 | 忽略 |
| `price_sensitivity` | 枚举值 | VARCHAR(50) | 接受任意字符串 |

## 🎯 总结

本实现严格遵循设计文档，确保了：
- 数据库结构与设计文档100%一致
- API接口完整可用
- 错误处理和日志完善
- 代码结构清晰，便于维护

这个版本是设计文档的忠实实现，适用于严格按照既定设计规范执行的项目场景。
