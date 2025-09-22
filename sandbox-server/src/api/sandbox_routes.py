"""
沙箱信息 API - 简化版
提供基本的沙箱信息查询功能
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import time

# 创建路由器
sandbox_router = APIRouter()

@sandbox_router.get("/info")
async def get_sandbox_info():
    """获取当前沙箱信息"""
    try:
        sandbox_id = os.getenv('E2B_SANDBOX_ID', 'unknown')
        display = os.environ.get('DISPLAY', '未设置')
        
        info = {
            "sandbox_id": sandbox_id,
            "display": display,
            "vnc_available": display == ":1",
            "timestamp": time.time(),
            "status": "running"
        }
        
        if sandbox_id != 'unknown':
            info["vnc_access"] = {
                "vnc_web_url": f"https://6080-{sandbox_id}.e2b.app",
                "vnc_direct_url": f"vnc://5901-{sandbox_id}.e2b.app"
            }
        
        return {
            "success": True,
            "message": "沙箱信息获取成功",
            "data": info
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取沙箱信息失败: {str(e)}",
            "error": str(e)
        }

@sandbox_router.get("/status")
async def get_sandbox_status():
    """获取沙箱运行状态"""
    try:
        sandbox_id = os.getenv('E2B_SANDBOX_ID')
        
        if not sandbox_id:
            return {
                "success": False,
                "message": "无法获取沙箱ID",
                "status": "unknown"
            }
        
        # 检查环境状态
        status_data = {
            "sandbox_id": sandbox_id,
            "status": "running",
            "display": os.environ.get('DISPLAY', '未设置'),
            "python_path": os.environ.get('PYTHONPATH', '未设置'),
            "current_time": time.time()
        }
        
        return {
            "success": True,
            "message": "沙箱状态正常",
            "data": status_data
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"状态检查失败: {str(e)}",
            "error": str(e)
        }

@sandbox_router.get("/env")
async def get_environment_info():
    """获取沙箱环境信息"""
    try:
        env_info = {
            "E2B_SANDBOX_ID": os.getenv('E2B_SANDBOX_ID', '未设置'),
            "DISPLAY": os.environ.get('DISPLAY', '未设置'),
            "VNC_PORT": os.getenv('VNC_PORT', '5901'),
            "NO_VNC_PORT": os.getenv('NO_VNC_PORT', '6080'),
            "VNC_RESOLUTION": os.getenv('VNC_RESOLUTION', '1920x1080'),
            "PYTHONPATH": os.environ.get('PYTHONPATH', '未设置'),
            "PLAYWRIGHT_BROWSERS_PATH": os.getenv('PLAYWRIGHT_BROWSERS_PATH', '未设置'),
            "HOME": os.environ.get('HOME', '未设置'),
            "USER": os.environ.get('USER', '未设置')
        }
        
        return {
            "success": True,
            "message": "环境信息获取成功",
            "data": env_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取环境信息失败: {str(e)}",
            "error": str(e)
        }

