"""
API 响应构建器工具类
统一处理各种API响应格式，减少重复代码
"""
import time
from typing import Optional


class ApiTimer:
    """API执行时间管理器"""
    
    def __init__(self):
        """初始化并记录开始时间"""
        self.start_time = time.time()
    
    def elapsed(self) -> float:
        """获取已经过的时间"""
        return time.time() - self.start_time
    
    def reset(self) -> float:
        """重置计时器，返回上次重置到现在的时间"""
        elapsed = self.elapsed()
        self.start_time = time.time()
        return elapsed
    
    @classmethod
    def start(cls) -> 'ApiTimer':
        """类方法：创建并返回新的计时器实例"""
        return cls()


class ApiResponseBuilder:
    """API响应构建器，统一处理存储结果和响应格式"""
    
    @staticmethod
    def _get_elapsed_time(timer_or_start_time) -> float:
        """内部方法：从ApiTimer对象或start_time获取执行时间"""
        if isinstance(timer_or_start_time, ApiTimer):
            return timer_or_start_time.elapsed()
        else:
            # 向后兼容：传统的start_time方式
            return time.time() - timer_or_start_time
    
    @staticmethod
    def build_storage_message(storage_result: dict, success_template: str, failure_template: str) -> str:
        """构建存储结果消息"""
        if storage_result.get('success', False):
            return success_template.format(**storage_result)
        else:
            return failure_template.format(**storage_result)
    
    @staticmethod
    def build_batch_api_response(
        storage_result: dict, 
        timer_or_start_time,
        success_template: str,
        failure_template: str,
        extra_data: Optional[dict] = None
    ) -> dict:
        """构建批量API响应格式"""
        message = ApiResponseBuilder.build_storage_message(
            storage_result, success_template, failure_template
        )
        
        execution_time = ApiResponseBuilder._get_elapsed_time(timer_or_start_time)
        
        base_response = {
            "success": storage_result.get('success', False),
            "message": message,
            "data": {
                **storage_result,
                "batch_id": f"batch_{int(time.time())}",
                "stored_at": storage_result.get('stored_at', time.strftime('%Y-%m-%d %H:%M:%S')),
                "execution_time": storage_result.get('execution_time', 0)
            },
            "execution_time": execution_time
        }
        
        # 合并额外数据
        if extra_data:
            base_response["data"].update(extra_data)
            
        return base_response
    
    @staticmethod
    def build_insights_api_response(
        storage_result: dict,
        timer_or_start_time, 
        user_id: str,
        tags_count: int,
        intent_level: str,
        intent_type: str
    ) -> dict:
        """构建客户洞察API响应格式"""
        if storage_result.get('success', False):
            message = f"客户洞察存储成功: 用户 {user_id}, 包含 {storage_result.get('tags_count', tags_count)} 个标签"
        else:
            message = f"客户洞察存储失败: {storage_result.get('message', '未知错误')}"
            
        execution_time = ApiResponseBuilder._get_elapsed_time(timer_or_start_time)
            
        return {
            "success": storage_result.get('success', False),
            "message": message,
            "data": {
                "user_id": user_id,
                "tags_count": tags_count,
                "intent_level": intent_level,
                "intent_type": intent_type,
                "storage_result": storage_result,
                "batch_id": f"insights_{int(time.time())}",
                "stored_at": time.strftime('%Y-%m-%d %H:%M:%S')
            },
            "execution_time": execution_time
        }
    
    @staticmethod
    def build_batch_insights_api_response(
        batch_result: dict,
        timer_or_start_time
    ) -> dict:
        """构建批量客户洞察API响应格式"""
        if batch_result.get('success', False):
            message = f"批量客户洞察存储完成: {batch_result['success_count']}/{batch_result['total']} 个用户成功"
        else:
            message = f"批量客户洞察存储部分失败: {batch_result['success_count']}/{batch_result['total']} 个用户成功"
            
        execution_time = ApiResponseBuilder._get_elapsed_time(timer_or_start_time)
            
        return {
            "success": batch_result.get('success', False),
            "message": message,
            "data": {
                "total_users": batch_result['total'],
                "success_count": batch_result['success_count'], 
                "error_count": batch_result['error_count'],
                "errors": batch_result['errors'],
                "batch_id": f"batch_insights_{int(time.time())}",
                "stored_at": time.strftime('%Y-%m-%d %H:%M:%S')
            },
            "execution_time": execution_time
        }
    
    @staticmethod 
    def build_error_response(error_msg: str, timer_or_start_time, **extra_fields) -> dict:
        """构建错误响应格式"""
        execution_time = ApiResponseBuilder._get_elapsed_time(timer_or_start_time)
        
        return {
            "success": False,
            "message": error_msg,
            "execution_time": execution_time,
            "error": error_msg,
            **extra_fields
        }
    
    @staticmethod
    def build_success_response(
        message: str, 
        timer_or_start_time,
        data: Optional[dict] = None,
        **extra_fields
    ) -> dict:
        """构建成功响应格式"""
        execution_time = ApiResponseBuilder._get_elapsed_time(timer_or_start_time)
        
        response = {
            "success": True,
            "message": message,
            "execution_time": execution_time,
            **extra_fields
        }
        
        if data:
            response["data"] = data
            
        return response
