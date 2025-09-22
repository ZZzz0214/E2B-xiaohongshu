"""
文本处理 API 路由 - 统一接口版
提供统一的文本处理接口，支持单一操作和批量操作
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
import time
import json
import logging

from models.request_models import BaseResponse
from core.sandbox_manager import sandbox_manager
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 创建路由器
text_router = APIRouter()

async def _get_or_create_sandbox(sandbox_id: Optional[str] = None):
    """获取或创建沙箱"""
    if sandbox_id:
        # 检查沙箱是否还存在
        info = sandbox_manager.get_sandbox_info(sandbox_id)
        if info["success"]:
            return sandbox_id, False  # 沙箱存在，不需要清理
    
    # 创建新沙箱
    result = await sandbox_manager.create_sandbox()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"创建沙箱失败: {result.get('message', 'Unknown error')}")
    return result["sandbox_id"], True  # 新创建的沙箱，需要清理

async def _execute_text_in_persistent_sandbox(sandbox_id: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """在持久化沙盒中执行文本处理工具"""
    try:
        # 检查持久化沙盒是否存在
        if sandbox_id not in sandbox_manager.persistent_sandboxes:
            return {
                "success": False,
                "message": f"持久化沙盒 {sandbox_id} 不存在"
            }
        
        sandbox = sandbox_manager.persistent_sandboxes[sandbox_id]
        logger.info(f"在持久化沙盒 {sandbox_id} 中执行文本工具: {method}")
        
        # 构建文本处理命令
        command = sandbox_manager._build_text_command(method, params)
        
        # 执行命令
        result = await sandbox.commands.run(command, timeout=60)
        
        # 解析结果
        if result.exit_code == 0:
            try:
                output_data = json.loads(result.stdout)
                return {
                    "success": True,
                    "message": f"文本工具 {method} 执行成功",
                    "data": output_data
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "message": f"文本工具 {method} 执行成功",
                    "data": result.stdout.strip()
                }
        else:
            return {
                "success": False,
                "message": f"文本工具 {method} 执行失败: {result.stderr}"
            }
            
    except Exception as e:
        logger.error(f"在持久化沙盒 {sandbox_id} 中执行文本工具失败: {str(e)}")
        return {
            "success": False,
            "message": f"执行失败: {str(e)}"
        }

# ==================== 统一文本处理接口 ====================

class TextAction(BaseModel):
    """单个文本处理操作定义"""
    method: str = Field(..., description="方法名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="方法参数")
    description: Optional[str] = Field(None, description="操作描述")
    required: bool = Field(default=True, description="是否必须成功")
    delay: float = Field(default=0, description="执行后延迟（秒）")

class TextAutomationRequest(BaseModel):
    """文本处理自动化统一请求"""
    # 单一操作模式
    action: Optional[str] = Field(None, description="单一操作名称")
    params: Optional[Dict[str, Any]] = Field(None, description="单一操作参数")
    
    # 批量操作模式
    actions: Optional[List[TextAction]] = Field(None, description="批量操作列表")
    
    # 通用配置
    sandbox_id: Optional[str] = Field(None, description="沙箱ID（可选）")
    task_name: Optional[str] = Field(None, description="任务名称")
    auto_cleanup: bool = Field(default=False, description="是否自动清理沙箱")

class TextAutomationResponse(BaseModel):
    """文本处理自动化统一响应"""
    success: bool
    message: str
    data: Optional[Any] = None
    sandbox_id: str
    execution_time: float
    results: Optional[List[Dict[str, Any]]] = None

@text_router.post("/automation", response_model=TextAutomationResponse)
async def text_automation(request: TextAutomationRequest):
    """
    文本处理自动化统一接口
    
    支持两种模式：
    1. 单一操作模式：action + params
    2. 批量操作模式：actions列表
    
    用于处理Dify的Function Calling请求
    """
    start_time = time.time()
    
    try:
        # 获取或创建沙箱
        if request.sandbox_id:
            # 先检查是否在持久化沙盒中存在
            if request.sandbox_id in sandbox_manager.persistent_sandboxes:
                # 持久化沙盒存在
                sandbox_id = request.sandbox_id
                should_cleanup = False
                logger.info(f"使用持久化沙盒: {sandbox_id}")
            elif request.sandbox_id in sandbox_manager.sandboxes:
                # 普通沙盒存在
                sandbox_id = request.sandbox_id
                should_cleanup = False
                logger.info(f"使用普通沙盒: {sandbox_id}")
            else:
                # 沙盒不存在
                return TextAutomationResponse(
                    success=False,
                    message=f"指定的沙箱不存在: {request.sandbox_id}",
                    sandbox_id="",
                    execution_time=time.time() - start_time
                )
        else:
            # 创建新沙箱
            create_result = await sandbox_manager.create_sandbox()
            if not create_result["success"]:
                return TextAutomationResponse(
                    success=False,
                    message=f"创建沙箱失败: {create_result.get('message', 'Unknown error')}",
                    sandbox_id="",
                    execution_time=time.time() - start_time
                )
            sandbox_id = create_result["sandbox_id"]
            should_cleanup = True
        
        # 映射方法名到内部方法名
        method_mapping = {
            "parse": "parse_html",
            "extract": "extract_text",
            "filter": "filter_content",
            "clean": "clean_text",
            "links": "extract_links",
            "analyze": "analyze_text"
        }
        
        if request.action and request.params is not None:
            # 单一操作模式
            action = request.action
            params = request.params
            
            # 转换方法名
            internal_method = method_mapping.get(action, action)
            
            logger.info(f"执行单一文本处理操作: {action} -> {internal_method}")
            
            # 检查是否为持久化沙盒
            if sandbox_id in sandbox_manager.persistent_sandboxes:
                # 在持久化沙盒中执行文本工具
                result = await _execute_text_in_persistent_sandbox(
                    sandbox_id=sandbox_id,
                    method=internal_method,
                    params=params
                )
            else:
                # 在普通沙盒中执行
                result = await sandbox_manager.execute_tool(
                    sandbox_id=sandbox_id,
                    tool_type="text",
                    method=internal_method,
                    params=params
                )
            
            # 自动清理
            if request.auto_cleanup or should_cleanup:
                await sandbox_manager.kill_sandbox(sandbox_id)
                
            return TextAutomationResponse(
                success=result["success"],
                message=result.get("message", "Operation completed"),
                data=result.get("data"),
                sandbox_id=sandbox_id,
                execution_time=time.time() - start_time
            )
            
        elif request.actions:
            # 批量操作模式
            task_name = request.task_name or f"文本处理批量操作_{len(request.actions)}步"
            logger.info(f"执行文本处理批量操作: {task_name}")
            
            results = []
            overall_success = True
            
            for i, action in enumerate(request.actions):
                logger.info(f"执行步骤 {i+1}/{len(request.actions)}: {action.method}")
                
                # 转换方法名
                internal_method = method_mapping.get(action.method, action.method)
                
                step_result = await sandbox_manager.execute_tool(
                    sandbox_id=sandbox_id,
                    tool_type="text",
                    method=internal_method,
                    params=action.params
                )
                
                step_info = {
                    "step": i + 1,
                    "method": action.method,
                    "internal_method": internal_method,
                    "description": action.description or f"执行{action.method}",
                    "result": step_result,
                    "success": step_result.get("success", False)
                }
                results.append(step_info)
                
                # 检查必须成功的步骤
                if not step_result.get("success", False) and action.required:
                    overall_success = False
                    logger.error(f"必须步骤失败，停止执行: {action.method}")
                    break
                
                # 步骤延迟
                if action.delay > 0:
                    import asyncio
                    await asyncio.sleep(action.delay)
            
            # 自动清理
            if request.auto_cleanup or should_cleanup:
                await sandbox_manager.kill_sandbox(sandbox_id)
            
            return TextAutomationResponse(
                success=overall_success,
                message=f"批量操作{'成功' if overall_success else '部分失败'}完成",
                data=results[-1]["result"].get("data") if results else None,
                sandbox_id=sandbox_id,
                execution_time=time.time() - start_time,
                results=results
            )
        
        else:
            return TextAutomationResponse(
                success=False,
                message="请求格式错误：必须提供action+params或actions列表",
                sandbox_id=sandbox_id,
                execution_time=time.time() - start_time
            )
            
    except Exception as e:
        logger.error(f"执行文本处理自动化时发生错误: {str(e)}")
        return TextAutomationResponse(
            success=False,
            message=f"执行失败: {str(e)}",
            sandbox_id="",
            execution_time=time.time() - start_time
        )

@text_router.get("/automation/methods", response_model=BaseResponse)
async def get_automation_methods():
    """获取支持的文本处理自动化方法列表"""
    methods = {
        "parse": {
            "internal_method": "parse_html",
            "description": "解析HTML内容，提取结构化信息",
            "params": {
                "html_content": {"type": "string", "required": True, "description": "HTML内容字符串"}
            }
        },
        "extract": {
            "internal_method": "extract_text",
            "description": "从HTML中提取指定选择器的文本",
            "params": {
                "html_content": {"type": "string", "required": True, "description": "HTML内容"},
                "selector": {"type": "string", "required": True, "description": "CSS选择器"}
            }
        },
        "filter": {
            "internal_method": "filter_content",
            "description": "根据关键词筛选文本内容",
            "params": {
                "text_list": {"type": "array", "required": True, "description": "文本列表"},
                "keywords": {"type": "array", "required": True, "description": "关键词列表"},
                "mode": {"type": "string", "default": "any", "description": "筛选模式：any/all/exact"}
            }
        },
        "clean": {
            "internal_method": "clean_text",
            "description": "清理文本：去除多余空格、特殊字符等",
            "params": {
                "text": {"type": "string", "required": True, "description": "待清理的文本"}
            }
        },
        "links": {
            "internal_method": "extract_links",
            "description": "从HTML中提取所有链接",
            "params": {
                "html_content": {"type": "string", "required": True, "description": "HTML内容"},
                "base_url": {"type": "string", "description": "基础URL（可选，用于处理相对链接）"}
            }
        },
        "analyze": {
            "internal_method": "analyze_text",
            "description": "基础文本分析：字数、关键信息等",
            "params": {
                "text": {"type": "string", "required": True, "description": "待分析的文本"}
            }
        }
    }
    
    return BaseResponse(
        success=True,
        message="文本处理自动化方法列表",
        data={
            "methods": methods,
            "total_methods": len(methods),
            "usage_examples": {
                "single_action": {
                    "action": "parse",
                    "params": {"html_content": "<html><head><title>测试</title></head><body><p>内容</p></body></html>"}
                },
                "batch_actions": {
                    "actions": [
                        {
                            "method": "parse",
                            "params": {"html_content": "<html>...</html>"},
                            "description": "解析HTML"
                        },
                        {
                            "method": "clean",
                            "params": {"text": "{{previous_result.data.text_content}}"},
                            "description": "清理提取的文本"
                        },
                        {
                            "method": "analyze",
                            "params": {"text": "{{previous_result.data}}"},
                            "description": "分析文本"
                        }
                    ]
                }
            }
        }
    )
