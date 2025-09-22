#!/usr/bin/env python3
"""
API数据模型 - 极简版本
只保留守护进程实际使用的数据模型
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel

# ==================== 通用响应模型 ====================

class BrowserOperationResponse(BaseModel):
    """通用浏览器操作响应模型"""
    success: bool
    message: str = ""
    data: Dict[str, Any] = {}
    error: str = ""

# ==================== 基础请求模型 ====================

class NavigateRequest(BaseModel):
    """页面导航请求模型"""
    url: str

# ==================== 小红书专用请求模型 ====================

class XiaohongshuAutoScrollRequest(BaseModel):
    """小红书自动滚动请求"""
    max_scrolls: int = 10
    delay_between_scrolls: float = 2.0

class XiaohongshuClickPostRequest(BaseModel):
    """小红书点击帖子请求"""
    title: str

class XiaohongshuExpandCommentsRequest(BaseModel):
    """小红书展开评论请求"""
    max_attempts: int = 10

class XiaohongshuExtractCommentsRequest(BaseModel):
    """小红书提取评论请求"""
    include_replies: bool = True

class XiaohongshuAnalyzePostRequest(BaseModel):
    """小红书完整帖子分析请求"""
    global_index: int
    include_images: bool = True
    include_comments: bool = True

class XiaohongshuExtractAllPostsRequest(BaseModel):
    """小红书提取所有帖子请求"""
    limit: Optional[int] = None

class XiaohongshuReplyCommentRequest(BaseModel):
    """小红书回复评论请求"""
    target_user_id: str
    target_username: str  
    target_content: str
    reply_content: str

class XiaohongshuClickAuthorAvatarRequest(BaseModel):
    """小红书点击作者头像并获取用户信息请求"""
    userid: str
    username: str

class XiaohongshuExtractUserProfileRequest(BaseModel):
    """小红书提取用户个人主页信息请求"""
    pass  # 无需参数，直接在当前用户主页执行

class XiaohongshuClosePageRequest(BaseModel):
    """小红书关闭页面请求"""
    pass  # 无需参数，直接关闭当前页面 