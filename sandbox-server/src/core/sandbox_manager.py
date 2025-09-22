"""
E2B 沙盒管理器 - 真正的E2B集成版本
负责创建、管理和控制E2B沙盒
"""
import asyncio
import json
import logging
import time
import base64
import uuid
import os
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

try:
    from e2b import AsyncSandbox
except ImportError:
    print("⚠️ E2B SDK未安装，请运行: pip install e2b")
    AsyncSandbox = None

# 导入小红书专用管理器
from .xiaohongshu_manager import xiaohongshu_manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class E2BSandboxManager:
    """E2B沙盒管理器 - 真正的云端沙盒控制"""
    
    def __init__(self):
        # E2B配置
        self.api_key = os.getenv('E2B_API_KEY', 'e2b_ee6777b1277ca33ceb4d4347ad240292b1b31b30')
        self.template_id = os.getenv('E2B_TEMPLATE_ID', 'dgcanzrrlvhyju0asxth')
        self.sandbox_timeout = int(os.getenv('E2B_SANDBOX_TIMEOUT', '1800'))  # 默认30分钟
        
        # 活跃沙盒存储
        self.active_sandboxes: Dict[str, AsyncSandbox] = {}
        self.sandbox_info: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"E2B沙盒管理器初始化完成")
        logger.info(f"模板ID: {self.template_id}")
        logger.info(f"API Key配置: {'已配置' if self.api_key else '未配置'}")
        logger.info(f"沙盒超时: {self.sandbox_timeout//60}分钟)")
    
    async def create_sandbox(self, persistent_id: Optional[str] = None) -> Dict[str, Any]:
        """创建新的E2B沙盒"""
        try:
            if not AsyncSandbox:
                return {
                    "success": False,
                    "message": "E2B SDK未安装，无法创建沙盒"
                }
            
            # 生成持久化ID
            if not persistent_id:
                persistent_id = f"browser_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            logger.info(f"🚀 创建E2B沙盒: {persistent_id}")
            
            # 创建沙盒
            sandbox = await AsyncSandbox.create(
                template=self.template_id,
                api_key=self.api_key,
                timeout=self.sandbox_timeout
            )
            
            # 等待沙盒就绪
            logger.info(f"⏳ 等待沙盒就绪: {sandbox.sandbox_id}")
            await asyncio.sleep(2)
            
            # 存储沙盒实例和信息
            self.active_sandboxes[persistent_id] = sandbox
            self.sandbox_info[persistent_id] = {
                "e2b_sandbox_id": sandbox.sandbox_id,
                "created_at": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "status": "active"
            }
            
            # 检查沙盒状态
            try:
                result = await sandbox.commands.run("echo 'sandbox ready'", timeout=10)
                if result.exit_code != 0:
                    raise Exception(f"沙盒状态检查失败: {result.stderr}")
            except Exception as e:
                logger.warning(f"沙盒状态检查异常: {e}")
            
            logger.info(f"✅ E2B沙盒创建成功: {sandbox.sandbox_id}")
            
            return {
                "success": True,
                "message": "E2B沙盒创建成功",
                "persistent_id": persistent_id,
                "e2b_sandbox_id": sandbox.sandbox_id,
                "vnc_access": {
                    "vnc_web_url": f"https://6080-{sandbox.sandbox_id}.e2b.app",
                    "vnc_direct_url": f"vnc://5901-{sandbox.sandbox_id}.e2b.app",
                    "display": ":1",
                    "note": "通过VNC Web URL可实时观察浏览器操作"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ E2B沙盒创建失败: {e}")
            return {
                "success": False,
                "message": f"E2B沙盒创建失败: {str(e)}"
            }
    
    async def get_or_create_sandbox(self, persistent_id: Optional[str] = None) -> Dict[str, Any]:
        """获取现有沙盒或创建新沙盒"""
        if persistent_id and persistent_id in self.active_sandboxes:
            # 检查沙盒是否仍然活跃
            try:
                sandbox = self.active_sandboxes[persistent_id]
                result = await sandbox.commands.run("echo 'ping'", timeout=5)
                if result.exit_code == 0:
                    logger.info(f"♻️ 复用现有沙盒: {persistent_id}")
                    self.sandbox_info[persistent_id]["last_used"] = datetime.now().isoformat()
                    return {
                        "success": True,
                        "persistent_id": persistent_id,
                        "e2b_sandbox_id": sandbox.sandbox_id,
                        "existing": True,
                        "vnc_access": {
                            "vnc_web_url": f"https://6080-{sandbox.sandbox_id}.e2b.app",
                            "vnc_direct_url": f"vnc://5901-{sandbox.sandbox_id}.e2b.app",
                            "display": ":1",
                            "note": "通过VNC Web URL可实时观察浏览器操作"
                        }
                    }
                else:
                    logger.warning(f"沙盒 {persistent_id} 已失效，将创建新沙盒")
                    del self.active_sandboxes[persistent_id]
                    del self.sandbox_info[persistent_id]
            except Exception as e:
                logger.warning(f"检查沙盒状态失败: {e}，将创建新沙盒")
                if persistent_id in self.active_sandboxes:
                    del self.active_sandboxes[persistent_id]
                if persistent_id in self.sandbox_info:
                    del self.sandbox_info[persistent_id]
        
        # 创建新沙盒
        return await self.create_sandbox(persistent_id)

    async def execute_browser_operations(self, persistent_id: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """🎯 在E2B沙盒中执行浏览器操作 - 直接HTTP调用版本"""
        try:
            start_time = time.time()
            
            # 检查沙盒是否存在
            if persistent_id not in self.active_sandboxes:
                return {
                    "success": False,
                    "message": f"沙盒 {persistent_id} 不存在，请先创建沙盒"
                }
            
            sandbox = self.active_sandboxes[persistent_id]
            logger.info(f"🔄 在沙盒 {sandbox.sandbox_id} 中执行 {len(operations)} 个操作")
            
            # 🎯 新架构：直接HTTP调用沙盒内的守护进程
            daemon_base_url = f"https://8080-{sandbox.sandbox_id}.e2b.app"
            
            logger.info(f"🚀 开始直接HTTP调用执行 {len(operations)} 个操作")
            logger.info(f"🌐 守护进程URL: {daemon_base_url}")
            
            results = []
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
                for i, operation in enumerate(operations):
                    action = operation.get('action', '')
                    params = operation.get('params', {})
                    
                    logger.info(f"🚀 执行操作 {i+1}/{len(operations)}: {action}")
                    
                    # 根据action映射到具体的API端点
                    endpoint = ''
                    request_data = {}
                    
                    if action == 'start_browser':
                        endpoint = '/browser/start'
                    elif action == 'navigate':
                        endpoint = '/browser/navigate'
                        request_data = {'url': params.get('url', '')}
                    elif action == 'execute_script':
                        endpoint = '/browser/execute_script'
                        request_data = {'script': params.get('script', '')}
                    elif action == 'click_selector':
                        endpoint = '/browser/click_selector'
                        request_data = {'selector': params.get('selector', '')}
                    elif action == 'type_text':
                        endpoint = '/browser/type_text'
                        request_data = {
                            'selector': params.get('selector', ''),
                            'text': params.get('text', '')
                        }
                    # 🎯 小红书专用操作支持
                    elif xiaohongshu_manager.is_xiaohongshu_operation(action):
                        xiaohongshu_mapping = xiaohongshu_manager.get_xiaohongshu_operation_mapping()
                        endpoint = xiaohongshu_mapping[action]
                        request_data = xiaohongshu_manager.prepare_xiaohongshu_request_data(action, params)
                        logger.info(f'🎯 小红书专用操作: {action} -> {endpoint}')
                    else:
                        results.append({
                            'action': action,
                            'success': False,
                            'message': f'不支持的操作: {action}',
                            'data': {}
                        })
                        continue
                    
                    try:
                        # 🌐 直接HTTP调用沙盒内守护进程
                        url = f"{daemon_base_url}{endpoint}"
                        logger.debug(f"📡 HTTP请求: {url}")
                        logger.debug(f"📋 请求数据: {request_data}")
                        
                        async with session.post(url, json=request_data) as response:
                            if response.status == 200:
                                result = await response.json()
                                results.append({
                                    'action': action,
                                    'success': result.get('success', True),
                                    'message': result.get('message', '操作完成'),
                                    'data': result
                                })
                                logger.info(f'✅ {action} 操作成功')
                            else:
                                response_text = await response.text()
                                results.append({
                                    'action': action,
                                    'success': False,
                                    'message': f'HTTP {response.status}: {response_text}',
                                    'data': {}
                                })
                                logger.error(f'❌ {action} 操作失败: {response.status}')
                    
                    except Exception as e:
                        results.append({
                            'action': action,
                            'success': False,
                            'message': f'请求异常: {str(e)}',
                            'data': {}
                        })
                        logger.error(f'❌ {action} 请求异常: {str(e)}')
            
            # 计算结果统计
            success_count = sum(1 for r in results if r['success'])
            total_count = len(results)
            execution_time = time.time() - start_time
            
            # 构建最终结果
            final_result = {
                'success': success_count == total_count,
                'message': f'批量操作完成: {success_count}/{total_count} 成功',
                'total_operations': total_count,
                'successful_operations': success_count,
                'results': results,
                'execution_time': execution_time,
                'persistent_id': persistent_id,
                'e2b_sandbox_id': sandbox.sandbox_id
            }
            
            # 添加VNC访问信息
            final_result["vnc_access"] = {
                "vnc_web_url": f"https://6080-{sandbox.sandbox_id}.e2b.app",
                "vnc_direct_url": f"vnc://5901-{sandbox.sandbox_id}.e2b.app",
                "display": ":1",
                "note": "通过VNC Web URL可实时观察浏览器操作"
            }
            
            # 更新使用时间
            self.sandbox_info[persistent_id]["last_used"] = datetime.now().isoformat()
            
            logger.info(f"✅ 所有操作执行完成，耗时: {execution_time:.2f}s")
            return final_result
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 浏览器操作执行失败: {e}")
            return {
                "success": False,
                "message": f"浏览器操作执行失败: {str(e)}",
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def cleanup_sandbox(self, persistent_id: str) -> Dict[str, Any]:
        """清理指定沙盒"""
        try:
            if persistent_id not in self.active_sandboxes:
                return {
                    "success": False,
                    "message": f"沙盒 {persistent_id} 不存在"
                }
            
            sandbox = self.active_sandboxes[persistent_id]
            await sandbox.kill()
            
            # 清理存储
            del self.active_sandboxes[persistent_id]
            if persistent_id in self.sandbox_info:
                del self.sandbox_info[persistent_id]
            
            logger.info(f"🛑 沙盒 {persistent_id} 已清理")
            return {
                "success": True,
                "message": f"沙盒 {persistent_id} 已清理"
            }
            
        except Exception as e:
            logger.error(f"清理沙盒失败: {str(e)}")
            return {
                "success": False,
                "message": f"清理沙盒失败: {str(e)}"
            }

    def list_active_sandboxes(self) -> Dict[str, Any]:
        """列出所有活跃沙盒"""
        sandboxes = []
        for persistent_id, info in self.sandbox_info.items():
            sandbox_data = info.copy()
            sandbox_data["persistent_id"] = persistent_id
            sandbox_data["connected"] = persistent_id in self.active_sandboxes
            sandboxes.append(sandbox_data)
        
        return {
            "success": True,
            "message": f"找到 {len(sandboxes)} 个活跃沙盒",
            "sandboxes": sandboxes,
            "count": len(sandboxes)
        }
    
    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return {
            "manager_type": "E2B云端沙盒管理器",
            "template_id": self.template_id,
            "api_key_configured": bool(self.api_key),
            "active_sandboxes": len(self.active_sandboxes),
            "timestamp": time.time()
        }

# 全局沙盒管理器实例
sandbox_manager = E2BSandboxManager()