"""
E2B浏览器工具 - HTTP客户端版本
直接调用守护进程，不再自己管理浏览器状态
"""

import os
import time
import json
import requests
from typing import Dict, Any, List, Optional


class BrowserUtils:
    """浏览器工具类 - HTTP客户端版本"""
    
    def __init__(self):
        self.daemon_url = "http://localhost:8080"  # 守护进程地址
        self.timeout = 600  # 请求超时时间 - 增加到10分钟以支持用户登录等待
    
    def _make_request(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """向守护进程发送HTTP请求"""
        try:
            url = f"{self.daemon_url}/api{endpoint}"
            
            if data:
                response = requests.post(url, json=data, timeout=self.timeout)
            else:
                response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "message": f"守护进程响应错误: {response.status_code}",
                    "data": {},
                    "error": response.text
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"请求守护进程失败: {str(e)}",
                "data": {},
                "error": str(e)
            }
    
    def start_browser(self) -> Dict[str, Any]:
        """启动浏览器"""
        print("🚀 请求守护进程启动浏览器...")
        result = self._make_request("/browser/start")
        
        if result.get("success", False):
            print("✅ 浏览器启动成功")
        else:
            print(f"❌ 浏览器启动失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def navigate(self, url: str, return_mode: str = "basic", purpose: str = None) -> Dict[str, Any]:
        """智能导航到指定URL
        
        Args:
            url: 目标URL
            return_mode: 返回数据模式 (如果指定purpose会自动选择最佳模式)
                - "basic": 只返回URL和标题（最快，适合纯导航）
                - "elements": 返回可交互元素（适合需要点击操作）
                - "content": 返回页面内容（适合内容分析）
                - "full": 返回所有信息包括截图（最慢，调试用）
            purpose: 导航目的 (可选，会自动选择最佳return_mode)
                - "open": 纯打开页面 → basic模式
                - "search": 需要搜索操作 → elements模式
                - "login": 需要登录操作 → elements模式
                - "interact": 需要点击/输入 → elements模式
                - "analyze": 需要分析内容 → content模式
                - "debug": 调试问题 → full模式
        """
        # 🎯 如果指定了purpose，自动选择最佳模式
        if purpose:
            mode_map = {
                "open": "basic",
                "search": "elements",
                "login": "elements",
                "interact": "elements",
                "analyze": "content",
                "debug": "full"
            }
            return_mode = mode_map.get(purpose, "basic")
            print(f"🎯 智能导航: {purpose} → 自动选择{return_mode}模式")
        else:
            print(f"🌐 导航到: {url} (模式: {return_mode})")
        
        data = {"url": url, "return_mode": return_mode}
        result = self._make_request("/browser/navigate", data)
        
        if result.get("success", False):
            print(f"✅ 导航成功: {url} (模式: {return_mode})")
        else:
            print(f"❌ 导航失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def click_element(self, index: int) -> Dict[str, Any]:
        """点击元素"""
        print(f"👆 点击元素: {index}")
        data = {"index": index}
        result = self._make_request("/browser/click", data)
        
        if result.get("success", False):
            print(f"✅ 点击成功: 元素 {index}")
        else:
            print(f"❌ 点击失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def input_text(self, index: int, text: str) -> Dict[str, Any]:
        """在元素中输入文本"""
        print(f"⌨️ 在元素 {index} 中输入: {text}")
        data = {"index": index, "text": text}
        result = self._make_request("/browser/type", data)
        
        if result.get("success", False):
            print(f"✅ 输入成功: 元素 {index}")
        else:
            print(f"❌ 输入失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def scroll_down(self, amount: Optional[int] = None) -> Dict[str, Any]:
        """向下滚动"""
        print(f"⬇️ 向下滚动: {amount or '默认'}")
        data = {"direction": "down", "amount": amount}
        result = self._make_request("/browser/scroll", data)
        
        if result.get("success", False):
            print("✅ 滚动成功")
        else:
            print(f"❌ 滚动失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def scroll_up(self, amount: Optional[int] = None) -> Dict[str, Any]:
        """向上滚动"""
        print(f"⬆️ 向上滚动: {amount or '默认'}")
        data = {"direction": "up", "amount": amount}
        result = self._make_request("/browser/scroll", data)
        
        if result.get("success", False):
            print("✅ 滚动成功")
        else:
            print(f"❌ 滚动失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def take_screenshot(self) -> Dict[str, Any]:
        """截图"""
        print("📸 截图中...")
        result = self._make_request("/browser/screenshot")
        
        if result.get("success", False):
            print("✅ 截图成功")
        else:
            print(f"❌ 截图失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def reply_to_comment(self, comment_index: int, reply_content: str) -> Dict[str, Any]:
        """回复指定索引的评论"""
        print(f"💬 回复第 {comment_index} 个评论: {reply_content}")
        data = {
            "comment_index": comment_index,
            "reply_content": reply_content
        }
        result = self._make_request("/browser/reply_comment", data)
        
        if result.get("success", False):
            print(f"✅ 回复成功: 评论 {comment_index}")
        else:
            print(f"❌ 回复失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def reply_to_top_liked_comment(self, reply_content: str, target_rank: int = 1) -> Dict[str, Any]:
        """回复指定排名的高赞评论"""
        print(f"🏆 回复第 {target_rank} 名高赞评论: {reply_content}")
        data = {
            "reply_content": reply_content,
            "target_rank": target_rank
        }
        result = self._make_request("/browser/reply_top_comment", data)
        
        if result.get("success", False):
            print(f"✅ 高赞评论回复成功: 第{target_rank}名")
        else:
            print(f"❌ 高赞评论回复失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    # 向后兼容的别名方法
    def reply_to_top_comment(self, reply_content: str, target_rank: int = 1) -> Dict[str, Any]:
        """向后兼容方法 - 调用 reply_to_top_liked_comment"""
        return self.reply_to_top_liked_comment(reply_content, target_rank)
    
    def get_top_comments(self, limit: int = 5) -> Dict[str, Any]:
        """获取按点赞数排序的高赞评论"""
        print(f"📊 获取前 {limit} 个高赞评论...")
        data = {"limit": limit}
        result = self._make_request("/browser/get_top_comments", data)
        
        if result.get("success", False):
            comments_data = result.get("data", {})
            top_comments = comments_data.get("comments", [])
            print(f"✅ 成功获取 {len(top_comments)} 个高赞评论")
            
            # 打印高赞评论信息
            for i, comment in enumerate(top_comments, 1):
                print(f"  {i}. 👍{comment.get('likeCount', '0')} | {comment.get('author', 'Unknown')} | {comment.get('content', '')[:50]}...")
        else:
            print(f"❌ 获取高赞评论失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def click_post_by_index(self, post_index: int) -> Dict[str, Any]:
        """点击指定索引的帖子"""
        print(f"🎯 点击索引为 {post_index} 的帖子...")
        data = {"post_index": post_index}
        result = self._make_request("/browser/click_post", data)
        
        if result.get("success", False):
            print(f"✅ 成功点击索引 {post_index} 的帖子")
        else:
            print(f"❌ 点击帖子失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def click_top_liked_post(self, target_rank: int = 1) -> Dict[str, Any]:
        """点击指定排名的高赞帖子"""
        print(f"🎯 点击第 {target_rank} 名高赞帖子...")
        data = {"target_rank": target_rank}
        result = self._make_request("/browser/click_top_liked_post", data)
        
        if result.get("success", False):
            print(f"✅ 成功点击第{target_rank}名高赞帖子")
        else:
            print(f"❌ 点击高赞帖子失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def smart_wait(self,
                    wait_type: str = "user_action",
                    max_timeout: int = 300,
                    check_interval: int = 2,
                    success_selectors: list = None,
                    failure_selectors: list = None,
                    wait_message: str = "等待用户操作完成...",
                    target_url: str = None,
                    fixed_seconds: int = None) -> Dict[str, Any]:
        print(f"⏰ 开始智能等待: {wait_message}")
        print(f"📋 等待类型: {wait_type}, 最大超时: {max_timeout}秒")
        
        data = {
            "wait_type": wait_type,
            "max_timeout": max_timeout,
            "check_interval": check_interval,
            "wait_message": wait_message
        }
        
        # 添加可选参数
        if success_selectors:
            data["success_selectors"] = success_selectors
        if failure_selectors:
            data["failure_selectors"] = failure_selectors
        if target_url:
            data["target_url"] = target_url
        if fixed_seconds:
            data["fixed_seconds"] = fixed_seconds
            
        result = self._make_request("/browser/smart_wait", data)
        
        if result.get("success", False):
            print(f"✅ 智能等待完成: {result.get('message', '')}")
        else:
            print(f"❌ 智能等待失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def get_page_info(self, return_mode: str = "elements") -> Dict[str, Any]:
        """获取页面信息
        
        Args:
            return_mode: 返回数据模式
                - "basic": 只返回URL和标题
                - "elements": 返回精简的交互元素（默认，性能最佳）
                - "full": 返回所有信息包括截图
        """
        print(f"📋 获取页面信息 (模式: {return_mode})...")
        data = {"return_mode": return_mode}
        result = self._make_request("/browser/page_info", data)
        
        if result.get("success", False):
            print(f"✅ 获取页面信息成功 (模式: {return_mode})")
        else:
            print(f"❌ 获取页面信息失败: {result.get('message', 'Unknown error')}")
        
        return result
    
    def get_element_children(self, parent_index: int) -> Dict[str, Any]:
        """获取指定元素的子节点信息
        
        Args:
            parent_index: 父元素的索引
            
        Returns:
            包含父元素信息和子节点列表的字典
        """
        print(f"🔍 获取元素 {parent_index} 的子节点信息...")
        
        # 构造批量操作请求
        operations = [
            {
                "method": "get_element_children",
                "params": {
                    "parent_index": parent_index
                },
                "description": f"分析元素 {parent_index} 的子节点结构"
            }
        ]
        
        result = batch_browser_operations(
            operations=operations,
            user_intent="data_interaction"
        )
        
        if result.get("success", False):
            print(f"✅ 获取元素 {parent_index} 子节点成功")
        else:
            print(f"❌ 获取元素 {parent_index} 子节点失败: {result.get('message', 'Unknown error')}")
        
        return result


def batch_browser_operations(operations: List[Dict[str, Any]], persistent_id: str = None,
                            user_intent: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    批量执行浏览器操作 - 通过守护进程，支持智能响应控制
    
    Args:
        operations: 操作列表
        persistent_id: 持久化ID
        user_intent: 用户意图 (setup/data_collection/simple_interaction/data_interaction/browsing)
        options: 用户选项配置
    
    Returns:
        执行结果 (根据意图智能返回不同的数据结构)
    """
    start_time = time.time()
    
    if not persistent_id:
        persistent_id = f"browser_{int(time.time())}_daemon"
    
    print(f"🚀 开始批量操作，持久化ID: {persistent_id}")
    print(f"📋 操作数量: {len(operations)}")
    if user_intent:
        print(f"🎯 用户指定意图: {user_intent}")
    if options:
        print(f"⚙️ 用户选项: {options}")
    
    # 创建浏览器工具实例
    browser_utils = BrowserUtils()
    
    # 直接调用守护进程的批量操作接口，包含新参数
    request_data = {
        "method": "batch_operations",
        "params": {
            "operations": operations,
            "persistent_id": persistent_id
        }
    }
    
    # 🎯 添加智能响应控制参数
    if user_intent:
        request_data["params"]["user_intent"] = user_intent
    if options:
        request_data["params"]["options"] = options
    
    try:
        result = browser_utils._make_request("/browser/batch", request_data)
                
        if result.get("success", False):
            print("✅ 批量操作完成")
            
            # 添加VNC访问信息
            sandbox_id = os.getenv('E2B_SANDBOX_ID', 'unknown')
            if sandbox_id != 'unknown':
                vnc_info = {
                    "vnc_web_url": f"https://6080-{sandbox_id}.e2b.app",
                    "vnc_direct_url": f"vnc://5901-{sandbox_id}.e2b.app",
                    "display": ":1",
                    "note": "通过VNC Web URL可实时观察浏览器操作"
                }
                
                # 更新结果中的VNC信息
                if "data" not in result:
                    result["data"] = {}
                result["data"]["vnc_access"] = vnc_info
                result["vnc_access"] = vnc_info
            
            # 添加执行时间和其他元数据
            execution_time = time.time() - start_time
            result.update({
                "persistent_id": persistent_id,
                "task_name": "浏览器自动化任务",
                "execution_time": execution_time,
                "e2b_sandbox_id": sandbox_id,
                "total_execution_time": execution_time
            })
            
            return result
            
        else:
            print(f"❌ 批量操作失败: {result.get('message', 'Unknown error')}")
            
            # 失败时也返回VNC信息
            sandbox_id = os.getenv('E2B_SANDBOX_ID', 'unknown')
            vnc_message = ""
            if sandbox_id != 'unknown':
                vnc_url = f"https://6080-{sandbox_id}.e2b.app"
                vnc_message = f" | VNC界面: {vnc_url}"
            
            execution_time = time.time() - start_time
            
            return {
                    "success": False,
                "message": f"批量操作失败{vnc_message}",
                "data": result.get("data", {}),
                "persistent_id": persistent_id,
                "task_name": "浏览器自动化任务",
                "execution_time": execution_time,
                "e2b_sandbox_id": sandbox_id,
                "error": result.get("error", "Unknown error")
            }
            
    except Exception as e:
        print(f"❌ 批量操作异常: {str(e)}")
        
        sandbox_id = os.getenv('E2B_SANDBOX_ID', 'unknown')
        vnc_message = ""
        if sandbox_id != 'unknown':
            vnc_url = f"https://6080-{sandbox_id}.e2b.app"
            vnc_message = f" | VNC界面: {vnc_url}"
        
        execution_time = time.time() - start_time
        
        return {
            "success": False,
            "message": f"批量操作异常{vnc_message}: {str(e)}",
            "data": {},
            "persistent_id": persistent_id,
            "task_name": "浏览器自动化任务",
            "execution_time": execution_time,
            "e2b_sandbox_id": sandbox_id,
            "error": str(e)
        }


# ==================== 向后兼容性 ====================

def _get_global_browser():
    """获取全局浏览器实例 - 兼容现有调用"""
    return BrowserUtils()

# 全局实例，保持向后兼容
browser_utils_instance = BrowserUtils()

# 向后兼容的函数别名
def run_async(coro):
    """向后兼容 - 不再需要，但保留以防破坏现有代码"""
    print("⚠️ run_async已废弃，现在使用HTTP调用守护进程")
    return None
