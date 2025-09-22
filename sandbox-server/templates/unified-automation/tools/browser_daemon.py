#!/usr/bin/env python3
"""
E2B Browser Daemon - 极简版本
只做API路由转发，零业务逻辑
"""

import os
import sys
import asyncio
import logging
import traceback
from typing import Optional, Dict, Any

from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
import uvicorn

# 确保能导入本地模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入服务层
from browser_service import BrowserService
from xiaohongshu_analyzer import XiaohongshuAnalyzer

# 导入API数据模型（只保留需要的）
from api_models import (
    BrowserOperationResponse, NavigateRequest, 
    XiaohongshuAutoScrollRequest, XiaohongshuClickPostRequest,
    XiaohongshuExpandCommentsRequest, XiaohongshuExtractCommentsRequest,
    XiaohongshuAnalyzePostRequest, XiaohongshuExtractAllPostsRequest,
    XiaohongshuReplyCommentRequest, XiaohongshuClickAuthorAvatarRequest,
    XiaohongshuExtractUserProfileRequest, XiaohongshuClosePageRequest
)

#######################################################
# E2B浏览器守护进程 - 极简版本
#######################################################

class E2BBrowserDaemon:
    """E2B浏览器守护进程 - 纯API Gateway，零业务逻辑"""
    
    def __init__(self):
        self.router = APIRouter()
        self.browser_service: Optional[BrowserService] = None
        self.xiaohongshu_analyzer: Optional[XiaohongshuAnalyzer] = None
        self.is_initialized = False
        self.logger = logging.getLogger("e2b_browser_daemon")
        
        # 设置显示环境
        os.environ["DISPLAY"] = ":1"
        
        # 注册路由
        self.setup_routes()
    
    def setup_routes(self):
        """设置API路由 - 只做转发"""
        
        # ==================== 浏览器基础功能 ====================
        
        @self.router.get("/api/health")
        async def health_check():
            """健康检查"""
            return {"status": "healthy", "service": "e2b-browser-daemon"}
        
        @self.router.post("/browser/start")
        async def start_browser():
            """启动浏览器"""
            if not self.browser_service:
                await self.ensure_services_ready()
            return await self.browser_service.start_browser()
        
        @self.router.post("/browser/navigate", response_model=BrowserOperationResponse)
        async def navigate(request: NavigateRequest):
            """导航到URL"""
            await self.ensure_services_ready()
            result = await self.browser_service.navigate(request.url)
            return BrowserOperationResponse(
                success=result.success,
                message=result.message,
                data=result.__dict__
            )
        
        @self.router.post("/browser/execute_script", response_model=BrowserOperationResponse)
        async def execute_script(request: dict):
            """执行JavaScript脚本"""
            await self.ensure_services_ready()
            script = request.get('script', '')
            if not script:
                raise HTTPException(status_code=400, detail="脚本内容不能为空")
            
            result = await self.browser_service.execute_script(script)
            return BrowserOperationResponse(
                success=result.success,
                message=result.message,
                data=result.__dict__
            )
        
        @self.router.post("/browser/click_selector", response_model=BrowserOperationResponse)
        async def click_selector(request: dict):
            """通过选择器点击元素"""
            await self.ensure_services_ready()
            selector = request.get('selector', '')
            if not selector:
                raise HTTPException(status_code=400, detail="选择器不能为空")
            
            result = await self.browser_service.click_by_selector(selector)
            return BrowserOperationResponse(
                success=result.success,
                message=result.message,
                data=result.__dict__
            )
        
        @self.router.post("/browser/type_text", response_model=BrowserOperationResponse)
        async def type_text(request: dict):
            """在元素中输入文本"""
            await self.ensure_services_ready()
            selector = request.get('selector', '')
            text = request.get('text', '')
            if not selector or not text:
                raise HTTPException(status_code=400, detail="选择器和文本都不能为空")
            
            result = await self.browser_service.type_text(selector, text)
            return BrowserOperationResponse(
                success=result.success,
                message=result.message,
                data=result.__dict__
            )
        
        @self.router.post("/browser/scroll_down", response_model=BrowserOperationResponse)
        async def scroll_down(request: dict):
            """向下滚动"""
            await self.ensure_services_ready()
            amount = request.get('amount')
            result = await self.browser_service.scroll_down(amount)
            return BrowserOperationResponse(
                success=result.success,
                message=result.message,
                data=result.__dict__
            )
        
        @self.router.post("/browser/scroll_up", response_model=BrowserOperationResponse)
        async def scroll_up(request: dict):
            """向上滚动"""
            await self.ensure_services_ready()
            amount = request.get('amount')
            result = await self.browser_service.scroll_up(amount)
            return BrowserOperationResponse(
                success=result.success,
                message=result.message,
                data=result.__dict__
            )
        
        # ==================== 小红书专用功能 ====================
        
        @self.router.post("/xiaohongshu/auto_scroll", response_model=BrowserOperationResponse)
        async def xiaohongshu_auto_scroll(request: XiaohongshuAutoScrollRequest):
            """小红书自动滚动"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.auto_scroll_load_posts()
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
            
        @self.router.post("/xiaohongshu/extract_all_posts", response_model=BrowserOperationResponse)
        async def xiaohongshu_extract_all_posts(request: XiaohongshuExtractAllPostsRequest):
            """提取所有帖子"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.extract_all_posts(limit=request.limit)
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.post("/xiaohongshu/click_post_by_index", response_model=BrowserOperationResponse)
        async def xiaohongshu_click_post_by_index(request: XiaohongshuClickPostRequest):
            """通过标题点击帖子"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.click_post_by_title(request.title)
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.post("/xiaohongshu/expand_comments", response_model=BrowserOperationResponse)
        async def xiaohongshu_expand_comments(request: XiaohongshuExpandCommentsRequest):
            """展开所有评论"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.expand_all_comments()
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.post("/xiaohongshu/extract_comments", response_model=BrowserOperationResponse)
        async def xiaohongshu_extract_comments(request: XiaohongshuExtractCommentsRequest):
            """提取所有评论"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.extract_all_comments()
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.post("/xiaohongshu/analyze_post", response_model=BrowserOperationResponse)
        async def xiaohongshu_analyze_post(request: XiaohongshuAnalyzePostRequest):
            """完整的帖子分析"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.analyze_post_complete(request.global_index)
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.post("/xiaohongshu/reply_comment", response_model=BrowserOperationResponse)
        async def xiaohongshu_reply_comment(request: XiaohongshuReplyCommentRequest):
            """回复指定评论"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.reply_to_comment(
                request.target_user_id, 
                request.target_username, 
                request.target_content, 
                request.reply_content
            )
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.post("/xiaohongshu/close_post", response_model=BrowserOperationResponse)
        async def xiaohongshu_close_post():
            """关闭小红书帖子详情页"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.close_post()
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.post("/xiaohongshu/click_author_avatar", response_model=BrowserOperationResponse)
        async def xiaohongshu_click_author_avatar(request: XiaohongshuClickAuthorAvatarRequest):
            """点击作者头像并获取用户信息"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.click_author_avatar_and_extract_profile(
                request.userid, 
                request.username
            )
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.post("/xiaohongshu/extract_user_profile", response_model=BrowserOperationResponse)
        async def xiaohongshu_extract_user_profile(request: XiaohongshuExtractUserProfileRequest):
            """提取用户个人主页信息"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.extract_user_profile()
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
        
        @self.router.get("/browser/tabs", response_model=BrowserOperationResponse)
        async def get_tab_info():
            """获取当前标签页信息"""
            await self.ensure_services_ready()
            result = await self.browser_service.get_tab_info()
            return BrowserOperationResponse(
                success=True,
                message="获取标签页信息成功",
                data=result
            )
        
        @self.router.post("/xiaohongshu/close_page", response_model=BrowserOperationResponse)
        async def xiaohongshu_close_page(request: XiaohongshuClosePageRequest):
            """关闭当前页面"""
            await self.ensure_services_ready()
            result = await self.xiaohongshu_analyzer.close_page()
            return BrowserOperationResponse(
                success=result.get('success', False),
                message=result.get('message', ''),
                data=result
            )
    
    async def ensure_services_ready(self):
        """确保服务已准备好"""
        if not self.is_initialized:
            await self.startup()
    
    async def startup(self):
        """启动服务"""
        try:
            print("🚀 启动 E2B Browser Daemon...")
            
            # 创建浏览器服务实例
            self.browser_service = BrowserService()
            
            # 创建小红书分析器实例
            self.xiaohongshu_analyzer = XiaohongshuAnalyzer(self.browser_service)
            
            self.is_initialized = True
            print("✅ E2B Browser Daemon 启动成功")
            
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            traceback.print_exc()
            raise
    
    async def shutdown(self):
        """关闭服务"""
        try:
            print("🔄 关闭 E2B Browser Daemon...")
            
            if self.browser_service:
                await self.browser_service.close_browser()
            
        except Exception as e:
            print(f"⚠️ 关闭时出错: {e}")

# ==================== FastAPI应用实例 ====================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI生命周期管理"""
    # 启动时
    daemon = app.state.daemon
    await daemon.startup()
    yield
    # 关闭时  
    await daemon.shutdown()

def create_app() -> FastAPI:
    """创建FastAPI应用"""
    
    # 创建守护进程实例
    daemon = E2BBrowserDaemon()

    # 创建FastAPI应用
    app = FastAPI(
        title="E2B Browser Daemon",
        description="E2B云端浏览器自动化服务 - 极简版本",
        version="2.0.0",
        lifespan=lifespan
    )

    # 存储daemon实例到app状态
    app.state.daemon = daemon

    # 注册路由
    app.include_router(daemon.router)
    
    return app

# ==================== 主函数 ====================

if __name__ == "__main__":
    print("🚀 Starting E2B Browser Daemon...")
    
    app = create_app()
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False  # E2B环境中不使用reload
    )
 