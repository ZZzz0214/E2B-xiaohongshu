"""
统一错误处理中间件
标准化API错误响应格式
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
import time

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并捕获异常"""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as exc:
            # FastAPI HTTPException - 标准HTTP错误
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "message": exc.detail,
                    "error_type": "http_exception",
                    "status_code": exc.status_code
                }
            )
            
        except Exception as exc:
            # 未捕获的异常 - 服务器内部错误
            process_time = time.time() - start_time
            
            # 记录详细错误信息
            logger.error(
                f"未处理的异常 - {request.method} {request.url.path}\n"
                f"处理时间: {process_time:.2f}s\n"
                f"错误: {str(exc)}\n"
                f"堆栈跟踪: {traceback.format_exc()}"
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "服务器内部错误",
                    "error_type": "internal_server_error",
                    "status_code": 500,
                    "details": str(exc) if request.app.debug else "请联系管理员"
                }
            )

def handle_validation_error(request: Request, exc):
    """处理数据验证错误"""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "请求数据验证失败",
            "error_type": "validation_error",
            "status_code": 422,
            "details": exc.errors()
        }
    )

def create_error_response(
    message: str, 
    status_code: int = 500, 
    error_type: str = "error",
    details: any = None
) -> dict:
    """创建标准错误响应"""
    response = {
        "success": False,
        "message": message,
        "error_type": error_type,
        "status_code": status_code
    }
    
    if details is not None:
        response["details"] = details
        
    return response 