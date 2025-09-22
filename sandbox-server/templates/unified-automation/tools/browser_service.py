#!/usr/bin/env python3
"""
E2B Browser Service - 简化版本
只包含最基础的浏览器操作能力
"""

import asyncio
import logging
import os
import json
import base64
import traceback
from typing import Dict, Any, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
# 尝试相对导入，如果失败则使用绝对导入
try:
    from .tab_manager import TabManager, ContextSwitcher, EnvironmentValidator, TabType
except ImportError:
    from tab_manager import TabManager, ContextSwitcher, EnvironmentValidator, TabType

# ==================== 简化的数据模型 ====================

@dataclass
class BrowserActionRequest:
    action: str
    params: Dict[str, Any]

@dataclass
class BrowserActionResult:
    success: bool
    message: str
    url: str = ""
    title: str = ""
    content: str = ""
    error: str = ""
    element_count: int = 0

# ==================== 简化的浏览器服务 ====================

class BrowserService:
    """浏览器服务 - 只包含最基础的浏览器操作"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self._initialized: bool = False
        self.logger = logging.getLogger("browser_service")
        
        # 多标签页管理
        self.tab_manager: Optional[TabManager] = None
        self.context_switcher: Optional[ContextSwitcher] = None
        self.env_validator: Optional[EnvironmentValidator] = None
        
        # 设置DISPLAY环境变量
        os.environ["DISPLAY"] = ":1"
        
    # ==================== 浏览器生命周期 ====================
    
    async def start_browser(self) -> Dict[str, Any]:
        """启动浏览器"""
        try:
            print("🚀 启动浏览器服务...")
            
            if not self.playwright:
                self.playwright = await async_playwright().start()
            
            launch_options = {
                "headless": False,
                "timeout": 60000,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--display=:1",
                    "--start-maximized",
                    "--window-size=1920,1080"
                ]
            }
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await self.context.new_page()
            self.page.set_default_timeout(30000)
            
            # 导航到Google首页
            try:
                await self.page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                self.logger.warning(f"导航到Google失败，但不影响启动: {str(e)}")
                pass  # 导航失败不影响启动
            
            # 初始化标签页管理器
            self.tab_manager = TabManager(self.context)
            self.context_switcher = ContextSwitcher(self.tab_manager)
            self.env_validator = EnvironmentValidator(self.tab_manager)
            
            # 注册初始页面
            await self.tab_manager.register_page(self.page, TabType.MAIN)
            
            self._initialized = True
            
            return {
                "success": True,
                "message": "浏览器启动成功",
                "browser_ready": True,
                "tab_manager_ready": True
            }
                
        except Exception as e:
            print(f"❌ 浏览器启动失败: {str(e)}")
            return {
                "success": False,
                "message": f"浏览器启动失败: {str(e)}"
            }
    
    async def close_browser(self):
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self._initialized = False
            print("✅ 浏览器已关闭")
        except Exception as e:
            print(f"⚠️ 关闭浏览器时出错: {e}")
    
    async def get_current_page(self) -> Page:
        """获取当前页面"""
        if self.tab_manager:
            # 使用标签页管理器获取当前活跃页面
            page = await self.tab_manager.get_active_page()
            if page:
                return page
        
        # 回退到原始逻辑
        if not self.page:
            raise Exception("没有可用的浏览器页面，请先启动浏览器")
        return self.page
    
    async def execute_with_context(self, operation: str, operation_func, **kwargs):
        """在正确的上下文中执行操作"""
        if not self.context_switcher or not self.env_validator:
            # 如果没有标签页管理器，使用原始逻辑
            page = await self.get_current_page()
            return await operation_func(page, **kwargs)
        
        # 确保在正确的上下文中执行
        success, page = await self.context_switcher.ensure_context_for_operation(operation, **kwargs)
        
        if not success or not page:
            raise Exception(f"无法为操作 {operation} 找到合适的上下文")
        
        # 验证环境
        valid, error_msg = await self.env_validator.validate_before_operation(operation, page, **kwargs)
        if not valid:
            raise Exception(f"环境验证失败: {error_msg}")
        
        # 执行操作
        return await operation_func(page, **kwargs)
    
    async def get_tab_info(self) -> Dict[str, Any]:
        """获取标签页信息"""
        if self.tab_manager:
            await self.tab_manager.discover_new_tabs()
            await self.tab_manager.cleanup_tabs()
            return self.tab_manager.get_tab_summary()
        else:
            return {
                "total_tabs": 1,
                "active_tab": "legacy",
                "tabs": [{"tab_id": "legacy", "type": "main", "title": "Legacy Page", "url": self.page.url if self.page else "unknown"}]
            }
    
    # ==================== 基础导航操作 ====================
    
    async def navigate(self, url: str) -> BrowserActionResult:
        """导航到指定URL"""
        try:
            page = await self.get_current_page()
            print(f"🌐 导航到: {url}")
            
            await page.goto(url, wait_until="domcontentloaded")
            
            # 等待页面加载
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                self.logger.debug(f"网络空闲状态等待超时: {str(e)}")
                pass  # 网络空闲超时不算错误
            
            current_url = page.url
            current_title = await page.title()
            
            return BrowserActionResult(
                success=True,
                message="导航成功",
                url=current_url,
                title=current_title
            )
                
        except Exception as e:
            print(f"❌ 导航错误: {str(e)}")
            return BrowserActionResult(
                success=False,
                message=f"导航失败: {str(e)}",
                error=str(e)
            )
    
    async def wait_for_load(self, timeout: int = 10000) -> BrowserActionResult:
        """等待页面加载完成"""
        try:
            page = await self.get_current_page()
            
            try:
                await page.wait_for_load_state("networkidle", timeout=timeout)
                return BrowserActionResult(
                    success=True,
                    message="页面加载完成",
                    url=page.url,
                    title=await page.title()
                )
            except Exception as e:
                # 容错处理
                self.logger.debug(f"等待页面加载超时，使用容错模式: {str(e)}")
                return BrowserActionResult(
                    success=True,
                    message="页面基本加载完成",
                    url=page.url,
                    title=await page.title()
                )
                
        except Exception as e:
            return BrowserActionResult(
                success=False,
                message=f"等待页面加载失败: {str(e)}",
                error=str(e)
            )
    
    async def take_screenshot(self) -> str:
        """截图并返回base64字符串"""
        try:
            page = await self.get_current_page()
            screenshot_bytes = await page.screenshot(
                type='jpeg',
                quality=60,
                full_page=False
            )
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            print(f"截图错误: {e}")
            return ""
    
    # ==================== 基础交互操作 ====================
    
    async def click_by_selector(self, selector: str) -> BrowserActionResult:
        """通过选择器点击元素"""
        try:
            page = await self.get_current_page()
            
            # 等待元素出现并点击
            await page.wait_for_selector(selector, timeout=10000)
            await page.click(selector)
            
            return BrowserActionResult(
                success=True,
                message=f"成功点击元素: {selector}",
                url=page.url,
                title=await page.title()
            )
            
        except Exception as e:
            print(f"❌ 点击失败: {str(e)}")
            return BrowserActionResult(
                success=False,
                message=f"点击元素失败: {str(e)}",
                error=str(e)
            )
    
    async def type_text(self, selector: str, text: str) -> BrowserActionResult:
        """在指定元素中输入文本"""
        try:
            page = await self.get_current_page()
            
            # 等待元素出现并输入文本
            await page.wait_for_selector(selector, timeout=10000)
            await page.fill(selector, text)
            
            return BrowserActionResult(
                success=True,
                message=f"成功输入文本到: {selector}",
                url=page.url,
                title=await page.title()
            )
            
        except Exception as e:
            print(f"❌ 输入文本失败: {str(e)}")
            return BrowserActionResult(
                success=False,
                message=f"输入文本失败: {str(e)}",
                error=str(e)
            )           
    
    async def scroll_down(self, amount: Optional[int] = None) -> BrowserActionResult:
        """向下滚动"""
        try:
            page = await self.get_current_page()
            
            if amount:
                await page.evaluate(f"window.scrollBy(0, {amount});")
            else:
                await page.evaluate("window.scrollBy(0, window.innerHeight);")
            
            await asyncio.sleep(0.5)  # 等待滚动完成
            
            return BrowserActionResult(
                success=True,
                message="向下滚动成功",
                url=page.url,
                title=await page.title()
            )
            
        except Exception as e:
            return BrowserActionResult(
                success=False,
                message=f"滚动失败: {str(e)}",
                error=str(e)
            )
    
    async def scroll_up(self, amount: Optional[int] = None) -> BrowserActionResult:
        """向上滚动"""
        try:
            page = await self.get_current_page()
            
            if amount:
                await page.evaluate(f"window.scrollBy(0, -{amount});")
            else:
                await page.evaluate("window.scrollBy(0, -window.innerHeight);")
            
            await asyncio.sleep(0.5)  # 等待滚动完成
            
            return BrowserActionResult(
                success=True,
                message="向上滚动成功",
                url=page.url,
                title=await page.title()
            )
            
        except Exception as e:
            return BrowserActionResult(
                success=False,
                message=f"滚动失败: {str(e)}",
                error=str(e)
            )
    
    # ==================== 基础脚本执行 ====================
    
    async def execute_script(self, script: str) -> BrowserActionResult:
        """执行JavaScript脚本"""
        try:
            page = await self.get_current_page()
            result = await page.evaluate(script)
            
            return BrowserActionResult(
                success=True,
                message="脚本执行成功",
                url=page.url,
                title=await page.title(),
                content=json.dumps(result, ensure_ascii=False) if result else ""
            )
            
        except Exception as e:
            print(f"❌ 脚本执行失败: {str(e)}")
            return BrowserActionResult(
                success=False,
                message=f"脚本执行失败: {str(e)}",
                error=str(e)
            )
    
    async def get_page_content(self) -> BrowserActionResult:
        """获取页面内容"""
        try:
            page = await self.get_current_page()
            
            # 获取页面文本内容
            content = await page.evaluate("""
                () => {
                    // 移除script和style标签
                    const scripts = document.querySelectorAll('script, style');
                    scripts.forEach(el => el.remove());
                    
                    // 获取body文本
                    const text = document.body.innerText || document.body.textContent || '';
                    return text.slice(0, 5000);  // 限制长度
                }
            """)
            
            return BrowserActionResult(
                success=True,
                message="获取页面内容成功",
                url=page.url,
                title=await page.title(),
                content=content
            )
            
        except Exception as e:
            return BrowserActionResult(
                success=False,
                message=f"获取页面内容失败: {str(e)}",
                error=str(e)
            )
    
    # ==================== 基础页面信息获取 ====================
    
    async def get_page_info(self, return_mode: str = "basic") -> BrowserActionResult:
        """获取页面基础信息"""
        try:
            page = await self.get_current_page()
            current_url = page.url
            current_title = await page.title()
            
            if return_mode == "basic":
                return BrowserActionResult(
                    success=True,
                    message="获取页面基础信息成功",
                    url=current_url,
                    title=current_title
                )
            elif return_mode == "elements":
                # 简单的元素提取
                elements_script = """
                () => {
                    const elements = [];
                    const selectors = ['a[href]', 'button', 'input', 'textarea'];
                    
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach((el, index) => {
                            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                                elements.push({
                                    index: elements.length + 1,
                                    tag: el.tagName.toLowerCase(),
                                    text: el.innerText ? el.innerText.trim().substring(0, 50) : '',
                                    href: el.href || '',
                                    id: el.id || ''
                                });
                            }
                        });
                    });
                    
                    return elements.slice(0, 20);  // 最多返回20个元素
                }
                """
                
                elements_data = await page.evaluate(elements_script)
                
                return BrowserActionResult(
                    success=True,
                    message=f"获取页面信息成功，找到 {len(elements_data)} 个可交互元素",
                    url=current_url,
                    title=current_title,
                    content=json.dumps(elements_data, ensure_ascii=False),
                    element_count=len(elements_data)
                )
            else:
                return BrowserActionResult(
                    success=False,
                    message=f"不支持的返回模式: {return_mode}"
                )
                
        except Exception as e:
            return BrowserActionResult(
                success=False,
                message=f"获取页面信息失败: {str(e)}",
                error=str(e)
            )
    
    async def click_element_by_index(self, element_index: int) -> BrowserActionResult:
        """通过索引点击元素"""
        try:
            page = await self.get_current_page()
            
            # 简单的索引点击脚本
            click_script = f"""
            (targetIndex) => {{
                const selectors = ['a[href]', 'button', 'input[type="button"]', 'input[type="submit"]'];
                
                let allElements = [];
                selectors.forEach(selector => {{
                    document.querySelectorAll(selector).forEach(el => {{
                        if (el.offsetWidth > 0 && el.offsetHeight > 0) {{
                            allElements.push(el);
                        }}
                    }});
                }});
                
                const targetElement = allElements[targetIndex - 1];  // 1-based index
                if (targetElement) {{
                    targetElement.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    setTimeout(() => targetElement.click(), 100);
                    return {{
                        success: true,
                        message: `成功点击索引 ${{targetIndex}} 的元素`,
                        tag: targetElement.tagName.toLowerCase()
                    }};
                }} else {{
                    return {{
                        success: false,
                        message: `未找到索引 ${{targetIndex}} 的元素`
                    }};
                }}
            }}
            """
            
            result = await page.evaluate(click_script, element_index)
            
            return BrowserActionResult(
                success=result.get('success', False),
                message=result.get('message', ''),
                url=page.url,
                title=await page.title()
            )
            
        except Exception as e:
            return BrowserActionResult(
                success=False,
                message=f"点击元素失败: {str(e)}",
                error=str(e)
            )

# ==================== 全局服务实例 ====================
browser_service = BrowserService() 
