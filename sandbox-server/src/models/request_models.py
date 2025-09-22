"""
API请求和响应的数据模型 - 简化版
使用Pydantic进行数据验证和序列化
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# ==================== 基础响应模型 ====================
class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool
    message: str
    data: Optional[Any] = None

# ==================== 浏览器操作模型 ====================
class BrowserOperation(BaseModel):
    """单个浏览器操作"""
    action: str = Field(..., description="操作类型", example="navigate")
    params: Dict[str, Any] = Field(default_factory=dict, description="操作参数")
    description: Optional[str] = Field(default=None, description="操作描述")

class BatchBrowserRequest(BaseModel):
    """批量浏览器操作请求 - 支持单操作和批量操作"""
    # 支持单操作格式
    action: Optional[str] = Field(default=None, description="单个操作类型")
    params: Optional[Dict[str, Any]] = Field(default=None, description="单个操作参数") 
    
    # 支持批量操作格式
    operations: Optional[List[BrowserOperation]] = Field(default=None, description="操作列表")
    
    # 沙盒管理
    persistent_id: Optional[str] = Field(default=None, description="沙盒持久化ID")
    auto_cleanup: Optional[bool] = Field(default=False, description="是否自动清理沙盒")
    
    # 用户来源追踪（用于用户个人信息提取）
    source_post_id: Optional[str] = Field(default=None, description="来源帖子ID")
    source_comment_id: Optional[str] = Field(default=None, description="来源评论ID")
    
    def get_operations_list(self) -> List[Dict[str, Any]]:
        """获取标准化的操作列表"""
        if self.operations:
            # 批量操作格式
            return [{"action": op.action, "params": op.params, "description": op.description} for op in self.operations]
        elif self.action:
            # 单操作格式
            return [{
                "action": self.action,
                "params": self.params or {},
                "description": f"执行{self.action}操作"
            }]
        else:
            return []

class NavigateRequest(BaseModel):
    """导航请求"""
    url: str = Field(..., description="目标URL", example="https://example.com")

class ClickRequest(BaseModel):
    """点击请求"""
    selector: str = Field(..., description="CSS选择器", example="button#submit")

class TypeRequest(BaseModel):
    """输入文本请求"""
    selector: str = Field(..., description="CSS选择器", example="input[name='username']")
    text: str = Field(..., description="要输入的文本", example="hello world")

class ScrollRequest(BaseModel):
    """滚动请求"""
    direction: str = Field(default="down", description="滚动方向: up/down", example="down")
    pixels: int = Field(default=500, description="滚动像素", example=500)

# ==================== 小红书专用模型 ====================
class XiaohongshuAutoScrollRequest(BaseModel):
    """小红书自动滚动请求"""
    max_scrolls: int = Field(default=10, description="最大滚动次数", example=10)
    delay_between_scrolls: float = Field(default=2.0, description="滚动间隔(秒)", example=2.0)

class XiaohongshuExtractAllPostsRequest(BaseModel):
    """小红书提取所有帖子请求"""
    limit: Optional[int] = Field(default=None, description="提取帖子数量限制", example=50)

class XiaohongshuClickPostRequest(BaseModel):
    """小红书点击帖子请求"""
    global_index: int = Field(..., description="帖子全局索引", example=0)

class XiaohongshuExpandCommentsRequest(BaseModel):
    """小红书展开评论请求"""
    max_attempts: int = Field(default=10, description="最大尝试次数", example=10)

class XiaohongshuExtractCommentsRequest(BaseModel):
    """小红书提取评论请求"""
    include_replies: bool = Field(default=True, description="是否包含回复", example=True)

class XiaohongshuExtractImagesRequest(BaseModel):
    """小红书提取图片请求"""
    high_resolution: bool = Field(default=False, description="是否提取高分辨率图片", example=False)

class XiaohongshuAnalyzePostRequest(BaseModel):
    """小红书完整分析帖子请求"""
    global_index: int = Field(..., description="帖子全局索引", example=0)
    include_comments: bool = Field(default=True, description="是否包含评论", example=True)
    include_images: bool = Field(default=True, description="是否包含图片", example=True)

# ==================== 环境信息模型 ====================
class EnvironmentInfo(BaseModel):
    """环境信息"""
    sandbox_id: str
    display: str
    vnc_available: bool
    timestamp: float

class VNCInfo(BaseModel):
    """VNC访问信息"""
    vnc_web_url: str
    vnc_direct_url: str
    display: str
    note: str

# ==================== 响应模型 ====================
class BrowserAutomationResponse(BaseModel):
    """浏览器自动化响应"""
    success: bool
    message: str
    total_operations: int
    successful_operations: int
    results: List[Dict[str, Any]]
    execution_time: float
    persistent_id: str
    e2b_sandbox_id: str
    vnc_access: VNCInfo
    total_execution_time: float
    sandbox_created: bool

# ==================== 数据库驱动的批量处理请求 ====================

class BatchProcessFromDatabaseRequest(BaseModel):
    """数据库驱动的批量处理请求"""
    query_condition: Optional[str] = Field(default="detail_extracted = FALSE", description="数据库查询条件")
    limit: int = Field(default=50, description="处理的帖子数量上限", ge=1, le=200)
    persistent_id: str = Field(..., description="现有沙盒的持久化ID（必须提供）")
    delay_between_posts: float = Field(default=2.0, description="处理帖子间的延迟(秒)", ge=0.5, le=10.0)
    base_url: Optional[str] = Field(default=None, description="关键词页面的基础URL（用于返回，可选）")
