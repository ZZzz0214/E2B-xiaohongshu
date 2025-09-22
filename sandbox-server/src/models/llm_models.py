"""
LLM分析相关的数据模型
包含帖子分类、评论分析、客户洞察等大语言模型处理的数据结构
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


# ==================== 帖子分类模型 ====================

class PostClassificationItem(BaseModel):
    """单个帖子分类结果"""
    post_id: str = Field(..., description="帖子ID")
    author_id: Optional[str] = Field(None, description="作者ID")
    author_name: Optional[str] = Field(None, description="作者名称")
    title: Optional[str] = Field(None, description="帖子标题")
    classification: str = Field(..., description="分类结果：PROMOTIONAL/USER_GENERATED/INVALID")
    confidence_score: float = Field(..., description="置信度 0.0-1.0", ge=0.0, le=1.0)
    reasoning: Optional[str] = Field(None, description="分类理由")
    commercial_value: str = Field(..., description="商业价值：HIGH/MEDIUM/LOW/NONE")
    need_ai_analysis: bool = Field(True, description="是否需要进一步AI分析")


class PostClassificationRequest(BaseModel):
    """LLM帖子分类请求包装"""
    post_classification: List[PostClassificationItem] = Field(..., description="帖子分类结果数组")


# ==================== 评论分析模型 ====================

class KeyFeatures(BaseModel):
    """关键特征信息"""
    product_category: Optional[str] = Field(None, description="产品类别")
    functional_needs: Optional[str] = Field(None, description="功能需求")
    user_profile: Optional[str] = Field(None, description="用户画像")
    size_info: Optional[str] = Field(None, description="尺寸信息")


class CommentAnalysisItem(BaseModel):
    """单个评论分析结果"""
    comment_id: str = Field(..., description="评论ID")
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    content: str = Field(..., description="评论内容")
    is_valid: bool = Field(True, description="评论是否有效")
    intent_type: str = Field(..., description="意向类型：求助/咨询/购买/推荐/吐槽/分享/无意向")
    intent_level: str = Field(..., description="意向等级：高/中/低")
    sentiment: str = Field(..., description="情感：积极/消极/中性")
    confidence: float = Field(..., description="分析置信度", ge=0.0, le=1.0)
    key_features: KeyFeatures = Field(..., description="关键特征信息")
    business_value: str = Field(..., description="商业价值：HIGH/MEDIUM/LOW/NONE")
    follow_up_action: Optional[str] = Field(None, description="后续行动建议")


class CommentAnalysisRequest(BaseModel):
    """LLM评论分析请求包装"""
    comment_analysis: List[CommentAnalysisItem] = Field(..., description="评论分析结果数组")


# ==================== 客户洞察模型 ====================

class CustomerTag(BaseModel):
    """客户标签"""
    tag_name: str = Field(..., description="标签名称")
    tag_category: str = Field(..., description="标签分类：身份/需求/行为/商业")
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    source_content: str = Field(..., description="支撑该标签的关键证据")


class CustomerInsightsItem(BaseModel):
    """客户洞察分析结果"""
    user_id: str = Field(..., description="用户ID")
    latest_intent_level: str = Field(..., description="最新意向等级：HIGH/MEDIUM/LOW/NONE")
    latest_intent_type: str = Field(..., description="最新意向类型")
    customer_status: str = Field(..., description="客户状态描述")
    tags_overview: str = Field(..., description="标签概览")
    primary_tags: List[CustomerTag] = Field(default_factory=list, description="主要标签列表")
    key_insights: List[str] = Field(default_factory=list, description="关键洞察")
    recommendation: Dict[str, str] = Field(default_factory=dict, description="推荐行动")


# ==================== 数据转换工具函数 ====================

def convert_customer_insight_to_db_format(insight: CustomerInsightsItem) -> Dict[str, Any]:
    """将CustomerInsightsItem转换为数据库格式"""
    return {
        'latest_intent_level': insight.latest_intent_level,
        'latest_intent_type': insight.latest_intent_type,
        'customer_status': insight.customer_status,
        'tags_overview': insight.tags_overview,
        'primary_tags': [
            {
                'tag_name': tag.tag_name,
                'tag_category': tag.tag_category,
                'confidence': tag.confidence,
                'source_content': tag.source_content
            }
            for tag in insight.primary_tags
        ]
    }
