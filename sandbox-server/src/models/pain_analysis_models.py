"""
小红书痛点分析数据模型
用于痛点分析JSON数据的验证和序列化
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum

# ==================== 枚举类型定义 ====================
class ContentType(str, Enum):
    """内容类型"""
    POST = "post"
    COMMENT = "comment"

class Sentiment(str, Enum):
    """情感类型"""
    POSITIVE = "正面"
    NEGATIVE = "负面"
    NEUTRAL = "中性"

class Severity(str, Enum):
    """严重程度"""
    SEVERE = "严重"
    MODERATE = "中等"
    MILD = "轻微"

class PainCategory(str, Enum):
    """痛点分类"""
    COMFORT = "舒适度"
    SUPPORT = "支撑性"
    DESIGN = "设计"
    SIZE = "尺寸"
    FUNCTION = "功能"
    SERVICE = "服务"

class Priority(str, Enum):
    """优先级"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

class NeedType(str, Enum):
    """需求类型"""
    FUNCTIONAL = "功能性"
    EMOTIONAL = "情感性"
    SOCIAL = "社交性"

class Satisfaction(str, Enum):
    """满意度"""
    VERY_SATISFIED = "非常满意"
    SATISFIED = "满意"
    AVERAGE = "一般"
    DISSATISFIED = "不满意"
    VERY_DISSATISFIED = "非常不满意"

class PurchaseIntent(str, Enum):
    """购买意向"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"
    NONE = "无"

class RecommendationLikelihood(str, Enum):
    """推荐可能性"""
    WILL_RECOMMEND = "会推荐"
    MIGHT_RECOMMEND = "可能推荐"
    WILL_NOT_RECOMMEND = "不会推荐"

# 竞品对比不使用枚举，按设计文档使用VARCHAR(100)
# 价格敏感度不使用枚举，按设计文档使用VARCHAR(50)

# ==================== 基础数据模型 ====================
class PainPoint(BaseModel):
    """痛点模型"""
    pain_point: str = Field(..., description="痛点描述")
    category: PainCategory = Field(..., description="痛点分类")
    severity: Severity = Field(..., description="严重程度")
    evidence: str = Field(..., description="支撑证据")

class SolvedProblem(BaseModel):
    """解决方案模型"""
    problem: str = Field(..., description="已解决的问题描述")
    solution: str = Field(..., description="采用的解决方案")
    satisfaction: Satisfaction = Field(..., description="解决方案满意度")

class UserNeed(BaseModel):
    """用户需求模型"""
    need: str = Field(..., description="用户需求描述")
    priority: Priority = Field(..., description="需求优先级")
    type: NeedType = Field(..., description="需求类型")

class UsageScenario(BaseModel):
    """使用场景模型"""
    scenario: str = Field(..., description="使用场景名称")
    
    # 接受但不验证的额外字段，存储时会被过滤
    class Config:
        extra = "ignore"  # 忽略额外字段，不报错

class EmotionalAnalysis(BaseModel):
    """情感分析模型"""
    overall_sentiment: Sentiment = Field(..., description="整体情感倾向")
    intensity_score: float = Field(..., ge=0.0, le=1.0, description="情感强度分数")
    emotional_keywords: List[str] = Field(..., description="情感关键词")
    user_satisfaction: Satisfaction = Field(..., description="用户满意度")

class CommercialInsights(BaseModel):
    """商业洞察模型"""
    purchase_intent: PurchaseIntent = Field(..., description="购买意向")
    recommendation_likelihood: RecommendationLikelihood = Field(..., description="推荐可能性")
    competitor_comparison: str = Field(..., description="是否涉及竞品对比")
    price_sensitivity: str = Field(..., description="价格敏感度评估")

class ContentAnalysis(BaseModel):
    """内容分析模型"""
    content_id: str = Field(..., description="内容唯一标识")
    content_type: ContentType = Field(..., description="内容类型")
    user_name: str = Field(..., description="发布用户昵称")
    content_snippet: Optional[str] = Field(None, description="内容片段")
    
    # 可选字段（仅帖子有）
    tags: Optional[List[str]] = Field(None, description="帖子标签")
    brand_mentions: Optional[List[str]] = Field(None, description="品牌提及")
    product_models: Optional[List[str]] = Field(None, description="产品型号")
    
    # 分析结果
    identified_pain_points: List[PainPoint] = Field(..., description="识别的痛点")
    solved_problems: List[SolvedProblem] = Field(..., description="已解决的问题")
    user_needs: List[UserNeed] = Field(..., description="用户需求")
    usage_scenarios: List[UsageScenario] = Field(..., description="使用场景")
    emotional_analysis: EmotionalAnalysis = Field(..., description="情感分析")
    commercial_insights: CommercialInsights = Field(..., description="商业洞察")

# ==================== 汇总洞察模型 ====================
class SummaryInsights(BaseModel):
    """汇总洞察模型"""
    high_frequency_pain_points: List[str] = Field(..., description="高频痛点")
    scenario_pain_ranking: Dict[str, List[str]] = Field(..., description="场景痛点排名")
    brand_pain_correlation: Dict[str, List[str]] = Field(..., description="品牌痛点关联")
    urgent_needs: List[str] = Field(..., description="紧急需求")
    market_opportunities: List[str] = Field(..., description="市场机会")

# ==================== 主要请求模型 ====================
class PainAnalysisRequest(BaseModel):
    """痛点分析请求模型"""
    pain_point_analysis: List[ContentAnalysis] = Field(..., description="痛点分析数据")
    summary_insights: Optional[SummaryInsights] = Field(None, description="汇总洞察")
    analysis_batch: Optional[str] = Field(None, description="分析批次标识")

# ==================== 响应模型 ====================
class PainAnalysisResponse(BaseModel):
    """痛点分析响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    analysis_batch: Optional[str] = Field(None, description="分析批次标识")
    storage_stats: Optional[Dict[str, Any]] = Field(None, description="存储统计")

# ==================== 统计和查询模型 ====================
class PainAnalysisStats(BaseModel):
    """痛点分析统计模型"""
    total_contents: int = Field(..., description="内容总数")
    posts_count: int = Field(..., description="帖子数量")
    comments_count: int = Field(..., description="评论数量")
    positive_sentiment_count: int = Field(..., description="正面情感数量")
    negative_sentiment_count: int = Field(..., description="负面情感数量")
    neutral_sentiment_count: int = Field(..., description="中性情感数量")
    total_pain_points: int = Field(..., description="总痛点数量")
    high_priority_needs: int = Field(..., description="高优先级需求数量")

class QueryPainAnalysisRequest(BaseModel):
    """查询痛点分析请求模型"""
    analysis_batch: Optional[str] = Field(None, description="分析批次标识")
    content_type: Optional[ContentType] = Field(None, description="内容类型筛选")
    sentiment: Optional[Sentiment] = Field(None, description="情感类型筛选")
    pain_category: Optional[PainCategory] = Field(None, description="痛点分类筛选")
    severity: Optional[Severity] = Field(None, description="严重程度筛选")
    limit: int = Field(default=50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(default=0, ge=0, description="偏移量")
