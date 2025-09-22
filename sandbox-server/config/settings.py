"""
E2B Sandbox 浏览器自动化 API 配置文件 - 简化版
"""
import os
from typing import List

class Settings:
    """应用配置类 - 简化版"""
    
    # ==================== 服务器基础配置 ====================
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8989))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ==================== E2B配置 ====================
    # 🔐 安全提示：请通过环境变量设置API密钥，不要硬编码
    E2B_API_KEY: str = os.getenv("E2B_API_KEY", "")
    E2B_TEMPLATE_ID: str = os.getenv("E2B_TEMPLATE_ID", "dgcanzrrlvhyju0asxth")
    E2B_SANDBOX_TIMEOUT: int = int(os.getenv("E2B_SANDBOX_TIMEOUT", "1800"))  # 30分钟默认超时
    
    # ==================== VNC配置 ====================
    VNC_PORT: int = int(os.getenv("VNC_PORT", 5901))
    VNC_WEB_PORT: int = int(os.getenv("VNC_WEB_PORT", 6080))
    DISPLAY: str = os.getenv("DISPLAY", ":1")
    
    # ==================== CORS配置 ====================
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://localhost:8080"
    ).split(",")
    
    @classmethod
    def get_environment_info(cls) -> dict:
        """获取环境配置信息"""
        return {
            "e2b_api_configured": bool(cls.E2B_API_KEY),
            "template_id": cls.E2B_TEMPLATE_ID,
            "display": cls.DISPLAY,
            "vnc_port": cls.VNC_PORT,
            "vnc_web_port": cls.VNC_WEB_PORT,
            "debug_mode": cls.DEBUG
        }
    
    @classmethod
    def validate_config(cls) -> dict:
        """验证配置完整性"""
        issues = []
        
        if not cls.E2B_API_KEY:
            issues.append("E2B_API_KEY 未设置 - 请通过环境变量配置")
        
        if not cls.E2B_TEMPLATE_ID:
            issues.append("E2B_TEMPLATE_ID 未设置")
        
        if cls.DISPLAY != ":1":
            issues.append(f"DISPLAY 配置异常: {cls.DISPLAY} (推荐: :1)")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config_info": cls.get_environment_info()
        }

# 全局配置实例
settings = Settings()
