"""
Unified Automation Tools Package - 极简版本
只导出实际使用的组件
"""

# 尝试相对导入，如果失败则使用绝对导入
try:
    from .browser_service import BrowserService, BrowserActionRequest, BrowserActionResult, browser_service
    from .browser_utils import BrowserUtils, batch_browser_operations
    from .xiaohongshu_analyzer import XiaohongshuAnalyzer
    from .api_models import (
        BrowserOperationResponse, NavigateRequest,
        XiaohongshuAutoScrollRequest, XiaohongshuClickPostRequest,
        XiaohongshuExpandCommentsRequest, XiaohongshuExtractCommentsRequest,
        XiaohongshuAnalyzePostRequest, XiaohongshuExtractAllPostsRequest,
        XiaohongshuReplyCommentRequest, XiaohongshuClickAuthorAvatarRequest,
        XiaohongshuExtractUserProfileRequest, XiaohongshuClosePageRequest
    )
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from browser_service import BrowserService, BrowserActionRequest, BrowserActionResult, browser_service
    from browser_utils import BrowserUtils, batch_browser_operations
    from xiaohongshu_analyzer import XiaohongshuAnalyzer
    from api_models import (
        BrowserOperationResponse, NavigateRequest,
        XiaohongshuAutoScrollRequest, XiaohongshuClickPostRequest,
        XiaohongshuExpandCommentsRequest, XiaohongshuExtractCommentsRequest,
        XiaohongshuAnalyzePostRequest, XiaohongshuExtractAllPostsRequest,
        XiaohongshuReplyCommentRequest, XiaohongshuClickAuthorAvatarRequest,
        XiaohongshuExtractUserProfileRequest, XiaohongshuClosePageRequest
    )

__all__ = [
    'BrowserService',
    'BrowserActionRequest', 
    'BrowserActionResult',
    'browser_service',
    'BrowserUtils',
    'batch_browser_operations',
    'XiaohongshuAnalyzer',
    'BrowserOperationResponse',
    'NavigateRequest',
    'XiaohongshuAutoScrollRequest',
    'XiaohongshuClickPostRequest',
    'XiaohongshuExpandCommentsRequest',
    'XiaohongshuExtractCommentsRequest',
    'XiaohongshuAnalyzePostRequest',
    'XiaohongshuExtractAllPostsRequest',
    'XiaohongshuReplyCommentRequest',
    'XiaohongshuClickAuthorAvatarRequest',
    'XiaohongshuExtractUserProfileRequest',
    'XiaohongshuClosePageRequest'
]

__version__ = "2.0.0" 