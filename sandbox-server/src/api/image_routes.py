"""
图片处理 API 路由
提供图片下载和base64转换功能
"""
import base64
import io
import time
import logging
from typing import Optional
import httpx
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from models.request_models import BaseResponse
from utils.api_response_builder import ApiResponseBuilder, ApiTimer

logger = logging.getLogger(__name__)

# 创建路由器
image_router = APIRouter()

class ImageToBase64Request(BaseModel):
    """图片转base64请求模型"""
    image_url: str = Field(
        ..., 
        description="图片URL地址", 
        example="https://xiaohongshu-images.bj.bcebos.com/shared/28/282c1ae75091e244f83b23661aa82a56.jpg"
    )
    format: Optional[str] = Field(
        default="PNG", 
        description="输出图片格式 (PNG, JPEG, WEBP)", 
        example="PNG"
    )
    quality: Optional[int] = Field(
        default=95, 
        description="JPEG质量 (1-100，仅对JPEG格式有效)", 
        ge=1, 
        le=100, 
        example=95
    )
    max_size: Optional[int] = Field(
        default=None, 
        description="图片最大尺寸限制（像素，保持比例缩放）", 
        ge=100, 
        le=4096, 
        example=1920
    )
    timeout: Optional[int] = Field(
        default=30, 
        description="下载超时时间（秒）", 
        ge=5, 
        le=120, 
        example=30
    )

    @validator('format')
    def validate_format(cls, v):
        """验证图片格式"""
        allowed_formats = ['PNG', 'JPEG', 'JPG', 'WEBP']
        if v.upper() not in allowed_formats:
            raise ValueError(f'格式必须是以下之一: {", ".join(allowed_formats)}')
        return v.upper()

    @validator('image_url')
    def validate_image_url(cls, v):
        """验证图片URL"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('图片URL必须以http://或https://开头')
        return v

class ImageToBase64Response(BaseModel):
    """图片转base64响应模型"""
    success: bool
    message: str
    data: Optional[dict] = None
    execution_time: float

class ImageInfo(BaseModel):
    """图片信息模型"""
    original_url: str
    original_format: str
    original_size: tuple
    final_format: str
    final_size: tuple
    file_size_bytes: int
    base64_length: int
    base64_data: str

async def download_image(url: str, timeout: int = 30, max_retries: int = 3) -> bytes:
    """
    下载图片
    
    Args:
        url: 图片URL
        timeout: 超时时间
        
    Returns:
        图片的二进制数据
        
    Raises:
        HTTPException: 下载失败时抛出异常
    """
    # 针对OSS对象存储的简化请求头配置
    header_configs = [
        # 配置1：最基础的请求头（适合OSS）
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/*,*/*;q=0.8'
        },
        # 配置2：无User-Agent（完全基础）
        {
            'Accept': '*/*'
        },
        # 配置3：空请求头（让httpx使用默认）
        {}
    ]
    
    for attempt in range(max_retries):
        for config_idx, headers in enumerate(header_configs):
            try:
                logger.info(f"尝试下载图片 (第{attempt+1}次，配置{config_idx+1})")
                logger.info(f"使用请求头: {headers}")
                logger.info(f"完整URL: {url}")
                
                # 创建简单的客户端（适合OSS对象存储）
                async with httpx.AsyncClient(
                    timeout=timeout, 
                    follow_redirects=True
                ) as client:
                    response = await client.get(url, headers=headers)
                    
                    # 记录详细响应信息
                    logger.info(f"HTTP响应: {response.status_code} {response.reason_phrase}")
                    logger.info(f"响应头: {dict(response.headers)}")
                    
                    # 如果是400错误，记录更多信息并尝试下一个配置
                    if response.status_code == 400:
                        logger.error(f"400错误详情: {response.text[:500]}")
                        if config_idx < len(header_configs) - 1:
                            logger.warning(f"配置{config_idx+1}返回400，尝试下一个配置...")
                            continue
                    
                    response.raise_for_status()
                    
                    # 检查内容类型
                    content_type = response.headers.get('content-type', '')
                    logger.info(f"响应内容类型: {content_type}")
                    
                    if not content_type.startswith('image/'):
                        logger.warning(f"警告：响应的内容类型不是图片: {content_type}")
                        # 但仍然继续处理，可能是服务器配置问题
                    
                    logger.info(f"图片下载成功，大小: {len(response.content)} bytes")
                    return response.content
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP错误 (配置{config_idx+1}): {e.response.status_code} {e.response.reason_phrase}")
                if config_idx == len(header_configs) - 1:  # 最后一个配置也失败了
                    if attempt < max_retries - 1:  # 还有重试机会
                        logger.info(f"等待重试... ({attempt+1}/{max_retries})")
                        import asyncio
                        await asyncio.sleep(1)  # 等待1秒后重试
                        break
                continue
            
            except Exception as e:
                logger.error(f"下载异常 (配置{config_idx+1}): {str(e)}")
                continue
            
    # 所有重试和配置都失败了
    error_msg = f"下载图片失败，已尝试{max_retries}次，使用了{len(header_configs)}种配置: {url[:100]}..."
    logger.error(error_msg)
    raise HTTPException(status_code=400, detail=error_msg)

def process_image(image_data: bytes, output_format: str = "PNG", quality: int = 95, max_size: Optional[int] = None) -> tuple[bytes, dict]:
    """
    处理图片：格式转换、尺寸调整等
    
    Args:
        image_data: 原始图片数据
        output_format: 输出格式
        quality: JPEG质量
        max_size: 最大尺寸限制
        
    Returns:
        (处理后的图片数据, 图片信息字典)
    """
    try:
        # 打开图片
        with Image.open(io.BytesIO(image_data)) as img:
            original_format = img.format or "UNKNOWN"
            original_size = img.size
            
            logger.info(f"原始图片信息: 格式={original_format}, 尺寸={original_size}")
            
            # 转换为RGB模式（如果需要）
            if output_format in ["JPEG", "JPG"] and img.mode in ["RGBA", "P"]:
                # JPEG不支持透明度，转换为RGB
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif output_format == "PNG" and img.mode not in ["RGBA", "RGB", "L"]:
                # 确保PNG格式兼容性
                img = img.convert("RGBA")
            
            # 尺寸调整
            final_size = original_size
            if max_size and max(original_size) > max_size:
                # 保持宽高比的缩放
                ratio = max_size / max(original_size)
                new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                final_size = new_size
                logger.info(f"图片已缩放至: {final_size}")
            
            # 保存处理后的图片
            output_buffer = io.BytesIO()
            save_kwargs = {"format": output_format}
            
            if output_format in ["JPEG", "JPG"]:
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            elif output_format == "PNG":
                save_kwargs["optimize"] = True
            
            img.save(output_buffer, **save_kwargs)
            processed_data = output_buffer.getvalue()
            
            # 构建图片信息
            image_info = {
                "original_format": original_format,
                "original_size": original_size,
                "final_format": output_format,
                "final_size": final_size,
                "file_size_bytes": len(processed_data)
            }
            
            logger.info(f"图片处理完成: 输出格式={output_format}, 最终尺寸={final_size}, 文件大小={len(processed_data)} bytes")
            
            return processed_data, image_info
            
    except Exception as e:
        error_msg = f"图片处理失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

def image_to_base64(image_data: bytes, image_format: str = "PNG") -> dict:
    """
    将图片数据转换为base64编码
    
    Args:
        image_data: 图片二进制数据
        image_format: 图片格式
        
    Returns:
        包含多种base64格式的字典
    """
    try:
        # 转换为base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        # 构建MIME类型
        mime_type_map = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg", 
            "WEBP": "image/webp"
        }
        mime_type = mime_type_map.get(image_format.upper(), "image/png")
        
        # 构建data URL格式
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        logger.info(f"Base64转换完成，长度: {len(base64_data)} 字符")
        
        # 返回多种格式
        return {
            "base64": base64_data,              # 纯base64编码
            "data_url": data_url,               # 完整Data URL格式
            "mime_type": mime_type              # MIME类型
        }
        
    except Exception as e:
        error_msg = f"Base64转换失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@image_router.post("/url-to-base64", response_model=ImageToBase64Response)
async def convert_url_to_base64(request: ImageToBase64Request):
    """
    将图片URL转换为base64编码
    
    支持的图片格式：PNG, JPEG, WEBP等主流格式
    支持图片尺寸调整和质量控制
    自动处理各种图片源，包括小红书等平台的图片
    """
    timer = ApiTimer.start()
    
    try:
        logger.info(f"开始处理图片转base64请求: {request.image_url}")
        
        # 步骤1：下载图片
        image_data = await download_image(request.image_url, request.timeout)
        
        # 步骤2：处理图片
        processed_data, image_info = process_image(
            image_data=image_data,
            output_format=request.format,
            quality=request.quality,
            max_size=request.max_size
        )
        
        # 步骤3：转换为base64
        base64_result = image_to_base64(processed_data, request.format)
        
        # 构建完整响应数据
        response_data = {
            "original_url": request.image_url,
            "base64": base64_result["base64"],           # 纯base64编码
            "base64_data": base64_result["data_url"],    # Data URL格式（兼容性）
            "data_url": base64_result["data_url"],       # Data URL格式
            "mime_type": base64_result["mime_type"],     # MIME类型
            "image_info": {
                **image_info,
                "base64_length": len(base64_result["base64"]),
                "data_url_length": len(base64_result["data_url"])
            },
            "processing_info": {
                "requested_format": request.format,
                "requested_quality": request.quality if request.format in ["JPEG", "JPG"] else None,
                "requested_max_size": request.max_size,
                "timeout": request.timeout
            }
        }
        
        success_msg = f"图片转换成功：{image_info['original_format']} -> {request.format}, " \
                     f"尺寸 {image_info['original_size']} -> {image_info['final_size']}, " \
                     f"文件大小 {image_info['file_size_bytes']} bytes"
        
        return ApiResponseBuilder.build_success_response(
            message=success_msg,
            timer_or_start_time=timer,
            data=response_data
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        error_msg = f"图片转base64失败: {str(e)}"
        logger.error(error_msg)
        return ApiResponseBuilder.build_error_response(
            error_msg=error_msg,
            timer_or_start_time=timer
        )

@image_router.get("/supported-formats")
async def get_supported_formats():
    """获取支持的图片格式列表"""
    return BaseResponse(
        success=True,
        message="支持的图片格式列表",
        data={
            "input_formats": [
                "JPEG", "JPG", "PNG", "WEBP", "BMP", "GIF", "TIFF", "ICO"
            ],
            "output_formats": [
                {
                    "format": "PNG",
                    "description": "便携式网络图形，支持透明度，无损压缩",
                    "supports_transparency": True,
                    "supports_quality": False
                },
                {
                    "format": "JPEG",
                    "description": "联合图像专家组格式，有损压缩，文件较小",
                    "supports_transparency": False,
                    "supports_quality": True,
                    "quality_range": "1-100"
                },
                {
                    "format": "WEBP",
                    "description": "Google开发的现代图像格式，压缩率高",
                    "supports_transparency": True,
                    "supports_quality": True,
                    "quality_range": "1-100"
                }
            ],
            "features": {
                "auto_format_detection": True,
                "size_optimization": True,
                "quality_control": True,
                "transparency_preservation": True,
                "batch_processing": False
            },
            "limits": {
                "max_file_size": "50MB",
                "max_dimensions": "4096x4096",
                "timeout_range": "5-120 seconds"
            }
        }
    )

@image_router.get("/health")
async def image_service_health():
    """图片服务健康检查"""
    return BaseResponse(
        success=True,
        message="图片处理服务运行正常",
        data={
            "service": "图片处理服务",
            "version": "1.0.0",
            "status": "healthy",
            "timestamp": time.time(),
            "features": [
                "URL图片下载",
                "Base64编码转换", 
                "格式转换",
                "尺寸调整",
                "质量控制"
            ]
        }
    )
