"""
E2B Sandbox 浏览器自动化工具 API服务器 - 简化版
提供浏览器自动化功能的HTTP API接口
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import time

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
# 添加当前目录和父目录到Python路径
project_root = current_dir.parent
sys.path.insert(0, str(current_dir))  # 添加src目录
sys.path.insert(0, str(project_root))  # 添加sandbox-server目录

from api.browser_routes import browser_router
from api.sandbox_routes import sandbox_router
from middleware.error_handler import ErrorHandlerMiddleware
from config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的处理"""
    logger.info("🚀 启动 E2B 沙盒服务...")
    
    # 获取环境信息
    from core.sandbox_manager import sandbox_manager
    env_info = sandbox_manager.get_environment_info()
    
    print(f"🔧 {env_info.get('manager_type', 'E2B沙盒管理器')}")
    print(f"📋 模板ID: {env_info.get('template_id', '未配置')}")
    print(f"🔑 API密钥: {'已配置' if env_info.get('api_key_configured') else '未配置'}")
    print("✅ E2B浏览器自动化API准备就绪")
    
    yield
    
    logger.info("🔄 关闭 E2B 沙盒服务...")

# 创建FastAPI应用
app = FastAPI(
    title="E2B 浏览器自动化沙盒服务",
    description="基于E2B云平台的浏览器自动化服务，支持VNC可视化操作",
    version="2.0.0",
    lifespan=lifespan
)

# 添加错误处理中间件（优先级最高）
app.add_middleware(ErrorHandlerMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(browser_router, prefix="/api/browser", tags=["浏览器自动化"])
app.include_router(sandbox_router, prefix="/api/sandbox", tags=["沙盒信息"])

@app.get("/")
async def root():
    """根路径 - 服务信息"""
    return {
        "service": "E2B 浏览器自动化沙盒服务",
        "version": "2.0.0", 
        "status": "running",
        "timestamp": time.time(),
        "features": {
            "browser_automation": "支持完整的浏览器自动化操作",
            "vnc_access": "支持VNC远程桌面访问",
            "anti_detection": "内置反检测机制",
            "batch_operations": "支持批量操作处理",
            "persistent_sessions": "支持持久化会话管理"
        },
        "api_endpoints": {
            "browser_automation": "/api/browser/automation",
            "sandbox_management": "/api/sandbox/*"
        },
        "llm_friendly_endpoints": {
            "visit": "/api/browser/visit",
            "click": "/api/browser/click", 
            "type": "/api/browser/type",
            "scroll": "/api/browser/scroll",
            "elements": "/api/browser/elements"
        },
        "xiaohongshu_operations": {
            "auto_scroll": "xiaohongshu_auto_scroll",
            "extract_posts": "xiaohongshu_extract_all_posts",
            "click_post": "xiaohongshu_click_post",
            "expand_comments": "xiaohongshu_expand_comments",
            "extract_comments": "xiaohongshu_extract_comments",
            "reply_comment": "xiaohongshu_reply_comment",
            "close_post": "xiaohongshu_close_post",
            "close_page": "xiaohongshu_close_page",
            "click_author_avatar": "xiaohongshu_click_author_avatar",
            "extract_user_profile": "xiaohongshu_extract_user_profile",
            "analyze_post": "xiaohongshu_analyze_post",
            "description": "小红书专用数据提取和分析操作，支持帖子滚动、内容提取、评论分析、关闭帖子、关闭页面、用户信息获取等功能"
        },
        "sandbox_info": {
            "info": "/api/sandbox/info",
            "status": "/api/sandbox/status",
            "env": "/api/sandbox/env"
        },
        "architecture": {
            "platform": "E2B Cloud Sandbox",
            "browser_engine": "Chromium + Playwright",
            "vnc_display": "Xvfb + noVNC",
            "communication": "Direct HTTP API calls (优化后的架构)"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    from core.sandbox_manager import sandbox_manager
    env_info = sandbox_manager.get_environment_info()
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "E2B 浏览器自动化沙盒服务"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
