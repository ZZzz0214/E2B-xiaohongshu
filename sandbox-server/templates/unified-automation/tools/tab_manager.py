"""
多标签页管理器
解决小红书等网站的多标签页上下文切换问题
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from playwright.async_api import Page, BrowserContext
from enum import Enum

logger = logging.getLogger(__name__)

class TabType(Enum):
    """标签页类型"""
    MAIN = "main"                    # 主页面（首页、搜索页等）
    POST_DETAIL = "post_detail"      # 帖子详情页
    USER_PROFILE = "user_profile"    # 用户个人资料页
    OTHER = "other"                  # 其他类型页面

@dataclass
class TabInfo:
    """标签页信息"""
    page: Page
    tab_id: str
    tab_type: TabType
    url: str
    title: str
    created_time: float
    last_active_time: float
    is_active: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class TabManager:
    """动态标签页管理器"""
    
    def __init__(self, browser_context: BrowserContext):
        self.context = browser_context
        self.tabs: Dict[str, TabInfo] = {}
        self.active_tab_id: Optional[str] = None
        self.logger = logging.getLogger("tab_manager")
        
        # 标签页类型识别规则
        self.type_patterns = {
            TabType.MAIN: [
                r"xiaohongshu\.com/?$",
                r"xiaohongshu\.com/explore",
                r"xiaohongshu\.com/search"
            ],
            TabType.POST_DETAIL: [
                r"xiaohongshu\.com/discovery/item/",
                r"xiaohongshu\.com/explore/\w+"
            ],
            TabType.USER_PROFILE: [
                r"xiaohongshu\.com/user/profile/",
                r"xiaohongshu\.com/@\w+"
            ]
        }
    
    async def register_page(self, page: Page, tab_type: TabType = TabType.OTHER) -> str:
        """注册一个新的标签页"""
        tab_id = f"tab_{int(time.time() * 1000)}"
        
        try:
            url = page.url
            title = await page.title()
        except Exception as e:
            self.logger.warning(f"获取页面信息失败: {e}")
            url = "unknown"
            title = "unknown"
        
        # 自动检测标签页类型
        detected_type = self._detect_tab_type(url)
        if detected_type != TabType.OTHER:
            tab_type = detected_type
        
        tab_info = TabInfo(
            page=page,
            tab_id=tab_id,
            tab_type=tab_type,
            url=url,
            title=title,
            created_time=time.time(),
            last_active_time=time.time()
        )
        
        self.tabs[tab_id] = tab_info
        
        # 设置页面事件监听
        await self._setup_page_listeners(page, tab_id)
        
        self.logger.info(f"注册新标签页: {tab_id} ({tab_type.value}) - {title}")
        return tab_id
    
    async def discover_new_tabs(self) -> List[str]:
        """发现新打开的标签页"""
        current_pages = self.context.pages
        existing_pages = {tab.page for tab in self.tabs.values()}
        
        new_tabs = []
        for page in current_pages:
            if page not in existing_pages:
                tab_id = await self.register_page(page)
                new_tabs.append(tab_id)
        
        if new_tabs:
            self.logger.info(f"发现 {len(new_tabs)} 个新标签页: {new_tabs}")
        
        return new_tabs
    
    async def switch_to_tab(self, tab_id: str) -> bool:
        """切换到指定标签页"""
        if tab_id not in self.tabs:
            self.logger.error(f"标签页不存在: {tab_id}")
            return False
        
        tab_info = self.tabs[tab_id]
        
        try:
            # 将目标页面置于前台
            await tab_info.page.bring_to_front()
            
            # 更新活跃状态
            for tid, tab in self.tabs.items():
                tab.is_active = (tid == tab_id)
            
            tab_info.last_active_time = time.time()
            self.active_tab_id = tab_id
            
            self.logger.info(f"切换到标签页: {tab_id} ({tab_info.tab_type.value}) - {tab_info.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"切换标签页失败: {e}")
            return False
    
    async def get_active_page(self) -> Optional[Page]:
        """获取当前活跃的页面"""
        if not self.active_tab_id or self.active_tab_id not in self.tabs:
            # 尝试发现新标签页
            await self.discover_new_tabs()
            
            # 如果还是没有活跃标签页，使用最新的一个
            if not self.active_tab_id and self.tabs:
                latest_tab = max(self.tabs.values(), key=lambda t: t.created_time)
                await self.switch_to_tab(latest_tab.tab_id)
        
        if self.active_tab_id and self.active_tab_id in self.tabs:
            return self.tabs[self.active_tab_id].page
        
        return None
    
    async def find_tab_by_type(self, tab_type: TabType) -> Optional[str]:
        """根据类型查找标签页"""
        matching_tabs = [
            tab_id for tab_id, tab in self.tabs.items() 
            if tab.tab_type == tab_type
        ]
        
        if matching_tabs:
            # 返回最新的匹配标签页
            latest_tab_id = max(matching_tabs, key=lambda tid: self.tabs[tid].last_active_time)
            return latest_tab_id
        
        return None
    
    async def find_tab_by_url_pattern(self, pattern: str) -> Optional[str]:
        """根据URL模式查找标签页"""
        import re
        for tab_id, tab in self.tabs.items():
            if re.search(pattern, tab.url):
                return tab_id
        return None
    
    async def close_tab(self, tab_id: str) -> bool:
        """关闭指定标签页"""
        if tab_id not in self.tabs:
            return False
        
        tab_info = self.tabs[tab_id]
        
        try:
            await tab_info.page.close()
            del self.tabs[tab_id]
            
            # 如果关闭的是活跃标签页，智能切换到其他标签页
            if self.active_tab_id == tab_id:
                self.active_tab_id = None
                if self.tabs:
                    # 智能选择下一个标签页：优先选择主页面，其次是帖子详情页
                    next_tab = self._select_next_tab_after_close(tab_info.tab_type)
                    if next_tab:
                        await self.switch_to_tab(next_tab.tab_id)
                    else:
                        # 回退到最近使用的标签页
                        latest_tab = max(self.tabs.values(), key=lambda t: t.last_active_time)
                        await self.switch_to_tab(latest_tab.tab_id)
            
            self.logger.info(f"关闭标签页: {tab_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"关闭标签页失败: {e}")
            return False
    
    async def cleanup_tabs(self) -> int:
        """清理已关闭的标签页"""
        closed_tabs = []
        
        for tab_id, tab_info in list(self.tabs.items()):
            try:
                # 检查页面是否仍然存在
                await tab_info.page.title()
            except Exception:
                # 页面已关闭
                closed_tabs.append(tab_id)
                del self.tabs[tab_id]
        
        if closed_tabs:
            self.logger.info(f"清理了 {len(closed_tabs)} 个已关闭的标签页")
            
            # 重新设置活跃标签页
            if self.active_tab_id in closed_tabs:
                self.active_tab_id = None
                if self.tabs:
                    latest_tab = max(self.tabs.values(), key=lambda t: t.last_active_time)
                    await self.switch_to_tab(latest_tab.tab_id)
        
        return len(closed_tabs)
    
    def _detect_tab_type(self, url: str) -> TabType:
        """根据URL检测标签页类型"""
        import re
        
        for tab_type, patterns in self.type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url):
                    return tab_type
        
        return TabType.OTHER
    
    def _select_next_tab_after_close(self, closed_tab_type: TabType) -> Optional[TabInfo]:
        """智能选择关闭标签页后的下一个活跃标签页"""
        
        if closed_tab_type == TabType.USER_PROFILE:
            # 关闭用户资料页后，优先返回到主页面或帖子详情页
            priority_types = [TabType.MAIN, TabType.POST_DETAIL, TabType.OTHER]
        elif closed_tab_type == TabType.POST_DETAIL:
            # 关闭帖子详情页后，优先返回到主页面
            priority_types = [TabType.MAIN, TabType.OTHER]
        else:
            # 其他情况，优先选择主页面
            priority_types = [TabType.MAIN, TabType.POST_DETAIL, TabType.USER_PROFILE, TabType.OTHER]
        
        # 按优先级查找可用的标签页
        for tab_type in priority_types:
            matching_tabs = [
                tab for tab in self.tabs.values() 
                if tab.tab_type == tab_type
            ]
            if matching_tabs:
                # 选择该类型中最近使用的标签页
                return max(matching_tabs, key=lambda t: t.last_active_time)
        
        return None
    
    async def _setup_page_listeners(self, page: Page, tab_id: str):
        """设置页面事件监听器"""
        
        def on_page_close():
            if tab_id in self.tabs:
                self.logger.info(f"页面关闭事件: {tab_id}")
        
        page.on("close", on_page_close)
    
    def get_tab_summary(self) -> Dict[str, Any]:
        """获取标签页摘要信息"""
        return {
            "total_tabs": len(self.tabs),
            "active_tab": self.active_tab_id,
            "tabs": [
                {
                    "tab_id": tab.tab_id,
                    "type": tab.tab_type.value,
                    "title": tab.title,
                    "url": tab.url,
                    "is_active": tab.is_active,
                    "created_time": tab.created_time
                }
                for tab in self.tabs.values()
            ]
        }


class ContextSwitcher:
    """智能上下文切换器"""
    
    def __init__(self, tab_manager: TabManager):
        self.tab_manager = tab_manager
        self.logger = logging.getLogger("context_switcher")
    
    async def ensure_context_for_operation(self, operation: str, **kwargs) -> Tuple[bool, Optional[Page]]:
        """确保操作在正确的上下文中执行"""
        
        # 首先发现新标签页
        await self.tab_manager.discover_new_tabs()
        
        # 根据操作类型确定需要的上下文
        required_context = self._determine_required_context(operation, **kwargs)
        
        if required_context:
            # 查找合适的标签页
            target_tab_id = await self._find_suitable_tab(required_context, **kwargs)
            
            if target_tab_id:
                success = await self.tab_manager.switch_to_tab(target_tab_id)
                if success:
                    page = await self.tab_manager.get_active_page()
                    
                    # 验证页面状态
                    if await self._validate_page_state(page, required_context, **kwargs):
                        return True, page
                    else:
                        self.logger.warning(f"页面状态验证失败: {operation}")
                        return False, None
            else:
                self.logger.warning(f"未找到合适的标签页: {operation}")
                return False, None
        
        # 使用当前活跃页面
        page = await self.tab_manager.get_active_page()
        return True, page
    
    def _determine_required_context(self, operation: str, **kwargs) -> Optional[TabType]:
        """确定操作需要的上下文类型"""
        
        context_mapping = {
            # 需要在主页面执行的操作
            "xiaohongshu_auto_scroll": TabType.MAIN,
            "xiaohongshu_extract_all_posts": TabType.MAIN,
            "xiaohongshu_click_post": TabType.MAIN,
            
            # 需要在帖子详情页执行的操作
            "xiaohongshu_expand_comments": TabType.POST_DETAIL,
            "xiaohongshu_extract_comments": TabType.POST_DETAIL,
            "xiaohongshu_reply_comment": TabType.POST_DETAIL,
            "xiaohongshu_close_post": TabType.POST_DETAIL,
            
            # 需要在用户资料页执行的操作
            "xiaohongshu_extract_user_profile": TabType.USER_PROFILE,
            
            # 可能创建新标签页的操作
            "xiaohongshu_click_author_avatar": None,  # 这个操作会创建新标签页
        }
        
        return context_mapping.get(operation)
    
    async def _find_suitable_tab(self, required_type: TabType, **kwargs) -> Optional[str]:
        """查找合适的标签页"""
        
        # 首先按类型查找
        tab_id = await self.tab_manager.find_tab_by_type(required_type)
        if tab_id:
            return tab_id
        
        # 如果是用户资料页，可以根据用户信息进一步筛选
        if required_type == TabType.USER_PROFILE:
            userid = kwargs.get('userid')
            username = kwargs.get('username')
            
            if userid or username:
                # 查找包含特定用户信息的标签页
                for tab_id, tab in self.tab_manager.tabs.items():
                    if tab.tab_type == TabType.USER_PROFILE:
                        if userid and userid in tab.url:
                            return tab_id
                        if username and username in tab.title:
                            return tab_id
        
        return None
    
    async def _validate_page_state(self, page: Page, required_type: TabType, **kwargs) -> bool:
        """验证页面状态是否符合要求"""
        if not page:
            return False
        
        try:
            current_url = page.url
            current_title = await page.title()
            
            # 基础URL验证
            if required_type == TabType.MAIN:
                return "xiaohongshu.com" in current_url and not any(
                    pattern in current_url for pattern in ["/discovery/item/", "/user/profile/", "/@"]
                )
            elif required_type == TabType.POST_DETAIL:
                return "/discovery/item/" in current_url or "/explore/" in current_url
            elif required_type == TabType.USER_PROFILE:
                return "/user/profile/" in current_url or "/@" in current_url
            
            return True
            
        except Exception as e:
            self.logger.error(f"页面状态验证失败: {e}")
            return False


class EnvironmentValidator:
    """操作前环境验证器"""
    
    def __init__(self, tab_manager: TabManager):
        self.tab_manager = tab_manager
        self.logger = logging.getLogger("environment_validator")
    
    async def validate_before_operation(self, operation: str, page: Page, **kwargs) -> Tuple[bool, str]:
        """操作前验证环境"""
        
        if not page:
            return False, "页面对象为空"
        
        try:
            # 基础页面可用性检查
            await page.title()
            
            # 特定操作的验证规则
            validation_result = await self._validate_operation_specific(operation, page, **kwargs)
            
            if validation_result[0]:
                self.logger.info(f"环境验证通过: {operation}")
            else:
                self.logger.warning(f"环境验证失败: {operation} - {validation_result[1]}")
            
            return validation_result
            
        except Exception as e:
            error_msg = f"页面不可用: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    async def _validate_operation_specific(self, operation: str, page: Page, **kwargs) -> Tuple[bool, str]:
        """特定操作的验证逻辑"""
        
        current_url = page.url
        
        if operation == "xiaohongshu_expand_comments":
            # 验证是否在帖子详情页
            if "/discovery/item/" not in current_url and "/explore/" not in current_url:
                return False, "不在帖子详情页"
            
            # 检查是否有评论区域
            try:
                comment_area = await page.query_selector('.note-scroller, .comments-container')
                if not comment_area:
                    return False, "未找到评论区域"
            except Exception:
                return False, "无法检查评论区域"
        
        elif operation == "xiaohongshu_extract_user_profile":
            # 验证是否在用户资料页
            if "/user/profile/" not in current_url and "/@" not in current_url:
                return False, "不在用户资料页"
        
        elif operation in ["xiaohongshu_auto_scroll", "xiaohongshu_extract_all_posts"]:
            # 验证是否在主页面
            if any(pattern in current_url for pattern in ["/discovery/item/", "/user/profile/", "/@"]):
                return False, "不在主页面"
        
        return True, "验证通过"
